#!/usr/bin/env python3
"""Profile full-session and bounded-prefix input requirements."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import DB_PATH, SESSION_CONFIG
from src.session_dataset import get_feature_columns


MANIFEST_DIR = ROOT / "results" / "split_manifests" / "session_protocol_v1"
PUBLISHED_DIR = ROOT / "results" / "published"
OUTPUT_PATH = PUBLISHED_DIR / "session_input_requirements.summary.json"
CONTEXTS = (("1 s", 1.0), ("5 s", 5.0), ("30 s", 30.0), ("Whole", None))
FEATURES = ("minimal", "mercury", "combined")


def _one_file(pattern: str) -> Path:
    matches = sorted(MANIFEST_DIR.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one manifest for {pattern!r}; found {matches}")
    return matches[0]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(values: list[float]) -> dict[str, float]:
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("Cannot summarize an empty input-requirement series")
    return {
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "p25": float(np.percentile(data, 25)),
        "p75": float(np.percentile(data, 75)),
        "p95": float(np.percentile(data, 95)),
        "max": float(np.max(data)),
        "sum": float(np.sum(data)),
    }


def _manifest_session_ids(path: Path) -> set[int]:
    payload = _load_json(path)
    ids = [int(value) for value in payload["cohort_sample_ids"]]
    if "behavior_window" in path.name:
        return {value // 100000 for value in ids}
    return set(ids)


def _verify_shared_cohort(reference: set[int]) -> list[dict]:
    checked: list[dict] = []
    for seconds in (1.0, 5.0, 30.0):
        code = str(seconds).replace(".", "p")
        path = _one_file(
            f"behavior_window_capture_disjoint_5fold_deployment_{code}s__*.json"
        )
        ids = _manifest_session_ids(path)
        if ids != reference:
            raise RuntimeError(f"Behavior-window cohort differs from {reference=}: {path}")
        checked.append(
            {
                "artifact": path.name,
                "sha256": _sha256(path),
                "n_sessions": len(ids),
            }
        )
    return checked


def _load_packet_rows(session_ids: set[int]) -> dict[int, list[tuple[float, int]]]:
    grouped: dict[int, list[tuple[float, int]]] = {}
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TEMP TABLE selected_sessions (id INTEGER PRIMARY KEY)")
        conn.executemany(
            "INSERT INTO selected_sessions (id) VALUES (?)",
            ((session_id,) for session_id in sorted(session_ids)),
        )
        rows = conn.execute(
            """
            SELECT p.session_id, p.timestamp, p.packet_size
            FROM packets p
            INNER JOIN selected_sessions s ON (s.id = p.session_id)
            ORDER BY p.session_id, p.packet_idx
            """
        )
        for session_id, timestamp, packet_size in rows:
            grouped.setdefault(int(session_id), []).append(
                (float(timestamp or 0.0), int(packet_size))
            )
    if set(grouped) != session_ids:
        raise RuntimeError("Database packet rows do not reconstruct the frozen cohort")
    return grouped


def _segment_count(n_packets: int) -> int:
    segment_size = int(SESSION_CONFIG["sequence_segment_size"])
    max_segments = int(SESSION_CONFIG["max_sequence_segments"])
    return min(int(math.ceil(n_packets / segment_size)), max_segments)


def _load_observed_api_tokens() -> list[dict]:
    records: list[dict] = []
    for mode in ("balanced", "deployment"):
        path = PUBLISHED_DIR / (
            "session_llm_capture_disjoint_5fold_"
            f"{mode}_expanded_openai_memory.summary.json"
        )
        payload = _load_json(path)
        for row in payload["records"]:
            if row.get("record_type") != "summary":
                continue
            records.append(
                {
                    "evaluation_mode": mode,
                    "feature_set": row["feature_set"],
                    "representation": (
                        "Whole" if row["sample_unit"] == "session_sequence" else "5 s"
                    ),
                    "mean_total_api_tokens": float(row["avg_tokens"]),
                    "note": "Includes system, memory, held-out input, and output tokens",
                }
            )
    return records


def main() -> None:
    whole_manifest = _one_file(
        "session_sequence_capture_disjoint_5fold_deployment__*.json"
    )
    whole_payload = _load_json(whole_manifest)
    session_ids = _manifest_session_ids(whole_manifest)
    if len(session_ids) != 6000:
        raise RuntimeError(f"Expected 6,000 deployment sessions; found {len(session_ids)}")
    checked_manifests = _verify_shared_cohort(session_ids)
    grouped = _load_packet_rows(session_ids)

    prefix_packets = {label: [] for label, _seconds in CONTEXTS}
    prefix_wire_bytes = {label: [] for label, _seconds in CONTEXTS}
    current_reported_summaries = {label: [] for label, _seconds in CONTEXTS}

    for samples in grouped.values():
        timestamps = np.asarray([sample[0] for sample in samples], dtype=float)
        packet_sizes = np.asarray([sample[1] for sample in samples], dtype=int)
        elapsed = timestamps - float(np.min(timestamps))
        n_packets = len(samples)
        prefix_packets["Whole"].append(float(n_packets))
        prefix_wire_bytes["Whole"].append(float(np.sum(packet_sizes)))
        current_reported_summaries["Whole"].append(float(_segment_count(n_packets)))

        for label, seconds in CONTEXTS[:-1]:
            mask = elapsed <= float(seconds)
            prefix_packets[label].append(float(np.sum(mask)))
            prefix_wire_bytes[label].append(float(np.sum(packet_sizes[mask])))
            source_windows = len(
                np.unique(np.floor(elapsed / max(float(seconds), 1e-9)).astype(np.int64))
            )
            current_reported_summaries[label].append(
                float(min(source_windows, int(SESSION_CONFIG["max_sequence_segments"])))
            )

    raw_context_records: list[dict] = []
    prefix_feature_records: list[dict] = []
    current_feature_records: list[dict] = []
    for label, seconds in CONTEXTS:
        raw_context_records.append(
            {
                "context": label,
                "seconds": seconds,
                "packet_count": _stats(prefix_packets[label]),
                "observed_wire_bytes": _stats(prefix_wire_bytes[label]),
                "note": "Wire bytes traverse the sensor; they are not retained LLM payload",
            }
        )
        for feature in FEATURES:
            n_features = len(get_feature_columns(feature))
            projected_values: list[float] = []
            current_values: list[float] = []
            for n_packets, n_summaries in zip(
                prefix_packets[label], current_reported_summaries[label]
            ):
                projected_segments = _segment_count(int(n_packets))
                projected_top_level = 2 if label == "Whole" else 3
                projected_values.append(
                    float(projected_top_level + projected_segments * (4 + 2 * n_features))
                )
                if label == "Whole":
                    current_values.append(float(2 + n_summaries * (4 + 2 * n_features)))
                else:
                    current_values.append(float(5 + n_summaries * (7 + 2 * n_features)))

            prefix_feature_records.append(
                {
                    "context": label,
                    "seconds": seconds,
                    "feature_set": feature,
                    "n_features": n_features,
                    "numeric_metadata_values": _stats(projected_values),
                    "encoding": "ordered_packet_segments_over_first_prefix_only",
                }
            )
            current_feature_records.append(
                {
                    "context": label,
                    "seconds": seconds,
                    "feature_set": feature,
                    "n_features": n_features,
                    "reported_summaries": _stats(current_reported_summaries[label]),
                    "numeric_metadata_values": _stats(current_values),
                    "encoding": "complete_session_current_phase7_protocol",
                }
            )

    output = {
        "schema_version": "session_input_requirements_v1",
        "provenance": {
            "database": str(Path(DB_PATH).name),
            "database_in_public_repository": False,
            "reference_manifest": whole_manifest.name,
            "reference_manifest_sha256": _sha256(whole_manifest),
            "manifest_hash": whole_payload.get("manifest_hash"),
            "cohort_hash": whole_payload.get("cohort_hash"),
            "verified_equivalent_window_manifests": checked_manifests,
            "n_sessions": len(session_ids),
        },
        "production_prefix_projection": {
            "status": "data_volume_projection_not_detector_accuracy_experiment",
            "raw_context_records": raw_context_records,
            "feature_records": prefix_feature_records,
        },
        "current_phase7_full_session_encoding": {
            "status": "measured_structure_over_complete_sessions",
            "same_raw_packets_at_every_bin_width": True,
            "total_sessions": len(session_ids),
            "total_packets": int(sum(prefix_packets["Whole"])),
            "total_observed_wire_bytes": int(sum(prefix_wire_bytes["Whole"])),
            "feature_records": current_feature_records,
            "observed_api_token_records": _load_observed_api_tokens(),
        },
        "limitations": [
            "Prefix values project input volume only; Phase 7 F1 cannot be "
            "assigned to them.",
            "Numeric metadata counts exclude JSON syntax, feature-name strings, "
            "system prompts, memory examples, and model output.",
            "Observed wire bytes are packet_size sums, not bytes that a "
            "metadata-only detector must retain.",
            "The cohort is not an enterprise throughput, flow-concurrency, or "
            "memory benchmark.",
        ],
    }
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
