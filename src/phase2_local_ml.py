#!/usr/bin/env python3
"""
Phase 2: Local tree-ensemble baselines over the five ESORICS side-channel features.

These experiments are fully local and do not require any LLM provider or API key.
They mirror the grouped-holdout protocol used by Phase 3 while evaluating:
  - Random Forest
  - XGBoost
  - LightGBM
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import ML_CONFIG, RESULTS_DIR
from src.classical_ml import (
    ensure_algorithms_available,
    load_or_create_standard_manifest,
    print_detection_table,
    print_performance_table,
    run_experiment,
    run_lofo_experiment,
)
from src.database import get_db


PHASE_2_ALGORITHMS = list(
    ML_CONFIG.get(
        "phase_2_algorithms",
        ["RandomForestClassifier", "XGBClassifier", "LGBMClassifier"],
    )
)


def _annotate_results(results: list[dict]) -> list[dict]:
    for row in results:
        row["phase"] = 2
        row["suite"] = "local_ensembles"
    return results


def main() -> None:
    try:
        ensure_algorithms_available(PHASE_2_ALGORITHMS)
    except RuntimeError as e:
        raise SystemExit(str(e)) from e

    conn = get_db()
    all_results: list[dict] = []

    holdout_modes = ML_CONFIG.get("holdout_modes", ["session", "capture"])

    for group_by in holdout_modes:
        print("\n" + "#" * 70)
        print(f"# Local tree-ensemble repeated holdout mode: {group_by}")
        print("#" * 70)

        experiments = [
            {
                "key": "E1_full_mixed",
                "sample_size": int(ML_CONFIG["experiment_1_sample_size"]),
                "encrypted_only": False,
            },
            {
                "key": "E2_limited_20k",
                "sample_size": int(ML_CONFIG["experiment_2_sample_size"]),
                "encrypted_only": False,
            },
            {
                "key": "E3_encrypted_only",
                "sample_size": int(ML_CONFIG["experiment_3_sample_size"]),
                "encrypted_only": True,
            },
        ]

        for spec in experiments:
            exp_name = f"{spec['key']}_{group_by}_repeated_group_holdout"
            try:
                df, manifest, manifest_path = load_or_create_standard_manifest(
                    conn,
                    experiment_key=spec["key"],
                    group_by=group_by,
                    sample_size=spec["sample_size"],
                    encrypted_only=spec["encrypted_only"],
                )
            except Exception as e:
                print(f"[ERROR] {exp_name}: {e}")
                conn.close()
                raise

            if len(df) < 100:
                print(f"[SKIP] Not enough data for {exp_name}.")
                continue
            try:
                results = run_experiment(
                    df,
                    exp_name,
                    group_by=group_by,
                    algorithms=PHASE_2_ALGORITHMS,
                    raise_on_error=True,
                    manifest=manifest,
                    manifest_path=manifest_path,
                )
            except Exception as e:
                print(f"[ERROR] {exp_name}: {e}")
                conn.close()
                raise
            results = _annotate_results(results)
            all_results.extend(results)
            print_detection_table(all_results, exp_name)
            print_performance_table(all_results, exp_name)

    for group_by in holdout_modes:
        try:
            lofo_results = run_lofo_experiment(
                conn,
                group_by=group_by,
                algorithms=PHASE_2_ALGORITHMS,
                raise_on_error=True,
            )
            all_results.extend(_annotate_results(lofo_results))
        except Exception as e:
            print(f"[ERROR] LOFO {group_by}: {e}")
            conn.close()
            raise

    results_path = RESULTS_DIR / "phase2_local_ml_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_path}")
    conn.close()


if __name__ == "__main__":
    main()
