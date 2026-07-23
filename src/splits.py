#!/usr/bin/env python3
"""
Deterministic grouped split utilities.

The original project selected the "best" holdout after inspecting multiple
grouped candidates, which leaks information about the holdout distribution into
the protocol. The helpers here deliberately avoid that pattern:

- grouped splits are accepted on the first valid seed, not the "best" one
- repeated grouped train/validation/test manifests are frozen to disk and reused
- downstream consumers can materialize the exact same disjoint splits later
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


MANIFEST_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class GroupHoldoutSummary:
    group_col: str
    test_size_target: float
    test_size_actual: float
    overall_positive_rate: float
    train_positive_rate: float
    test_positive_rate: float
    n_train_groups: int
    n_test_groups: int
    valid: bool
    trials: int

    def as_dict(self) -> dict:
        return {
            "group_col": self.group_col,
            "test_size_target": self.test_size_target,
            "test_size_actual": self.test_size_actual,
            "overall_positive_rate": self.overall_positive_rate,
            "train_positive_rate": self.train_positive_rate,
            "test_positive_rate": self.test_positive_rate,
            "n_train_groups": self.n_train_groups,
            "n_test_groups": self.n_test_groups,
            "valid": self.valid,
            "trials": self.trials,
        }


GROUP_TO_COLUMN = {
    "session": "session_id",
    "capture": "dataset_id",
}


def resolve_group_column(group_by: str) -> str:
    group_by_norm = str(group_by).strip().lower()
    if group_by_norm not in GROUP_TO_COLUMN:
        raise ValueError(
            f"Unknown group_by={group_by!r}. Expected one of: "
            f"{', '.join(sorted(GROUP_TO_COLUMN))}"
        )
    return GROUP_TO_COLUMN[group_by_norm]


def _json_ready(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_json_ready(v) for v in value.tolist()]
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    return value


def _stable_hash(payload: dict) -> str:
    canonical = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _positive_rate(values: np.ndarray) -> float:
    return float(np.mean(values.astype(int))) if len(values) else 0.0


def _group_partition_key(values: Iterable) -> tuple:
    return tuple(sorted(_json_ready(list(set(values)))))


def _validate_label_split(y_train: np.ndarray, y_test: np.ndarray) -> bool:
    return len(np.unique(y_train)) >= 2 and len(np.unique(y_test)) >= 2


def _build_summary(
    *,
    df: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    group_col: str,
    label_col: str,
    test_size: float,
    trials: int,
) -> GroupHoldoutSummary:
    groups = df[group_col].to_numpy()
    y = df[label_col].astype(int).to_numpy()
    y_train = y[train_idx]
    y_test = y[test_idx]
    train_groups = set(groups[train_idx])
    test_groups = set(groups[test_idx])
    overlap = len(train_groups & test_groups)
    valid = overlap == 0 and _validate_label_split(y_train, y_test)
    return GroupHoldoutSummary(
        group_col=group_col,
        test_size_target=float(test_size),
        test_size_actual=float(len(test_idx) / len(df)),
        overall_positive_rate=_positive_rate(y),
        train_positive_rate=_positive_rate(y_train),
        test_positive_rate=_positive_rate(y_test),
        n_train_groups=len(train_groups),
        n_test_groups=len(test_groups),
        valid=valid,
        trials=trials,
    )


def _first_valid_group_split(
    df: pd.DataFrame,
    *,
    group_col: str,
    label_col: str,
    test_size: float,
    base_seed: int,
    max_attempts: int,
    used_test_group_partitions: set[tuple] | None = None,
) -> tuple[np.ndarray, np.ndarray, GroupHoldoutSummary, int]:
    if group_col not in df.columns:
        raise KeyError(f"Missing group column: {group_col}")
    if label_col not in df.columns:
        raise KeyError(f"Missing label column: {label_col}")
    if len(df) < 2:
        raise ValueError("Need at least two rows for a grouped split")

    groups = df[group_col].to_numpy()
    y = df[label_col].astype(int).to_numpy()
    used = used_test_group_partitions if used_test_group_partitions is not None else set()
    last_summary: GroupHoldoutSummary | None = None

    for attempt in range(max(1, int(max_attempts))):
        seed = int(base_seed + attempt)
        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=test_size,
            random_state=seed,
        )
        train_idx, test_idx = next(splitter.split(df, y, groups))
        test_partition = _group_partition_key(groups[test_idx])
        if test_partition in used:
            continue
        summary = _build_summary(
            df=df,
            train_idx=train_idx,
            test_idx=test_idx,
            group_col=group_col,
            label_col=label_col,
            test_size=test_size,
            trials=attempt + 1,
        )
        last_summary = summary
        if summary.valid:
            used.add(test_partition)
            return train_idx, test_idx, summary, seed

    summary_dump = last_summary.as_dict() if last_summary is not None else {}
    raise RuntimeError(
        f"Unable to build a valid grouped split for {group_col} after {max_attempts} "
        f"attempts. Last summary: {summary_dump}"
    )


def group_holdout_indices(
    df: pd.DataFrame,
    group_col: str,
    label_col: str = "is_malicious",
    test_size: float = 0.3,
    random_state: int = 42,
    n_trials: int = 256,
) -> tuple[np.ndarray, np.ndarray, GroupHoldoutSummary]:
    """
    Return train/test indices for a group-disjoint holdout.

    The first valid split is used. No holdout-label-based score optimisation is
    performed.
    """
    train_idx, test_idx, summary, _ = _first_valid_group_split(
        df,
        group_col=group_col,
        label_col=label_col,
        test_size=test_size,
        base_seed=random_state,
        max_attempts=n_trials,
    )
    return train_idx, test_idx, summary


def group_holdout_split(
    df: pd.DataFrame,
    group_col: str,
    label_col: str = "is_malicious",
    test_size: float = 0.3,
    random_state: int = 42,
    n_trials: int = 256,
) -> tuple[pd.DataFrame, pd.DataFrame, GroupHoldoutSummary]:
    """Convenience wrapper returning train/test dataframes plus summary."""
    train_idx, test_idx, summary = group_holdout_indices(
        df=df,
        group_col=group_col,
        label_col=label_col,
        test_size=test_size,
        random_state=random_state,
        n_trials=n_trials,
    )
    train_df = df.iloc[train_idx].copy().reset_index(drop=True)
    test_df = df.iloc[test_idx].copy().reset_index(drop=True)
    return train_df, test_df, summary


def build_repeated_grouped_holdout_manifest(
    df: pd.DataFrame,
    *,
    packet_ids: list[int],
    experiment_key: str,
    group_by: str,
    group_col: str,
    label_col: str = "is_malicious",
    sample_size: int | None,
    cohort_filters: dict,
    random_state: int,
    n_repeats: int,
    test_size: float,
    validation_size: float,
    max_attempts: int,
    metadata: dict | None = None,
) -> dict:
    """
    Build a deterministic repeated grouped holdout manifest.

    The manifest stores one frozen cohort plus per-repeat train/validation/test
    group memberships. Repeats are generated by stepping through deterministic
    seeds and accepting the first valid split at each repeat.
    """
    if "packet_id" not in df.columns:
        raise KeyError("Cohort dataframe must include packet_id")
    if list(df["packet_id"].astype(int)) != [int(x) for x in packet_ids]:
        raise ValueError("Manifest packet_ids must match dataframe packet_id order exactly")
    if not (0.0 < test_size < 1.0):
        raise ValueError(f"Invalid test_size={test_size}")
    if not (0.0 < validation_size < 1.0):
        raise ValueError(f"Invalid validation_size={validation_size}")

    packet_ids = [int(x) for x in packet_ids]
    used_outer_partitions: set[tuple] = set()
    repeats: list[dict] = []
    groups = df[group_col].to_numpy()
    y = df[label_col].astype(int).to_numpy()

    for repeat_index in range(int(n_repeats)):
        outer_seed_base = int(random_state + repeat_index * 10_000)
        accepted: tuple[np.ndarray, np.ndarray, GroupHoldoutSummary, int, np.ndarray, np.ndarray, GroupHoldoutSummary, int] | None = None
        last_inner_error: RuntimeError | None = None
        seen_outer_partitions: set[tuple] = set()

        for outer_attempt in range(int(max_attempts)):
            outer_seed = int(outer_seed_base + outer_attempt)
            splitter = GroupShuffleSplit(
                n_splits=1,
                test_size=test_size,
                random_state=outer_seed,
            )
            train_val_idx, test_idx = next(splitter.split(df, y, groups))
            outer_partition = _group_partition_key(groups[test_idx])
            if outer_partition in used_outer_partitions or outer_partition in seen_outer_partitions:
                continue
            seen_outer_partitions.add(outer_partition)

            outer_summary = _build_summary(
                df=df,
                train_idx=train_val_idx,
                test_idx=test_idx,
                group_col=group_col,
                label_col=label_col,
                test_size=test_size,
                trials=outer_attempt + 1,
            )
            if not outer_summary.valid:
                continue

            train_val_df = df.iloc[train_val_idx].reset_index(drop=True)
            inner_seed_base = int(random_state + 1_000_000 + repeat_index * 10_000 + outer_attempt * 1_000)
            try:
                inner_train_local, val_local, inner_summary, inner_seed = _first_valid_group_split(
                    train_val_df,
                    group_col=group_col,
                    label_col=label_col,
                    test_size=validation_size,
                    base_seed=inner_seed_base,
                    max_attempts=max_attempts,
                )
            except RuntimeError as e:
                last_inner_error = e
                continue

            used_outer_partitions.add(outer_partition)
            accepted = (
                train_val_idx,
                test_idx,
                outer_summary,
                outer_seed,
                inner_train_local,
                val_local,
                inner_summary,
                inner_seed,
            )
            break

        if accepted is None:
            if last_inner_error is not None:
                raise RuntimeError(
                    f"Unable to build a nested grouped split for {group_col} in repeat {repeat_index}. "
                    f"The outer split existed, but no grouped validation split was feasible within it. "
                    f"Last inner error: {last_inner_error}"
                ) from last_inner_error
            raise RuntimeError(
                f"Unable to build a valid grouped outer split for {group_col} in repeat {repeat_index}"
            )

        (
            train_val_idx,
            test_idx,
            outer_summary,
            outer_seed,
            inner_train_local,
            val_local,
            inner_summary,
            inner_seed,
        ) = accepted

        train_idx = train_val_idx[inner_train_local]
        val_idx = train_val_idx[val_local]

        repeat = {
            "repeat_index": int(repeat_index),
            "outer_seed": int(outer_seed),
            "inner_seed": int(inner_seed),
            "train_groups": _group_partition_key(df.iloc[train_idx][group_col].tolist()),
            "validation_groups": _group_partition_key(df.iloc[val_idx][group_col].tolist()),
            "test_groups": _group_partition_key(df.iloc[test_idx][group_col].tolist()),
            "n_train_packets": int(len(train_idx)),
            "n_validation_packets": int(len(val_idx)),
            "n_test_packets": int(len(test_idx)),
            "n_train_groups": int(df.iloc[train_idx][group_col].nunique()),
            "n_validation_groups": int(df.iloc[val_idx][group_col].nunique()),
            "n_test_groups": int(df.iloc[test_idx][group_col].nunique()),
            "train_positive_rate": _positive_rate(y[train_idx]),
            "validation_positive_rate": _positive_rate(y[val_idx]),
            "test_positive_rate": _positive_rate(y[test_idx]),
            "outer_summary": outer_summary.as_dict(),
            "inner_summary": inner_summary.as_dict(),
        }
        repeats.append(_json_ready(repeat))

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_kind": "repeated_grouped_holdout",
        "experiment_key": experiment_key,
        "group_by": group_by,
        "group_col": group_col,
        "label_col": label_col,
        "split_type": f"{group_by}_repeated_group_holdout",
        "sample_size": int(sample_size) if sample_size is not None else None,
        "cohort_filters": _json_ready(cohort_filters),
        "cohort_packet_ids": packet_ids,
        "cohort_hash": hashlib.sha256(",".join(map(str, packet_ids)).encode("utf-8")).hexdigest()[:16],
        "cohort_size": int(len(packet_ids)),
        "random_state": int(random_state),
        "n_repeats": int(n_repeats),
        "test_size": float(test_size),
        "validation_size": float(validation_size),
        "max_attempts": int(max_attempts),
        "repeats": repeats,
        "metadata": _json_ready(metadata or {}),
    }
    manifest["manifest_hash"] = _stable_hash(
        {k: v for k, v in manifest.items() if k != "manifest_hash"}
    )[:16]
    return manifest


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_ready(manifest), f, indent=2)


def load_manifest(path: Path, expected_kind: str | None = None) -> dict:
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported manifest schema in {path}: "
            f"{manifest.get('schema_version')} != {MANIFEST_SCHEMA_VERSION}"
        )
    if expected_kind is not None and manifest.get("manifest_kind") != expected_kind:
        raise RuntimeError(
            f"Unexpected manifest kind in {path}: {manifest.get('manifest_kind')}"
        )
    return manifest


def materialize_repeated_grouped_holdout_splits(
    df: pd.DataFrame,
    manifest: dict,
) -> list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """
    Materialize train/validation/test dataframes from a frozen manifest.
    """
    if manifest.get("manifest_kind") != "repeated_grouped_holdout":
        raise ValueError("Expected a repeated_grouped_holdout manifest")
    if "packet_id" not in df.columns:
        raise KeyError("Cohort dataframe must include packet_id")

    expected_packet_ids = [int(x) for x in manifest.get("cohort_packet_ids", [])]
    df_by_packet = df.set_index("packet_id", drop=False)
    missing = [pid for pid in expected_packet_ids if pid not in df_by_packet.index]
    if missing:
        raise RuntimeError(
            f"Cohort dataframe is missing {len(missing)} packet_ids required by the manifest"
        )
    cohort_df = df_by_packet.loc[expected_packet_ids].reset_index(drop=True)
    group_col = manifest["group_col"]

    materialized: list[tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for repeat in manifest.get("repeats", []):
        train_groups = set(repeat["train_groups"])
        validation_groups = set(repeat["validation_groups"])
        test_groups = set(repeat["test_groups"])
        train_df = cohort_df[cohort_df[group_col].isin(train_groups)].copy().reset_index(drop=True)
        validation_df = cohort_df[cohort_df[group_col].isin(validation_groups)].copy().reset_index(drop=True)
        test_df = cohort_df[cohort_df[group_col].isin(test_groups)].copy().reset_index(drop=True)

        expected_counts = {
            "train": int(repeat["n_train_packets"]),
            "validation": int(repeat["n_validation_packets"]),
            "test": int(repeat["n_test_packets"]),
        }
        actual_counts = {
            "train": len(train_df),
            "validation": len(validation_df),
            "test": len(test_df),
        }
        if expected_counts != actual_counts:
            raise RuntimeError(
                f"Manifest materialization mismatch for repeat {repeat['repeat_index']}: "
                f"expected {expected_counts}, got {actual_counts}"
            )
        if set(train_df[group_col]) & set(validation_df[group_col]):
            raise RuntimeError(f"Train/validation group overlap detected for {group_col}")
        if set(train_df[group_col]) & set(test_df[group_col]):
            raise RuntimeError(f"Train/test group overlap detected for {group_col}")
        if set(validation_df[group_col]) & set(test_df[group_col]):
            raise RuntimeError(f"Validation/test group overlap detected for {group_col}")

        materialized.append((repeat, train_df, validation_df, test_df))
    return materialized


def group_shuffle_split_unlabeled(
    df: pd.DataFrame,
    group_col: str,
    test_size: float = 0.3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Group-disjoint split that does not require multiple classes."""
    if group_col not in df.columns:
        raise KeyError(f"Missing group column: {group_col}")
    if len(df) < 2:
        raise ValueError("Need at least two rows for a holdout split")
    groups = df[group_col].to_numpy()
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(df, groups=groups))
    train_df = df.iloc[train_idx].copy().reset_index(drop=True)
    test_df = df.iloc[test_idx].copy().reset_index(drop=True)
    if set(train_df[group_col]) & set(test_df[group_col]):
        raise RuntimeError(f"Group overlap remained in unlabeled split for {group_col}")
    return train_df, test_df
