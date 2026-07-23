#!/usr/bin/env python3
"""
Phase 3: Classical ML baselines over the five ESORICS side-channel features.

This version removes packet-level train/test leakage by using grouped holdout
splits.  Two split modes are supported:
  - session holdout  (group by session_id)
  - capture holdout  (group by dataset_id)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from tabulate import tabulate

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import DB_PATH, ML_CONFIG, RESULTS_DIR, SIDE_CHANNEL_FEATURES
from src.database import get_db
from src.splits import group_holdout_split, group_shuffle_split_unlabeled, resolve_group_column


FEATURE_COLS = list(SIDE_CHANNEL_FEATURES)


class MissingDependencyError(RuntimeError):
    """Raised when an optional local ML dependency is unavailable."""


# ============================================================================
# DATA LOADING
# ============================================================================

def load_packet_features(
    conn,
    sample_size: int | None = None,
    encrypted_only: bool = False,
    exclude_families: list[str] | None = None,
    include_families: list[str] | None = None,
    is_malicious: int | None = None,
) -> pd.DataFrame:
    """
    Load packet-level side-channel features plus grouping columns.

    Returns at least:
      packet_id, session_id, dataset_id, packet_size, payload_size,
      payload_ratio, ratio_to_prev, time_diff, is_malicious,
      malware_family, is_encrypted
    """
    query = """
        SELECT
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

    query += " ORDER BY RANDOM()"
    if sample_size:
        query += f" LIMIT {int(sample_size)}"

    return pd.read_sql_query(query, conn, params=params if params else None)


# ============================================================================
# MODELS
# ============================================================================

def get_algorithm(name: str):
    algos = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "LinearDiscriminantAnalysis": LinearDiscriminantAnalysis(),
        "KNeighborsClassifier": KNeighborsClassifier(n_neighbors=5),
        "DecisionTreeClassifier": DecisionTreeClassifier(random_state=42),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
        ),
        "GaussianNB": GaussianNB(),
        "SVC": SVC(kernel="rbf", random_state=42, max_iter=5000),
        "MLPClassifier": MLPClassifier(
            hidden_layer_sizes=(100,), max_iter=500, random_state=42
        ),
    }
    if name in algos:
        return algos[name]
    if name == "XGBClassifier":
        try:
            from xgboost import XGBClassifier
        except ImportError as e:
            raise MissingDependencyError(
                "XGBoost is not installed. Run `pip install xgboost` or `pip install -r requirements.txt`."
            ) from e
        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    if name == "LGBMClassifier":
        try:
            from lightgbm import LGBMClassifier
        except ImportError as e:
            raise MissingDependencyError(
                "LightGBM is not installed. Run `pip install lightgbm` or `pip install -r requirements.txt`."
            ) from e
        return LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
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
    """
    Validate that every requested algorithm is available locally.

    This is used by strict experiment suites such as Phase 2 so they fail fast
    instead of silently degrading into partial runs.
    """
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


def _holdout_label(group_by: str) -> str:
    return f"{group_by}_group_holdout"


def _sample_lofo_normal_packets(
    conn,
    n_pool: int,
) -> pd.DataFrame:
    return load_packet_features(conn, sample_size=n_pool, is_malicious=0)


def _balanced_concat(parts: list[pd.DataFrame]) -> pd.DataFrame:
    parts = [p for p in parts if p is not None and len(p) > 0]
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================

def run_experiment(
    df: pd.DataFrame,
    experiment_name: str,
    group_by: str = "session",
    algorithms: list[str] | None = None,
    raise_on_error: bool = False,
) -> list[dict]:
    if algorithms is None:
        algorithms = ML_CONFIG["algorithms"]
    if len(df) < 100:
        return []

    group_col = resolve_group_column(group_by)
    train_df, test_df, split_summary = group_holdout_split(
        df,
        group_col=group_col,
        label_col="is_malicious",
        test_size=ML_CONFIG["test_size"],
        random_state=ML_CONFIG["random_state"],
        n_trials=ML_CONFIG.get("group_holdout_trials", 256),
    )

    X_train, y_train = _prepare_matrix(train_df)
    X_test, y_test = _prepare_matrix(test_df)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"\n{'='*70}")
    print(f"Experiment: {experiment_name}")
    print(
        f"Split: {_holdout_label(group_by)} on {group_col} | "
        f"train_groups={split_summary.n_train_groups}, test_groups={split_summary.n_test_groups}"
    )
    print(
        f"Dataset: {len(df)} sampled packets "
        f"({int(df['is_malicious'].sum())} malicious, {int(len(df) - df['is_malicious'].sum())} normal)"
    )
    print(
        f"Train: {len(train_df)} packets, Test: {len(test_df)} packets | "
        f"train_pos={split_summary.train_positive_rate:.3f}, "
        f"test_pos={split_summary.test_positive_rate:.3f}"
    )
    print(f"{'='*70}")

    results: list[dict] = []
    for algo_name in algorithms:
        short = SHORT_NAMES.get(algo_name, algo_name)
        print(f"\n  Training {short}...", end=" ", flush=True)
        try:
            model = get_algorithm(algo_name)
            if model is None:
                if raise_on_error:
                    raise ValueError(f"Unknown algorithm: {algo_name}")
                print(f"[SKIP] Unknown algorithm: {algo_name}")
                continue

            t0 = time.time()
            model.fit(X_train_scaled, y_train)
            train_time = time.time() - t0

            t1 = time.time()
            y_pred = model.predict(X_test_scaled)
            predict_time = time.time() - t1

            tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
            acc = accuracy_score(y_test, y_pred)
            prec_0 = precision_score(y_test, y_pred, pos_label=0, zero_division=0)
            prec_1 = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
            rec_0 = recall_score(y_test, y_pred, pos_label=0, zero_division=0)
            rec_1 = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
            f1_0 = f1_score(y_test, y_pred, pos_label=0, zero_division=0)
            f1_1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)

            result = {
                "experiment": experiment_name,
                "algorithm": short,
                "split_type": _holdout_label(group_by),
                "group_col": group_col,
                "accuracy": acc,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "precision_0": prec_0,
                "precision_1": prec_1,
                "recall_0": rec_0,
                "recall_1": rec_1,
                "f1_0": f1_0,
                "f1_1": f1_1,
                "train_time_s": train_time,
                "predict_time_s": predict_time,
                "test_support_0": int(tn + fp),
                "test_support_1": int(tp + fn),
                **split_summary.as_dict(),
            }
            results.append(result)
            print(
                f"Acc={acc:.4f}  TP={tp} FP={fp} FN={fn} TN={tn}  ({train_time:.1f}s train)"
            )
        except MissingDependencyError as e:
            if raise_on_error:
                raise
            print(f"[SKIP] {e}")
            results.append({
                "experiment": experiment_name,
                "algorithm": short,
                "split_type": _holdout_label(group_by),
                "group_col": group_col,
                "accuracy": 0,
                "error": str(e),
            })
        except Exception as e:
            if raise_on_error:
                raise
            print(f"[ERROR] {e}")
            results.append({
                "experiment": experiment_name,
                "algorithm": short,
                "split_type": _holdout_label(group_by),
                "group_col": group_col,
                "accuracy": 0,
                "error": str(e),
            })
    return results


def run_lofo_experiment(
    conn,
    group_by: str = "capture",
    train_sample_size: int = 50_000,
    test_sample_size: int = 10_000,
    algorithms: list[str] | None = None,
    raise_on_error: bool = False,
) -> list[dict]:
    """
    Leave-One-Family-Out with group-disjoint normal traffic.

    The held-out family's malicious packets are always tested only. Normal traffic
    is split by the chosen grouping column so that train/test remain disjoint.
    This is sufficient for the packaged local-capture corpus, where captures are
    either benign or malicious.
    """
    print(f"\n{'='*70}")
    print(f"Experiment E4: Leave-One-Family-Out [{_holdout_label(group_by)}]")
    print("Tests generalisation to unseen malware families")
    print(f"{'='*70}")

    families = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT malware_family FROM sessions "
            "WHERE malware_family NOT IN ('', 'Unknown') AND is_malicious = 1 "
            "ORDER BY malware_family"
        ).fetchall()
    ]
    if len(families) < 2:
        print("  [SKIP] Need at least 2 named malware families for LOFO.")
        return []

    group_col = resolve_group_column(group_by)
    if algorithms is None:
        algorithms = ["DecisionTreeClassifier", "KNeighborsClassifier"]
    results: list[dict] = []

    # Large normal pool reused across families; split later with locked groups.
    normal_pool = _sample_lofo_normal_packets(
        conn,
        n_pool=max(train_sample_size + test_sample_size, 10_000),
    )
    if len(normal_pool) < 100:
        print("  [SKIP] Not enough normal packets for LOFO.")
        return []

    for held_out_family in families:
        print(f"\n  --- Held out: {held_out_family} ---")

        df_other_mal = pd.read_sql_query(
            """
            SELECT
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
            FROM packets p
            INNER JOIN sessions s ON (p.session_id = s.id)
            WHERE p.is_malicious = 1 AND s.malware_family NOT IN (?, '', 'Unknown')
            ORDER BY RANDOM() LIMIT ?
            """,
            conn,
            params=[held_out_family, max(train_sample_size // 2, 2000)],
        )
        df_heldout_mal = pd.read_sql_query(
            """
            SELECT
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
            FROM packets p
            INNER JOIN sessions s ON (p.session_id = s.id)
            WHERE p.is_malicious = 1 AND s.malware_family = ?
            ORDER BY RANDOM() LIMIT ?
            """,
            conn,
            params=[held_out_family, max(test_sample_size // 2, 500)],
        )

        if len(df_other_mal) < 100 or len(df_heldout_mal) < 50:
            print("    [SKIP] Not enough malicious data for this family.")
            continue

        # If a capture appears in the held-out set, drop it from the train-side
        # malicious pool to preserve group disjointness even on mixed captures.
        test_locked_groups = set(df_heldout_mal[group_col].tolist())
        df_other_mal = df_other_mal[~df_other_mal[group_col].isin(test_locked_groups)]
        if len(df_other_mal) < 100:
            print("    [SKIP] Train-side malicious data vanished after group locking.")
            continue
        train_locked_groups = set(df_other_mal[group_col].tolist())

        norm_forced_train = normal_pool[normal_pool[group_col].isin(train_locked_groups)]
        norm_forced_test = normal_pool[normal_pool[group_col].isin(test_locked_groups)]
        norm_free = normal_pool[
            ~normal_pool[group_col].isin(train_locked_groups | test_locked_groups)
        ].copy()

        train_norm_target = max(train_sample_size // 2, 1000)
        test_norm_target = max(test_sample_size // 2, 500)

        if len(norm_free) >= 2 and len(norm_free[group_col].unique()) >= 2:
            desired_test = test_norm_target / max(train_norm_target + test_norm_target, 1)
            desired_test = min(max(desired_test, 0.05), 0.95)
            try:
                norm_train_free, norm_test_free = group_shuffle_split_unlabeled(
                    norm_free,
                    group_col=group_col,
                    test_size=desired_test,
                    random_state=ML_CONFIG["random_state"],
                )
            except Exception:
                norm_train_free = norm_free.sample(frac=0.7, random_state=42)
                norm_test_free = norm_free.drop(norm_train_free.index)
        else:
            norm_train_free = pd.DataFrame(columns=normal_pool.columns)
            norm_test_free = pd.DataFrame(columns=normal_pool.columns)

        norm_train = _balanced_concat([norm_forced_train, norm_train_free]).head(train_norm_target)
        norm_test = _balanced_concat([norm_forced_test, norm_test_free]).head(test_norm_target)

        train_mal = df_other_mal.head(max(train_sample_size - len(norm_train), 1000))
        test_mal = df_heldout_mal.head(max(test_sample_size - len(norm_test), 500))
        train_df = _balanced_concat([train_mal, norm_train])
        test_df = _balanced_concat([test_mal, norm_test])

        if len(train_df) < 200 or len(test_df) < 100:
            print("    [SKIP] LOFO split too small after normal-group allocation.")
            continue

        if set(train_df[group_col]) & set(test_df[group_col]):
            print("    [SKIP] Overlapping groups remained after LOFO split.")
            continue

        X_train, y_train = _prepare_matrix(train_df)
        X_test, y_test = _prepare_matrix(test_df)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        for algo_name in algorithms:
            short = SHORT_NAMES.get(algo_name, algo_name)
            try:
                model = get_algorithm(algo_name)
                if model is None:
                    if raise_on_error:
                        raise ValueError(f"Unknown algorithm: {algo_name}")
                    print(f"    [SKIP] Unknown algorithm: {algo_name}")
                    continue
                model.fit(X_train_s, y_train)
                y_pred = model.predict(X_test_s)
            except MissingDependencyError as e:
                if raise_on_error:
                    raise
                print(f"    [SKIP] {e}")
                results.append({
                    "experiment": f"E4_LOFO_{group_by}_holdout",
                    "held_out_family": held_out_family,
                    "algorithm": short,
                    "split_type": _holdout_label(group_by),
                    "group_col": group_col,
                    "accuracy": 0,
                    "error": str(e),
                })
                continue
            except Exception as e:
                if raise_on_error:
                    raise
                print(f"    [ERROR] {short}: {e}")
                results.append({
                    "experiment": f"E4_LOFO_{group_by}_holdout",
                    "held_out_family": held_out_family,
                    "algorithm": short,
                    "split_type": _holdout_label(group_by),
                    "group_col": group_col,
                    "accuracy": 0,
                    "error": str(e),
                })
                continue

            tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
            acc = accuracy_score(y_test, y_pred)
            result = {
                "experiment": f"E4_LOFO_{group_by}_holdout",
                "held_out_family": held_out_family,
                "algorithm": short,
                "split_type": _holdout_label(group_by),
                "group_col": group_col,
                "accuracy": acc,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "f1_1": f1_score(y_test, y_pred, pos_label=1, zero_division=0),
                "test_malicious": int(y_test.sum()),
                "test_normal": int(len(y_test) - y_test.sum()),
                "n_train_groups": int(train_df[group_col].nunique()),
                "n_test_groups": int(test_df[group_col].nunique()),
            }
            results.append(result)
            print(
                f"    {short}: Acc={acc:.4f}  F1(mal)={result['f1_1']:.4f}  "
                f"TP={tp} FP={fp} FN={fn} TN={tn}"
            )

    return results


# ============================================================================
# REPORTING
# ============================================================================

def print_detection_table(results: list[dict], experiment: str):
    exp_results = [r for r in results if r.get("experiment") == experiment and "error" not in r]
    if not exp_results:
        return
    headers = ["AI", "Accuracy", "True Pos", "False Pos", "False Neg", "True Neg"]
    rows = [
        [r["algorithm"], f"{r['accuracy']:.5f}", r["tp"], r["fp"], r["fn"], r["tn"]]
        for r in exp_results
    ]
    print(f"\nDetection Comparison - {experiment}")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


def print_performance_table(results: list[dict], experiment: str):
    exp_results = [r for r in results if r.get("experiment") == experiment and "error" not in r]
    if not exp_results:
        return
    headers = ["AI", "Prec(0)", "Prec(1)", "Recall(0)", "Recall(1)", "F1(0)", "F1(1)", "Support(0)", "Support(1)"]
    rows = [
        [
            r["algorithm"],
            f"{r.get('precision_0', 0):.2f}",
            f"{r.get('precision_1', 0):.2f}",
            f"{r.get('recall_0', 0):.2f}",
            f"{r.get('recall_1', 0):.2f}",
            f"{r.get('f1_0', 0):.2f}",
            f"{r.get('f1_1', 0):.2f}",
            r.get("test_support_0", ""),
            r.get("test_support_1", ""),
        ]
        for r in exp_results
    ]
    print(f"\nPerformance Comparison - {experiment}")
    print(tabulate(rows, headers=headers, tablefmt="grid"))


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    conn = get_db()
    all_results: list[dict] = []

    holdout_modes = ML_CONFIG.get("holdout_modes", ["session", "capture"])

    for group_by in holdout_modes:
        print("\n" + "#" * 70)
        print(f"# Grouped holdout mode: {group_by}")
        print("#" * 70)

        experiments = [
            (
                load_packet_features(conn, sample_size=ML_CONFIG["experiment_1_sample_size"]),
                f"E1_full_mixed_{group_by}_holdout",
                ML_CONFIG["algorithms"],
            ),
            (
                load_packet_features(conn, sample_size=ML_CONFIG["experiment_2_sample_size"]),
                f"E2_limited_20k_{group_by}_holdout",
                ML_CONFIG["algorithms"],
            ),
            (
                load_packet_features(conn, sample_size=100_000, encrypted_only=True),
                f"E3_encrypted_only_{group_by}_holdout",
                ["DecisionTreeClassifier", "KNeighborsClassifier"],
            ),
        ]

        for df, exp_name, algos in experiments:
            if len(df) < 100:
                print(f"[SKIP] Not enough data for {exp_name}.")
                continue
            try:
                results = run_experiment(df, exp_name, group_by=group_by, algorithms=algos)
            except Exception as e:
                print(f"[SKIP] {exp_name}: {e}")
                continue
            all_results.extend(results)
            print_detection_table(all_results, exp_name)
            print_performance_table(all_results, exp_name)

    for group_by in holdout_modes:
        try:
            all_results.extend(run_lofo_experiment(conn, group_by=group_by))
        except Exception as e:
            print(f"[SKIP] LOFO {group_by}: {e}")

    results_path = RESULTS_DIR / "classical_ml_results.json"
    with open(results_path, "w") as f:
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
    Train CART and KNN for Gap 5 using a grouped holdout split.

    Returns the fitted models, scaler, and raw train/test matrices.
    """
    df = load_packet_features(conn, sample_size=sample_size)
    if len(df) < 100:
        raise ValueError(
            f"Insufficient data for adversarial training: {len(df)} rows. Run feature extraction first."
        )

    group_col = resolve_group_column(group_by)
    train_df, test_df, summary = group_holdout_split(
        df,
        group_col=group_col,
        label_col="is_malicious",
        test_size=ML_CONFIG["test_size"],
        random_state=ML_CONFIG["random_state"],
        n_trials=ML_CONFIG.get("group_holdout_trials", 256),
    )

    X_train, y_train = _prepare_matrix(train_df)
    X_test, y_test = _prepare_matrix(test_df)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    cart = DecisionTreeClassifier(random_state=42)
    cart.fit(X_train_s, y_train)

    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(X_train_s, y_train)

    cart_acc = accuracy_score(y_test, cart.predict(X_test_s))
    knn_acc = accuracy_score(y_test, knn.predict(X_test_s))
    print(
        f"  [adversarial] split={_holdout_label(group_by)} | "
        f"CART accuracy: {cart_acc:.4f}  KNN accuracy: {knn_acc:.4f}  "
        f"(n_train={len(X_train)}, n_test={len(X_test)})"
    )

    return {
        "cart": cart,
        "knn": knn,
        "scaler": scaler,
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
        "feature_cols": FEATURE_COLS,
        "split_type": _holdout_label(group_by),
        "group_col": group_col,
        "split_summary": summary.as_dict(),
    }

from src.classical_ml_v2 import *  # noqa: F401,F403


if __name__ == "__main__":
    main()
