#!/usr/bin/env python3
"""Fine-tuned LLM baseline helpers for the Session suite."""

from __future__ import annotations

import json
import os
from pathlib import Path

from configs.config import SESSION_CONFIG, RESULTS_DIR
from src.llm_experiments import LLMClient
from src.session_prompts import build_supervised_label, build_system_prompt, build_user_prompt
from src.session_splits import materialize_session_splits


def _jsonl_line(messages: list[dict]) -> str:
    return json.dumps({"messages": messages}, separators=(",", ":"))


def export_finetune_corpus(
    dataset,
    manifest: dict,
    *,
    output_stem: str,
) -> dict:
    """
    Export one supervised train/validation/test corpus from the first frozen fold.

    Fine-tuning uses one protocol-qualified fold so examples are not duplicated
    across folds and no validation/test capture enters supervised training.
    """
    output_dir = Path(RESULTS_DIR) / str(SESSION_CONFIG.get("finetune_export_dir", "finetune"))
    output_dir.mkdir(parents=True, exist_ok=True)

    materialized = materialize_session_splits(dataset, manifest)
    if not materialized:
        raise RuntimeError("Cannot export fine-tune corpus without materialized folds")

    repeat_meta, train_df, validation_df, test_df = materialized[0]
    sample_unit = str(train_df["sample_unit"].iloc[0])
    feature_set = str(train_df["feature_set"].iloc[0])
    system_prompt = build_system_prompt(feature_set, sample_unit)

    def _rows_to_jsonl(df) -> list[str]:
        lines: list[str] = []
        for row in df.to_dict("records"):
            lines.append(
                _jsonl_line(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": build_user_prompt(row)},
                        {
                            "role": "assistant",
                            "content": build_supervised_label(int(row["is_malicious"])),
                        },
                    ]
                )
            )
        return lines

    train_path = output_dir / f"{output_stem}_train.jsonl"
    validation_path = output_dir / f"{output_stem}_validation.jsonl"
    test_path = output_dir / f"{output_stem}_test.jsonl"
    for path, lines in [
        (train_path, _rows_to_jsonl(train_df)),
        (validation_path, _rows_to_jsonl(validation_df)),
        (test_path, _rows_to_jsonl(test_df)),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            if lines:
                f.write("\n")

    metadata = {
        "sample_unit": sample_unit,
        "feature_set": feature_set,
        "manifest_hash": manifest.get("manifest_hash"),
        "split_mode": manifest.get("split_mode"),
        "repeat_index": int(repeat_meta["repeat_index"]),
        "fold_index": int(repeat_meta["fold_index"]),
        "held_out_malware_family": repeat_meta.get("held_out_malware_family"),
        "evaluation_scope": (
            "evaluate supplied fine-tuned models only on this fold's held-out test split"
        ),
        "train_path": str(train_path),
        "validation_path": str(validation_path),
        "test_path": str(test_path),
        "n_train": int(len(train_df)),
        "n_validation": int(len(validation_df)),
        "n_test": int(len(test_df)),
    }
    meta_path = output_dir / f"{output_stem}_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    metadata["metadata_path"] = str(meta_path)
    return metadata


def create_openai_finetune_job(
    *,
    training_path: str | Path,
    validation_path: str | Path,
    base_model: str | None = None,
    suffix: str | None = None,
) -> dict:
    try:
        import openai
    except ImportError as e:
        raise RuntimeError("OpenAI client is not installed. Run `pip install openai`.") from e

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = openai.OpenAI(api_key=api_key)
    with open(training_path, "rb") as f_train, open(validation_path, "rb") as f_val:
        train_file = client.files.create(file=f_train, purpose="fine-tune")
        val_file = client.files.create(file=f_val, purpose="fine-tune")

    job = client.fine_tuning.jobs.create(
        model=base_model or SESSION_CONFIG.get("finetune_base_model", "gpt-4.1-nano-2025-04-14"),
        training_file=train_file.id,
        validation_file=val_file.id,
        suffix=suffix or SESSION_CONFIG.get("finetune_job_suffix", "session"),
        seed=42,
    )
    return {
        "training_file_id": train_file.id,
        "validation_file_id": val_file.id,
        "job_id": job.id,
        "base_model": base_model or SESSION_CONFIG.get("finetune_base_model", "gpt-4.1-nano-2025-04-14"),
    }


def evaluate_finetuned_model(
    model_id: str,
    test_df,
    *,
    max_samples: int | None = None,
) -> list[dict]:
    client = LLMClient(provider="openai")
    client.model = model_id
    rows = test_df.to_dict("records")
    if max_samples is not None:
        rows = rows[: int(max_samples)]

    results: list[dict] = []
    for row in rows:
        sys_prompt = build_system_prompt(str(row["feature_set"]), str(row["sample_unit"]))
        user_prompt = build_user_prompt(row)
        response = client.classify(sys_prompt, user_prompt, max_tokens=256)
        results.append(
            {
                "sample_unit": row["sample_unit"],
                "feature_set": row["feature_set"],
                "packet_id": int(row["packet_id"]),
                "session_id": int(row["session_id"]),
                "dataset_id": int(row["dataset_id"]),
                "ground_truth": int(row["is_malicious"]),
                "prediction": int(response.get("prediction", -1)),
                "confidence": float(response.get("confidence", 0.0)),
                "reasoning": str(response.get("reasoning", "")),
                "tokens": int(response.get("tokens", 0)),
                "latency_ms": float(response.get("latency_ms", 0.0)),
                "model": model_id,
                "suite": "session_finetune",
            }
        )
    return results
