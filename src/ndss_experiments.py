#!/usr/bin/env python3
"""Session-based major-version experiment suite."""

from __future__ import annotations

import json
import hashlib
import math
import os
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from tabulate import tabulate

from configs.config import ML_CONFIG, NDSS_CONFIG, RESULTS_DIR, SESSION_SPLIT_CONFIG
from src.classical_ml_v2 import (
    BOOSTER_ALGORITHMS,
    SHORT_NAMES,
    ensure_algorithms_available,
    get_algorithm,
)
from src.llm_experiments import LLMClient
from src.ndss_dataset import NDSSDatasetSpec, load_or_create_ndss_manifest
from src.ndss_finetune import create_openai_finetune_job, export_finetune_corpus
from src.ndss_prompts import build_system_prompt, build_user_prompt
from src.database import get_db
from src.session_splits import (
    CAPTURE_DISJOINT_5FOLD,
    SESSION_SPLIT_MODES,
    WITHIN_CAPTURE_TEMPORAL,
    SessionSplitFeasibilityError,
    materialize_session_splits,
)


@dataclass(frozen=True)
class NDSSLLMRunConfig:
    budget_profile: str
    result_label: str
    feature_sets: list[str] | None
    sample_units: list[str] | None
    behavior_window_seconds: list[float] | None
    repeat_indices: list[int] | None
    repeat_limit: int | None
    balanced_samples_per_repeat: int
    deployment_validation_samples_per_repeat: int
    deployment_test_samples_per_repeat: int
    max_calls: int | None
    family_stratified_balanced: bool


def _json_scalar(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if pd.isna(value):
        return None
    return value


def _parse_csv_choice(value: str | None, *, allowed: set[str], field_name: str) -> list[str] | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "all":
        return None
    items = [item.strip().lower() for item in normalized.split(",") if item.strip()]
    invalid = sorted(set(items) - allowed)
    if invalid:
        raise ValueError(f"Unknown {field_name} values: {invalid}; allowed={sorted(allowed)}")
    return items


def _parse_window_seconds(value: str | None) -> list[float] | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "all":
        return None
    windows: list[float] = []
    for item in normalized.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            window = float(item)
        except ValueError as exc:
            raise ValueError(f"Invalid --ndss-window-seconds value {item!r}") from exc
        if window <= 0:
            raise ValueError("--ndss-window-seconds values must be positive")
        windows.append(window)
    return windows or None


def _positive_optional_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if int(value) <= 0:
        raise ValueError(f"{field_name} must be positive when supplied")
    return int(value)


def _parse_repeat_indices(value: str | None) -> list[int] | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "all":
        return None
    indices: list[int] = []
    for item in normalized.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            index = int(item)
        except ValueError as exc:
            raise ValueError(f"Invalid --ndss-repeat-indices value {item!r}") from exc
        if index < 0:
            raise ValueError("--ndss-repeat-indices values must be non-negative")
        indices.append(index)
    if not indices:
        return None
    return sorted(set(indices))


def _resolve_llm_run_config(
    *,
    budget_profile: str,
    feature_set: str | None,
    sample_unit: str | None,
    window_seconds: str | None,
    repeat_indices: str | None,
    repeat_limit: int | None,
    samples_per_repeat: int | None,
    validation_samples_per_repeat: int | None,
    test_samples_per_repeat: int | None,
    max_calls: int | None,
) -> NDSSLLMRunConfig:
    profiles = dict(NDSS_CONFIG.get("llm_budget_profiles", {"full": {}}))
    profile_key = str(budget_profile or "full").strip().lower()
    if profile_key not in profiles:
        raise ValueError(f"Unknown Session LLM budget profile={budget_profile!r}")
    profile = dict(profiles.get(profile_key) or {})

    feature_sets = _parse_csv_choice(
        feature_set,
        allowed={"minimal", "mercury", "combined"},
        field_name="feature set",
    )
    if feature_sets is None and profile.get("feature_sets"):
        feature_sets = [str(item).strip().lower() for item in profile["feature_sets"]]

    sample_units = _parse_csv_choice(
        sample_unit,
        allowed={"session_sequence", "behavior_window", "packet_ablation"},
        field_name="sample unit",
    )
    if sample_units is None and profile.get("sample_units"):
        sample_units = [str(item).strip().lower() for item in profile["sample_units"]]

    windows = _parse_window_seconds(window_seconds)
    if windows is None and profile.get("behavior_window_seconds") is not None:
        windows = [float(item) for item in profile["behavior_window_seconds"]]

    cli_repeat_indices = _parse_repeat_indices(repeat_indices)
    cli_repeat_limit = _positive_optional_int(repeat_limit, "--ndss-repeat-limit")
    if cli_repeat_indices is not None and cli_repeat_limit is not None:
        raise ValueError("Use either --ndss-repeat-indices or --ndss-repeat-limit, not both")

    resolved_repeat_indices = cli_repeat_indices
    resolved_repeat_limit = cli_repeat_limit
    if (
        resolved_repeat_indices is None
        and resolved_repeat_limit is None
        and profile.get("repeat_indices") is not None
    ):
        resolved_repeat_indices = sorted({int(item) for item in profile["repeat_indices"]})
    if (
        resolved_repeat_indices is None
        and resolved_repeat_limit is None
        and profile.get("repeat_limit") is not None
    ):
        resolved_repeat_limit = int(profile["repeat_limit"])

    balanced_samples = _positive_optional_int(samples_per_repeat, "--ndss-llm-samples-per-repeat")
    if balanced_samples is None:
        balanced_samples = int(
            profile.get(
                "balanced_eval_samples_per_repeat",
                NDSS_CONFIG.get("llm_balanced_eval_samples_per_repeat", 80),
            )
        )

    deployment_val = _positive_optional_int(
        validation_samples_per_repeat,
        "--ndss-llm-validation-samples-per-repeat",
    )
    if deployment_val is None:
        deployment_val = int(
            profile.get(
                "deployment_validation_samples_per_repeat",
                NDSS_CONFIG.get("llm_deployment_validation_samples_per_repeat", 80),
            )
        )

    deployment_test = _positive_optional_int(
        test_samples_per_repeat,
        "--ndss-llm-test-samples-per-repeat",
    )
    if deployment_test is None:
        deployment_test = int(
            profile.get(
                "deployment_test_samples_per_repeat",
                NDSS_CONFIG.get("llm_deployment_test_samples_per_repeat", 160),
            )
        )

    resolved_max_calls = _positive_optional_int(max_calls, "--ndss-llm-max-calls")
    if resolved_max_calls is None and profile.get("max_calls_per_run") is not None:
        resolved_max_calls = int(profile["max_calls_per_run"])

    result_label = profile_key
    has_cli_override = any(
        value is not None
        for value in [
            feature_set,
            sample_unit,
            window_seconds,
            repeat_indices,
            repeat_limit,
            samples_per_repeat,
            validation_samples_per_repeat,
            test_samples_per_repeat,
            max_calls,
        ]
    )
    if has_cli_override:
        label_payload = {
            "profile": profile_key,
            "feature_sets": feature_sets,
            "sample_units": sample_units,
            "windows": windows,
            "repeat_indices": resolved_repeat_indices,
            "repeat_limit": resolved_repeat_limit,
            "balanced_samples": balanced_samples,
            "deployment_validation": deployment_val,
            "deployment_test": deployment_test,
            "max_calls": resolved_max_calls,
        }
        label_hash = hashlib.sha256(
            json.dumps(label_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:10]
        result_label = f"{profile_key}_custom_{label_hash}"

    return NDSSLLMRunConfig(
        budget_profile=profile_key,
        result_label=result_label,
        feature_sets=feature_sets,
        sample_units=sample_units,
        behavior_window_seconds=windows,
        repeat_indices=resolved_repeat_indices,
        repeat_limit=resolved_repeat_limit,
        balanced_samples_per_repeat=int(balanced_samples),
        deployment_validation_samples_per_repeat=int(deployment_val),
        deployment_test_samples_per_repeat=int(deployment_test),
        max_calls=resolved_max_calls,
        family_stratified_balanced=bool(profile.get("family_stratified_balanced", False)),
    )


def _filter_llm_specs(specs: list[NDSSDatasetSpec], config: NDSSLLMRunConfig) -> list[NDSSDatasetSpec]:
    filtered: list[NDSSDatasetSpec] = []
    for spec in specs:
        if config.feature_sets is not None and spec.feature_set not in config.feature_sets:
            continue
        if config.sample_units is not None and spec.sample_unit not in config.sample_units:
            continue
        if (
            spec.sample_unit == "behavior_window"
            and config.behavior_window_seconds is not None
            and not any(math.isclose(float(spec.window_seconds or 0.0), target) for target in config.behavior_window_seconds)
        ):
            continue
        filtered.append(spec)
    if not filtered:
        raise ValueError("Session LLM filters selected zero experiment specs")
    return filtered


def _protocol_fold_count(split_mode: str) -> int:
    if split_mode == CAPTURE_DISJOINT_5FOLD:
        return 5
    if split_mode == WITHIN_CAPTURE_TEMPORAL:
        return 1
    raise ValueError(f"Unknown session split mode={split_mode!r}")


def _allowed_repeat_indices(
    config: NDSSLLMRunConfig,
    split_mode: str,
) -> set[int] | None:
    if config.repeat_indices is not None:
        available = set(range(_protocol_fold_count(split_mode)))
        selected = set(config.repeat_indices) & available
        if not selected:
            raise ValueError(
                f"Requested fold indices {config.repeat_indices} do not exist for {split_mode}"
            )
        return selected
    if config.repeat_limit is None:
        return None
    limit = min(int(config.repeat_limit), _protocol_fold_count(split_mode))
    return set(range(limit))


def _llm_result_suffix(evaluation_mode: str, config: NDSSLLMRunConfig) -> str:
    if config.result_label == "full":
        return str(evaluation_mode)
    return f"{evaluation_mode}_{config.result_label}"


def _prepare_matrix(df: pd.DataFrame, feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = df[feature_cols].values.astype(float)
    y = df["is_malicious"].values.astype(int)
    return X, y


def _as_feature_frame(array: np.ndarray, feature_cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(array, columns=feature_cols)


def _metric_stats(values: list[float], *, bounded: bool = False) -> tuple[float, float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    if len(arr) <= 1:
        return mean, 0.0, mean, mean
    std = float(np.std(arr, ddof=1))
    ci95 = 1.96 * std / math.sqrt(len(arr))
    low = mean - ci95
    high = mean + ci95
    if bounded:
        low = max(low, 0.0)
        high = min(high, 1.0)
    return mean, std, low, high


def _compute_binary_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray | None = None,
) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    metrics = {
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
    if scores is None:
        metrics["pr_auc"] = None
        metrics["roc_auc"] = None
        metrics["ranking_metric_status"] = "scores_not_available"
    elif len(np.unique(y_true)) != 2:
        metrics["pr_auc"] = None
        metrics["roc_auc"] = None
        metrics["ranking_metric_status"] = "single_class_test_partition"
    else:
        scores = np.asarray(scores, dtype=float)
        if len(scores) != len(y_true) or not np.isfinite(scores).all():
            metrics["pr_auc"] = None
            metrics["roc_auc"] = None
            metrics["ranking_metric_status"] = "invalid_or_incomplete_scores"
        else:
            metrics["pr_auc"] = float(average_precision_score(y_true, scores))
            metrics["roc_auc"] = float(roc_auc_score(y_true, scores))
            metrics["ranking_metric_status"] = "ok"
    return metrics


def _positive_scores_from_model(model, X) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        if np.ndim(proba) == 2 and proba.shape[1] >= 2:
            return np.asarray(proba[:, 1], dtype=float)
        return np.asarray(proba, dtype=float).reshape(-1)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(X), dtype=float).reshape(-1)
        return 1.0 / (1.0 + np.exp(-raw))
    preds = np.asarray(model.predict(X), dtype=float).reshape(-1)
    return preds


def _threshold_metric_value(y_true: np.ndarray, scores: np.ndarray, threshold: float, metric: str) -> tuple[float, dict]:
    y_pred = (scores >= float(threshold)).astype(int)
    metrics = _compute_binary_metrics(y_true, y_pred)
    metric_key = str(metric).strip().lower()
    if metric_key == "f1":
        score = float(metrics["f1_1"])
    elif metric_key == "balanced_accuracy":
        score = float((metrics["recall_0"] + metrics["recall_1"]) / 2.0)
    elif metric_key == "youden_j":
        score = float(metrics["recall_1"] + metrics["recall_0"] - 1.0)
    else:
        raise ValueError(f"Unknown deployment_threshold_metric={metric!r}")
    metrics["threshold_metric_score"] = score
    return score, metrics


def _select_threshold_from_validation(y_true: np.ndarray, scores: np.ndarray) -> tuple[float, dict]:
    if len(np.unique(y_true)) != 2:
        raise ValueError("Deployment threshold selection requires both validation classes")
    strategy = str(
        NDSS_CONFIG.get("deployment_threshold_strategy", "max_recall_at_fpr")
    ).strip().lower()
    metric = str(NDSS_CONFIG.get("deployment_threshold_metric", "f1"))
    max_fpr = float(NDSS_CONFIG.get("deployment_max_validation_fpr", 0.05))
    grid_size = int(NDSS_CONFIG.get("deployment_threshold_grid_size", 101))
    clipped = np.clip(np.asarray(scores, dtype=float), 0.0, 1.0)
    unique_scores = np.unique(clipped)
    if len(unique_scores) <= grid_size:
        candidates = np.unique(
            np.concatenate(([0.0, 0.5, 1.0, np.nextafter(1.0, 2.0)], unique_scores))
        )
    else:
        quantiles = np.linspace(0.0, 1.0, grid_size)
        candidates = np.unique(
            np.concatenate(
                ([0.0, 0.5, 1.0, np.nextafter(1.0, 2.0)], np.quantile(clipped, quantiles))
            )
        )

    best_threshold = 0.5
    best_key: tuple[float, ...] | None = None
    best_metrics: dict | None = None
    for threshold in candidates:
        metric_score, metrics = _threshold_metric_value(y_true, clipped, float(threshold), metric)
        fpr = 1.0 - float(metrics["recall_0"])
        if strategy == "max_recall_at_fpr":
            if fpr > max_fpr + 1e-12:
                continue
            metric_score = float(metrics["recall_1"])
            tie_key = (
                metric_score,
                float(metrics["precision_1"]),
                float(metrics["f1_1"]),
                -fpr,
                float(threshold),
            )
        elif strategy == "metric":
            tie_key = (metric_score, -fpr, float(metrics["precision_1"]), float(threshold))
        else:
            raise ValueError(f"Unknown deployment_threshold_strategy={strategy!r}")
        if best_key is None or tie_key > best_key:
            best_key = tie_key
            best_threshold = float(threshold)
            best_metrics = metrics

    if best_metrics is None:
        raise RuntimeError(
            f"No validation threshold satisfies max FPR={max_fpr:.4f}; this indicates "
            "a threshold-candidate construction bug"
        )
    best_metrics["selected_threshold"] = float(best_threshold)
    best_metrics["threshold_metric"] = (
        "validation_recall_at_fpr_constraint" if strategy == "max_recall_at_fpr" else metric
    )
    best_metrics["threshold_strategy"] = strategy
    best_metrics["validation_max_fpr_constraint"] = max_fpr
    best_metrics["threshold_metric_score"] = float(best_key[0])
    best_metrics["validation_fpr"] = 1.0 - float(best_metrics["recall_0"])
    return float(best_threshold), best_metrics


def _fit_booster_with_validation(
    algo_name: str,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
) -> tuple[int, dict]:
    early_rounds = int(ML_CONFIG.get("early_stopping_rounds", 30))
    if algo_name == "XGBClassifier":
        model = get_algorithm(algo_name, early_stopping_rounds=early_rounds)
        _fit_model_with_safe_n_jobs(
            model,
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        best_iteration = getattr(model, "best_iteration", None)
        best_n_estimators = int(best_iteration) + 1 if best_iteration is not None else int(model.get_params()["n_estimators"])
        return max(best_n_estimators, 1), {
            "validation_only_early_stopping": True,
            "best_iteration": None if best_iteration is None else int(best_iteration),
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
        best_iteration = getattr(model, "best_iteration_", None) or getattr(model, "n_estimators_", None)
        if best_iteration is None:
            best_iteration = model.get_params()["n_estimators"]
        return max(int(best_iteration), 1), {
            "validation_only_early_stopping": True,
            "best_iteration": int(best_iteration),
        }
    raise ValueError(f"Unexpected booster algorithm: {algo_name}")


def _fit_model_with_safe_n_jobs(model, X, y, **fit_kwargs):
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


def _train_and_evaluate_repeat(
    algo_name: str,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    evaluation_mode: str,
) -> dict:
    X_train, y_train = _prepare_matrix(train_df, feature_cols)
    X_val, y_val = _prepare_matrix(validation_df, feature_cols)
    X_test, y_test = _prepare_matrix(test_df, feature_cols)
    mode = str(evaluation_mode).strip().lower()

    early_info = {
        "validation_only_early_stopping": False,
        "best_iteration": None,
        "best_n_estimators": None,
        "selected_threshold": 0.5,
        "threshold_metric": None,
        "validation_metric_score": None,
        "validation_precision_1": None,
        "validation_recall_1": None,
        "validation_f1_1": None,
        "validation_fpr": None,
        "threshold_strategy": None,
        "validation_max_fpr_constraint": None,
    }

    train_start = time.time()
    if algo_name in BOOSTER_ALGORITHMS:
        validation_scaler = StandardScaler()
        X_train_s = _as_feature_frame(validation_scaler.fit_transform(X_train), feature_cols)
        X_val_s = _as_feature_frame(validation_scaler.transform(X_val), feature_cols)
        best_n_estimators, early_info = _fit_booster_with_validation(
            algo_name, X_train_s, y_train, X_val_s, y_val
        )
        early_info["best_n_estimators"] = int(best_n_estimators)
        if mode == "balanced":
            train_val_df = pd.concat([train_df, validation_df], ignore_index=True)
            X_train_val, y_train_val = _prepare_matrix(train_val_df, feature_cols)
            final_scaler = StandardScaler()
            X_train_val_s = _as_feature_frame(final_scaler.fit_transform(X_train_val), feature_cols)
            X_test_s = _as_feature_frame(final_scaler.transform(X_test), feature_cols)
            model = get_algorithm(algo_name, n_estimators=best_n_estimators)
            _fit_model_with_safe_n_jobs(model, X_train_val_s, y_train_val)
            train_time = time.time() - train_start
            predict_start = time.time()
            test_scores = _positive_scores_from_model(model, X_test_s)
            y_pred = (test_scores >= 0.5).astype(int)
            predict_time = time.time() - predict_start
        elif mode == "deployment":
            model = get_algorithm(algo_name, n_estimators=best_n_estimators)
            _fit_model_with_safe_n_jobs(model, X_train_s, y_train)
            val_scores = _positive_scores_from_model(model, X_val_s)
            threshold, threshold_metrics = _select_threshold_from_validation(y_val, val_scores)
            X_test_s = _as_feature_frame(validation_scaler.transform(X_test), feature_cols)
            train_time = time.time() - train_start
            predict_start = time.time()
            test_scores = _positive_scores_from_model(model, X_test_s)
            y_pred = (test_scores >= threshold).astype(int)
            predict_time = time.time() - predict_start
            early_info.update(
                {
                    "selected_threshold": float(threshold),
                    "threshold_metric": str(threshold_metrics["threshold_metric"]),
                    "validation_metric_score": float(threshold_metrics["threshold_metric_score"]),
                    "validation_precision_1": float(threshold_metrics["precision_1"]),
                    "validation_recall_1": float(threshold_metrics["recall_1"]),
                    "validation_f1_1": float(threshold_metrics["f1_1"]),
                    "validation_fpr": float(threshold_metrics["validation_fpr"]),
                    "threshold_strategy": threshold_metrics["threshold_strategy"],
                    "validation_max_fpr_constraint": float(
                        threshold_metrics["validation_max_fpr_constraint"]
                    ),
                }
            )
        else:
            raise ValueError(f"Unknown NDSS evaluation_mode={evaluation_mode!r}")
    else:
        base_scaler = StandardScaler()
        X_train_s = _as_feature_frame(base_scaler.fit_transform(X_train), feature_cols)
        X_val_s = _as_feature_frame(base_scaler.transform(X_val), feature_cols)
        X_test_s = _as_feature_frame(base_scaler.transform(X_test), feature_cols)
        model = get_algorithm(algo_name)
        if model is None:
            raise ValueError(f"Unknown algorithm: {algo_name}")
        if mode == "balanced":
            train_val_df = pd.concat([train_df, validation_df], ignore_index=True)
            X_train_val, y_train_val = _prepare_matrix(train_val_df, feature_cols)
            final_scaler = StandardScaler()
            X_train_val_s = _as_feature_frame(final_scaler.fit_transform(X_train_val), feature_cols)
            X_test_s = _as_feature_frame(final_scaler.transform(X_test), feature_cols)
            _fit_model_with_safe_n_jobs(model, X_train_val_s, y_train_val)
            train_time = time.time() - train_start
            predict_start = time.time()
            test_scores = _positive_scores_from_model(model, X_test_s)
            y_pred = (test_scores >= 0.5).astype(int)
            predict_time = time.time() - predict_start
        elif mode == "deployment":
            _fit_model_with_safe_n_jobs(model, X_train_s, y_train)
            val_scores = _positive_scores_from_model(model, X_val_s)
            threshold, threshold_metrics = _select_threshold_from_validation(y_val, val_scores)
            train_time = time.time() - train_start
            predict_start = time.time()
            test_scores = _positive_scores_from_model(model, X_test_s)
            y_pred = (test_scores >= threshold).astype(int)
            predict_time = time.time() - predict_start
            early_info.update(
                {
                    "selected_threshold": float(threshold),
                    "threshold_metric": str(threshold_metrics["threshold_metric"]),
                    "validation_metric_score": float(threshold_metrics["threshold_metric_score"]),
                    "validation_precision_1": float(threshold_metrics["precision_1"]),
                    "validation_recall_1": float(threshold_metrics["recall_1"]),
                    "validation_f1_1": float(threshold_metrics["f1_1"]),
                    "validation_fpr": float(threshold_metrics["validation_fpr"]),
                    "threshold_strategy": threshold_metrics["threshold_strategy"],
                    "validation_max_fpr_constraint": float(
                        threshold_metrics["validation_max_fpr_constraint"]
                    ),
                }
            )
        else:
            raise ValueError(f"Unknown NDSS evaluation_mode={evaluation_mode!r}")
    metrics = _compute_binary_metrics(y_test, y_pred, test_scores)
    metrics.update(
        {
            "train_time_s": float(train_time),
            "predict_time_s": float(predict_time),
            "samples_per_second": float(len(y_test) / max(predict_time, 1e-9)),
            "n_test_samples": int(len(y_test)),
            **early_info,
        }
    )
    return metrics


LOCAL_NUMERIC_FIELDS = [
    "accuracy",
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
    "pr_auc",
    "roc_auc",
    "train_time_s",
    "predict_time_s",
    "samples_per_second",
    "n_test_samples",
    "test_support_0",
    "test_support_1",
    "best_iteration",
    "best_n_estimators",
    "selected_threshold",
    "validation_metric_score",
    "validation_precision_1",
    "validation_recall_1",
    "validation_f1_1",
    "validation_fpr",
    "validation_max_fpr_constraint",
]


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


def _summarise_local_rows(rows: list[dict], expected_repeats: int) -> dict | None:
    if len(rows) != expected_repeats:
        return None
    first = rows[0]
    fold_specific = {
        "repeat_index",
        "fold_index",
        "outer_seed",
        "inner_seed",
        "seed",
        "held_out_malware_capture_id",
        "held_out_malware_family",
        "train_capture_ids",
        "validation_capture_ids",
        "test_capture_ids",
        "train_support",
        "validation_support",
        "test_support",
        "test_positive_rate",
        "ranking_metric_status",
    }
    summary = {
        key: value
        for key, value in first.items()
        if key not in ({"record_type"} | fold_specific) and key not in LOCAL_NUMERIC_FIELDS
    }
    summary["record_type"] = "summary"
    summary["n_repeats"] = int(expected_repeats)
    summary["held_out_malware_families"] = [
        row.get("held_out_malware_family") for row in rows
    ]
    summary["fold_test_support"] = [row.get("test_support") for row in rows]
    for field in LOCAL_NUMERIC_FIELDS:
        values = _complete_numeric_values(rows, field, expected_repeats)
        if values is None:
            continue
        bounded = field in {"accuracy", "precision_0", "precision_1", "recall_0", "recall_1", "f1_0", "f1_1"}
        mean, std, low, high = _metric_stats(values, bounded=bounded)
        summary[field] = mean
        summary[f"{field}_std"] = std
        summary[f"{field}_ci95_low"] = low
        summary[f"{field}_ci95_high"] = high
        summary[f"{field}_median"] = float(np.median(values))
        summary[f"{field}_q1"] = float(np.quantile(values, 0.25))
        summary[f"{field}_q3"] = float(np.quantile(values, 0.75))
        summary[f"{field}_min"] = float(np.min(values))
        summary[f"{field}_max"] = float(np.max(values))
    summary["aggregation_unit"] = "held-out capture/family fold"
    summary["dispersion_interpretation"] = (
        "between-fold heterogeneity; standard deviation is not a score range"
    )
    pooled_tn = sum(int(row["tn"]) for row in rows)
    pooled_fp = sum(int(row["fp"]) for row in rows)
    pooled_fn = sum(int(row["fn"]) for row in rows)
    pooled_tp = sum(int(row["tp"]) for row in rows)
    pooled_total = pooled_tn + pooled_fp + pooled_fn + pooled_tp
    summary["pooled_accuracy"] = float((pooled_tp + pooled_tn) / pooled_total)
    summary["pooled_recall_1"] = float(pooled_tp / max(pooled_tp + pooled_fn, 1))
    summary["pooled_precision_1"] = float(pooled_tp / max(pooled_tp + pooled_fp, 1))
    summary["pooled_f1_1"] = float(
        2 * pooled_tp / max(2 * pooled_tp + pooled_fp + pooled_fn, 1)
    )
    return summary


def _ci_text(row: dict, key: str) -> str:
    low = row.get(f"{key}_ci95_low")
    high = row.get(f"{key}_ci95_high")
    if low is None or high is None:
        return "N/A"
    return f"[{low:.4f}, {high:.4f}]"


def run_local_ndss_experiment(
    dataset: pd.DataFrame,
    feature_cols: list[str],
    manifest: dict,
    manifest_path: Path,
    *,
    experiment_name: str,
    algorithms: list[str],
    evaluation_mode: str,
) -> list[dict]:
    materialized = materialize_session_splits(dataset, manifest)
    split_type = manifest["split_type"]
    split_mode = manifest["split_mode"]
    expected_repeats = len(materialized)
    print("\n" + "=" * 70)
    print(f"Session Local Experiment: {experiment_name}")
    print(
        f"Protocol: {split_type} | folds={expected_repeats} | "
        f"features={dataset['feature_set'].iloc[0]} | sample_unit={dataset['sample_unit'].iloc[0]} | "
        f"evaluation_mode={evaluation_mode}"
    )
    print(f"Interpretation: {manifest['interpretation']}")
    print(f"Manifest: {manifest_path.name} | cohort_hash={manifest.get('cohort_hash', 'n/a')}")
    print("=" * 70)

    repeat_rows: list[dict] = []
    summary_rows: list[dict] = []
    for algo_name in algorithms:
        short = SHORT_NAMES.get(algo_name, algo_name)
        print(f"\n  Training {short} across {expected_repeats} folds...", end=" ", flush=True)
        algo_rows: list[dict] = []
        for repeat_meta, train_df, validation_df, test_df in materialized:
            base_row = {
                "experiment": experiment_name,
                "algorithm": short,
                "split_type": split_type,
                "split_mode": split_mode,
                "record_type": "repeat",
                "repeat_index": int(repeat_meta["repeat_index"]),
                "fold_index": int(repeat_meta["fold_index"]),
                "seed": int(repeat_meta["seed"]),
                "held_out_malware_capture_id": repeat_meta.get(
                    "held_out_malware_capture_id"
                ),
                "held_out_malware_family": repeat_meta.get("held_out_malware_family"),
                "train_capture_ids": repeat_meta["train_capture_ids"],
                "validation_capture_ids": repeat_meta["validation_capture_ids"],
                "test_capture_ids": repeat_meta["test_capture_ids"],
                "train_support": repeat_meta["train"],
                "validation_support": repeat_meta["validation"],
                "test_support": repeat_meta["test"],
                "test_positive_rate": float(repeat_meta["test"]["positive_rate"]),
                "manifest_hash": manifest.get("manifest_hash"),
                "manifest_path": str(manifest_path.resolve()),
                "cohort_hash": manifest.get("cohort_hash"),
                "feature_set": str(train_df["feature_set"].iloc[0]),
                "sample_unit": str(train_df["sample_unit"].iloc[0]),
                "window_seconds": _json_scalar(train_df["window_seconds"].iloc[0]),
                "evaluation_mode": evaluation_mode,
                "suite": "session_local",
                "phase": 7,
            }
            result = _train_and_evaluate_repeat(
                algo_name,
                train_df,
                validation_df,
                test_df,
                feature_cols,
                evaluation_mode=evaluation_mode,
            )
            algo_rows.append({**base_row, **result})

        repeat_rows.extend(algo_rows)
        summary = _summarise_local_rows(algo_rows, expected_repeats)
        if summary is not None:
            summary_rows.append(summary)
            print(
                f"Acc median={summary['accuracy_median']:.4f} "
                f"IQR=[{summary['accuracy_q1']:.4f}, {summary['accuracy_q3']:.4f}] "
                f"min/max=[{summary['accuracy_min']:.4f}, {summary['accuracy_max']:.4f}]  "
                f"F1 median={summary['f1_1_median']:.4f}"
            )
        else:
            print("[INCOMPLETE]")
    return repeat_rows + summary_rows


def _print_session_local_table(results: list[dict], experiment_name: str) -> None:
    summaries = [
        row for row in results
        if row.get("experiment") == experiment_name and row.get("record_type") == "summary"
    ]
    if not summaries:
        return
    rows = []
    for row in summaries:
        rows.append(
            [
                row["algorithm"],
                f"{row['accuracy_median']:.4f} "
                f"[{row['accuracy_q1']:.4f}, {row['accuracy_q3']:.4f}]",
                f"[{row['accuracy_min']:.4f}, {row['accuracy_max']:.4f}]",
                f"{row['f1_1_median']:.4f} "
                f"[{row['f1_1_q1']:.4f}, {row['f1_1_q3']:.4f}]",
                f"[{row['f1_1_min']:.4f}, {row['f1_1_max']:.4f}]",
                f"{row.get('pooled_accuracy', 0):.4f}",
                f"{row.get('pooled_f1_1', 0):.4f}",
            ]
        )
    print(f"\nHeld-Out-Capture Summary - {experiment_name}")
    print(
        tabulate(
            rows,
            headers=[
                "Model",
                "Accuracy median [IQR]",
                "Accuracy min/max",
                "F1(mal) median [IQR]",
                "F1(mal) min/max",
                "Pooled accuracy",
                "Pooled F1(mal)",
            ],
            tablefmt="grid",
        )
    )


def _random_subset(df: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if len(df) <= int(sample_size):
        return df.copy()
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(df), size=int(sample_size), replace=False)
    return df.iloc[idx].copy()


def _family_label(value) -> str:
    text = str(value or "").strip()
    return text if text else "Unknown"


def _expected_malware_families() -> list[str]:
    return [
        str(family).strip()
        for family in NDSS_CONFIG.get("expected_malware_families", [])
        if str(family).strip()
    ]


def _malicious_family_counts(df: pd.DataFrame) -> dict[str, int]:
    if "is_malicious" not in df.columns or "malware_family" not in df.columns:
        return {}
    malicious = df[df["is_malicious"].astype(int) == 1]
    counts = Counter(_family_label(value) for value in malicious["malware_family"])
    return {family: int(count) for family, count in sorted(counts.items())}


def _missing_expected_families(family_counts: dict[str, int]) -> list[str]:
    observed = {family for family, count in family_counts.items() if int(count) > 0}
    return [family for family in _expected_malware_families() if family not in observed]


def _stratified_subset_by_family(df: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if len(df) <= int(sample_size):
        return df.copy()
    if "malware_family" not in df.columns:
        return _random_subset(df, int(sample_size), seed)

    work = df.copy()
    work["_family_label"] = work["malware_family"].map(_family_label)
    groups = [
        (family, group.reset_index(drop=True))
        for family, group in work.groupby("_family_label", sort=True)
    ]
    if not groups:
        return work.drop(columns=["_family_label"], errors="ignore")

    rng = np.random.default_rng(seed)
    quotas = {family: 0 for family, _group in groups}
    capacities = {family: len(group) for family, group in groups}
    remaining = int(sample_size)

    active = [family for family, _group in groups if capacities[family] > 0]
    while remaining > 0 and active:
        order = list(rng.permutation(active))
        allocated_this_round = 0
        for family in order:
            if remaining <= 0:
                break
            if quotas[family] >= capacities[family]:
                continue
            quotas[family] += 1
            remaining -= 1
            allocated_this_round += 1
        active = [family for family in active if quotas[family] < capacities[family]]
        if allocated_this_round == 0:
            break

    chosen_parts = []
    for family, group in groups:
        take = quotas[family]
        if take <= 0:
            continue
        idx = rng.choice(len(group), size=take, replace=False)
        chosen_parts.append(group.iloc[idx])
    if not chosen_parts:
        return work.iloc[[]].drop(columns=["_family_label"], errors="ignore")
    return pd.concat(chosen_parts, ignore_index=True).drop(columns=["_family_label"], errors="ignore")


def _balanced_subset(
    df: pd.DataFrame,
    sample_size: int,
    seed: int,
    *,
    family_stratified: bool = False,
) -> pd.DataFrame:
    if len(df) <= sample_size:
        return df.sort_values("packet_id").reset_index(drop=True)
    mal = df[df["is_malicious"] == 1]
    norm = df[df["is_malicious"] == 0]
    target_each = min(int(sample_size) // 2, len(mal), len(norm))
    if target_each <= 0:
        return df.iloc[[]].copy()
    mal_subset = (
        _stratified_subset_by_family(mal, target_each, seed + 13)
        if family_stratified
        else _random_subset(mal, target_each, seed + 13)
    )
    norm_subset = _random_subset(norm, target_each, seed + 29)
    chosen_parts = [mal_subset, norm_subset]
    subset = pd.concat(chosen_parts, ignore_index=True)
    return subset.sort_values("packet_id").reset_index(drop=True)


def _natural_subset(df: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    if len(df) <= sample_size:
        return df.sort_values("packet_id").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    sample_size = int(sample_size)
    for _attempt in range(32):
        idx = rng.choice(len(df), size=sample_size, replace=False)
        subset = df.iloc[idx].copy()
        if subset["is_malicious"].nunique() >= 2:
            return subset.sort_values("packet_id").reset_index(drop=True)

    mal = df[df["is_malicious"] == 1]
    norm = df[df["is_malicious"] == 0]
    if mal.empty or norm.empty:
        return _random_subset(df, sample_size, seed + 101).sort_values("packet_id").reset_index(drop=True)

    forced_parts = [
        _random_subset(mal, 1, seed + 211),
        _random_subset(norm, 1, seed + 307),
    ]
    remaining = max(sample_size - 2, 0)
    already = set(pd.concat(forced_parts, ignore_index=True)["packet_id"].astype(int).tolist())
    pool = df[~df["packet_id"].astype(int).isin(already)]
    if remaining > 0 and not pool.empty:
        forced_parts.append(_random_subset(pool, min(remaining, len(pool)), seed + 401))
    subset = pd.concat(forced_parts, ignore_index=True)
    return subset.sort_values("packet_id").reset_index(drop=True)


def _sample_eval_subset(
    df: pd.DataFrame,
    sample_size: int | None,
    seed: int,
    evaluation_mode: str,
    *,
    family_stratified: bool = False,
) -> pd.DataFrame:
    if sample_size is None or sample_size <= 0:
        return df.sort_values("packet_id").reset_index(drop=True)
    mode = str(evaluation_mode).strip().lower()
    if mode == "balanced":
        return _balanced_subset(df, int(sample_size), seed, family_stratified=family_stratified)
    if mode == "deployment":
        return _natural_subset(df, int(sample_size), seed)
    raise ValueError(f"Unknown NDSS evaluation_mode={evaluation_mode!r}")


def _positive_score_from_llm_response(response: dict) -> float | None:
    prediction = int(response.get("prediction", -1))
    confidence = float(response.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    if prediction == 1:
        return confidence
    if prediction == 0:
        return 1.0 - confidence
    return None


def _label_text(value: int) -> str:
    return "malicious" if int(value) == 1 else "normal"


def _truncate_text(value: str, limit: int) -> str:
    text = str(value)
    if len(text) <= int(limit):
        return text
    return text[: int(limit)] + "...[truncated]"


def _build_llm_memory_context(
    train_df: pd.DataFrame,
    *,
    feature_set: str,
    sample_unit: str,
    seed: int,
) -> tuple[str, dict]:
    examples_per_class = int(NDSS_CONFIG.get("llm_memory_examples_per_class", 4))
    chars_per_example = int(NDSS_CONFIG.get("llm_memory_chars_per_example", 900))
    rng = np.random.default_rng(seed)

    class_counts = train_df["is_malicious"].astype(int).value_counts().to_dict()
    family_counts = (
        train_df[train_df["is_malicious"].astype(int) == 1]["malware_family"]
        .fillna("")
        .replace("", "Unknown")
        .value_counts()
        .head(8)
        .to_dict()
    )

    examples: list[dict] = []
    for label in [0, 1]:
        label_df = train_df[train_df["is_malicious"].astype(int) == label]
        if label_df.empty:
            continue
        take = min(examples_per_class, len(label_df))
        chosen_idx = rng.choice(len(label_df), size=take, replace=False)
        for row in label_df.iloc[chosen_idx].sort_values("packet_id").to_dict("records"):
            examples.append(
                {
                    "label": _label_text(int(row["is_malicious"])),
                    "malware_family": str(row.get("malware_family") or "benign"),
                    "sample": _truncate_text(str(row["sequence_json"]), chars_per_example),
                }
            )

    context_payload = {
        "purpose": "training-split ground-truth context for held-out classification",
        "feature_set": feature_set,
        "sample_unit": sample_unit,
        "class_counts": {
            "normal": int(class_counts.get(0, 0)),
            "malicious": int(class_counts.get(1, 0)),
        },
        "malicious_family_counts": {str(k): int(v) for k, v in family_counts.items()},
        "examples": examples,
    }
    context = (
        "Ground-truth context from the training split only. Use these labeled "
        "examples as calibration memory, but classify the held-out sample independently.\n"
        + json.dumps(context_payload, separators=(",", ":"))
    )
    metadata = {
        "llm_context_mode": "memory",
        "memory_n_examples": len(examples),
        "memory_context_hash": hashlib.sha256(context.encode("utf-8")).hexdigest()[:16],
    }
    return context, metadata


def _summarise_llm_rows(rows: list[dict], experiment_name: str) -> list[dict]:
    sample_rows = [row for row in rows if row.get("record_type") is None]
    by_repeat: dict[int, list[dict]] = defaultdict(list)
    for row in sample_rows:
        by_repeat[int(row["repeat_index"])].append(row)

    repeat_metric_rows: list[dict] = []
    for repeat_index, samples in sorted(by_repeat.items()):
        y_true = [int(r["ground_truth"]) for r in samples]
        invalid_count = sum(1 for r in samples if int(r.get("prediction", -1)) not in (0, 1))
        # Invalid LLM outputs are counted as wrong predictions so parse/API
        # failures cannot silently improve the aggregate metrics.
        y_pred = [
            int(r["prediction"])
            if int(r.get("prediction", -1)) in (0, 1)
            else 1 - int(r["ground_truth"])
            for r in samples
        ]
        raw_scores = [r.get("positive_score") for r in samples]
        score_array = None
        if all(value is not None and np.isfinite(float(value)) for value in raw_scores):
            score_array = np.asarray(raw_scores, dtype=float)
        metrics = _compute_binary_metrics(
            np.asarray(y_true), np.asarray(y_pred), score_array
        )
        metrics["invalid_count"] = int(invalid_count)
        metrics["valid_count"] = int(len(samples) - invalid_count)
        metrics["avg_latency_ms"] = float(np.mean([float(r.get("latency_ms", 0.0)) for r in samples]))
        metrics["avg_tokens"] = float(np.mean([float(r.get("tokens", 0.0)) for r in samples]))
        metrics["repeat_index"] = repeat_index
        metrics["experiment"] = experiment_name
        metrics["record_type"] = "repeat_metrics"
        metrics["suite"] = rows[0]["suite"]
        metrics["phase"] = 7
        metrics["feature_set"] = rows[0]["feature_set"]
        metrics["sample_unit"] = rows[0]["sample_unit"]
        metrics["window_seconds"] = rows[0].get("window_seconds")
        metrics["evaluation_mode"] = rows[0].get("evaluation_mode")
        metrics["llm_context_mode"] = samples[0].get("llm_context_mode", "blind")
        metrics["memory_n_examples"] = samples[0].get("memory_n_examples", 0)
        metrics["memory_context_hash"] = samples[0].get("memory_context_hash")
        metrics["model"] = rows[0]["model"]
        metrics["split_mode"] = samples[0].get("split_mode")
        metrics["fold_index"] = int(samples[0].get("fold_index", repeat_index))
        metrics["held_out_malware_capture_id"] = samples[0].get(
            "held_out_malware_capture_id"
        )
        metrics["held_out_malware_family"] = samples[0].get(
            "held_out_malware_family"
        )
        metrics["test_support"] = samples[0].get("test_support")
        for field in (
            "selected_threshold",
            "threshold_metric",
            "threshold_metric_score",
            "threshold_strategy",
            "validation_fpr",
            "validation_max_fpr_constraint",
            "full_test_positive_rate",
            "budgeted_test_positive_rate",
        ):
            metrics[field] = samples[0].get(field)
        repeat_metric_rows.append(metrics)

    if not repeat_metric_rows:
        return []

    family_summary_rows: list[dict] = []
    malicious_rows = [
        row for row in sample_rows
        if int(row.get("ground_truth", 0)) == 1
    ]
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in malicious_rows:
        by_family[_family_label(row.get("malware_family"))].append(row)
    malicious_family_support = {
        family: int(len(family_rows))
        for family, family_rows in sorted(by_family.items())
    }
    for family, family_rows in sorted(by_family.items()):
        n_family = len(family_rows)
        invalid_count = sum(1 for row in family_rows if int(row.get("prediction", -1)) not in (0, 1))
        detected = sum(1 for row in family_rows if int(row.get("prediction", -1)) == 1)
        family_summary_rows.append(
            {
                "experiment": experiment_name,
                "record_type": "family_summary",
                "suite": rows[0]["suite"],
                "phase": 7,
                "feature_set": rows[0]["feature_set"],
                "sample_unit": rows[0]["sample_unit"],
                "window_seconds": rows[0].get("window_seconds"),
                "evaluation_mode": rows[0].get("evaluation_mode"),
                "split_mode": rows[0].get("split_mode"),
                "llm_context_mode": rows[0].get("llm_context_mode", "blind"),
                "memory_n_examples": rows[0].get("memory_n_examples", 0),
                "memory_context_hash": rows[0].get("memory_context_hash"),
                "model": rows[0]["model"],
                "malware_family": family,
                "n_samples": int(n_family),
                "detected_count": int(detected),
                "missed_count": int(n_family - detected - invalid_count),
                "invalid_count": int(invalid_count),
                "detection_rate": float(detected / n_family) if n_family else 0.0,
                "invalid_rate": float(invalid_count / n_family) if n_family else 0.0,
            }
        )

    summary = {
        "experiment": experiment_name,
        "record_type": "summary",
        "suite": rows[0]["suite"],
        "phase": 7,
        "feature_set": rows[0]["feature_set"],
        "sample_unit": rows[0]["sample_unit"],
        "window_seconds": rows[0].get("window_seconds"),
        "evaluation_mode": rows[0].get("evaluation_mode"),
        "llm_context_mode": rows[0].get("llm_context_mode", "blind"),
        "memory_n_examples": rows[0].get("memory_n_examples", 0),
        "memory_context_hash": None,
        "memory_context_hashes": sorted(
            {
                str(row["memory_context_hash"])
                for row in repeat_metric_rows
                if row.get("memory_context_hash")
            }
        ),
        "n_repeats": len(repeat_metric_rows),
        "model": rows[0]["model"],
        "n_malicious_families": len(by_family),
        "malicious_family_support": malicious_family_support,
        "expected_malicious_families": _expected_malware_families(),
        "missing_malicious_families": _missing_expected_families(malicious_family_support),
        "split_mode": rows[0].get("split_mode"),
        "held_out_malware_families": [
            row.get("held_out_malware_family") for row in repeat_metric_rows
        ],
        "fold_test_support": [row.get("test_support") for row in repeat_metric_rows],
        "aggregation_unit": "held-out capture/family fold",
        "dispersion_interpretation": (
            "between-fold heterogeneity; standard deviation is not a score range"
        ),
    }
    fields = [
        "accuracy",
        "precision_1",
        "recall_1",
        "f1_1",
        "pr_auc",
        "roc_auc",
        "avg_latency_ms",
        "avg_tokens",
        "tp",
        "fp",
        "fn",
        "tn",
        "invalid_count",
        "valid_count",
    ]
    for field in fields:
        if any(r.get(field) is None for r in repeat_metric_rows):
            continue
        values = [float(r[field]) for r in repeat_metric_rows]
        bounded = field in {
            "accuracy", "precision_1", "recall_1", "f1_1", "pr_auc", "roc_auc"
        }
        mean, std, low, high = _metric_stats(values, bounded=bounded)
        summary[field] = mean
        summary[f"{field}_std"] = std
        summary[f"{field}_ci95_low"] = low
        summary[f"{field}_ci95_high"] = high
        summary[f"{field}_median"] = float(np.median(values))
        summary[f"{field}_q1"] = float(np.quantile(values, 0.25))
        summary[f"{field}_q3"] = float(np.quantile(values, 0.75))
        summary[f"{field}_min"] = float(np.min(values))
        summary[f"{field}_max"] = float(np.max(values))
    return repeat_metric_rows + family_summary_rows + [summary]


def run_llm_ndss_experiment(
    dataset: pd.DataFrame,
    manifest: dict,
    *,
    experiment_name: str,
    provider: str,
    dry_run: bool,
    evaluation_mode: str,
    llm_context_mode: str = "blind",
    model_override: str | None = None,
    allowed_repeat_indices: set[int] | None = None,
    checkpoint_path: Path | None = None,
    checkpoint_prefix_rows: list[dict] | None = None,
    balanced_samples_per_repeat: int | None = None,
    deployment_validation_samples_per_repeat: int | None = None,
    deployment_test_samples_per_repeat: int | None = None,
    family_stratified_balanced: bool = False,
) -> list[dict]:
    materialized = materialize_session_splits(dataset, manifest)
    if allowed_repeat_indices is not None:
        materialized = [
            item for item in materialized
            if int(item[0]["repeat_index"]) in allowed_repeat_indices
        ]
    if not materialized:
        raise ValueError(
            f"No frozen folds selected; requested indices={sorted(allowed_repeat_indices or [])}, "
            f"available=0..{int(manifest['n_folds']) - 1}"
        )
    sample_unit = str(dataset["sample_unit"].iloc[0])
    feature_set = str(dataset["feature_set"].iloc[0])
    context_mode = str(llm_context_mode).strip().lower()
    if context_mode not in {"blind", "memory"}:
        raise ValueError(f"Unknown llm_context_mode={llm_context_mode!r}")
    llm_rows: list[dict] = []
    if dry_run:
        memory_context = ""
        memory_metadata = {
            "llm_context_mode": context_mode,
            "memory_n_examples": 0,
            "memory_context_hash": None,
        }
        if context_mode == "memory":
            memory_context, memory_metadata = _build_llm_memory_context(
                materialized[0][1],
                feature_set=feature_set,
                sample_unit=sample_unit,
                seed=int(ML_CONFIG["random_state"]),
            )
        example = materialized[0][3].iloc[0].to_dict()
        print("\n" + "=" * 70)
        print(f"Session LLM dry-run: {experiment_name}")
        print(f"Evaluation mode: {evaluation_mode}")
        print(f"LLM context mode: {context_mode}")
        print(f"Memory metadata: {memory_metadata}")
        available_test_family_counts: Counter[str] = Counter()
        for _repeat_meta, _train_df, _validation_df, full_test_df in materialized:
            available_test_family_counts.update(_malicious_family_counts(full_test_df))
        available_test_families = {
            family: int(count)
            for family, count in sorted(available_test_family_counts.items())
        }
        missing_available_families = _missing_expected_families(available_test_families)
        print(f"Available test malicious families: {available_test_families or 'none'}")
        if missing_available_families:
            print(
                "[COVERAGE WARNING] Frozen test folds are missing expected malware "
                f"families: {missing_available_families}"
            )
        print("-" * 70)
        print(build_system_prompt(feature_set, sample_unit))
        print("-" * 70)
        user_prompt = build_user_prompt(example)
        if memory_context:
            user_prompt = memory_context + "\n\nHeld-out sample:\n" + user_prompt
        print(user_prompt)
        print("=" * 70)
        return []

    client = LLMClient(provider=provider)
    if model_override:
        client.model = model_override

    mode = str(evaluation_mode).strip().lower()
    balanced_limit = int(
        balanced_samples_per_repeat
        if balanced_samples_per_repeat is not None
        else NDSS_CONFIG.get("llm_balanced_eval_samples_per_repeat", 80)
    )
    deployment_val_limit = int(
        deployment_validation_samples_per_repeat
        if deployment_validation_samples_per_repeat is not None
        else NDSS_CONFIG.get("llm_deployment_validation_samples_per_repeat", 80)
    )
    deployment_test_limit = int(
        deployment_test_samples_per_repeat
        if deployment_test_samples_per_repeat is not None
        else NDSS_CONFIG.get("llm_deployment_test_samples_per_repeat", 160)
    )
    if mode == "balanced":
        estimated_calls = len(materialized) * balanced_limit
    elif mode == "deployment":
        estimated_calls = len(materialized) * (deployment_val_limit + deployment_test_limit)
    else:
        estimated_calls = 0
    progress_every = max(1, int(NDSS_CONFIG.get("llm_progress_every_calls", 20)))
    call_counter = 0
    checkpoint_prefix_rows = checkpoint_prefix_rows or []

    print("\n" + "=" * 70, flush=True)
    print(f"Session LLM Experiment: {experiment_name}", flush=True)
    print(
        f"Provider/model: {provider}/{client.model} | evaluation_mode={mode} | "
        f"context={context_mode} | repeats={len(materialized)} | "
        f"estimated_calls={estimated_calls}",
        flush=True,
    )
    print(f"feature_set={feature_set} | sample_unit={sample_unit}", flush=True)
    available_test_family_counts: Counter[str] = Counter()
    for _repeat_meta, _train_df, _validation_df, full_test_df in materialized:
        available_test_family_counts.update(_malicious_family_counts(full_test_df))
    available_test_families = {family: int(count) for family, count in sorted(available_test_family_counts.items())}
    missing_available_families = _missing_expected_families(available_test_families)
    print(f"available_test_malicious_families={available_test_families or 'none'}", flush=True)
    if missing_available_families:
        print(
            "[COVERAGE WARNING] Frozen test folds are missing expected malware "
            f"families: {missing_available_families}",
            flush=True,
        )
    if checkpoint_path is not None:
        print(f"Partial checkpoint: {checkpoint_path}", flush=True)
    print("=" * 70, flush=True)

    def checkpoint_progress() -> None:
        if checkpoint_path is not None:
            _write_result_rows(checkpoint_path, checkpoint_prefix_rows + llm_rows)

    def note_call(stage: str) -> None:
        nonlocal call_counter
        call_counter += 1
        if call_counter % progress_every == 0 or call_counter == estimated_calls:
            avg_latency = client.total_tokens / max(client.total_calls, 1)
            print(
                f"    [LLM PROGRESS] {experiment_name} | {stage} | "
                f"calls={call_counter}/{estimated_calls} | "
                f"client_calls={client.total_calls} | tokens={client.total_tokens} | "
                f"avg_tokens_per_call={avg_latency:.1f}",
                flush=True,
            )
            checkpoint_progress()

    for repeat_number, (repeat_meta, _train_df, _validation_df, test_df) in enumerate(materialized, start=1):
        repeat_index = int(repeat_meta["repeat_index"])
        repeat_seed = int(ML_CONFIG["random_state"]) + repeat_index * 1000
        memory_context = ""
        memory_metadata = {
            "llm_context_mode": context_mode,
            "memory_n_examples": 0,
            "memory_context_hash": None,
        }
        if context_mode == "memory":
            memory_context, memory_metadata = _build_llm_memory_context(
                _train_df,
                feature_set=feature_set,
                sample_unit=sample_unit,
                seed=repeat_seed + 7,
            )
        if mode == "balanced":
            eval_df = _sample_eval_subset(
                test_df,
                balanced_limit,
                repeat_seed,
                mode,
                family_stratified=family_stratified_balanced,
            )
            selected_threshold = 0.5
            threshold_metric = None
            threshold_metric_score = None
            threshold_strategy = "fixed_0.5_balanced_protocol"
            validation_fpr = None
            validation_max_fpr_constraint = None
        elif mode == "deployment":
            validation_df = _sample_eval_subset(_validation_df, deployment_val_limit, repeat_seed + 17, mode)
            validation_family_counts = _malicious_family_counts(validation_df)
            val_scores: list[float] = []
            val_labels: list[int] = []
            print(
                f"  Repeat {repeat_number}/{len(materialized)} "
                f"(index={repeat_index}) validation_samples={len(validation_df)} "
                f"validation_families={validation_family_counts or 'none'}",
                flush=True,
            )
            for row in validation_df.to_dict("records"):
                sys_prompt = build_system_prompt(feature_set, sample_unit)
                user_prompt = build_user_prompt(row)
                if memory_context:
                    user_prompt = memory_context + "\n\nHeld-out validation sample:\n" + user_prompt
                response = client.classify(sys_prompt, user_prompt, max_tokens=256)
                note_call("validation")
                pos_score = _positive_score_from_llm_response(response)
                if pos_score is None:
                    continue
                val_scores.append(float(pos_score))
                val_labels.append(int(row["is_malicious"]))
            if len(val_scores) != len(validation_df) or len(set(val_labels)) < 2:
                raise RuntimeError(
                    "Deployment LLM threshold calibration is incomplete: every validation "
                    "response must parse and both classes must be represented. Test samples "
                    "were not evaluated for this fold."
                )
            selected_threshold, threshold_metrics = _select_threshold_from_validation(
                np.asarray(val_labels, dtype=int),
                np.asarray(val_scores, dtype=float),
            )
            threshold_metric = str(threshold_metrics["threshold_metric"])
            threshold_metric_score = float(threshold_metrics["threshold_metric_score"])
            threshold_strategy = str(threshold_metrics["threshold_strategy"])
            validation_fpr = float(threshold_metrics["validation_fpr"])
            validation_max_fpr_constraint = float(
                threshold_metrics["validation_max_fpr_constraint"]
            )
            eval_df = _sample_eval_subset(test_df, deployment_test_limit, repeat_seed + 31, mode)
        else:
            raise ValueError(f"Unknown NDSS evaluation_mode={evaluation_mode!r}")

        print(
            f"  Repeat {repeat_number}/{len(materialized)} "
            f"(index={repeat_index}) test_samples={len(eval_df)} "
            f"test_families={_malicious_family_counts(eval_df) or 'none'}",
            flush=True,
        )
        for row in eval_df.to_dict("records"):
            sys_prompt = build_system_prompt(feature_set, sample_unit)
            user_prompt = build_user_prompt(row)
            if memory_context:
                user_prompt = memory_context + "\n\nHeld-out test sample:\n" + user_prompt
            response = client.classify(sys_prompt, user_prompt, max_tokens=256)
            note_call("test")
            final_prediction = int(response.get("prediction", -1))
            positive_score = _positive_score_from_llm_response(response)
            if mode == "deployment" and positive_score is not None:
                final_prediction = 1 if positive_score >= float(selected_threshold) else 0
            llm_rows.append(
                {
                    "experiment": experiment_name,
                    "repeat_index": repeat_index,
                    "fold_index": int(repeat_meta["fold_index"]),
                    "split_mode": manifest["split_mode"],
                    "held_out_malware_capture_id": repeat_meta.get(
                        "held_out_malware_capture_id"
                    ),
                    "held_out_malware_family": repeat_meta.get(
                        "held_out_malware_family"
                    ),
                    "test_capture_ids": repeat_meta["test_capture_ids"],
                    "test_support": repeat_meta["test"],
                    "suite": "session_llm" if model_override is None else "session_finetune_eval",
                    "phase": 7,
                    "feature_set": feature_set,
                    "sample_unit": sample_unit,
                    "window_seconds": _json_scalar(row.get("window_seconds")),
                    "evaluation_mode": evaluation_mode,
                    **memory_metadata,
                    "selected_threshold": float(selected_threshold),
                    "threshold_metric": threshold_metric,
                    "threshold_metric_score": threshold_metric_score,
                    "threshold_strategy": threshold_strategy,
                    "validation_fpr": validation_fpr,
                    "validation_max_fpr_constraint": validation_max_fpr_constraint,
                    "full_test_positive_rate": float(repeat_meta["test"]["positive_rate"]),
                    "budgeted_test_positive_rate": float(
                        eval_df["is_malicious"].astype(int).mean()
                    ),
                    "positive_score": None if positive_score is None else float(positive_score),
                    "raw_prediction": int(response.get("prediction", -1)),
                    "packet_id": int(row["packet_id"]),
                    "session_id": int(row["session_id"]),
                    "dataset_id": int(row["dataset_id"]),
                    "malware_family": str(row.get("malware_family") or "benign"),
                    "ground_truth": int(row["is_malicious"]),
                    "prediction": final_prediction,
                    "confidence": float(response.get("confidence", 0.0)),
                    "reasoning": str(response.get("reasoning", "")),
                    "tokens": int(response.get("tokens", 0)),
                    "latency_ms": float(response.get("latency_ms", 0.0)),
                    "model": client.model,
                }
            )
        checkpoint_progress()
    llm_rows.extend(_summarise_llm_rows(llm_rows, experiment_name))
    checkpoint_progress()
    print(
        f"Completed {experiment_name}: calls={call_counter}, "
        f"tokens={client.total_tokens}, rows={len(llm_rows)}",
        flush=True,
    )
    return llm_rows


def _default_specs(
    evaluation_mode: str,
    split_mode: str,
) -> tuple[list[NDSSDatasetSpec], list[NDSSDatasetSpec], NDSSDatasetSpec]:
    group_by = "capture"
    session_size = int(NDSS_CONFIG.get("session_sample_size", 6000))
    packet_size = int(NDSS_CONFIG.get("packet_ablation_sample_size", 3000))
    llm_specs: list[NDSSDatasetSpec] = []
    local_specs: list[NDSSDatasetSpec] = []
    for feature_set in NDSS_CONFIG.get("feature_sets", ["minimal", "mercury", "combined"]):
        local_specs.append(
            NDSSDatasetSpec(
                sample_unit="session_sequence",
                feature_set=feature_set,
                group_by=group_by,
                sample_size=session_size,
                evaluation_mode=evaluation_mode,
                split_mode=split_mode,
            )
        )
        llm_specs.append(
            NDSSDatasetSpec(
                sample_unit="session_sequence",
                feature_set=feature_set,
                group_by=group_by,
                sample_size=session_size,
                evaluation_mode=evaluation_mode,
                split_mode=split_mode,
            )
        )
        for window_seconds in NDSS_CONFIG.get("behavior_window_seconds", [5.0]):
            spec = NDSSDatasetSpec(
                sample_unit="behavior_window",
                feature_set=feature_set,
                group_by=group_by,
                sample_size=session_size,
                evaluation_mode=evaluation_mode,
                window_seconds=float(window_seconds),
                split_mode=split_mode,
            )
            local_specs.append(spec)
            llm_specs.append(spec)

        if NDSS_CONFIG.get("include_packet_ablation", True):
            packet_spec = NDSSDatasetSpec(
                sample_unit="packet_ablation",
                feature_set=feature_set,
                group_by=group_by,
                sample_size=packet_size,
                evaluation_mode=evaluation_mode,
                split_mode=split_mode,
            )
            local_specs.append(packet_spec)
            llm_specs.append(packet_spec)

    finetune_sample_unit = str(
        NDSS_CONFIG.get("finetune_sample_unit", "behavior_window")
    )
    finetune_spec = NDSSDatasetSpec(
        sample_unit=finetune_sample_unit,
        feature_set=str(NDSS_CONFIG.get("default_feature_set", "combined")),
        group_by=group_by,
        sample_size=session_size,
        evaluation_mode=evaluation_mode,
        window_seconds=(
            float(NDSS_CONFIG.get("finetune_window_seconds", 5.0))
            if finetune_sample_unit == "behavior_window"
            else None
        ),
        split_mode=split_mode,
    )
    return local_specs, llm_specs, finetune_spec


def _spec_name(spec: NDSSDatasetSpec) -> str:
    bits = [spec.sample_unit, spec.feature_set, spec.split_mode, spec.evaluation_mode]
    if spec.window_seconds is not None:
        bits.append(f"{str(spec.window_seconds).replace('.', 'p')}s")
    return "Session_" + "_".join(bits)


def _requested_llm_context_modes(mode: str) -> list[str]:
    normalized = str(mode).strip().lower()
    if normalized == "both":
        return ["blind", "memory"]
    if normalized in {"blind", "memory"}:
        return [normalized]
    raise ValueError(f"Unknown llm_context_mode={mode!r}")


def write_session_report(
    local_results: list[dict],
    llm_results: list[dict],
    finetune_metadata: dict | None,
    output_path: Path,
    *,
    evaluation_mode: str,
) -> None:
    title = (
        "Session Balanced Comparison Report"
        if evaluation_mode == "balanced"
        else "Session Deployment Report"
    )
    lines = [
        f"# {title}",
        "",
        "Fold dispersion is reported as median [IQR] and min--max. Standard deviation, "
        "when retained in JSON, measures between-capture heterogeneity and is not a score range.",
        "",
    ]

    def dispersion(row: dict, metric: str) -> str:
        return (
            f"{row.get(f'{metric}_median', row.get(metric, 0)):.4f} "
            f"[{row.get(f'{metric}_q1', row.get(metric, 0)):.4f}, "
            f"{row.get(f'{metric}_q3', row.get(metric, 0)):.4f}]; "
            f"{row.get(f'{metric}_min', row.get(metric, 0)):.4f}--"
            f"{row.get(f'{metric}_max', row.get(metric, 0)):.4f}"
        )

    local_summary = [r for r in local_results if r.get("record_type") == "summary"]
    if local_summary:
        rows = []
        for row in local_summary:
            rows.append(
                [
                    row["experiment"],
                    row["algorithm"],
                    dispersion(row, "accuracy"),
                    dispersion(row, "f1_1"),
                    f"{row.get('samples_per_second', 0):.1f}",
                ]
            )
        lines.extend(
            [
                "## Local Baselines",
                "",
                tabulate(
                    rows,
                    headers=[
                        "Experiment", "Model", "Accuracy median [IQR]; min--max",
                        "F1(mal) median [IQR]; min--max", "Samples/s"
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )

    local_folds = [r for r in local_results if r.get("record_type") == "repeat"]
    if local_folds:
        lines.extend(
            [
                "## Local Held-Out-Family Folds",
                "",
                tabulate(
                    [
                        [
                            row["experiment"],
                            row["algorithm"],
                            row.get("fold_index"),
                            row.get("held_out_malware_family") or "seen-capture temporal",
                            row.get("test_support", {}).get("support_0"),
                            row.get("test_support", {}).get("support_1"),
                            f"{row.get('test_positive_rate', 0):.4f}",
                            f"{row.get('accuracy', 0):.4f}",
                            f"{row.get('f1_1', 0):.4f}",
                        ]
                        for row in local_folds
                    ],
                    headers=[
                        "Experiment", "Model", "Fold", "Held-out family", "Test N0",
                        "Test N1", "Test prevalence", "Accuracy", "F1(mal)"
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )

    llm_summary = [r for r in llm_results if r.get("record_type") == "summary"]
    if llm_summary:
        rows = []
        for row in llm_summary:
            rows.append(
                [
                    row["experiment"],
                    row.get("llm_context_mode", "blind"),
                    row["model"],
                    dispersion(row, "accuracy"),
                    dispersion(row, "f1_1"),
                    f"{row.get('invalid_count', 0):.1f}",
                    f"{row.get('avg_latency_ms', 0):.1f}",
                    f"{row.get('avg_tokens', 0):.1f}",
                ]
            )
        lines.extend(
            [
                "## LLM Baselines",
                "",
                tabulate(
                    rows,
                    headers=[
                        "Experiment",
                        "Context",
                        "Model",
                        "Accuracy median [IQR]; min--max",
                        "F1(mal) median [IQR]; min--max",
                        "Invalid",
                        "Latency ms",
                        "Tokens",
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )
        expected_families = _expected_malware_families()
        if expected_families:
            coverage_rows = []
            for row in llm_summary:
                support = row.get("malicious_family_support") or {}
                support = {str(family): int(count) for family, count in support.items()}
                missing = row.get("missing_malicious_families")
                if missing is None:
                    missing = _missing_expected_families(support)
                coverage_rows.append(
                    [
                        row["experiment"],
                        row.get("llm_context_mode", "blind"),
                        int(len([count for count in support.values() if count > 0])),
                        int(sum(support.values())),
                        ", ".join(missing) if missing else "none",
                    ]
                )
            lines.extend(
                [
                    "## LLM Family Coverage Audit",
                    "",
                    tabulate(
                        coverage_rows,
                        headers=[
                            "Experiment",
                            "Context",
                            "Families observed",
                            "Malicious samples",
                            "Missing expected families",
                        ],
                        tablefmt="github",
                    ),
                    "",
                ]
            )

    llm_folds = [
        row for row in llm_results if row.get("record_type") == "repeat_metrics"
    ]
    if llm_folds:
        lines.extend(
            [
                "## LLM Held-Out-Family Folds",
                "",
                tabulate(
                    [
                        [
                            row["experiment"],
                            row.get("llm_context_mode"),
                            row.get("fold_index"),
                            row.get("held_out_malware_family") or "seen-capture temporal",
                            row.get("test_support", {}).get("support_0"),
                            row.get("test_support", {}).get("support_1"),
                            row.get("test_support_0"),
                            row.get("test_support_1"),
                            f"{row.get('full_test_positive_rate', 0):.4f}",
                            f"{row.get('budgeted_test_positive_rate', 0):.4f}",
                            f"{row.get('accuracy', 0):.4f}",
                            f"{row.get('f1_1', 0):.4f}",
                        ]
                        for row in llm_folds
                    ],
                    headers=[
                        "Experiment", "Context", "Fold", "Held-out family", "Full N0",
                        "Full N1", "Evaluated N0", "Evaluated N1", "Full prevalence",
                        "Evaluated prevalence", "Accuracy", "F1(mal)"
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )

    family_summary = [r for r in llm_results if r.get("record_type") == "family_summary"]
    if family_summary:
        rows = []
        for row in family_summary:
            rows.append(
                [
                    row["experiment"],
                    row.get("llm_context_mode", "blind"),
                    row.get("malware_family", "Unknown"),
                    int(row.get("n_samples", 0)),
                    f"{row.get('detection_rate', 0.0):.4f}",
                    int(row.get("invalid_count", 0)),
                ]
            )
        lines.extend(
            [
                "## LLM Malicious-Family Coverage",
                "",
                tabulate(
                    rows,
                    headers=[
                        "Experiment",
                        "Context",
                        "Malware family",
                        "Samples",
                        "Detection rate",
                        "Invalid",
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )

    unsupported = [
        row for row in local_results + llm_results
        if row.get("record_type") == "unsupported"
    ]
    if unsupported:
        lines.extend(
            [
                "## Unsupported Protocol Cells",
                "",
                tabulate(
                    [
                        [row["experiment"], row.get("suite"), row.get("reason")]
                        for row in unsupported
                    ],
                    headers=["Experiment", "Suite", "Fail-closed reason"],
                    tablefmt="github",
                ),
                "",
            ]
        )

    paired = [
        row for row in local_results + llm_results
        if row.get("record_type") == "paired_difference_summary"
    ]
    if paired:
        pair_rows = []
        for row in paired:
            delta = row.get("delta_accuracy") or {}
            pair_rows.append(
                [
                    row.get("comparison_type"),
                    f"{row.get('candidate')} - {row.get('reference')}",
                    row.get("algorithm") or row.get("model"),
                    row.get("sample_unit"),
                    int(row.get("n_pairs", 0)),
                    f"{delta.get('median', 0):.4f} "
                    f"[{delta.get('q1', 0):.4f}, {delta.get('q3', 0):.4f}]",
                ]
            )
        lines.extend(
            [
                "## Paired Differences",
                "",
                tabulate(
                    pair_rows,
                    headers=[
                        "Comparison", "Candidate - reference", "Model", "Sample unit",
                        "Pairs", "Accuracy delta median [IQR]"
                    ],
                    tablefmt="github",
                ),
                "",
            ]
        )

    if finetune_metadata:
        lines.extend(
            [
                "## Fine-Tune Corpus",
                "",
                f"- Sample unit: `{finetune_metadata.get('sample_unit')}`",
                f"- Feature set: `{finetune_metadata.get('feature_set')}`",
                f"- Train / validation / test: `{finetune_metadata.get('n_train')}` / "
                f"`{finetune_metadata.get('n_validation')}` / `{finetune_metadata.get('n_test')}`",
                f"- Metadata file: `{finetune_metadata.get('metadata_path')}`",
                "",
            ]
        )

    temporary_report = output_path.with_suffix(
        output_path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    with open(temporary_report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    temporary_report.replace(output_path)


def _load_existing_result_rows(
    path: Path,
    *,
    expected_split_mode: str,
) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    incompatible = [
        row for row in rows
        if row.get("split_mode") != expected_split_mode
    ]
    if incompatible:
        raise RuntimeError(
            f"Result artifact {path} contains {len(incompatible)} rows without the requested "
            f"split_mode={expected_split_mode}; refusing to mix protocols"
        )
    return rows


def _write_result_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(
        path.suffix + f".{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    tmp_path.replace(path)


def _difference_statistics(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    mean, std, low, high = _metric_stats(values, bounded=False)
    return {
        "mean": mean,
        "std": std,
        "ci95_low": low,
        "ci95_high": high,
        "median": float(np.median(arr)),
        "q1": float(np.quantile(arr, 0.25)),
        "q3": float(np.quantile(arr, 0.75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "values": [float(value) for value in values],
    }


def _build_local_paired_differences(rows: list[dict]) -> list[dict]:
    repeats = [row for row in rows if row.get("record_type") == "repeat"]
    output: list[dict] = []
    group_fields = (
        "algorithm",
        "sample_unit",
        "window_seconds",
        "evaluation_mode",
        "split_mode",
    )
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in repeats:
        grouped[tuple(row.get(field) for field in group_fields)].append(row)
    for group_key, group_rows in grouped.items():
        by_feature_fold = {
            (row["feature_set"], int(row["fold_index"])): row for row in group_rows
        }
        for candidate, reference in (
            ("mercury", "minimal"),
            ("combined", "minimal"),
            ("combined", "mercury"),
        ):
            folds = sorted(
                set(fold for feature, fold in by_feature_fold if feature == candidate)
                & set(fold for feature, fold in by_feature_fold if feature == reference)
            )
            if not folds:
                continue
            candidate_rows = [by_feature_fold[(candidate, fold)] for fold in folds]
            reference_rows = [by_feature_fold[(reference, fold)] for fold in folds]
            if any(
                left.get("manifest_hash") != right.get("manifest_hash")
                for left, right in zip(candidate_rows, reference_rows)
            ):
                raise RuntimeError(
                    f"Cannot pair {candidate} against {reference}: frozen manifests differ"
                )
            result = {
                "record_type": "paired_difference_summary",
                "comparison_type": "feature_set",
                "candidate": candidate,
                "reference": reference,
                "paired_on": "identical frozen fold and test sample IDs",
                "n_pairs": len(folds),
                "fold_indices": folds,
                "held_out_malware_families": [
                    row.get("held_out_malware_family") for row in candidate_rows
                ],
                "suite": "session_local",
                "phase": 7,
                **dict(zip(group_fields, group_key)),
            }
            for metric in ("accuracy", "f1_1", "recall_1", "precision_1", "pr_auc", "roc_auc"):
                if any(row.get(metric) is None for row in candidate_rows + reference_rows):
                    continue
                deltas = [
                    float(left[metric]) - float(right[metric])
                    for left, right in zip(candidate_rows, reference_rows)
                ]
                result[f"delta_{metric}"] = _difference_statistics(deltas)
            output.append(result)

    algorithm_group_fields = (
        "feature_set",
        "sample_unit",
        "window_seconds",
        "evaluation_mode",
        "split_mode",
    )
    algorithm_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in repeats:
        algorithm_groups[
            tuple(row.get(field) for field in algorithm_group_fields)
        ].append(row)
    for group_key, group_rows in algorithm_groups.items():
        by_algorithm_fold = {
            (row["algorithm"], int(row["fold_index"])): row for row in group_rows
        }
        algorithms = sorted({row["algorithm"] for row in group_rows} - {"RF"})
        for candidate in algorithms:
            folds = sorted(
                set(fold for algorithm, fold in by_algorithm_fold if algorithm == candidate)
                & set(fold for algorithm, fold in by_algorithm_fold if algorithm == "RF")
            )
            if not folds:
                continue
            candidate_rows = [by_algorithm_fold[(candidate, fold)] for fold in folds]
            reference_rows = [by_algorithm_fold[("RF", fold)] for fold in folds]
            if any(
                left.get("manifest_hash") != right.get("manifest_hash")
                for left, right in zip(candidate_rows, reference_rows)
            ):
                raise RuntimeError(
                    f"Cannot pair {candidate} against RF: frozen manifests differ"
                )
            result = {
                "record_type": "paired_difference_summary",
                "comparison_type": "algorithm",
                "candidate": candidate,
                "reference": "RF",
                "paired_on": "identical frozen fold and test sample IDs",
                "n_pairs": len(folds),
                "fold_indices": folds,
                "held_out_malware_families": [
                    row.get("held_out_malware_family") for row in candidate_rows
                ],
                "suite": "session_local",
                "phase": 7,
                **dict(zip(algorithm_group_fields, group_key)),
            }
            for metric in (
                "accuracy", "f1_1", "recall_1", "precision_1", "pr_auc", "roc_auc"
            ):
                if any(row.get(metric) is None for row in candidate_rows + reference_rows):
                    continue
                result[f"delta_{metric}"] = _difference_statistics(
                    [
                        float(left[metric]) - float(right[metric])
                        for left, right in zip(candidate_rows, reference_rows)
                    ]
                )
            output.append(result)
    return output


def _build_llm_context_paired_differences(rows: list[dict]) -> list[dict]:
    samples = [row for row in rows if row.get("record_type") is None]
    grouped: dict[tuple, dict[str, dict]] = defaultdict(dict)
    key_fields = (
        "feature_set",
        "sample_unit",
        "window_seconds",
        "evaluation_mode",
        "split_mode",
        "model",
        "fold_index",
        "packet_id",
    )
    for row in samples:
        key = tuple(row.get(field) for field in key_fields)
        grouped[key][str(row.get("llm_context_mode", "blind"))] = row
    pairs = [contexts for contexts in grouped.values() if {"blind", "memory"} <= set(contexts)]
    if not pairs:
        return []

    by_variant: dict[tuple, list[dict[str, dict]]] = defaultdict(list)
    variant_fields = key_fields[:6]
    for contexts in pairs:
        blind = contexts["blind"]
        key = tuple(blind.get(field) for field in variant_fields)
        by_variant[key].append(contexts)

    output: list[dict] = []
    for variant_key, variant_pairs in sorted(by_variant.items(), key=lambda item: str(item[0])):
        correctness_delta = []
        malicious_delta = []
        blind_only_correct = 0
        memory_only_correct = 0
        for contexts in variant_pairs:
            blind = contexts["blind"]
            memory = contexts["memory"]
            truth = int(blind["ground_truth"])
            blind_correct = int(int(blind.get("prediction", -1)) == truth)
            memory_correct = int(int(memory.get("prediction", -1)) == truth)
            correctness_delta.append(float(memory_correct - blind_correct))
            if truth == 1:
                malicious_delta.append(float(memory_correct - blind_correct))
            blind_only_correct += int(blind_correct == 1 and memory_correct == 0)
            memory_only_correct += int(blind_correct == 0 and memory_correct == 1)
        result = {
            "record_type": "paired_difference_summary",
            "comparison_type": "llm_context",
            "candidate": "memory",
            "reference": "blind",
            "paired_on": "identical frozen fold and held-out sample ID",
            "n_pairs": len(variant_pairs),
            "delta_accuracy": _difference_statistics(correctness_delta),
            "mcnemar_blind_only_correct": blind_only_correct,
            "mcnemar_memory_only_correct": memory_only_correct,
            "suite": "session_llm",
            "phase": 7,
            **dict(zip(variant_fields, variant_key)),
        }
        if malicious_delta:
            result["delta_malicious_detection_rate"] = _difference_statistics(
                malicious_delta
            )
        output.append(result)
    return output


def _estimate_llm_workload(
    llm_specs: list[NDSSDatasetSpec],
    context_modes: list[str],
    evaluation_mode: str,
    config: NDSSLLMRunConfig,
    split_mode: str,
) -> dict:
    if config.repeat_indices is not None:
        repeats = len(
            set(config.repeat_indices) & set(range(_protocol_fold_count(split_mode)))
        )
    elif config.repeat_limit is not None:
        repeats = min(int(config.repeat_limit), _protocol_fold_count(split_mode))
    else:
        repeats = _protocol_fold_count(split_mode)
    mode = str(evaluation_mode).strip().lower()
    per_repeat = (
        int(config.balanced_samples_per_repeat)
        if mode == "balanced"
        else int(config.deployment_validation_samples_per_repeat)
        + int(config.deployment_test_samples_per_repeat)
    )
    variants = 0
    skipped_memory_packet_variants = 0
    for spec in llm_specs:
        for context_mode in context_modes:
            if spec.sample_unit == "packet_ablation" and context_mode == "memory":
                skipped_memory_packet_variants += 1
                continue
            variants += 1
    return {
        "variants": variants,
        "repeats": repeats,
        "calls_per_repeat": per_repeat,
        "estimated_calls": variants * repeats * per_repeat,
        "skipped_memory_packet_variants": skipped_memory_packet_variants,
    }


def main(
    *,
    provider: str = "openai",
    dry_run: bool = False,
    run_local: bool = True,
    run_llm: bool = True,
    prepare_finetune: bool = True,
    start_finetune_job: bool = False,
    finetuned_model: str | None = None,
    evaluation_mode: str = str(NDSS_CONFIG.get("default_evaluation_mode", "balanced")),
    llm_context_mode: str = str(NDSS_CONFIG.get("llm_context_mode", "both")),
    allow_large_llm_run: bool = False,
    llm_budget_profile: str = "full",
    llm_feature_set: str | None = None,
    llm_sample_unit: str | None = None,
    llm_window_seconds: str | None = None,
    llm_repeat_indices: str | None = None,
    llm_repeat_limit: int | None = None,
    llm_samples_per_repeat: int | None = None,
    llm_validation_samples_per_repeat: int | None = None,
    llm_test_samples_per_repeat: int | None = None,
    llm_max_calls: int | None = None,
    split_mode: str = str(SESSION_SPLIT_CONFIG["default_mode"]),
) -> None:
    conn = get_db()
    eval_mode = str(evaluation_mode).strip().lower()
    if eval_mode not in set(NDSS_CONFIG.get("evaluation_modes", ["balanced", "deployment"])):
        raise ValueError(f"Unknown NDSS evaluation_mode={evaluation_mode!r}")
    split_mode = str(split_mode).strip().lower()
    if split_mode not in SESSION_SPLIT_MODES:
        raise ValueError(f"Unknown session split_mode={split_mode!r}")
    context_modes = _requested_llm_context_modes(llm_context_mode)
    local_specs, llm_specs, finetune_spec = _default_specs(eval_mode, split_mode)
    llm_run_config = _resolve_llm_run_config(
        budget_profile=llm_budget_profile,
        feature_set=llm_feature_set,
        sample_unit=llm_sample_unit,
        window_seconds=llm_window_seconds,
        repeat_indices=llm_repeat_indices,
        repeat_limit=llm_repeat_limit,
        samples_per_repeat=llm_samples_per_repeat,
        validation_samples_per_repeat=llm_validation_samples_per_repeat,
        test_samples_per_repeat=llm_test_samples_per_repeat,
        max_calls=llm_max_calls,
    )
    if run_llm:
        llm_specs = _filter_llm_specs(llm_specs, llm_run_config)
    allowed_repeats = _allowed_repeat_indices(llm_run_config, split_mode)
    local_results: list[dict] = []
    llm_results: list[dict] = []
    finetune_metadata: dict | None = None
    results_dir = Path(RESULTS_DIR)
    base_llm_suffix = _llm_result_suffix(eval_mode, llm_run_config)
    if run_llm:
        context_artifact_label = str(llm_context_mode).strip().lower()
    elif prepare_finetune or finetuned_model:
        context_artifact_label = "finetune"
    else:
        context_artifact_label = "local"
    llm_suffix = (
        f"{split_mode}_{base_llm_suffix}_{str(provider).strip().lower()}_"
        f"{context_artifact_label}"
    )
    local_path = results_dir / f"session_local_results_{split_mode}_{eval_mode}.json"
    llm_path = results_dir / f"session_llm_results_{llm_suffix}.json"
    llm_partial_path = results_dir / f"session_llm_results_{llm_suffix}.partial.json"
    report_path = results_dir / f"session_report_{llm_suffix}.md"

    if run_llm:
        workload = _estimate_llm_workload(
            llm_specs, context_modes, eval_mode, llm_run_config, split_mode
        )
        threshold = int(llm_run_config.max_calls or NDSS_CONFIG.get("llm_large_run_call_threshold", 1000))
        print("\nSession LLM preflight:")
        print(
            f"  profile={llm_run_config.budget_profile} | result_label={llm_run_config.result_label} | "
            f"family_stratified_balanced={llm_run_config.family_stratified_balanced}"
        )
        print(
            f"  variants={workload['variants']} | repeats={workload['repeats']} | "
            f"calls_per_repeat={workload['calls_per_repeat']} | "
            f"estimated_api_calls={workload['estimated_calls']}"
        )
        print(
            f"  feature_sets={llm_run_config.feature_sets or 'all'} | "
            f"sample_units={llm_run_config.sample_units or 'all'} | "
            f"behavior_windows={llm_run_config.behavior_window_seconds or 'all'}"
        )
        print(
            f"  repeat_indices={llm_run_config.repeat_indices or 'all'} | "
            f"repeat_limit={llm_run_config.repeat_limit or 'none'}"
        )
        print(f"  partial checkpoint path={llm_partial_path}")
        if workload["estimated_calls"] > threshold and not dry_run and not allow_large_llm_run:
            conn.close()
            raise RuntimeError(
                "Refusing to start a large Session LLM run without explicit opt-in. "
                f"Estimated calls={workload['estimated_calls']} exceeds threshold={threshold}. "
                "Rerun with --allow-large-llm-run, reduce NDSS_CONFIG LLM sample sizes, "
                "or run a narrower context/mode first."
            )

    if run_local:
        ensure_algorithms_available(list(NDSS_CONFIG.get("local_algorithms", [])))
        for spec in local_specs:
            exp_name = _spec_name(spec)
            try:
                dataset, feature_cols, manifest, manifest_path = load_or_create_ndss_manifest(
                    conn, spec
                )
            except SessionSplitFeasibilityError as exc:
                print(f"\n[UNSUPPORTED] {exp_name}: {exc}")
                local_results.append(
                    {
                        "experiment": exp_name,
                        "record_type": "unsupported",
                        "status": "infeasible_protocol_cell",
                        "reason": str(exc),
                        "split_mode": split_mode,
                        "evaluation_mode": eval_mode,
                        "feature_set": spec.feature_set,
                        "sample_unit": spec.sample_unit,
                        "window_seconds": spec.window_seconds,
                        "suite": "session_local",
                        "phase": 7,
                    }
                )
                continue
            local_results.extend(
                run_local_ndss_experiment(
                    dataset,
                    feature_cols,
                    manifest,
                    manifest_path,
                    experiment_name=exp_name,
                    algorithms=list(NDSS_CONFIG.get("local_algorithms", [])),
                    evaluation_mode=eval_mode,
                )
            )
            _print_session_local_table(local_results, exp_name)
        local_results.extend(_build_local_paired_differences(local_results))

    if run_llm:
        for spec in llm_specs:
            try:
                dataset, _feature_cols, manifest, _manifest_path = load_or_create_ndss_manifest(
                    conn, spec
                )
            except SessionSplitFeasibilityError as exc:
                exp_name = _spec_name(spec)
                print(f"\n[UNSUPPORTED] {exp_name}: {exc}")
                llm_results.append(
                    {
                        "experiment": exp_name,
                        "record_type": "unsupported",
                        "status": "infeasible_protocol_cell",
                        "reason": str(exc),
                        "split_mode": split_mode,
                        "evaluation_mode": eval_mode,
                        "feature_set": spec.feature_set,
                        "sample_unit": spec.sample_unit,
                        "window_seconds": spec.window_seconds,
                        "suite": "session_llm",
                        "phase": 7,
                    }
                )
                continue
            for context_mode in context_modes:
                if spec.sample_unit == "packet_ablation" and context_mode == "memory":
                    continue
                exp_name = _spec_name(spec) + f"_{context_mode}"
                new_rows = run_llm_ndss_experiment(
                    dataset,
                    manifest,
                    experiment_name=exp_name,
                    provider=provider,
                    dry_run=dry_run,
                    evaluation_mode=eval_mode,
                    llm_context_mode=context_mode,
                    allowed_repeat_indices=allowed_repeats,
                    checkpoint_path=None if dry_run else llm_partial_path,
                    checkpoint_prefix_rows=llm_results,
                    balanced_samples_per_repeat=llm_run_config.balanced_samples_per_repeat,
                    deployment_validation_samples_per_repeat=llm_run_config.deployment_validation_samples_per_repeat,
                    deployment_test_samples_per_repeat=llm_run_config.deployment_test_samples_per_repeat,
                    family_stratified_balanced=llm_run_config.family_stratified_balanced,
                )
                llm_results.extend(new_rows)
                if not dry_run:
                    _write_result_rows(llm_partial_path, llm_results)
                    print(
                        f"[CHECKPOINT] Session LLM partial rows={len(llm_results)} "
                        f"written to {llm_partial_path}",
                        flush=True,
                    )

        llm_results.extend(_build_llm_context_paired_differences(llm_results))

    if prepare_finetune:
        dataset, _feature_cols, manifest, _manifest_path = load_or_create_ndss_manifest(conn, finetune_spec)
        finetune_metadata = export_finetune_corpus(
            dataset,
            manifest,
            output_stem=_spec_name(finetune_spec).lower(),
        )
        if start_finetune_job:
            job_info = create_openai_finetune_job(
                training_path=finetune_metadata["train_path"],
                validation_path=finetune_metadata["validation_path"],
            )
            finetune_metadata.update(job_info)
        if finetuned_model:
            eval_repeat_index = int(NDSS_CONFIG.get("finetune_eval_repeat_index", 0))
            finetune_experiment = _spec_name(finetune_spec) + "_finetuned_blind"
            llm_results.extend(
                run_llm_ndss_experiment(
                    dataset,
                    manifest,
                    experiment_name=finetune_experiment,
                    provider="openai",
                    dry_run=dry_run,
                    evaluation_mode=eval_mode,
                    llm_context_mode="blind",
                    model_override=finetuned_model,
                    allowed_repeat_indices={eval_repeat_index},
                    checkpoint_path=None if dry_run else llm_partial_path,
                    checkpoint_prefix_rows=llm_results,
                    balanced_samples_per_repeat=llm_run_config.balanced_samples_per_repeat,
                    deployment_validation_samples_per_repeat=llm_run_config.deployment_validation_samples_per_repeat,
                    deployment_test_samples_per_repeat=llm_run_config.deployment_test_samples_per_repeat,
                    family_stratified_balanced=llm_run_config.family_stratified_balanced,
                )
            )
            finetune_metadata["evaluation_repeat_index"] = eval_repeat_index
            finetune_metadata["evaluation_scope"] = (
                "held-out test split from the exported fine-tune fold"
            )

    if dry_run and run_llm and not run_local and not prepare_finetune and not finetuned_model:
        print("\nSession LLM dry-run complete; no result or report files were written.")
        conn.close()
        return

    if run_local:
        _write_result_rows(local_path, local_results)
    else:
        local_results = _load_existing_result_rows(
            local_path, expected_split_mode=split_mode
        )

    wrote_llm_results = (run_llm or bool(finetuned_model)) and not dry_run
    if wrote_llm_results:
        _write_result_rows(llm_path, llm_results)
    else:
        llm_results = _load_existing_result_rows(
            llm_path, expected_split_mode=split_mode
        )

    write_session_report(
        local_results,
        llm_results,
        finetune_metadata,
        report_path,
        evaluation_mode=eval_mode,
    )
    print(f"\nSession local results available at: {local_path}")
    print(f"Session LLM results available at:   {llm_path}")
    print(f"Session report saved to:            {report_path}")
    conn.close()
