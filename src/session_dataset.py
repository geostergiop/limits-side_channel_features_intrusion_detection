#!/usr/bin/env python3
"""
Session experiment dataset builders.

This module adds a second, more deployment-oriented feature configuration and
sample units beyond single packets:

- packet_ablation: retained only as an ablation against the original design
- session_sequence: whole-session ordered segment summaries + tabular profiles
- behavior_window: ordered summaries of fixed-duration windows across a session
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from configs.config import ML_CONFIG, SESSION_CONFIG, RESULTS_DIR, SESSION_SPLIT_CONFIG
from src.session_splits import (
    CAPTURE_DISJOINT_5FOLD,
    SESSION_MANIFEST_SCHEMA_VERSION,
    WITHIN_CAPTURE_TEMPORAL,
    build_session_split_manifest,
    capture_stratified_sample_ids,
    load_session_manifest,
    save_session_manifest,
)


MINIMAL_FEATURES = [
    "packet_size",
    "payload_size",
    "payload_ratio",
    "ratio_to_prev",
    "time_diff",
]

MERCURY_FEATURES = [
    "direction_is_outgoing",
    "direction_switch",
    "protocol_is_tcp",
    "protocol_is_udp",
    "session_is_encrypted",
    "src_port",
    "dst_port",
    "service_port",
    "src_port_well_known",
    "dst_port_well_known",
    "src_port_ephemeral",
    "dst_port_ephemeral",
    "service_port_is_tls",
    "service_port_is_dns",
    "service_port_is_web",
    "packet_idx_norm",
    "time_since_session_start",
    "log_time_diff",
    "packet_size_delta",
    "payload_size_delta",
]

COMBINED_FEATURES = MINIMAL_FEATURES + MERCURY_FEATURES

FEATURE_SET_DESCRIPTIONS = {
    "minimal": (
        "Five original side-channel features: packet size, payload size, "
        "payload ratio, ratio to previous packet, and inter-arrival time."
    ),
    "mercury": (
        "Mercury-style network metadata available from this project's extracted "
        "packet/session tables: direction, protocol, ports, service-port hints, "
        "encryption hint, packet position, elapsed time, direction changes, "
        "and packet/payload deltas. Raw TLS extension, SSH, HTTP, and TCP-option "
        "fingerprints are not present in the current SQLite schema."
    ),
    "combined": (
        "The original five side-channel features plus the Mercury-style metadata "
        "features available in the extracted packet/session tables."
    ),
    "practical_metadata": (
        "Backward-compatible alias for the combined minimal plus Mercury-style "
        "metadata feature set."
    ),
}

TLS_PORTS = {443, 465, 587, 8443, 993, 995}
DNS_PORTS = {53, 5353}
WEB_PORTS = {80, 443, 8000, 8080, 8443, 8888}


@dataclass(frozen=True)
class SessionDatasetSpec:
    sample_unit: str
    feature_set: str
    group_by: str
    sample_size: int
    evaluation_mode: str = "balanced"
    encrypted_only: bool = False
    window_seconds: float | None = None
    split_mode: str = CAPTURE_DISJOINT_5FOLD


def get_feature_columns(feature_set: str) -> list[str]:
    key = str(feature_set).strip().lower()
    if key == "minimal":
        return list(MINIMAL_FEATURES)
    if key == "mercury":
        return list(MERCURY_FEATURES)
    if key == "combined":
        return list(COMBINED_FEATURES)
    if key == "practical_metadata":
        return list(COMBINED_FEATURES)
    raise ValueError(f"Unknown feature_set={feature_set!r}")


def profile_feature_columns(feature_set: str) -> list[str]:
    feature_cols = get_feature_columns(feature_set)
    stats = ["mean", "std", "min", "max", "p25", "p75"]
    columns: list[str] = []
    for col in feature_cols:
        columns.extend([f"{col}__{stat}" for stat in stats])
    columns.extend(["sample_n_packets", "sample_duration_s"])
    return columns


def behavior_window_feature_columns(feature_set: str) -> list[str]:
    columns = profile_feature_columns(feature_set)
    columns.extend(
        [
            "window_n_windows",
            "window_packets_mean",
            "window_packets_std",
            "window_packets_max",
            "window_duration_mean",
            "window_duration_std",
            "window_duration_max",
        ]
    )
    return columns


def session_manifest_dir() -> Path:
    path = (
        Path(RESULTS_DIR)
        / str(ML_CONFIG.get("split_manifest_dir", "split_manifests"))
        / "session_protocol_v1"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def eligibility_for_spec(spec: SessionDatasetSpec) -> dict:
    if spec.sample_unit == "behavior_window":
        minimum = int(SESSION_CONFIG["behavior_window_min_packets"])
    elif spec.sample_unit == "session_sequence":
        minimum = int(SESSION_CONFIG["session_min_packets"])
    elif spec.sample_unit == "packet_ablation":
        minimum = 2
    else:
        raise ValueError(f"Unknown sample_unit={spec.sample_unit!r}")
    return {
        "sample_unit": str(spec.sample_unit),
        "minimum_packets_per_session": int(minimum),
        "encrypted_only": bool(spec.encrypted_only),
    }


def _manifest_path(spec: SessionDatasetSpec) -> Path:
    eligibility = eligibility_for_spec(spec)
    payload = {
        "session_manifest_schema": SESSION_MANIFEST_SCHEMA_VERSION,
        "session_dataset_version": "session_v4_split_redesign",
        "sample_unit": spec.sample_unit,
        "sample_size": int(spec.sample_size),
        "evaluation_mode": spec.evaluation_mode,
        "split_mode": spec.split_mode,
        "encrypted_only": bool(spec.encrypted_only),
        "window_seconds": None if spec.window_seconds is None else float(spec.window_seconds),
        "eligibility": eligibility,
        "random_state": int(ML_CONFIG["random_state"]),
    }
    suffix = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    stem = f"{spec.sample_unit}_{spec.split_mode}_{spec.evaluation_mode}"
    if spec.window_seconds is not None:
        stem += f"_{str(spec.window_seconds).replace('.', 'p')}s"
    return session_manifest_dir() / f"{stem}__{suffix}.json"


@contextmanager
def _manifest_lock(path: Path):
    """Serialize manifest creation so parallel feature runs cannot overwrite it."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    timeout = float(SESSION_SPLIT_CONFIG.get("manifest_lock_timeout_seconds", 60))
    deadline = time.monotonic() + timeout
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode("ascii"))
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for manifest lock: {lock_path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _sample_without_replacement(values: list[int], count: int, seed: int) -> list[int]:
    if count >= len(values):
        return list(values)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(values), size=count, replace=False)
    chosen = [int(values[i]) for i in idx]
    chosen.sort()
    return chosen


def _eligible_session_pool(
    conn,
    *,
    min_packets: int,
    encrypted_only: bool = False,
) -> pd.DataFrame:
    where = ["1=1"]
    params: list[object] = []
    if encrypted_only:
        where.append("s.is_encrypted = 1")
    query = f"""
        SELECT
            s.id AS session_id,
            s.dataset_id,
            s.is_malicious,
            COALESCE(s.malware_family, '') AS malware_family,
            COUNT(p.id) AS n_packets
        FROM sessions s
        INNER JOIN packets p ON (p.session_id = s.id)
        WHERE {' AND '.join(where)}
        GROUP BY s.id
        HAVING COUNT(p.id) >= ?
        ORDER BY s.id
    """
    params.append(int(min_packets))
    session_df = pd.read_sql_query(query, conn, params=params)
    return session_df


def sample_session_ids(
    conn,
    *,
    sample_size: int,
    min_packets: int,
    evaluation_mode: str,
    encrypted_only: bool = False,
    seed: int | None = None,
    family_stratified: bool = True,
) -> list[int]:
    session_df = _eligible_session_pool(
        conn,
        min_packets=min_packets,
        encrypted_only=encrypted_only,
    )
    if session_df.empty:
        return []

    mal_df = session_df[session_df["is_malicious"] == 1].copy()
    norm_df = session_df[session_df["is_malicious"] == 0].copy()
    if mal_df.empty or norm_df.empty:
        return []

    base_seed = int(seed if seed is not None else ML_CONFIG["random_state"])
    mode = str(evaluation_mode).strip().lower()
    if mode == "balanced":
        target_each = max(1, int(sample_size) // 2)
        target_each = min(target_each, len(mal_df), len(norm_df))
        if family_stratified:
            chosen_mal = capture_stratified_sample_ids(
                mal_df,
                target_each,
                base_seed + 11,
                id_col="session_id",
            )
            chosen_norm = capture_stratified_sample_ids(
                norm_df,
                target_each,
                base_seed + 29,
                id_col="session_id",
            )
        else:
            chosen_mal = _sample_without_replacement(
                mal_df["session_id"].astype(int).tolist(), target_each, base_seed + 11
            )
            chosen_norm = _sample_without_replacement(
                norm_df["session_id"].astype(int).tolist(), target_each, base_seed + 29
            )
        return sorted(chosen_mal + chosen_norm)

    if mode == "deployment":
        available = session_df["session_id"].astype(int).tolist()
        target = min(int(sample_size), len(available))
        captures = sorted(session_df["dataset_id"].astype(int).unique().tolist())
        if target < len(captures):
            raise RuntimeError(
                f"Deployment cohort size={target} cannot represent all {len(captures)} captures"
            )
        required: list[int] = []
        for capture_id in captures:
            values = session_df[session_df["dataset_id"].astype(int) == capture_id][
                "session_id"
            ].astype(int).tolist()
            required.extend(
                _sample_without_replacement(values, 1, base_seed + 41 + capture_id * 101)
            )
        remaining_pool = sorted(set(available) - set(required))
        chosen = sorted(
            required
            + _sample_without_replacement(
                remaining_pool,
                target - len(required),
                base_seed + 53,
            )
        )
        chosen_df = session_df[session_df["session_id"].isin(chosen)]
        if chosen_df["is_malicious"].nunique() < 2:
            raise RuntimeError(
                "Natural-prevalence Session sampling produced a single-class cohort. "
                "Increase sample_size or adjust filters."
            )
        return sorted(chosen)

    raise ValueError(f"Unknown Session evaluation_mode={evaluation_mode!r}")


def load_packets_for_session_ids(conn, session_ids: list[int]) -> pd.DataFrame:
    columns = [
        "packet_id",
        "session_id",
        "dataset_id",
        "packet_idx",
        "packet_size",
        "payload_size",
        "payload_ratio",
        "ratio_to_prev",
        "time_diff",
        "timestamp",
        "direction",
        "src_port",
        "dst_port",
        "protocol",
        "session_is_encrypted",
        "is_malicious",
        "malware_family",
    ]
    if not session_ids:
        return pd.DataFrame(columns=columns)

    table_name = "_selected_session_sessions"
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(
        f"CREATE TEMP TABLE {table_name} (session_id INTEGER PRIMARY KEY, ord INTEGER NOT NULL)"
    )
    try:
        conn.executemany(
            f"INSERT INTO {table_name} (session_id, ord) VALUES (?, ?)",
            ((int(session_id), idx) for idx, session_id in enumerate(session_ids)),
        )
        query = f"""
            SELECT
                p.id AS packet_id,
                p.session_id,
                s.dataset_id,
                p.packet_idx,
                p.packet_size,
                p.payload_size,
                p.payload_ratio,
                p.ratio_to_prev,
                p.time_diff,
                p.timestamp,
                p.direction,
                s.src_port,
                s.dst_port,
                s.protocol,
                s.is_encrypted AS session_is_encrypted,
                p.is_malicious,
                s.malware_family
            FROM {table_name} q
            INNER JOIN sessions s ON (s.id = q.session_id)
            INNER JOIN packets p ON (p.session_id = q.session_id)
            ORDER BY q.ord, p.packet_idx
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    return df


def derive_practical_packet_features(packet_df: pd.DataFrame) -> pd.DataFrame:
    df = packet_df.copy()
    if df.empty:
        return df

    df["direction_is_outgoing"] = (df["direction"].fillna("") == "outgoing").astype(int)
    prev_direction = df.groupby("session_id")["direction_is_outgoing"].shift(1)
    df["direction_switch"] = (
        (df["direction_is_outgoing"] != prev_direction.fillna(df["direction_is_outgoing"]))
        .astype(int)
    )
    df.loc[df["packet_idx"] == 0, "direction_switch"] = 0

    proto = df["protocol"].fillna("").str.lower()
    df["protocol_is_tcp"] = (proto == "tcp").astype(int)
    df["protocol_is_udp"] = (proto == "udp").astype(int)
    df["session_is_encrypted"] = df["session_is_encrypted"].fillna(0).astype(int)

    df["src_port"] = df["src_port"].fillna(0).astype(int)
    df["dst_port"] = df["dst_port"].fillna(0).astype(int)
    df["service_port"] = np.minimum(df["src_port"], df["dst_port"]).astype(int)
    df["src_port_well_known"] = (df["src_port"] <= 1024).astype(int)
    df["dst_port_well_known"] = (df["dst_port"] <= 1024).astype(int)
    df["src_port_ephemeral"] = (df["src_port"] >= 49152).astype(int)
    df["dst_port_ephemeral"] = (df["dst_port"] >= 49152).astype(int)
    df["service_port_is_tls"] = df["service_port"].isin(TLS_PORTS).astype(int)
    df["service_port_is_dns"] = df["service_port"].isin(DNS_PORTS).astype(int)
    df["service_port_is_web"] = df["service_port"].isin(WEB_PORTS).astype(int)

    session_counts = df.groupby("session_id")["packet_id"].transform("size").clip(lower=1)
    df["packet_idx_norm"] = df["packet_idx"].astype(float) / np.maximum(session_counts - 1, 1)
    session_start = df.groupby("session_id")["timestamp"].transform("min")
    df["time_since_session_start"] = (
        df["timestamp"].astype(float).fillna(0.0) - session_start.astype(float).fillna(0.0)
    )
    df["log_time_diff"] = np.log1p(df["time_diff"].clip(lower=0.0).astype(float))

    prev_packet_size = df.groupby("session_id")["packet_size"].shift(1).fillna(df["packet_size"])
    prev_payload_size = df.groupby("session_id")["payload_size"].shift(1).fillna(df["payload_size"])
    df["packet_size_delta"] = df["packet_size"].astype(float) - prev_packet_size.astype(float)
    df["payload_size_delta"] = df["payload_size"].astype(float) - prev_payload_size.astype(float)
    return df


def _safe_std(values: np.ndarray) -> float:
    if len(values) <= 1:
        return 0.0
    return float(np.std(values, ddof=1))


def _round_float(value: float) -> float:
    return round(float(value), 6)


def _segment_summary(segment_df: pd.DataFrame, feature_cols: list[str], segment_index: int) -> dict:
    payload = {
        "segment_index": int(segment_index),
        "n_packets": int(len(segment_df)),
        "start_s": _round_float(segment_df["time_since_session_start"].min()),
        "end_s": _round_float(segment_df["time_since_session_start"].max()),
        "mean": [],
        "std": [],
    }
    for col in feature_cols:
        values = segment_df[col].astype(float).to_numpy()
        payload["mean"].append(_round_float(np.mean(values)))
        payload["std"].append(_round_float(_safe_std(values)))
    return payload


def serialize_segment_sequence(
    sample_df: pd.DataFrame,
    *,
    feature_set: str,
    window_seconds: float | None = None,
) -> str:
    feature_cols = get_feature_columns(feature_set)
    segment_size = int(SESSION_CONFIG.get("sequence_segment_size", 16))
    max_segments = int(SESSION_CONFIG.get("max_sequence_segments", 32))
    work = sample_df.sort_values("packet_idx").reset_index(drop=True)
    if window_seconds is not None:
        work = work[work["time_since_session_start"] <= float(window_seconds)].reset_index(drop=True)
    if work.empty:
        return json.dumps({"feature_names": feature_cols, "segments": [], "total_packets": 0})

    if len(work) <= segment_size * max_segments:
        bounds = list(range(0, len(work), segment_size))
        chunks = [work.iloc[start:start + segment_size] for start in bounds]
    else:
        split_points = np.array_split(np.arange(len(work)), max_segments)
        chunks = [work.iloc[idx] for idx in split_points if len(idx) > 0]

    segments = [
        _segment_summary(chunk.reset_index(drop=True), feature_cols, idx)
        for idx, chunk in enumerate(chunks)
    ]
    payload = {
        "feature_set": feature_set,
        "feature_names": feature_cols,
        "total_packets": int(len(work)),
        "duration_s": _round_float(work["time_since_session_start"].max()),
        "window_seconds": None if window_seconds is None else float(window_seconds),
        "segments": segments,
    }
    return json.dumps(payload, separators=(",", ":"))


def _profile_payload(sample_df: pd.DataFrame, feature_cols: list[str]) -> dict[str, float]:
    payload: dict[str, float] = {}
    for col in feature_cols:
        values = sample_df[col].astype(float).to_numpy()
        payload[f"{col}__mean"] = float(np.mean(values))
        payload[f"{col}__std"] = _safe_std(values)
        payload[f"{col}__min"] = float(np.min(values))
        payload[f"{col}__max"] = float(np.max(values))
        payload[f"{col}__p25"] = float(np.percentile(values, 25))
        payload[f"{col}__p75"] = float(np.percentile(values, 75))
    payload["sample_n_packets"] = float(len(sample_df))
    payload["sample_duration_s"] = float(sample_df["time_since_session_start"].max())
    return payload


def _window_groups(sample_df: pd.DataFrame, window_seconds: float) -> list[pd.DataFrame]:
    work = sample_df.sort_values("packet_idx").reset_index(drop=True)
    if work.empty:
        return []
    window = max(float(window_seconds), 1e-9)
    window_index = np.floor(work["time_since_session_start"].astype(float) / window).astype(int)
    return [
        group.reset_index(drop=True)
        for _idx, group in work.assign(_window_index=window_index).groupby("_window_index", sort=True)
        if not group.empty
    ]


def _behavior_window_profile(sample_df: pd.DataFrame, feature_cols: list[str], window_seconds: float) -> dict[str, float]:
    payload = _profile_payload(sample_df, feature_cols)
    windows = _window_groups(sample_df, window_seconds)
    packet_counts = np.asarray([len(window) for window in windows], dtype=float)
    durations = np.asarray(
        [
            max(
                float(window["time_since_session_start"].max())
                - float(window["time_since_session_start"].min()),
                0.0,
            )
            for window in windows
        ],
        dtype=float,
    )
    payload["window_n_windows"] = float(len(windows))
    payload["window_packets_mean"] = float(np.mean(packet_counts)) if len(packet_counts) else 0.0
    payload["window_packets_std"] = _safe_std(packet_counts) if len(packet_counts) else 0.0
    payload["window_packets_max"] = float(np.max(packet_counts)) if len(packet_counts) else 0.0
    payload["window_duration_mean"] = float(np.mean(durations)) if len(durations) else 0.0
    payload["window_duration_std"] = _safe_std(durations) if len(durations) else 0.0
    payload["window_duration_max"] = float(np.max(durations)) if len(durations) else 0.0
    return payload


def serialize_behavior_window_sequence(
    sample_df: pd.DataFrame,
    *,
    feature_set: str,
    window_seconds: float,
) -> str:
    feature_cols = get_feature_columns(feature_set)
    windows = _window_groups(sample_df, window_seconds)
    max_windows = int(SESSION_CONFIG.get("max_sequence_segments", 32))
    reported: list[dict] = []
    if len(windows) <= max_windows:
        for idx, window in enumerate(windows):
            summary = _segment_summary(window, feature_cols, idx)
            summary["source_window_start"] = int(idx)
            summary["source_window_end"] = int(idx)
            summary["n_source_windows"] = 1
            reported.append(summary)
    else:
        for out_idx, source_indices in enumerate(np.array_split(np.arange(len(windows)), max_windows)):
            if len(source_indices) == 0:
                continue
            merged = pd.concat(
                [windows[int(source_idx)] for source_idx in source_indices],
                ignore_index=True,
            )
            summary = _segment_summary(merged, feature_cols, out_idx)
            summary["source_window_start"] = int(source_indices[0])
            summary["source_window_end"] = int(source_indices[-1])
            summary["n_source_windows"] = int(len(source_indices))
            reported.append(summary)
    payload = {
        "feature_set": feature_set,
        "feature_names": feature_cols,
        "window_seconds": float(window_seconds),
        "total_packets": int(len(sample_df)),
        "total_windows": int(len(windows)),
        "reported_windows": int(len(reported)),
        "window_reporting": "all" if len(windows) <= max_windows else "compressed_ordered_bins",
        "duration_s": _round_float(sample_df["time_since_session_start"].max()) if len(sample_df) else 0.0,
        "windows": reported,
    }
    return json.dumps(payload, separators=(",", ":"))


def _session_start_time(packet_df: pd.DataFrame) -> float:
    timestamps = pd.to_numeric(packet_df["timestamp"], errors="coerce").dropna()
    if timestamps.empty:
        session_id = packet_df["session_id"].iloc[0] if len(packet_df) else "unknown"
        raise RuntimeError(f"Session {session_id} has no usable packet timestamp")
    return float(timestamps.min())


def build_session_sequence_samples(packet_df: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    feature_cols = get_feature_columns(feature_set)
    rows: list[dict] = []
    for session_id, group in packet_df.groupby("session_id", sort=True):
        work = group.sort_values("packet_idx").reset_index(drop=True)
        profile = _profile_payload(work, feature_cols)
        rows.append(
            {
                "packet_id": int(session_id),
                "session_id": int(session_id),
                "dataset_id": int(work["dataset_id"].iloc[0]),
                "is_malicious": int(work["is_malicious"].iloc[0]),
                "malware_family": str(work["malware_family"].iloc[0] or ""),
                "session_start_time": _session_start_time(work),
                "sample_unit": "session_sequence",
                "feature_set": feature_set,
                "window_seconds": None,
                "sequence_json": serialize_segment_sequence(work, feature_set=feature_set),
                **profile,
            }
        )
    return pd.DataFrame(rows)


def build_behavior_window_samples(
    packet_df: pd.DataFrame,
    feature_set: str,
    *,
    window_seconds: float,
    min_packets: int,
) -> pd.DataFrame:
    feature_cols = get_feature_columns(feature_set)
    window_code = int(round(float(window_seconds) * 1000))
    rows: list[dict] = []
    for session_id, group in packet_df.groupby("session_id", sort=True):
        work = group.sort_values("packet_idx").reset_index(drop=True)
        if len(work) < int(min_packets):
            continue
        windows = _window_groups(work, float(window_seconds))
        if not windows:
            continue
        profile = _behavior_window_profile(work, feature_cols, float(window_seconds))
        rows.append(
            {
                "packet_id": int(session_id) * 100000 + window_code,
                "session_id": int(session_id),
                "dataset_id": int(work["dataset_id"].iloc[0]),
                "is_malicious": int(work["is_malicious"].iloc[0]),
                "malware_family": str(work["malware_family"].iloc[0] or ""),
                "session_start_time": _session_start_time(work),
                "sample_unit": "behavior_window",
                "feature_set": feature_set,
                "window_seconds": float(window_seconds),
                "sequence_json": serialize_behavior_window_sequence(
                    work,
                    feature_set=feature_set,
                    window_seconds=window_seconds,
                ),
                **profile,
            }
        )
    return pd.DataFrame(rows)


def build_packet_ablation_samples(
    packet_df: pd.DataFrame,
    feature_set: str,
    sample_size: int,
    *,
    evaluation_mode: str,
    packet_ids: list[int] | None = None,
) -> pd.DataFrame:
    feature_cols = get_feature_columns(feature_set)
    base = packet_df.copy().sort_values(["is_malicious", "packet_id"]).reset_index(drop=True)
    base_seed = int(ML_CONFIG["random_state"])
    mode = str(evaluation_mode).strip().lower()

    if packet_ids is not None:
        wanted = [int(packet_id) for packet_id in packet_ids]
        order = {packet_id: idx for idx, packet_id in enumerate(wanted)}
        work = base[base["packet_id"].astype(int).isin(order)].copy()
        if len(work) != len(wanted):
            missing = sorted(set(wanted) - set(work["packet_id"].astype(int).tolist()))
            raise RuntimeError(
                f"Unable to reconstruct packet-ablation cohort; missing {len(missing)} packet ids"
            )
        work["_manifest_order"] = work["packet_id"].astype(int).map(order)
        work = work.sort_values("_manifest_order").drop(columns=["_manifest_order"]).reset_index(drop=True)
    elif mode == "balanced":
        mal = base[base["is_malicious"] == 1]
        norm = base[base["is_malicious"] == 0]
        target_each = min(int(sample_size) // 2, len(mal), len(norm))
        mal_ids = capture_stratified_sample_ids(
            mal,
            target_each,
            base_seed + 101,
            id_col="packet_id",
        )
        norm_ids = capture_stratified_sample_ids(
            norm,
            target_each,
            base_seed + 211,
            id_col="packet_id",
        )
        chosen = set(mal_ids + norm_ids)
        work = base[base["packet_id"].isin(chosen)].copy().reset_index(drop=True)
    elif mode == "deployment":
        packet_ids = base["packet_id"].astype(int).tolist()
        target_size = min(int(sample_size), len(packet_ids))
        if target_size <= 0:
            return pd.DataFrame()
        captures = sorted(base["dataset_id"].astype(int).unique().tolist())
        if target_size < len(captures):
            raise RuntimeError(
                f"Deployment packet cohort size={target_size} cannot represent all "
                f"{len(captures)} captures"
            )
        required: list[int] = []
        for capture_id in captures:
            capture_ids = base[base["dataset_id"].astype(int) == capture_id][
                "packet_id"
            ].astype(int).tolist()
            required.extend(
                _sample_without_replacement(
                    capture_ids,
                    1,
                    base_seed + 307 + capture_id * 101,
                )
            )
        remaining_pool = sorted(set(packet_ids) - set(required))
        chosen_ids = required + _sample_without_replacement(
            remaining_pool,
            target_size - len(required),
            base_seed + 401,
        )
        work = base[base["packet_id"].isin(set(chosen_ids))].copy().reset_index(drop=True)
        if work["is_malicious"].nunique() < 2:
            raise RuntimeError(
                "Natural-prevalence packet-ablation sampling produced a single-class cohort. "
                "Increase SESSION_CONFIG['packet_ablation_sample_size'] to keep deployment-mode "
                "evaluation informative."
            )
    else:
        raise ValueError(f"Unknown Session evaluation_mode={evaluation_mode!r}")

    session_starts = {
        int(session_id): _session_start_time(group)
        for session_id, group in base.groupby("session_id", sort=False)
    }
    rows: list[dict] = []
    for row in work.itertuples(index=False):
        payload = {col: float(getattr(row, col)) for col in feature_cols}
        rows.append(
            {
                "packet_id": int(row.packet_id),
                "session_id": int(row.session_id),
                "dataset_id": int(row.dataset_id),
                "is_malicious": int(row.is_malicious),
                "malware_family": str(row.malware_family or ""),
                "session_start_time": float(session_starts[int(row.session_id)]),
                "sample_unit": "packet_ablation",
                "feature_set": feature_set,
                "window_seconds": None,
                "sequence_json": json.dumps(payload, separators=(",", ":")),
                **payload,
            }
        )
    return pd.DataFrame(rows)


def build_session_dataset(conn, spec: SessionDatasetSpec) -> tuple[pd.DataFrame, list[str]]:
    eligibility = eligibility_for_spec(spec)
    min_packets = int(eligibility["minimum_packets_per_session"])
    session_ids = sample_session_ids(
        conn,
        sample_size=int(spec.sample_size),
        min_packets=min_packets,
        evaluation_mode=spec.evaluation_mode,
        encrypted_only=bool(spec.encrypted_only),
        seed=int(ML_CONFIG["random_state"]),
        family_stratified=bool(
            SESSION_SPLIT_CONFIG.get("balanced_family_stratified", True)
        ),
    )
    if not session_ids:
        return pd.DataFrame(), []

    packet_df = load_packets_for_session_ids(conn, session_ids)
    packet_df = derive_practical_packet_features(packet_df)

    if spec.sample_unit == "session_sequence":
        dataset = build_session_sequence_samples(packet_df, spec.feature_set)
        return dataset, profile_feature_columns(spec.feature_set)
    if spec.sample_unit == "behavior_window":
        if spec.window_seconds is None:
            raise ValueError("behavior_window requires window_seconds")
        dataset = build_behavior_window_samples(
            packet_df,
            spec.feature_set,
            window_seconds=float(spec.window_seconds),
            min_packets=int(SESSION_CONFIG.get("behavior_window_min_packets", 6)),
        )
        return dataset, behavior_window_feature_columns(spec.feature_set)
    if spec.sample_unit == "packet_ablation":
        dataset = build_packet_ablation_samples(
            packet_df,
            spec.feature_set,
            sample_size=int(spec.sample_size),
            evaluation_mode=spec.evaluation_mode,
        )
        return dataset, get_feature_columns(spec.feature_set)
    raise ValueError(f"Unknown sample_unit={spec.sample_unit!r}")


def _session_ids_for_packet_ids(conn, packet_ids: list[int]) -> list[int]:
    if not packet_ids:
        return []
    table_name = "_selected_session_packet_ids"
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"CREATE TEMP TABLE {table_name} (packet_id INTEGER PRIMARY KEY)")
    try:
        conn.executemany(
            f"INSERT INTO {table_name} (packet_id) VALUES (?)",
            ((int(packet_id),) for packet_id in packet_ids),
        )
        rows = conn.execute(
            f"""
            SELECT DISTINCT p.session_id
            FROM packets p
            INNER JOIN {table_name} q ON (q.packet_id = p.id)
            ORDER BY p.session_id
            """
        ).fetchall()
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    return [int(row[0]) for row in rows]


def build_session_dataset_from_manifest(
    conn,
    spec: SessionDatasetSpec,
    manifest: dict,
) -> tuple[pd.DataFrame, list[str]]:
    cohort_ids = [int(packet_id) for packet_id in manifest.get("cohort_sample_ids", [])]
    if not cohort_ids:
        raise RuntimeError("Session manifest does not contain a frozen cohort")

    if spec.sample_unit == "session_sequence":
        session_ids = cohort_ids
    elif spec.sample_unit == "behavior_window":
        session_ids = sorted({int(packet_id) // 100000 for packet_id in cohort_ids})
    elif spec.sample_unit == "packet_ablation":
        session_ids = _session_ids_for_packet_ids(conn, cohort_ids)
    else:
        raise ValueError(f"Unknown sample_unit={spec.sample_unit!r}")

    packet_df = load_packets_for_session_ids(conn, session_ids)
    packet_df = derive_practical_packet_features(packet_df)

    if spec.sample_unit == "session_sequence":
        dataset = build_session_sequence_samples(packet_df, spec.feature_set)
        feature_cols = profile_feature_columns(spec.feature_set)
    elif spec.sample_unit == "behavior_window":
        if spec.window_seconds is None:
            raise ValueError("behavior_window requires window_seconds")
        dataset = build_behavior_window_samples(
            packet_df,
            spec.feature_set,
            window_seconds=float(spec.window_seconds),
            min_packets=int(SESSION_CONFIG.get("behavior_window_min_packets", 6)),
        )
        feature_cols = behavior_window_feature_columns(spec.feature_set)
    else:
        dataset = build_packet_ablation_samples(
            packet_df,
            spec.feature_set,
            sample_size=len(cohort_ids),
            evaluation_mode=spec.evaluation_mode,
            packet_ids=cohort_ids,
        )
        feature_cols = get_feature_columns(spec.feature_set)

    missing = sorted(set(cohort_ids) - set(dataset["packet_id"].astype(int).tolist()))
    if missing:
        raise RuntimeError(
            f"Unable to reconstruct Session manifest cohort; missing {len(missing)} sample ids"
        )
    return dataset, feature_cols


def _validate_manifest_request(manifest: dict, spec: SessionDatasetSpec) -> None:
    expected_filters = {
        "sample_unit": spec.sample_unit,
        "evaluation_mode": spec.evaluation_mode,
        "encrypted_only": bool(spec.encrypted_only),
        "window_seconds": None if spec.window_seconds is None else float(spec.window_seconds),
        "requested_sample_size": int(spec.sample_size),
    }
    if manifest.get("cohort_filters") != expected_filters:
        raise RuntimeError(
            "Frozen session manifest filters do not match the requested experiment: "
            f"{manifest.get('cohort_filters')} != {expected_filters}"
        )


def _build_manifest_for_spec(dataset: pd.DataFrame, spec: SessionDatasetSpec) -> dict:
    eligibility = eligibility_for_spec(spec)
    expected_families = list(SESSION_CONFIG["expected_malware_families"])
    common = {
        "experiment_key": f"Session_{spec.sample_unit}",
        "evaluation_mode": spec.evaluation_mode,
        "cohort_filters": {
            "sample_unit": spec.sample_unit,
            "evaluation_mode": spec.evaluation_mode,
            "encrypted_only": bool(spec.encrypted_only),
            "window_seconds": None if spec.window_seconds is None else float(spec.window_seconds),
            "requested_sample_size": int(spec.sample_size),
        },
        "eligibility": eligibility,
        "expected_families": expected_families,
        "random_state": int(ML_CONFIG["random_state"]),
    }
    if spec.split_mode == CAPTURE_DISJOINT_5FOLD:
        return build_session_split_manifest(
            dataset,
            split_mode=spec.split_mode,
            minimum_test_support_per_class=int(
                SESSION_SPLIT_CONFIG["minimum_test_support_per_class"]
            ),
            minimum_validation_support_per_class=int(
                SESSION_SPLIT_CONFIG["minimum_validation_support_per_class"]
            ),
            **common,
        )
    if spec.split_mode == WITHIN_CAPTURE_TEMPORAL:
        return build_session_split_manifest(
            dataset,
            split_mode=spec.split_mode,
            train_fraction=float(SESSION_SPLIT_CONFIG["within_capture_train_fraction"]),
            validation_fraction=float(
                SESSION_SPLIT_CONFIG["within_capture_validation_fraction"]
            ),
            test_fraction=float(SESSION_SPLIT_CONFIG["within_capture_test_fraction"]),
            minimum_sessions_per_capture=int(
                SESSION_SPLIT_CONFIG["within_capture_minimum_sessions_per_capture"]
            ),
            **common,
        )
    raise ValueError(f"Unknown session split mode={spec.split_mode!r}")


def load_or_create_session_manifest(conn, spec: SessionDatasetSpec) -> tuple[pd.DataFrame, list[str], dict, Path]:
    manifest_path = _manifest_path(spec)
    eligibility = eligibility_for_spec(spec)
    with _manifest_lock(manifest_path):
        if manifest_path.exists():
            manifest = load_session_manifest(
                manifest_path,
                expected_split_mode=spec.split_mode,
                expected_eligibility=eligibility,
            )
            _validate_manifest_request(manifest, spec)
            dataset, feature_cols = build_session_dataset_from_manifest(conn, spec, manifest)
            return dataset, feature_cols, manifest, manifest_path

        dataset, feature_cols = build_session_dataset(conn, spec)
        if dataset.empty:
            raise RuntimeError(
                f"Unable to build session dataset for sample_unit={spec.sample_unit}, "
                f"feature_set={spec.feature_set}, split_mode={spec.split_mode}"
            )
        manifest = _build_manifest_for_spec(dataset, spec)
        save_session_manifest(manifest_path, manifest)
        return dataset, feature_cols, manifest, manifest_path
