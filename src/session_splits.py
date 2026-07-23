#!/usr/bin/env python3
"""Deterministic manifests for the redesigned session evaluation protocols."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SESSION_MANIFEST_SCHEMA_VERSION = 1
SESSION_MANIFEST_KIND = "session_split_protocol"
CAPTURE_DISJOINT_5FOLD = "capture_disjoint_5fold"
WITHIN_CAPTURE_TEMPORAL = "within_capture_temporal"
SESSION_SPLIT_MODES = {CAPTURE_DISJOINT_5FOLD, WITHIN_CAPTURE_TEMPORAL}


class SessionSplitFeasibilityError(RuntimeError):
    """Raised when the requested leakage boundary cannot be evaluated safely."""


def _json_ready(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _stable_hash(payload) -> str:
    canonical = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cohort_hash(sample_ids: list[int], eligibility: dict) -> str:
    """Hash both membership and eligibility so threshold changes invalidate cohorts."""
    return _stable_hash(
        {
            "ordered_sample_ids": [int(sample_id) for sample_id in sample_ids],
            "eligibility": eligibility,
        }
    )[:16]


def _require_columns(df: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns - set(df.columns))
    if missing:
        raise KeyError(f"Session split dataframe is missing columns: {missing}")


def _partition_summary(df: pd.DataFrame) -> dict:
    support_0 = int((df["is_malicious"].astype(int) == 0).sum())
    support_1 = int((df["is_malicious"].astype(int) == 1).sum())
    family_support = {
        str(family): int(count)
        for family, count in (
            df[df["is_malicious"].astype(int) == 1]
            .groupby("malware_family", dropna=False)
            .size()
            .items()
        )
        if pd.notna(family) and str(family).strip()
    }
    return {
        "n_samples": int(len(df)),
        "n_sessions": int(df["session_id"].nunique()),
        "support_0": support_0,
        "support_1": support_1,
        "positive_rate": float(support_1 / len(df)) if len(df) else 0.0,
        "family_support": family_support,
    }


def _capture_inventory(df: pd.DataFrame) -> tuple[list[int], list[int], dict[int, str]]:
    benign: list[int] = []
    malicious: list[int] = []
    family_by_capture: dict[int, str] = {}
    for capture_id, group in df.groupby("dataset_id", sort=True):
        labels = set(group["is_malicious"].astype(int).tolist())
        if labels == {0}:
            benign.append(int(capture_id))
            continue
        if labels != {1}:
            raise SessionSplitFeasibilityError(
                f"Capture {capture_id} mixes benign and malicious labels; the five-fold "
                "capture protocol requires capture-level class identity."
            )
        families = sorted(
            {
                str(value).strip()
                for value in group["malware_family"].fillna("").tolist()
                if str(value).strip()
            }
        )
        if len(families) != 1:
            raise SessionSplitFeasibilityError(
                f"Malicious capture {capture_id} has ambiguous family labels: {families}"
            )
        malicious.append(int(capture_id))
        family_by_capture[int(capture_id)] = families[0]
    return benign, malicious, family_by_capture


def _quota_by_capture(total: int, available: dict[int, int]) -> dict[int, int]:
    captures = sorted(int(capture_id) for capture_id in available)
    if not captures:
        raise SessionSplitFeasibilityError("Cannot allocate a quota without captures")
    if sum(int(available[capture_id]) for capture_id in captures) < int(total):
        raise SessionSplitFeasibilityError(
            f"Requested {total} samples but only {sum(available.values())} are available"
        )

    base, remainder = divmod(int(total), len(captures))
    quota = {
        capture_id: min(base + int(index < remainder), int(available[capture_id]))
        for index, capture_id in enumerate(captures)
    }
    remaining = int(total) - sum(quota.values())
    while remaining:
        progressed = False
        for capture_id in captures:
            if quota[capture_id] >= int(available[capture_id]):
                continue
            quota[capture_id] += 1
            remaining -= 1
            progressed = True
            if remaining == 0:
                break
        if not progressed:
            raise SessionSplitFeasibilityError("Unable to complete deterministic capture quota")
    return quota


def capture_stratified_sample_ids(
    df: pd.DataFrame,
    total: int,
    seed: int,
    *,
    id_col: str = "packet_id",
) -> list[int]:
    """Sample a deterministic near-equal quota from every represented capture."""
    _require_columns(df, {"dataset_id", id_col})
    available = {
        int(capture_id): int(len(group))
        for capture_id, group in df.groupby("dataset_id", sort=True)
    }
    quota = _quota_by_capture(int(total), available)
    selected: list[int] = []
    for capture_id in sorted(quota):
        values = sorted(
            df[df["dataset_id"].astype(int) == capture_id][id_col].astype(int).tolist()
        )
        count = int(quota[capture_id])
        if count == len(values):
            chosen = values
        else:
            capture_seed = int(seed) + capture_id * 1009
            rng = np.random.default_rng(capture_seed)
            indices = sorted(rng.choice(len(values), size=count, replace=False).tolist())
            chosen = [values[index] for index in indices]
        selected.extend(chosen)
    return sorted(selected)


def _balanced_partition_subset(df: pd.DataFrame, per_class: int, seed: int) -> pd.DataFrame:
    selected: list[int] = []
    for label, offset in ((0, 11), (1, 29)):
        candidates = df[df["is_malicious"].astype(int) == label]
        if len(candidates) < int(per_class):
            raise SessionSplitFeasibilityError(
                f"Balanced partition requires {per_class} class-{label} samples; "
                f"only {len(candidates)} are available"
            )
        selected.extend(
            capture_stratified_sample_ids(candidates, int(per_class), int(seed) + offset)
        )
    order = {sample_id: index for index, sample_id in enumerate(sorted(selected))}
    result = df[df["packet_id"].astype(int).isin(order)].copy()
    result["_manifest_order"] = result["packet_id"].astype(int).map(order)
    return result.sort_values("_manifest_order").drop(columns="_manifest_order").reset_index(drop=True)


def _fold_record(
    *,
    fold_index: int,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    excluded_ids: list[int],
    train_captures: list[int],
    validation_captures: list[int],
    test_captures: list[int],
    held_out_capture: int | None,
    held_out_family: str | None,
    seed: int,
    temporal_boundaries: dict | None = None,
) -> dict:
    return {
        "fold_index": int(fold_index),
        "repeat_index": int(fold_index),
        "seed": int(seed),
        "train_capture_ids": sorted(int(value) for value in train_captures),
        "validation_capture_ids": sorted(int(value) for value in validation_captures),
        "test_capture_ids": sorted(int(value) for value in test_captures),
        "held_out_malware_capture_id": None if held_out_capture is None else int(held_out_capture),
        "held_out_malware_family": held_out_family,
        "train_sample_ids": train_df["packet_id"].astype(int).tolist(),
        "validation_sample_ids": validation_df["packet_id"].astype(int).tolist(),
        "test_sample_ids": test_df["packet_id"].astype(int).tolist(),
        "excluded_sample_ids": sorted(int(value) for value in excluded_ids),
        "train_session_ids": sorted(train_df["session_id"].astype(int).unique().tolist()),
        "validation_session_ids": sorted(validation_df["session_id"].astype(int).unique().tolist()),
        "test_session_ids": sorted(test_df["session_id"].astype(int).unique().tolist()),
        "train": _partition_summary(train_df),
        "validation": _partition_summary(validation_df),
        "test": _partition_summary(test_df),
        "temporal_boundaries": temporal_boundaries,
    }


def build_capture_disjoint_5fold_manifest(
    df: pd.DataFrame,
    *,
    experiment_key: str,
    evaluation_mode: str,
    cohort_filters: dict,
    eligibility: dict,
    expected_families: list[str],
    random_state: int,
    minimum_test_support_per_class: int | None,
    minimum_validation_support_per_class: int | None,
) -> dict:
    """Build five folds, each holding out one malware capture and benign captures."""
    _require_columns(
        df,
        {"packet_id", "session_id", "dataset_id", "is_malicious", "malware_family"},
    )
    if df["packet_id"].duplicated().any():
        raise ValueError("Session cohort sample identifiers must be unique")

    benign, malicious, family_by_capture = _capture_inventory(df)
    family_to_capture = {family: capture for capture, family in family_by_capture.items()}
    missing_families = [family for family in expected_families if family not in family_to_capture]
    extra_families = sorted(set(family_to_capture) - set(expected_families))
    if missing_families or extra_families or len(malicious) != 5:
        raise SessionSplitFeasibilityError(
            "Capture-disjoint five-fold evaluation requires exactly the five configured "
            f"malware families; missing={missing_families}, extra={extra_families}, "
            f"malicious_captures={malicious}"
        )
    if not benign:
        raise SessionSplitFeasibilityError("No benign captures are available")

    malware_order = [family_to_capture[family] for family in expected_families]
    test_benign: dict[int, list[int]] = {index: [] for index in range(5)}
    for index, capture_id in enumerate(sorted(benign)):
        test_benign[index % 5].append(int(capture_id))

    assignments: list[dict] = []
    all_captures = set(benign) | set(malicious)
    for fold_index, test_malware in enumerate(malware_order):
        test_captures = set(test_benign[fold_index]) | {int(test_malware)}
        validation_malware = int(malware_order[(fold_index + 1) % len(malware_order)])
        validation_benign_candidates = sorted(set(benign) - test_captures)
        if not validation_benign_candidates:
            raise SessionSplitFeasibilityError(
                f"Fold {fold_index} has no benign capture available for validation"
            )
        validation_benign = validation_benign_candidates[fold_index % len(validation_benign_candidates)]
        validation_captures = {validation_malware, int(validation_benign)}
        if test_captures & validation_captures:
            raise AssertionError("Capture assignment overlap before training")
        train_captures = all_captures - test_captures - validation_captures
        assignments.append(
            {
                "fold_index": fold_index,
                "test_malware": int(test_malware),
                "train": sorted(train_captures),
                "validation": sorted(validation_captures),
                "test": sorted(test_captures),
            }
        )

    mode = str(evaluation_mode).strip().lower()
    balanced_test_support = None
    balanced_validation_support = None
    if mode == "balanced":
        test_feasible: list[int] = []
        validation_feasible: list[int] = []
        for assignment in assignments:
            test_pool = df[df["dataset_id"].astype(int).isin(assignment["test"])]
            validation_pool = df[
                df["dataset_id"].astype(int).isin(assignment["validation"])
            ]
            test_feasible.append(
                min(
                    int((test_pool["is_malicious"].astype(int) == 0).sum()),
                    int((test_pool["is_malicious"].astype(int) == 1).sum()),
                )
            )
            validation_feasible.append(
                min(
                    int((validation_pool["is_malicious"].astype(int) == 0).sum()),
                    int((validation_pool["is_malicious"].astype(int) == 1).sum()),
                )
            )
        balanced_test_support = min(test_feasible)
        balanced_validation_support = min(validation_feasible)
        if minimum_test_support_per_class is not None and balanced_test_support < int(
            minimum_test_support_per_class
        ):
            raise SessionSplitFeasibilityError(
                "Balanced capture-disjoint test support is infeasible: "
                f"derived per-class support={balanced_test_support}, required minimum="
                f"{minimum_test_support_per_class}. Capture support={test_feasible}"
            )
        if minimum_validation_support_per_class is not None and balanced_validation_support < int(
            minimum_validation_support_per_class
        ):
            raise SessionSplitFeasibilityError(
                "Balanced capture-disjoint validation support is infeasible: "
                f"derived per-class support={balanced_validation_support}, required minimum="
                f"{minimum_validation_support_per_class}. Capture support={validation_feasible}"
            )
    elif mode != "deployment":
        raise ValueError(f"Unknown evaluation_mode={evaluation_mode!r}")

    folds: list[dict] = []
    cohort_ids = df["packet_id"].astype(int).tolist()
    for assignment in assignments:
        fold_index = int(assignment["fold_index"])
        train_df = df[df["dataset_id"].astype(int).isin(assignment["train"])].copy()
        validation_pool = df[
            df["dataset_id"].astype(int).isin(assignment["validation"])
        ].copy()
        test_pool = df[df["dataset_id"].astype(int).isin(assignment["test"])].copy()
        if mode == "balanced":
            validation_df = _balanced_partition_subset(
                validation_pool,
                int(balanced_validation_support),
                int(random_state) + fold_index * 10_000 + 101,
            )
            test_df = _balanced_partition_subset(
                test_pool,
                int(balanced_test_support),
                int(random_state) + fold_index * 10_000 + 503,
            )
        else:
            validation_df = validation_pool.sort_values("packet_id").reset_index(drop=True)
            test_df = test_pool.sort_values("packet_id").reset_index(drop=True)
            for partition_name, partition_df, minimum in (
                ("validation", validation_df, minimum_validation_support_per_class),
                ("test", test_df, minimum_test_support_per_class),
            ):
                summary = _partition_summary(partition_df)
                if minimum is not None and min(summary["support_0"], summary["support_1"]) < int(
                    minimum
                ):
                    raise SessionSplitFeasibilityError(
                        f"Deployment {partition_name} fold {fold_index} has support "
                        f"{summary['support_0']}/{summary['support_1']}, below minimum={minimum}"
                    )
        train_df = train_df.sort_values("packet_id").reset_index(drop=True)
        used_ids = set(train_df["packet_id"].astype(int))
        used_ids.update(validation_df["packet_id"].astype(int))
        used_ids.update(test_df["packet_id"].astype(int))
        folds.append(
            _fold_record(
                fold_index=fold_index,
                train_df=train_df,
                validation_df=validation_df,
                test_df=test_df,
                excluded_ids=sorted(set(cohort_ids) - used_ids),
                train_captures=assignment["train"],
                validation_captures=assignment["validation"],
                test_captures=assignment["test"],
                held_out_capture=assignment["test_malware"],
                held_out_family=family_by_capture[assignment["test_malware"]],
                seed=int(random_state) + fold_index * 10_000,
            )
        )

    tested_malware = [fold["held_out_malware_capture_id"] for fold in folds]
    tested_benign = {
        capture_id
        for fold in folds
        for capture_id in fold["test_capture_ids"]
        if capture_id in benign
    }
    if sorted(tested_malware) != sorted(malicious) or tested_benign != set(benign):
        raise AssertionError("Capture coverage audit failed")

    manifest = {
        "schema_version": SESSION_MANIFEST_SCHEMA_VERSION,
        "manifest_kind": SESSION_MANIFEST_KIND,
        "split_mode": CAPTURE_DISJOINT_5FOLD,
        "split_type": "capture_disjoint_5fold",
        "interpretation": "generalization to captures absent from training and validation",
        "experiment_key": experiment_key,
        "evaluation_mode": mode,
        "cohort_filters": _json_ready(cohort_filters),
        "eligibility": _json_ready(eligibility),
        "cohort_sample_ids": cohort_ids,
        "cohort_hash": cohort_hash(cohort_ids, eligibility),
        "cohort_size": int(len(cohort_ids)),
        "random_state": int(random_state),
        "n_folds": int(len(folds)),
        "expected_malware_families": list(expected_families),
        "benign_capture_ids": sorted(benign),
        "malware_capture_ids": sorted(malicious),
        "family_by_capture": {str(key): value for key, value in family_by_capture.items()},
        "balanced_test_support_per_class": balanced_test_support,
        "balanced_validation_support_per_class": balanced_validation_support,
        "quota_rule": "equal per class; deterministic near-equal capture quotas",
        "folds": folds,
    }
    manifest["manifest_hash"] = _stable_hash(manifest)[:16]
    return _json_ready(manifest)


def _session_time_table(capture_df: pd.DataFrame) -> pd.DataFrame:
    sessions = (
        capture_df.groupby("session_id", as_index=False)
        .agg(session_start_time=("session_start_time", "min"))
        .sort_values(["session_start_time", "session_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    if sessions["session_start_time"].isna().any():
        raise SessionSplitFeasibilityError("Temporal splitting requires non-null session timestamps")
    return sessions


def build_within_capture_temporal_manifest(
    df: pd.DataFrame,
    *,
    experiment_key: str,
    evaluation_mode: str,
    cohort_filters: dict,
    eligibility: dict,
    expected_families: list[str],
    random_state: int,
    train_fraction: float,
    validation_fraction: float,
    test_fraction: float,
    minimum_sessions_per_capture: int,
) -> dict:
    """Build one 60/20/20 chronological split inside every represented capture."""
    _require_columns(
        df,
        {
            "packet_id",
            "session_id",
            "dataset_id",
            "is_malicious",
            "malware_family",
            "session_start_time",
        },
    )
    fractions = [float(train_fraction), float(validation_fraction), float(test_fraction)]
    if any(value <= 0.0 for value in fractions) or not math.isclose(sum(fractions), 1.0):
        raise ValueError(f"Temporal fractions must be positive and sum to one: {fractions}")

    benign, malicious, family_by_capture = _capture_inventory(df)
    represented_families = set(family_by_capture.values())
    missing_families = sorted(set(expected_families) - represented_families)
    extra_families = sorted(represented_families - set(expected_families))
    if missing_families or extra_families:
        raise SessionSplitFeasibilityError(
            "Within-capture temporal evaluation does not match the configured malware "
            f"families; missing={missing_families}, extra={extra_families}"
        )
    train_session_ids: set[int] = set()
    validation_session_ids: set[int] = set()
    test_session_ids: set[int] = set()
    boundaries: dict[str, dict] = {}
    for capture_id, capture_df in df.groupby("dataset_id", sort=True):
        sessions = _session_time_table(capture_df)
        n_sessions = int(len(sessions))
        if n_sessions < int(minimum_sessions_per_capture):
            raise SessionSplitFeasibilityError(
                f"Capture {capture_id} has {n_sessions} represented sessions; "
                f"within-capture temporal evaluation requires {minimum_sessions_per_capture}"
            )
        train_end = max(1, int(math.floor(n_sessions * float(train_fraction))))
        validation_count = max(1, int(math.floor(n_sessions * float(validation_fraction))))
        validation_end = min(train_end + validation_count, n_sessions - 1)
        if validation_end <= train_end:
            validation_end = train_end + 1
        if validation_end >= n_sessions:
            raise SessionSplitFeasibilityError(
                f"Capture {capture_id} cannot provide non-empty temporal partitions"
            )
        train_part = sessions.iloc[:train_end]
        validation_part = sessions.iloc[train_end:validation_end]
        test_part = sessions.iloc[validation_end:]
        train_session_ids.update(train_part["session_id"].astype(int))
        validation_session_ids.update(validation_part["session_id"].astype(int))
        test_session_ids.update(test_part["session_id"].astype(int))
        boundaries[str(int(capture_id))] = {
            "n_sessions": n_sessions,
            "n_train_sessions": int(len(train_part)),
            "n_validation_sessions": int(len(validation_part)),
            "n_test_sessions": int(len(test_part)),
            "train_min_time": float(train_part["session_start_time"].min()),
            "train_max_time": float(train_part["session_start_time"].max()),
            "validation_min_time": float(validation_part["session_start_time"].min()),
            "validation_max_time": float(validation_part["session_start_time"].max()),
            "test_min_time": float(test_part["session_start_time"].min()),
            "test_max_time": float(test_part["session_start_time"].max()),
            "tie_breaker": "session_id ascending",
        }

    if train_session_ids & validation_session_ids or train_session_ids & test_session_ids:
        raise AssertionError("Temporal train session overlap")
    if validation_session_ids & test_session_ids:
        raise AssertionError("Temporal validation/test session overlap")
    train_df = df[df["session_id"].astype(int).isin(train_session_ids)].copy()
    validation_df = df[df["session_id"].astype(int).isin(validation_session_ids)].copy()
    test_df = df[df["session_id"].astype(int).isin(test_session_ids)].copy()
    capture_ids = sorted(df["dataset_id"].astype(int).unique().tolist())
    fold = _fold_record(
        fold_index=0,
        train_df=train_df.sort_values("packet_id").reset_index(drop=True),
        validation_df=validation_df.sort_values("packet_id").reset_index(drop=True),
        test_df=test_df.sort_values("packet_id").reset_index(drop=True),
        excluded_ids=[],
        train_captures=capture_ids,
        validation_captures=capture_ids,
        test_captures=capture_ids,
        held_out_capture=None,
        held_out_family=None,
        seed=int(random_state),
        temporal_boundaries=boundaries,
    )
    for partition in (fold["train"], fold["validation"], fold["test"]):
        if min(partition["support_0"], partition["support_1"]) <= 0:
            raise SessionSplitFeasibilityError(
                "Within-capture temporal partition is single-class after cohort construction"
            )

    cohort_ids = df["packet_id"].astype(int).tolist()
    manifest = {
        "schema_version": SESSION_MANIFEST_SCHEMA_VERSION,
        "manifest_kind": SESSION_MANIFEST_KIND,
        "split_mode": WITHIN_CAPTURE_TEMPORAL,
        "split_type": "within_capture_temporal_session_holdout",
        "interpretation": (
            "seen-capture upper bound: later sessions from capture environments represented "
            "during training"
        ),
        "unsupported_claims": [
            "generalization to unseen captures",
            "generalization to unseen malware families",
            "elimination of capture-specific shortcuts",
        ],
        "experiment_key": experiment_key,
        "evaluation_mode": str(evaluation_mode).strip().lower(),
        "cohort_filters": _json_ready(cohort_filters),
        "eligibility": _json_ready(eligibility),
        "cohort_sample_ids": cohort_ids,
        "cohort_hash": cohort_hash(cohort_ids, eligibility),
        "cohort_size": int(len(cohort_ids)),
        "random_state": int(random_state),
        "n_folds": 1,
        "temporal_fractions": {
            "train": float(train_fraction),
            "validation": float(validation_fraction),
            "test": float(test_fraction),
        },
        "expected_malware_families": list(expected_families),
        "benign_capture_ids": sorted(benign),
        "malware_capture_ids": sorted(malicious),
        "family_by_capture": {str(key): value for key, value in family_by_capture.items()},
        "folds": [fold],
    }
    manifest["manifest_hash"] = _stable_hash(manifest)[:16]
    return _json_ready(manifest)


def build_session_split_manifest(df: pd.DataFrame, *, split_mode: str, **kwargs) -> dict:
    mode = str(split_mode).strip().lower()
    if mode == CAPTURE_DISJOINT_5FOLD:
        return build_capture_disjoint_5fold_manifest(df, **kwargs)
    if mode == WITHIN_CAPTURE_TEMPORAL:
        return build_within_capture_temporal_manifest(df, **kwargs)
    raise ValueError(f"Unknown session split mode={split_mode!r}")


def save_session_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{manifest['manifest_hash']}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(_json_ready(manifest), handle, indent=2)
    temporary.replace(path)


def load_session_manifest(
    path: Path,
    *,
    expected_split_mode: str,
    expected_eligibility: dict,
) -> dict:
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != SESSION_MANIFEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported session manifest schema in {path}: "
            f"{manifest.get('schema_version')} != {SESSION_MANIFEST_SCHEMA_VERSION}"
        )
    if manifest.get("manifest_kind") != SESSION_MANIFEST_KIND:
        raise RuntimeError(f"Unexpected session manifest kind in {path}")
    if manifest.get("split_mode") != str(expected_split_mode).strip().lower():
        raise RuntimeError(
            f"Session manifest split mode mismatch in {path}: "
            f"{manifest.get('split_mode')} != {expected_split_mode}"
        )
    if manifest.get("eligibility") != _json_ready(expected_eligibility):
        raise RuntimeError(
            f"Session manifest eligibility mismatch in {path}: "
            f"{manifest.get('eligibility')} != {expected_eligibility}"
        )
    stored_hash = manifest.get("manifest_hash")
    calculated_hash = _stable_hash(
        {key: value for key, value in manifest.items() if key != "manifest_hash"}
    )[:16]
    if stored_hash != calculated_hash:
        raise RuntimeError(f"Session manifest hash mismatch in {path}")
    return manifest


def materialize_session_splits(
    df: pd.DataFrame,
    manifest: dict,
) -> list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Materialize exact sample-ID partitions and re-audit their leakage boundary."""
    if manifest.get("manifest_kind") != SESSION_MANIFEST_KIND:
        raise ValueError("Expected a session_split_protocol manifest")
    _require_columns(df, {"packet_id", "session_id", "dataset_id", "is_malicious"})
    if df["packet_id"].duplicated().any():
        raise ValueError("Cohort sample identifiers are not unique")
    expected_ids = [int(value) for value in manifest.get("cohort_sample_ids", [])]
    eligibility = manifest.get("eligibility") or {}
    actual_ids = df["packet_id"].astype(int).tolist()
    if expected_ids != actual_ids:
        raise RuntimeError("Cohort order or membership does not match the frozen manifest")
    if cohort_hash(actual_ids, eligibility) != manifest.get("cohort_hash"):
        raise RuntimeError("Cohort hash does not match the frozen session manifest")

    by_id = df.set_index("packet_id", drop=False)
    materialized = []
    split_mode = manifest["split_mode"]
    for fold in manifest.get("folds", []):
        partitions: dict[str, pd.DataFrame] = {}
        sample_sets: dict[str, set[int]] = {}
        for name in ("train", "validation", "test"):
            ids = [int(value) for value in fold[f"{name}_sample_ids"]]
            missing = [sample_id for sample_id in ids if sample_id not in by_id.index]
            if missing:
                raise RuntimeError(
                    f"Fold {fold['fold_index']} {name} is missing {len(missing)} samples"
                )
            partitions[name] = by_id.loc[ids].reset_index(drop=True)
            sample_sets[name] = set(ids)
            if _partition_summary(partitions[name]) != fold[name]:
                raise RuntimeError(
                    f"Fold {fold['fold_index']} {name} support does not match manifest"
                )
        if sample_sets["train"] & sample_sets["validation"]:
            raise RuntimeError("Train/validation sample overlap")
        if sample_sets["train"] & sample_sets["test"]:
            raise RuntimeError("Train/test sample overlap")
        if sample_sets["validation"] & sample_sets["test"]:
            raise RuntimeError("Validation/test sample overlap")

        session_sets = {
            name: set(frame["session_id"].astype(int)) for name, frame in partitions.items()
        }
        if session_sets["train"] & session_sets["validation"]:
            raise RuntimeError("Train/validation session overlap")
        if session_sets["train"] & session_sets["test"]:
            raise RuntimeError("Train/test session overlap")
        if session_sets["validation"] & session_sets["test"]:
            raise RuntimeError("Validation/test session overlap")

        if split_mode == CAPTURE_DISJOINT_5FOLD:
            capture_sets = {
                name: set(frame["dataset_id"].astype(int)) for name, frame in partitions.items()
            }
            if capture_sets["train"] & capture_sets["validation"]:
                raise RuntimeError("Train/validation capture overlap")
            if capture_sets["train"] & capture_sets["test"]:
                raise RuntimeError("Train/test capture overlap")
            if capture_sets["validation"] & capture_sets["test"]:
                raise RuntimeError("Validation/test capture overlap")
        elif split_mode == WITHIN_CAPTURE_TEMPORAL:
            for capture_id, boundary in (fold.get("temporal_boundaries") or {}).items():
                if boundary["train_max_time"] > boundary["validation_min_time"]:
                    raise RuntimeError(f"Temporal train/validation order violated in {capture_id}")
                if boundary["validation_max_time"] > boundary["test_min_time"]:
                    raise RuntimeError(f"Temporal validation/test order violated in {capture_id}")
        else:
            raise RuntimeError(f"Unknown split mode in manifest: {split_mode}")

        materialized.append(
            (fold, partitions["train"], partitions["validation"], partitions["test"])
        )
    if len(materialized) != int(manifest.get("n_folds", -1)):
        raise RuntimeError("Session manifest fold count mismatch")
    return materialized
