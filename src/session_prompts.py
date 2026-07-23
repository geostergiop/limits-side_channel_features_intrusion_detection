#!/usr/bin/env python3
"""Prompt builders shared across Session zero-shot and fine-tuned baselines."""

from __future__ import annotations

import json

from src.session_dataset import FEATURE_SET_DESCRIPTIONS, get_feature_columns


def build_system_prompt(feature_set: str, sample_unit: str) -> str:
    feature_desc = FEATURE_SET_DESCRIPTIONS[feature_set]
    response_schema = (
        'Return strict JSON only: {"classification":"malicious"|"normal",'
        '"confidence":0.0-1.0,"reasoning":"<=20 words"}'
    )
    base = (
        "You are a network security analyst evaluating encrypted or "
        "side-channel-only traffic metadata. "
        "You must classify the sample as malicious or normal using only the "
        "provided metadata, without assuming payload visibility.\n\n"
        f"Feature configuration: {feature_set}\n"
        f"Description: {feature_desc}\n"
    )
    if sample_unit == "packet_ablation":
        return (
            base
            + "The sample is a single packet represented as a JSON object.\n"
            + response_schema
        )
    if sample_unit == "session_sequence":
        return (
            base
            + "The sample is a complete session summarized as an ordered list of "
            + "contiguous packet-segment profiles. Each segment covers a block of "
            + "packets in arrival order, so you can reason over the whole session.\n"
            + response_schema
        )
    if sample_unit == "behavior_window":
        return (
            base
            + "The sample is a complete session summarized as an ordered list "
            + "of fixed-duration behavior windows, so you can reason about "
            + "patterns such as periodic callbacks and delayed beaconing. "
            + "Very long sessions may compress adjacent windows into ordered "
            + "bins while preserving counts and timing coverage.\n"
            + response_schema
        )
    raise ValueError(f"Unknown sample_unit={sample_unit!r}")


def build_user_prompt(row: dict) -> str:
    sample_unit = str(row["sample_unit"])
    feature_set = str(row["feature_set"])
    if sample_unit == "packet_ablation":
        return (
            "Classify the following single-packet metadata sample.\n\n"
            f"Feature names: {json.dumps(get_feature_columns(feature_set))}\n"
            f"Packet: {row['sequence_json']}\n"
        )

    if sample_unit == "session_sequence":
        return (
            "Classify the following complete network session. "
            "The session is represented as ordered packet-segment summaries so "
            "the full session behavior is preserved.\n\n"
            f"Feature names: {json.dumps(get_feature_columns(feature_set))}\n"
            f"Session summary: {row['sequence_json']}\n"
        )

    if sample_unit == "behavior_window":
        window_seconds = float(row.get("window_seconds", 0.0) or 0.0)
        return (
            f"Classify the following complete network session represented as "
            f"ordered {window_seconds:.1f}-second behavior windows.\n\n"
            f"Feature names: {json.dumps(get_feature_columns(feature_set))}\n"
            f"Behavior-window summary: {row['sequence_json']}\n"
        )

    raise ValueError(f"Unknown sample_unit={sample_unit!r}")


def build_supervised_label(is_malicious: int) -> str:
    label = "malicious" if int(is_malicious) == 1 else "normal"
    rationale = (
        "Ground-truth malicious traffic sample."
        if label == "malicious"
        else "Ground-truth benign traffic sample."
    )
    return json.dumps(
        {
            "classification": label,
            "confidence": 1.0,
            "reasoning": rationale,
        },
        separators=(",", ":"),
    )
