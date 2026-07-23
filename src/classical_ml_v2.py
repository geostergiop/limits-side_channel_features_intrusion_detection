#!/usr/bin/env python3
"""
Phase 3: Classical ML baselines over the five ESORICS side-channel features.

The evaluation protocol freezes deterministic cohort/split manifests once and
reuses them across Phase 2, Phase 3, and later reruns. Reporting is based on
repeated grouped train/validation/test holdouts with mean, standard deviation,
and 95% confidence intervals.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from tabulate import tabulate

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import ML_CONFIG, RESULTS_DIR, SIDE_CHANNEL_FEATURES
from src.database import get_db
from src.splits import (
    build_repeated_grouped_holdout_manifest,
    group_shuffle_split_unlabeled,
    load_manifest,
    materialize_repeated_grouped_holdout_splits,
    resolve_group_column,
    save_manifest,
)


FEATURE_COLS = list(SIDE_CHANNEL_FEATURES)
BOOSTER_ALGORITHMS = {"XGBClassifier", "LGBMClassifier"}
SPLIT_MANIFEST_DIR = RESULTS_DIR / ML_CONFIG.get("split_manifest_dir", "split_manifests")
SPLIT_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


class MissingDependencyError(RuntimeError):
    """Raised when an optional local ML dependency is unavailable."""


# ============================================================================
# DATA LOADING
# ============================================================================

def _build_packet_query(
    select_clause: str,
    *,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
    order_by_packet_id: bool = True,
) -> tuple[str, list]:
    query = f"""
        SELECT
            {select_clause}
        FROM packets p
        INNER JOIN sessions s ON (p.session_id = s.id)
    """
    conditions: list[str] = []
    params: list = []

    if encrypted_only:
        conditions.append("s.is_encrypted = 1")
    if is_malicious is not None:
        conditions.append("p.is_malicious = ?")
        params.append(int(is_malicious))
    if exclude_families:
        placeholders = ",".join("?" for _ in exclude_families)
        conditions.append(
            f"(s.malware_family NOT IN ({placeholders}) OR p.is_malicious = 0)"
        )
        params.extend(exclude_families)
    if include_families:
        placeholders = ",".join("?" for _ in include_families)
        conditions.append(
            f"(s.malware_family IN ({placeholders}) OR p.is_malicious = 0)"
        )
        params.extend(include_families)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if order_by_packet_id:
        query += " ORDER BY p.id"
    return query, params


def _feature_select_clause() -> str:
    return """
        p.id AS packet_id,
        p.session_id,
        s.dataset_id,
        p.packet_size,
        p.payload_size,
        p.payload_ratio,
        p.ratio_to_prev,
        p.time_diff,
        p.is_malicious,
        s.malware_family,
        s.is_encrypted
    """


def sample_packet_ids(
    conn,
    *,
    sample_size: int | None,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
    seed: int | None = None,
) -> list[int]:
    """
    Deterministically sample packet ids with reservoir sampling.

    This avoids SQL-level random ordering and gives a frozen, reproducible cohort
    when the sampled ids are written into a manifest.
    """
    query, params = _build_packet_query(
        "p.id AS packet_id",
        encrypted_only=encrypted_only,
        exclude_families=exclude_families,
        include_families=include_families,
        is_malicious=is_malicious,
        order_by_packet_id=True,
    )
    cursor = conn.execute(query, params if params else [])
    if sample_size is None:
        return [int(row[0]) for row in cursor]

    target_size = int(sample_size)
    if target_size <= 0:
        return []

    rng = np.random.default_rng(
        ML_CONFIG["random_state"] if seed is None else int(seed)
    )
    reservoir: list[int] = []
    for seen, (packet_id,) in enumerate(cursor, start=1):
        packet_id = int(packet_id)
        if len(reservoir) < target_size:
            reservoir.append(packet_id)
            continue
        slot = int(rng.integers(0, seen))
        if slot < target_size:
            reservoir[slot] = packet_id
    reservoir.sort()
    return reservoir


def load_packet_features_for_ids(conn, packet_ids: list[int]) -> pd.DataFrame:
    columns = [
        "packet_id",
        "session_id",
        "dataset_id",
        "packet_size",
        "payload_size",
        "payload_ratio",
        "ratio_to_prev",
        "time_diff",
        "is_malicious",
        "malware_family",
        "is_encrypted",
    ]
    if not packet_ids:
        return pd.DataFrame(columns=columns)

    table_name = "_selected_packet_ids"
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(
        f"CREATE TEMP TABLE {table_name} (packet_id INTEGER PRIMARY KEY, ord INTEGER NOT NULL)"
    )
    try:
        conn.executemany(
            f"INSERT INTO {table_name} (packet_id, ord) VALUES (?, ?)",
            ((int(packet_id), idx) for idx, packet_id in enumerate(packet_ids)),
        )
        query = f"""
            SELECT
                q.packet_id,
                p.session_id,
                s.dataset_id,
                p.packet_size,
                p.payload_size,
                p.payload_ratio,
                p.ratio_to_prev,
                p.time_diff,
                p.is_malicious,
                s.malware_family,
                s.is_encrypted
            FROM {table_name} q
            INNER JOIN packets p ON (p.id = q.packet_id)
            INNER JOIN sessions s ON (p.session_id = s.id)
            ORDER BY q.ord
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    ordered_ids = [int(x) for x in df["packet_id"].tolist()]
    if ordered_ids != [int(x) for x in packet_ids]:
        raise RuntimeError("Reloaded packet cohort does not match manifest packet_id order")
    return df


def load_packet_features(
    conn,
    sample_size: int | None = None,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Deterministically load packet-level side-channel features plus grouping columns.
    """
    if sample_size is None:
        query, params = _build_packet_query(
            _feature_select_clause(),
            encrypted_only=encrypted_only,
            exclude_families=exclude_families,
            include_families=include_families,
            is_malicious=is_malicious,
            order_by_packet_id=True,
        )
        return pd.read_sql_query(query, conn, params=params if params else None)

    packet_ids = sample_packet_ids(
        conn,
        sample_size=sample_size,
        encrypted_only=encrypted_only,
        exclude_families=exclude_families,
        include_families=include_families,
        is_malicious=is_malicious,
        seed=seed,
    )
    return load_packet_features_for_ids(conn, packet_ids)


# ============================================================================
# MODELS
# ============================================================================

def get_algorithm(name: str, **overrides):
    seed = ML_CONFIG["random_state"]
    base_algos = {
        "LogisticRegression": {
            "factory": LogisticRegression,
            "params": {"max_iter": 1000, "random_state": seed},
        },
        "LinearDiscriminantAnalysis": {
            "factory": LinearDiscriminantAnalysis,
            "params": {},
        },
        "KNeighborsClassifier": {
            "factory": KNeighborsClassifier,
            "params": {"n_neighbors": 5},
        },
        "DecisionTreeClassifier": {
            "factory": DecisionTreeClassifier,
            "params": {"random_state": seed},
        },
        "RandomForestClassifier": {
            "factory": RandomForestClassifier,
            "params": {"n_estimators": 300, "random_state": seed, "n_jobs": -1},
        },
        "GaussianNB": {
            "factory": GaussianNB,
            "params": {},
        },
        "SVC": {
            "factory": SVC,
            "params": {"kernel": "rbf", "random_state": seed, "max_iter": 5000},
        },
        "MLPClassifier": {
            "factory": MLPClassifier,
            "params": {
                "hidden_layer_sizes": (100,),
                "max_iter": 500,
                "random_state": seed,
            },
        },
    }
    if name in base_algos:
        spec = base_algos[name]
        params = {**spec["params"], **overrides}
        return spec["factory"](**params)

    if name == "XGBClassifier":
        try:
            from xgboost import XGBClassifier
        except ImportError as e:
            raise MissingDependencyError(
                "XGBoost is not installed. Run `pip install xgboost` or `pip install -r requirements.txt`."
            ) from e
        params = {
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "random_state": seed,
            "n_jobs": -1,
        }
        params.update(overrides)
        return XGBClassifier(**params)

    if name == "LGBMClassifier":
        try:
            from lightgbm import LGBMClassifier
        except ImportError as e:
            raise MissingDependencyError(
                "LightGBM is not installed. Run `pip install lightgbm` or `pip install -r requirements.txt`."
            ) from e
        params = {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": seed,
            "n_jobs": -1,
            "verbose": -1,
            "deterministic": True,
            "force_col_wise": True,
        }
        params.update(overrides)
        return LGBMClassifier(**params)
    return None


SHORT_NAMES = {
    "LogisticRegression": "LR",
    "LinearDiscriminantAnalysis": "LDA",
    "KNeighborsClassifier": "KNN",
    "DecisionTreeClassifier": "CART",
    "RandomForestClassifier": "RF",
    "XGBClassifier": "XGB",
    "LGBMClassifier": "LGBM",
    "GaussianNB": "NB",
    "SVC": "SVC",
    "MLPClassifier": "MLP",
}


def ensure_algorithms_available(algorithms: list[str]) -> None:
    issues: list[str] = []
    seen: set[str] = set()
    for algo_name in algorithms:
        if algo_name in seen:
            continue
        seen.add(algo_name)
        try:
            model = get_algorithm(algo_name)
            if model is None:
                issues.append(f"Unknown algorithm: {algo_name}")
        except MissingDependencyError as e:
            issues.append(str(e))
    if issues:
        raise RuntimeError(
            "Local baseline prerequisites are incomplete:\n  - " +
            "\n  - ".join(issues)
        )


# ============================================================================
# HELPERS
# ============================================================================

def _prepare_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    X = df[FEATURE_COLS].values.astype(float)
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
    y = df["is_malicious"].astype(int).values
    return X, y


def _as_feature_frame(array: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(array, columns=FEATURE_COLS)


def _fit_model_with_safe_n_jobs(model, X, y, **fit_kwargs):
    """
    Fit a model, falling back to single-threaded execution when joblib workers
    are blocked by the local Windows runtime.
    """
    try:
        model.fit(X, y, **fit_kwargs)
        return model
    except PermissionError:
        params = model.get_params(deep=False) if hasattr(model, "get_params") else {}
        n_jobs = params.get("n_jobs")
        if n_jobs in (None, 1):
            raise
        model.set_params(n_jobs=1)
        model.fit(X, y, **fit_kwargs)
        return model


def _split_type_label(group_by: str) -> str:
    return f"{group_by}_repeated_group_holdout"


def _balanced_concat(parts: list[pd.DataFrame]) -> pd.DataFrame:
    parts = [p for p in parts if p is not None and len(p) > 0]
    if not parts:
        return pd.DataFrame()
    return (
        pd.concat(parts, ignore_index=True)
        .sample(frac=1.0, random_state=ML_CONFIG["random_state"])
        .reset_index(drop=True)
    )


def _normalise_family_list(values: list[str] | None) -> list[str]:
    return sorted(str(v) for v in (values or []))


def _cohort_filters(
    *,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
) -> dict:
    return {
        "encrypted_only": bool(encrypted_only),
        "exclude_families": _normalise_family_list(exclude_families),
        "include_families": _normalise_family_list(include_families),
        "is_malicious": None if is_malicious is None else int(is_malicious),
    }


def _seed_from_text(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _manifest_path(experiment_key: str, suffix_payload: dict) -> Path:
    spec_hash = hashlib.sha256(
        json.dumps(suffix_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    safe_key = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in experiment_key)
    return SPLIT_MANIFEST_DIR / f"{safe_key}__{spec_hash}.json"


def _metric_stats(
    values: list[float],
    *,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
) -> tuple[float, float, float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    if len(arr) <= 1:
        return mean, 0.0, mean, mean, 0.0
    std = float(np.std(arr, ddof=1))
    ci95 = 1.96 * std / math.sqrt(len(arr))
    low = mean - ci95
    high = mean + ci95
    if lower_bound is not None:
        low = max(low, lower_bound)
    if upper_bound is not None:
        high = min(high, upper_bound)
    half_width = max(mean - low, high - mean)
    return mean, std, low, high, half_width


def _compute_binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision_0": float(precision_score(y_true, y_pred, pos_label=0, zero_division=0)),
        "precision_1": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_0": float(recall_score(y_true, y_pred, pos_label=0, zero_division=0)),
        "recall_1": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_0": float(f1_score(y_true, y_pred, pos_label=0, zero_division=0)),
        "f1_1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "test_support_0": int(tn + fp),
        "test_support_1": int(tp + fn),
    }


def _fit_booster_with_validation(
    algo_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[int, dict]:
    early_rounds = int(ML_CONFIG.get("early_stopping_rounds", 30))

    if algo_name == "XGBClassifier":
        model = get_algorithm(
            algo_name,
            early_stopping_rounds=early_rounds,
        )
        _fit_model_with_safe_n_jobs(
            model,
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        best_iteration = getattr(model, "best_iteration", None)
        best_n_estimators = int(best_iteration) + 1 if best_iteration is not None else int(model.get_params()["n_estimators"])
        best_n_estimators = max(best_n_estimators, 1)
        return best_n_estimators, {
            "validation_only_early_stopping": True,
            "early_stopping_rounds": early_rounds,
            "best_iteration": None if best_iteration is None else int(best_iteration),
            "best_n_estimators": best_n_estimators,
            "best_score": None if getattr(model, "best_score", None) is None else float(model.best_score),
        }

    if algo_name == "LGBMClassifier":
        from lightgbm import early_stopping

        model = get_algorithm(algo_name)
        _fit_model_with_safe_n_jobs(
            model,
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="binary_logloss",
            callbacks=[early_stopping(early_rounds, verbose=False)],
        )
        best_iteration = getattr(model, "best_iteration_", None)
        if best_iteration is None:
            best_iteration = getattr(model, "n_estimators_", None)
        if best_iteration is None:
            best_iteration = model.get_params()["n_estimators"]
        best_n_estimators = max(int(best_iteration), 1)
        return best_n_estimators, {
            "validation_only_early_stopping": True,
            "early_stopping_rounds": early_rounds,
            "best_iteration": int(best_iteration),
            "best_n_estimators": best_n_estimators,
            "best_score": None,
        }

    raise ValueError(f"Early stopping is only defined for boosters, got {algo_name}")


def _train_and_evaluate_repeat(
    algo_name: str,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict:
    X_train, y_train = _prepare_matrix(train_df)
    X_val, y_val = _prepare_matrix(validation_df)
    X_test, y_test = _prepare_matrix(test_df)
    train_val_df = pd.concat([train_df, validation_df], ignore_index=True)
    X_train_val, y_train_val = _prepare_matrix(train_val_df)

    early_info: dict = {
        "validation_only_early_stopping": False,
        "early_stopping_rounds": 0,
        "best_iteration": None,
        "best_n_estimators": None,
        "best_score": None,
    }

    train_start = time.time()
    if algo_name in BOOSTER_ALGORITHMS:
        validation_scaler = StandardScaler()
        X_train_s = _as_feature_frame(validation_scaler.fit_transform(X_train))
        X_val_s = _as_feature_frame(validation_scaler.transform(X_val))
        best_n_estimators, early_info = _fit_booster_with_validation(
            algo_name,
            X_train_s,
            y_train,
            X_val_s,
            y_val,
        )

        final_scaler = StandardScaler()
        X_train_val_s = _as_feature_frame(final_scaler.fit_transform(X_train_val))
        X_test_s = _as_feature_frame(final_scaler.transform(X_test))
        model = get_algorithm(algo_name, n_estimators=best_n_estimators)
        _fit_model_with_safe_n_jobs(model, X_train_val_s, y_train_val)
    else:
        final_scaler = StandardScaler()
        X_train_val_s = _as_feature_frame(final_scaler.fit_transform(X_train_val))
        X_test_s = _as_feature_frame(final_scaler.transform(X_test))
        model = get_algorithm(algo_name)
        if model is None:
            raise ValueError(f"Unknown algorithm: {algo_name}")
        _fit_model_with_safe_n_jobs(model, X_train_val_s, y_train_val)

    train_time = time.time() - train_start
    predict_start = time.time()
    y_pred = model.predict(X_test_s)
    predict_time = time.time() - predict_start

    metrics = _compute_binary_metrics(y_test, y_pred)
    metrics.update(
        {
            "train_time_s": float(train_time),
            "predict_time_s": float(predict_time),
            **early_info,
        }
    )
    return metrics


SUMMARY_NUMERIC_FIELDS = [
    "accuracy",
    "test_size",
    "validation_size",
    "tp",
    "fp",
    "fn",
    "tn",
    "precision_0",
    "precision_1",
    "recall_0",
    "recall_1",
    "f1_0",
    "f1_1",
    "train_time_s",
    "predict_time_s",
    "test_support_0",
    "test_support_1",
    "n_train_packets",
    "n_validation_packets",
    "n_test_packets",
    "n_train_groups",
    "n_validation_groups",
    "n_test_groups",
    "train_positive_rate",
    "validation_positive_rate",
    "test_positive_rate",
]


BOUNDED_SUMMARY_FIELDS = {
    "accuracy",
    "test_size",
    "validation_size",
    "precision_0",
    "precision_1",
    "recall_0",
    "recall_1",
    "f1_0",
    "f1_1",
    "train_positive_rate",
    "validation_positive_rate",
    "test_positive_rate",
}


def _complete_numeric_values(rows: list[dict], field: str, expected_repeats: int) -> list[float] | None:
    """Return numeric values only when every repeat has a real value for field."""
    values: list[float] = []
    for row in rows:
        if field not in row:
            return None
        value = row[field]
        if value is None or pd.isna(value):
            return None
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return None
    if len(values) != expected_repeats:
        return None
    return values


def _summarise_repeat_rows(
    rows: list[dict],
    *,
    expected_repeats: int,
) -> dict | None:
    if len(rows) != expected_repeats:
        return None

    first = rows[0]
    summary = {
        key: value
        for key, value in first.items()
        if key not in {
            "record_type",
            "repeat_index",
            "outer_seed",
            "inner_seed",
            "malicious_seed",
            "normal_outer_seed",
            "normal_inner_seed",
            "error",
        }
        and key not in SUMMARY_NUMERIC_FIELDS
    }
    summary["record_type"] = "summary"
    summary["n_repeats"] = int(expected_repeats)

    for field in SUMMARY_NUMERIC_FIELDS:
        values = _complete_numeric_values(rows, field, expected_repeats)
        if values is None:
            continue
        mean, std, low, high, half_width = _metric_stats(
            values,
            lower_bound=0.0 if field in BOUNDED_SUMMARY_FIELDS else None,
            upper_bound=1.0 if field in BOUNDED_SUMMARY_FIELDS else None,
        )
        summary[field] = mean
        summary[f"{field}_std"] = std
        summary[f"{field}_ci95_low"] = low
        summary[f"{field}_ci95_high"] = high
        summary[f"{field}_ci95"] = half_width

    best_estimators = [
        int(row["best_n_estimators"])
        for row in rows
        if row.get("best_n_estimators") is not None
    ]
    if best_estimators:
        mean, std, low, high, half_width = _metric_stats(best_estimators)
        summary["best_n_estimators"] = mean
        summary["best_n_estimators_std"] = std
        summary["best_n_estimators_ci95_low"] = low
        summary["best_n_estimators_ci95_high"] = high
        summary["best_n_estimators_ci95"] = half_width

    return summary


def _format_mean_std(row: dict, key: str, digits: int = 4) -> str:
    if f"{key}_std" in row:
        return f"{row.get(key, 0):.{digits}f} +/- {row.get(f'{key}_std', 0):.{digits}f}"
    return f"{row.get(key, 0):.{digits}f}"


def _format_ci(row: dict, key: str, digits: int = 4) -> str:
    low_key = f"{key}_ci95_low"
    high_key = f"{key}_ci95_high"
    if low_key in row and high_key in row:
        return f"[{row[low_key]:.{digits}f}, {row[high_key]:.{digits}f}]"
    return "N/A"


def _rows_for_experiment(results: list[dict], experiment: str) -> list[dict]:
    summaries = [
        row for row in results
        if row.get("experiment") == experiment
        and row.get("record_type") == "summary"
        and "error" not in row
    ]
    if summaries:
        return summaries
    return [
        row for row in results
        if row.get("experiment") == experiment
        and row.get("record_type") == "repeat"
        and "error" not in row
    ]


def _evaluate_repeated_splits(
    *,
    experiment_name: str,
    algorithms: list[str],
    group_by: str,
    manifest: dict,
    manifest_path: Path | None,
    materialized_splits: list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    raise_on_error: bool = False,
    extra_static_fields: dict | None = None,
) -> list[dict]:
    group_col = manifest["group_col"]
    split_type = manifest["split_type"]
    expected_repeats = len(materialized_splits)
    extra_static_fields = extra_static_fields or {}
    if expected_repeats == 0:
        return []

    print(f"\n{'=' * 70}")
    print(f"Experiment: {experiment_name}")
    protocol_bits = [f"repeats={expected_repeats}"]
    if manifest.get("manifest_kind") == "repeated_grouped_holdout":
        protocol_bits.append(f"test_size={manifest.get('test_size', 0):.2f}")
    elif manifest.get("normal_test_fraction") is not None:
        protocol_bits.append(f"normal_test_fraction={manifest.get('normal_test_fraction', 0):.2f}")
    protocol_bits.append(
        f"validation_size(within train+val)={manifest.get('validation_size', 0):.2f}"
    )
    print(f"Protocol: {split_type} on {group_col} | " + " | ".join(protocol_bits))
    print(
        f"Cohort: {manifest.get('cohort_size', 0)} packets | "
        f"cohort_hash={manifest.get('cohort_hash', 'n/a')} | "
        f"manifest={manifest_path.name if manifest_path else 'ephemeral'}"
    )
    print(f"{'=' * 70}")

    repeat_rows: list[dict] = []
    summary_rows: list[dict] = []
    error_rows: list[dict] = []

    for algo_name in algorithms:
        short = SHORT_NAMES.get(algo_name, algo_name)
        print(f"\n  Training {short} across {expected_repeats} repeats...", end=" ", flush=True)
        algo_rows: list[dict] = []
        algo_failed = False

        for repeat_meta, train_df, validation_df, test_df in materialized_splits:
            total_packets = (
                int(repeat_meta["n_train_packets"])
                + int(repeat_meta["n_validation_packets"])
                + int(repeat_meta["n_test_packets"])
            )
            train_val_packets = int(repeat_meta["n_train_packets"]) + int(repeat_meta["n_validation_packets"])
            base_row = {
                "experiment": experiment_name,
                "algorithm": short,
                "split_type": split_type,
                "group_col": group_col,
                "record_type": "repeat",
                "repeat_index": int(repeat_meta["repeat_index"]),
                "manifest_path": str(manifest_path.resolve()) if manifest_path else None,
                "manifest_hash": manifest.get("manifest_hash"),
                "cohort_hash": manifest.get("cohort_hash"),
                "protocol_version": ML_CONFIG.get("manifest_protocol_version"),
                "n_repeats": int(expected_repeats),
                "test_size": (int(repeat_meta["n_test_packets"]) / total_packets) if total_packets else 0.0,
                "validation_size": (int(repeat_meta["n_validation_packets"]) / train_val_packets) if train_val_packets else 0.0,
                "n_train_packets": int(repeat_meta["n_train_packets"]),
                "n_validation_packets": int(repeat_meta["n_validation_packets"]),
                "n_test_packets": int(repeat_meta["n_test_packets"]),
                "n_train_groups": int(repeat_meta["n_train_groups"]),
                "n_validation_groups": int(repeat_meta["n_validation_groups"]),
                "n_test_groups": int(repeat_meta["n_test_groups"]),
                "train_positive_rate": float(repeat_meta["train_positive_rate"]),
                "validation_positive_rate": float(repeat_meta["validation_positive_rate"]),
                "test_positive_rate": float(repeat_meta["test_positive_rate"]),
                **extra_static_fields,
            }
            for seed_key in [
                "outer_seed",
                "inner_seed",
                "malicious_seed",
                "normal_outer_seed",
                "normal_inner_seed",
            ]:
                if seed_key in repeat_meta:
                    base_row[seed_key] = int(repeat_meta[seed_key])

            try:
                result = _train_and_evaluate_repeat(
                    algo_name,
                    train_df,
                    validation_df,
                    test_df,
                )
                algo_rows.append({**base_row, **result})
            except MissingDependencyError as e:
                if raise_on_error:
                    raise
                algo_failed = True
                error_rows.append({**base_row, "record_type": "error", "accuracy": 0.0, "error": str(e)})
                break
            except Exception as e:
                if raise_on_error:
                    raise
                algo_failed = True
                error_rows.append({**base_row, "record_type": "error", "accuracy": 0.0, "error": str(e)})
                continue

        repeat_rows.extend(algo_rows)
        summary = None if algo_failed else _summarise_repeat_rows(algo_rows, expected_repeats=expected_repeats)
        if summary is not None:
            summary_rows.append(summary)
            print(
                f"Acc={summary['accuracy']:.4f} +/- {summary.get('accuracy_std', 0):.4f}  "
                f"F1(mal)={summary['f1_1']:.4f} +/- {summary.get('f1_1_std', 0):.4f}  "
                f"CI95={_format_ci(summary, 'accuracy')}"
            )
        else:
            print("[INCOMPLETE]")

    return repeat_rows + summary_rows + error_rows


def load_or_create_standard_manifest(
    conn,
    *,
    experiment_key: str,
    group_by: str,
    sample_size: int,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
) -> tuple[pd.DataFrame, dict, Path]:
    group_col = resolve_group_column(group_by)
    filters = _cohort_filters(
        encrypted_only=encrypted_only,
        exclude_families=exclude_families,
        include_families=include_families,
        is_malicious=is_malicious,
    )
    spec_payload = {
        "protocol_version": ML_CONFIG.get("manifest_protocol_version"),
        "experiment_key": experiment_key,
        "group_by": group_by,
        "group_col": group_col,
        "sample_size": int(sample_size),
        "filters": filters,
        "random_state": int(ML_CONFIG["random_state"]),
        "repeats": int(ML_CONFIG["repeated_holdout_repeats"]),
        "test_size": float(ML_CONFIG["test_size"]),
        "validation_size": float(ML_CONFIG["validation_size"]),
        "max_attempts": int(ML_CONFIG["max_split_attempts_per_repeat"]),
    }
    manifest_path = _manifest_path(f"{experiment_key}_{group_by}", spec_payload)
    if manifest_path.exists():
        manifest = load_manifest(manifest_path, expected_kind="repeated_grouped_holdout")
        df = load_packet_features_for_ids(conn, [int(x) for x in manifest["cohort_packet_ids"]])
        return df, manifest, manifest_path

    packet_ids = sample_packet_ids(
        conn,
        sample_size=sample_size,
        encrypted_only=encrypted_only,
        exclude_families=exclude_families,
        include_families=include_families,
        is_malicious=is_malicious,
        seed=ML_CONFIG["random_state"],
    )
    df = load_packet_features_for_ids(conn, packet_ids)
    manifest = build_repeated_grouped_holdout_manifest(
        df,
        packet_ids=packet_ids,
        experiment_key=experiment_key,
        group_by=group_by,
        group_col=group_col,
        sample_size=sample_size,
        cohort_filters=filters,
        random_state=ML_CONFIG["random_state"],
        n_repeats=ML_CONFIG["repeated_holdout_repeats"],
        test_size=ML_CONFIG["test_size"],
        validation_size=ML_CONFIG["validation_size"],
        max_attempts=ML_CONFIG["max_split_attempts_per_repeat"],
        metadata={"spec_payload": spec_payload},
    )
    save_manifest(manifest_path, manifest)
    return df, manifest, manifest_path


def _build_lofo_manifest(
    *,
    group_by: str,
    group_col: str,
    held_out_family: str,
    other_mal_df: pd.DataFrame,
    heldout_mal_df: pd.DataFrame,
    normal_df: pd.DataFrame,
    train_sample_size: int,
    test_sample_size: int,
) -> dict:
    random_state = int(ML_CONFIG["random_state"])
    n_repeats = int(ML_CONFIG["repeated_holdout_repeats"])
    validation_size = float(ML_CONFIG["validation_size"])
    max_attempts = int(ML_CONFIG["max_split_attempts_per_repeat"])
    train_norm_target = max(train_sample_size // 2, 1000)
    test_norm_target = max(test_sample_size // 2, 500)
    normal_test_fraction = min(
        max(test_norm_target / max(len(normal_df), 1), 0.05),
        0.95,
    )

    repeats: list[dict] = []
    used_keys: set[tuple] = set()

    for repeat_index in range(n_repeats):
        accepted = False
        for attempt in range(max_attempts):
            seed_base = random_state + _seed_from_text(held_out_family) + repeat_index * 10_000 + attempt * 100
            other_train_df, other_val_df = group_shuffle_split_unlabeled(
                other_mal_df,
                group_col=group_col,
                test_size=validation_size,
                random_state=seed_base + 1,
            )
            norm_trainval_df, norm_test_df = group_shuffle_split_unlabeled(
                normal_df,
                group_col=group_col,
                test_size=normal_test_fraction,
                random_state=seed_base + 2,
            )
            norm_train_df, norm_val_df = group_shuffle_split_unlabeled(
                norm_trainval_df,
                group_col=group_col,
                test_size=validation_size,
                random_state=seed_base + 3,
            )

            train_df = _balanced_concat([other_train_df, norm_train_df])
            validation_df = _balanced_concat([other_val_df, norm_val_df])
            test_df = _balanced_concat([heldout_mal_df, norm_test_df])

            if min(len(train_df), len(validation_df), len(test_df)) < 2:
                continue
            if len(train_df["is_malicious"].unique()) < 2:
                continue
            if len(validation_df["is_malicious"].unique()) < 2:
                continue
            if len(test_df["is_malicious"].unique()) < 2:
                continue

            train_groups = tuple(sorted(set(train_df[group_col].tolist())))
            validation_groups = tuple(sorted(set(validation_df[group_col].tolist())))
            test_groups = tuple(sorted(set(test_df[group_col].tolist())))
            if set(train_groups) & set(validation_groups):
                continue
            if set(train_groups) & set(test_groups):
                continue
            if set(validation_groups) & set(test_groups):
                continue

            key = (train_groups, validation_groups, test_groups)
            if key in used_keys:
                continue
            used_keys.add(key)

            repeat = {
                "repeat_index": int(repeat_index),
                "malicious_seed": int(seed_base + 1),
                "normal_outer_seed": int(seed_base + 2),
                "normal_inner_seed": int(seed_base + 3),
                "train_packet_ids": [int(x) for x in sorted(train_df["packet_id"].tolist())],
                "validation_packet_ids": [int(x) for x in sorted(validation_df["packet_id"].tolist())],
                "test_packet_ids": [int(x) for x in sorted(test_df["packet_id"].tolist())],
                "n_train_packets": int(len(train_df)),
                "n_validation_packets": int(len(validation_df)),
                "n_test_packets": int(len(test_df)),
                "n_train_groups": int(train_df[group_col].nunique()),
                "n_validation_groups": int(validation_df[group_col].nunique()),
                "n_test_groups": int(test_df[group_col].nunique()),
                "train_positive_rate": float(train_df["is_malicious"].mean()),
                "validation_positive_rate": float(validation_df["is_malicious"].mean()),
                "test_positive_rate": float(test_df["is_malicious"].mean()),
            }
            repeats.append(repeat)
            accepted = True
            break

        if not accepted:
            raise RuntimeError(
                f"Unable to build repeated LOFO split for family={held_out_family}, group_by={group_by}"
            )

    cohort_packet_ids = sorted(
        set(other_mal_df["packet_id"].tolist())
        | set(heldout_mal_df["packet_id"].tolist())
        | set(normal_df["packet_id"].tolist())
    )
    manifest = {
        "schema_version": 2,
        "manifest_kind": "lofo_repeated_grouped_holdout",
        "experiment_key": "E4_LOFO",
        "group_by": group_by,
        "group_col": group_col,
        "label_col": "is_malicious",
        "split_type": _split_type_label(group_by),
        "held_out_family": held_out_family,
        "train_sample_size": int(train_sample_size),
        "test_sample_size": int(test_sample_size),
        "cohort_packet_ids": [int(x) for x in cohort_packet_ids],
        "cohort_hash": hashlib.sha256(",".join(map(str, cohort_packet_ids)).encode("utf-8")).hexdigest()[:16],
        "cohort_size": int(len(cohort_packet_ids)),
        "random_state": random_state,
        "n_repeats": n_repeats,
        "test_size": float(ML_CONFIG["test_size"]),
        "validation_size": validation_size,
        "normal_test_fraction": float(normal_test_fraction),
        "max_attempts": max_attempts,
        "repeats": repeats,
        "metadata": {
            "protocol_version": ML_CONFIG.get("manifest_protocol_version"),
            "train_norm_target": int(train_norm_target),
            "test_norm_target": int(test_norm_target),
        },
    }
    manifest["manifest_hash"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return manifest


def _materialize_lofo_splits(
    df: pd.DataFrame,
    manifest: dict,
) -> list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    df_by_packet = df.set_index("packet_id", drop=False)
    expected_ids = [int(x) for x in manifest["cohort_packet_ids"]]
    missing = [packet_id for packet_id in expected_ids if packet_id not in df_by_packet.index]
    if missing:
        raise RuntimeError(
            f"LOFO cohort is missing {len(missing)} packet ids from the manifest"
        )

    materialized: list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for repeat in manifest["repeats"]:
        train_df = df_by_packet.loc[repeat["train_packet_ids"]].reset_index(drop=True)
        validation_df = df_by_packet.loc[repeat["validation_packet_ids"]].reset_index(drop=True)
        test_df = df_by_packet.loc[repeat["test_packet_ids"]].reset_index(drop=True)

        actual_counts = {
            "train": len(train_df),
            "validation": len(validation_df),
            "test": len(test_df),
        }
        expected_counts = {
            "train": int(repeat["n_train_packets"]),
            "validation": int(repeat["n_validation_packets"]),
            "test": int(repeat["n_test_packets"]),
        }
        if actual_counts != expected_counts:
            raise RuntimeError(
                f"LOFO manifest materialization mismatch for repeat {repeat['repeat_index']}: "
                f"expected {expected_counts}, got {actual_counts}"
            )
        materialized.append((repeat, train_df, validation_df, test_df))
    return materialized


def _load_or_create_lofo_manifest(
    conn,
    *,
    held_out_family: str,
    group_by: str,
    train_sample_size: int,
    test_sample_size: int,
) -> tuple[pd.DataFrame, dict, Path]:
    group_col = resolve_group_column(group_by)
    spec_payload = {
        "protocol_version": ML_CONFIG.get("manifest_protocol_version"),
        "experiment_key": "E4_LOFO",
        "held_out_family": held_out_family,
        "group_by": group_by,
        "group_col": group_col,
        "train_sample_size": int(train_sample_size),
        "test_sample_size": int(test_sample_size),
        "random_state": int(ML_CONFIG["random_state"]),
        "repeats": int(ML_CONFIG["repeated_holdout_repeats"]),
        "validation_size": float(ML_CONFIG["validation_size"]),
        "max_attempts": int(ML_CONFIG["max_split_attempts_per_repeat"]),
    }
    manifest_path = _manifest_path(f"E4_LOFO_{held_out_family}_{group_by}", spec_payload)
    if manifest_path.exists():
        manifest = load_manifest(manifest_path, expected_kind="lofo_repeated_grouped_holdout")
        df = load_packet_features_for_ids(conn, [int(x) for x in manifest["cohort_packet_ids"]])
        return df, manifest, manifest_path

    other_mal_ids = sample_packet_ids(
        conn,
        sample_size=max(train_sample_size // 2, 2000),
        exclude_families=[held_out_family],
        is_malicious=1,
        seed=ML_CONFIG["random_state"] + _seed_from_text(f"{held_out_family}:other"),
    )
    heldout_mal_ids = sample_packet_ids(
        conn,
        sample_size=max(test_sample_size // 2, 500),
        include_families=[held_out_family],
        is_malicious=1,
        seed=ML_CONFIG["random_state"] + _seed_from_text(f"{held_out_family}:heldout"),
    )
    normal_ids = sample_packet_ids(
        conn,
        sample_size=max(train_sample_size // 2, 1000) + max(test_sample_size // 2, 500),
        is_malicious=0,
        seed=ML_CONFIG["random_state"] + _seed_from_text(f"{held_out_family}:normal"),
    )

    other_mal_df = load_packet_features_for_ids(conn, other_mal_ids)
    heldout_mal_df = load_packet_features_for_ids(conn, heldout_mal_ids)
    normal_df = load_packet_features_for_ids(conn, normal_ids)
    if len(other_mal_df) < 100 or len(heldout_mal_df) < 50 or len(normal_df) < 100:
        raise RuntimeError(
            f"Insufficient LOFO data for family={held_out_family}: "
            f"other_mal={len(other_mal_df)}, heldout_mal={len(heldout_mal_df)}, normal={len(normal_df)}"
        )

    manifest = _build_lofo_manifest(
        group_by=group_by,
        group_col=group_col,
        held_out_family=held_out_family,
        other_mal_df=other_mal_df,
        heldout_mal_df=heldout_mal_df,
        normal_df=normal_df,
        train_sample_size=train_sample_size,
        test_sample_size=test_sample_size,
    )
    save_manifest(manifest_path, manifest)
    cohort_df = load_packet_features_for_ids(conn, [int(x) for x in manifest["cohort_packet_ids"]])
    return cohort_df, manifest, manifest_path


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================

def run_experiment(
    df: pd.DataFrame,
    experiment_name: str,
    group_by: str = "session",
    algorithms: list[str] | None = None,
    raise_on_error: bool = False,
    manifest: dict | None = None,
    manifest_path: Path | None = None,
) -> list[dict]:
    if algorithms is None:
        algorithms = list(ML_CONFIG["algorithms"])
    if len(df) < 100:
        return []

    group_col = resolve_group_column(group_by)
    if manifest is None:
        packet_ids = [int(x) for x in df["packet_id"].tolist()]
        manifest = build_repeated_grouped_holdout_manifest(
            df,
            packet_ids=packet_ids,
            experiment_key=experiment_name,
            group_by=group_by,
            group_col=group_col,
            sample_size=len(packet_ids),
            cohort_filters={"ephemeral": True},
            random_state=ML_CONFIG["random_state"],
            n_repeats=ML_CONFIG["repeated_holdout_repeats"],
            test_size=ML_CONFIG["test_size"],
            validation_size=ML_CONFIG["validation_size"],
            max_attempts=ML_CONFIG["max_split_attempts_per_repeat"],
            metadata={"ephemeral": True},
        )

    materialized = materialize_repeated_grouped_holdout_splits(df, manifest)
    return _evaluate_repeated_splits(
        experiment_name=experiment_name,
        algorithms=algorithms,
        group_by=group_by,
        manifest=manifest,
        manifest_path=manifest_path,
        materialized_splits=materialized,
        raise_on_error=raise_on_error,
    )


def run_lofo_experiment(
    conn,
    group_by: str = "capture",
    train_sample_size: int = 50_000,
    test_sample_size: int = 10_000,
    algorithms: list[str] | None = None,
    raise_on_error: bool = False,
) -> list[dict]:
    print(f"\n{'=' * 70}")
    print(f"Experiment E4: Leave-One-Family-Out [{_split_type_label(group_by)}]")
    print("Protocol: repeated grouped train/validation/test with frozen manifests")
    print(f"{'=' * 70}")

    families = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT malware_family FROM sessions "
            "WHERE malware_family NOT IN ('', 'Unknown') AND is_malicious = 1 "
            "ORDER BY malware_family"
        ).fetchall()
    ]
    if len(families) < 2:
        print("  [SKIP] Need at least 2 named malware families for LOFO.")
        return []

    if algorithms is None:
        algorithms = ["DecisionTreeClassifier", "KNeighborsClassifier"]

    all_results: list[dict] = []
    for held_out_family in families:
        experiment_name = f"E4_LOFO_{group_by}_repeated_group_holdout"
        print(f"\n  --- Held out: {held_out_family} ---")
        try:
            cohort_df, manifest, manifest_path = _load_or_create_lofo_manifest(
                conn,
                held_out_family=held_out_family,
                group_by=group_by,
                train_sample_size=train_sample_size,
                test_sample_size=test_sample_size,
            )
        except Exception as e:
            if raise_on_error:
                raise
            print(f"    [SKIP] {e}")
            continue

        materialized = _materialize_lofo_splits(cohort_df, manifest)
        family_results = _evaluate_repeated_splits(
            experiment_name=experiment_name,
            algorithms=algorithms,
            group_by=group_by,
            manifest=manifest,
            manifest_path=manifest_path,
            materialized_splits=materialized,
            raise_on_error=raise_on_error,
            extra_static_fields={"held_out_family": held_out_family},
        )
        all_results.extend(family_results)
    return all_results


# ============================================================================
# REPORTING
# ============================================================================

def print_detection_table(results: list[dict], experiment: str):
    exp_results = _rows_for_experiment(results, experiment)
    if not exp_results:
        return
    headers = ["AI", "Accuracy (mean +/- std)", "Accuracy CI95", "F1(mal)", "TP mean", "FP mean", "FN mean", "TN mean"]
    rows = [
        [
            row["algorithm"],
            _format_mean_std(row, "accuracy", digits=4),
            _format_ci(row, "accuracy", digits=4),
            _format_mean_std(row, "f1_1", digits=4),
            f"{row.get('tp', 0):.1f}" if row.get("record_type") == "summary" else row.get("tp", ""),
            f"{row.get('fp', 0):.1f}" if row.get("record_type") == "summary" else row.get("fp", ""),
            f"{row.get('fn', 0):.1f}" if row.get("record_type") == "summary" else row.get("fn", ""),
            f"{row.get('tn', 0):.1f}" if row.get("record_type") == "summary" else row.get("tn", ""),
        ]
        for row in exp_results
    ]
    print(f"\nDetection Comparison - {experiment}")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_performance_table(results: list[dict], experiment: str):
    exp_results = _rows_for_experiment(results, experiment)
    if not exp_results:
        return
    headers = ["AI", "Prec(0)", "Prec(1)", "Recall(0)", "Recall(1)", "F1(0)", "F1(1)", "Support(0)", "Support(1)"]
    rows = [
        [
            row["algorithm"],
            _format_mean_std(row, "precision_0", digits=3),
            _format_mean_std(row, "precision_1", digits=3),
            _format_mean_std(row, "recall_0", digits=3),
            _format_mean_std(row, "recall_1", digits=3),
            _format_mean_std(row, "f1_0", digits=3),
            _format_mean_std(row, "f1_1", digits=3),
            f"{row.get('test_support_0', 0):.1f}" if row.get("record_type") == "summary" else row.get("test_support_0", ""),
            f"{row.get('test_support_1', 0):.1f}" if row.get("record_type") == "summary" else row.get("test_support_1", ""),
        ]
        for row in exp_results
    ]
    print(f"\nPerformance Comparison - {experiment}")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


# ============================================================================
# MAIN
# ============================================================================

def _standard_experiment_definitions() -> list[dict]:
    return [
        {
            "key": "E1_full_mixed",
            "sample_size": int(ML_CONFIG["experiment_1_sample_size"]),
            "algorithms": list(ML_CONFIG["algorithms"]),
            "encrypted_only": False,
        },
        {
            "key": "E2_limited_20k",
            "sample_size": int(ML_CONFIG["experiment_2_sample_size"]),
            "algorithms": list(ML_CONFIG["algorithms"]),
            "encrypted_only": False,
        },
        {
            "key": "E3_encrypted_only",
            "sample_size": int(ML_CONFIG["experiment_3_sample_size"]),
            "algorithms": ["DecisionTreeClassifier", "KNeighborsClassifier"],
            "encrypted_only": True,
        },
    ]


def main() -> None:
    conn = get_db()
    all_results: list[dict] = []
    holdout_modes = ML_CONFIG.get("holdout_modes", ["session", "capture"])

    for group_by in holdout_modes:
        print("\n" + "#" * 70)
        print(f"# Repeated grouped holdout mode: {group_by}")
        print("#" * 70)

        for spec in _standard_experiment_definitions():
            experiment_name = f"{spec['key']}_{group_by}_repeated_group_holdout"
            try:
                cohort_df, manifest, manifest_path = load_or_create_standard_manifest(
                    conn,
                    experiment_key=spec["key"],
                    group_by=group_by,
                    sample_size=spec["sample_size"],
                    encrypted_only=spec.get("encrypted_only", False),
                )
            except Exception as e:
                print(f"[SKIP] {experiment_name}: {e}")
                continue

            if len(cohort_df) < 100:
                print(f"[SKIP] Not enough data for {experiment_name}.")
                continue

            try:
                results = run_experiment(
                    cohort_df,
                    experiment_name,
                    group_by=group_by,
                    algorithms=spec["algorithms"],
                    raise_on_error=False,
                    manifest=manifest,
                    manifest_path=manifest_path,
                )
            except Exception as e:
                print(f"[SKIP] {experiment_name}: {e}")
                continue

            all_results.extend(results)
            print_detection_table(all_results, experiment_name)
            print_performance_table(all_results, experiment_name)

    for group_by in holdout_modes:
        try:
            all_results.extend(run_lofo_experiment(conn, group_by=group_by))
        except Exception as e:
            print(f"[SKIP] LOFO {group_by}: {e}")

    results_path = RESULTS_DIR / "classical_ml_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_path}")
    conn.close()


# ============================================================================
# ADVERSARIAL EXPERIMENT SUPPORT
# ============================================================================

def train_for_adversarial(
    conn,
    sample_size: int = 50_000,
    group_by: str = "session",
) -> dict:
    """
    Train CART and KNN for Gap 5 using the first repeat of a frozen manifest.
    """
    cohort_df, manifest, manifest_path = load_or_create_standard_manifest(
        conn,
        experiment_key="adversarial_train",
        group_by=group_by,
        sample_size=sample_size,
        encrypted_only=False,
    )
    materialized = materialize_repeated_grouped_holdout_splits(cohort_df, manifest)
    if not materialized:
        raise RuntimeError("No repeated splits available for adversarial training")

    repeat_meta, train_df, validation_df, test_df = materialized[0]
    train_val_df = pd.concat([train_df, validation_df], ignore_index=True)
    X_train, y_train = _prepare_matrix(train_val_df)
    X_test, y_test = _prepare_matrix(test_df)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    cart = DecisionTreeClassifier(random_state=ML_CONFIG["random_state"])
    cart.fit(X_train_s, y_train)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(X_train_s, y_train)

    cart_acc = accuracy_score(y_test, cart.predict(X_test_s))
    knn_acc = accuracy_score(y_test, knn.predict(X_test_s))
    print(
        f"  [adversarial] split={manifest['split_type']} | "
        f"CART accuracy: {cart_acc:.4f}  KNN accuracy: {knn_acc:.4f}  "
        f"(n_train={len(X_train)}, n_test={len(X_test)})"
    )

    split_summary = {
        "manifest_path": str(manifest_path.resolve()),
        "manifest_hash": manifest.get("manifest_hash"),
        "cohort_hash": manifest.get("cohort_hash"),
        "repeat_index": int(repeat_meta["repeat_index"]),
        "n_train_packets": int(len(train_val_df)),
        "n_test_packets": int(len(test_df)),
        "n_train_groups": int(train_val_df[manifest["group_col"]].nunique()),
        "n_test_groups": int(test_df[manifest["group_col"]].nunique()),
        "train_positive_rate": float(train_val_df["is_malicious"].mean()),
        "test_positive_rate": float(test_df["is_malicious"].mean()),
    }
    return {
        "cart": cart,
        "knn": knn,
        "scaler": scaler,
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
        "feature_cols": FEATURE_COLS,
        "split_type": manifest["split_type"],
        "group_col": manifest["group_col"],
        "split_summary": split_summary,
    }


if __name__ == "__main__":
    main()
