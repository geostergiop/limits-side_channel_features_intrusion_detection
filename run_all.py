#!/usr/bin/env python3
"""
Master runner: Orchestrates all phases of the LLM Traffic Detection experiment.

Usage:
  python run_all.py                         # Run everything (verbose mode)
  python run_all.py --phase 1               # Only Phase 1 (extraction)
  python run_all.py --phase 2               # Only Phase 2 (local ensembles)
  python run_all.py --phase 3               # Only Phase 3 (classical ML)
  python run_all.py --phase 4               # Only Phase 4 (LLM experiments)
  python run_all.py --phase 5               # Only Phase 5 (analysis)
  python run_all.py --phase 6               # Only Phase 6 (Gap 5 adversarial)
  python run_all.py --phase 7               # Only Phase 7 (session-based suite)
  python run_all.py --phase 3 4 5           # Phases 3, 4, 5
  python run_all.py --dry-run               # Show prompts without API calls
  python run_all.py --phase 4 --compact     # LLM with compact formatting
  python run_all.py --phase 4 --compact --experiment 4a   # Single experiment
  python run_all.py --phase 6 --adv-phase generate        # Generate only
  python run_all.py --phase 6 --adv-phase evaluate --skip-llm  # Classical only
"""

import argparse
from pathlib import Path

from configs.config import SESSION_CONFIG, SESSION_SPLIT_CONFIG


def print_phase_banner(title: str, marker: str = "=") -> None:
    """Print ASCII-only banners so Windows consoles never fail on encoding."""
    print("\n" + marker * 70)
    print(title)
    print(marker * 70)


def run_phase_0():
    """Download datasets from CTU Malware Capture Facility."""
    print_phase_banner("PHASE 0: Dataset Acquisition", "#")
    from src.download_datasets import main as download_main
    download_main()


def run_phase_1(rebuild_db: bool = False):
    """Extract features and build database."""
    print_phase_banner("PHASE 1: Feature Extraction & Database Build", "#")
    from src.feature_extraction import run_extraction
    run_extraction(rebuild_db=rebuild_db)


def run_phase_2():
    """Run local tree-ensemble baselines."""
    print_phase_banner("PHASE 2: Local Tree-Ensemble Baselines")
    from src.phase2_local_ml import main as phase2_main
    phase2_main()


def run_phase_3():
    """Run classical ML baselines."""
    print_phase_banner("PHASE 3: Classical ML Baselines (ESORICS Reproduction)", "#")
    from src.classical_ml import main as ml_main
    ml_main()


def run_phase_4(provider="openai", experiment="all",
                dry_run=False, compact=False):
    """Run LLM experiments."""
    mode = "compact" if compact else "verbose"
    print_phase_banner(f"PHASE 4: LLM-Based Classification Experiments [{mode}]", "#")
    from src.llm_experiments import run as llm_run
    llm_run(provider=provider, experiment=experiment,
            dry_run=dry_run, compact=compact)


def run_phase_5():
    """Generate analysis and reports."""
    print_phase_banner("PHASE 5: Analysis & Reporting", "#")
    from src.analysis import main as analysis_main
    analysis_main()


def run_phase_6(adv_phase="all", provider="openai",
                skip_llm=False, dry_run=False, compact=True,
                epsilon=None):
    """Run Gap 5 adversarial robustness experiments."""
    print_phase_banner("PHASE 6: Adversarial Robustness Experiments (Gap 5)", "#")
    from src.adversarial_experiments import (
        phase_generate, phase_evaluate, phase_blackbox,
        phase_adaptive, phase_analyze,
    )
    import types

    # Build a simple namespace mimicking argparse output
    ns = types.SimpleNamespace(
        phase=adv_phase,
        epsilon=epsilon or [0.05, 0.10, 0.20, 0.30, 0.50],
        n_samples=200,
        provider=provider,
        skip_llm=skip_llm,
        verbose=not compact,
        dry_run=dry_run,
    )

    dispatch = {
        "generate": phase_generate,
        "evaluate": phase_evaluate,
        "blackbox": phase_blackbox,
        "adaptive": phase_adaptive,
        "analyze":  phase_analyze,
    }

    if adv_phase == "all":
        for fn in [phase_generate, phase_evaluate, phase_blackbox,
                   phase_adaptive, phase_analyze]:
            fn(ns)
    elif adv_phase in dispatch:
        dispatch[adv_phase](ns)
    else:
        print(f"  [WARN] Unknown adversarial phase: {adv_phase}")


def run_phase_7(provider="openai", dry_run=False,
                session_mode="all", finetuned_model=None,
                start_finetune_job=False,
                session_eval_mode="balanced",
                session_llm_context="both",
                allow_large_llm_run=False,
                session_budget_profile="full",
                session_feature_set=None,
                session_sample_unit=None,
                session_window_seconds=None,
                session_repeat_indices=None,
                session_repeat_limit=None,
                session_llm_samples_per_repeat=None,
                session_llm_validation_samples_per_repeat=None,
                session_llm_test_samples_per_repeat=None,
                session_llm_max_calls=None,
                session_split_mode=None):
    """Run the session-based major-version experiment suite."""
    print_phase_banner("PHASE 7: Session-Based Experiment Suite")
    from src.session_experiments import main as session_main

    run_local = session_mode in {"all", "local"}
    run_llm = session_mode in {"all", "llm"}
    prepare_finetune = session_mode in {"all", "finetune"}
    session_main(
        provider=provider,
        dry_run=dry_run,
        run_local=run_local,
        run_llm=run_llm,
        prepare_finetune=prepare_finetune,
        start_finetune_job=start_finetune_job,
        finetuned_model=finetuned_model,
        evaluation_mode=session_eval_mode,
        llm_context_mode=session_llm_context,
        allow_large_llm_run=allow_large_llm_run,
        llm_budget_profile=session_budget_profile,
        llm_feature_set=session_feature_set,
        llm_sample_unit=session_sample_unit,
        llm_window_seconds=session_window_seconds,
        llm_repeat_indices=session_repeat_indices,
        llm_repeat_limit=session_repeat_limit,
        llm_samples_per_repeat=session_llm_samples_per_repeat,
        llm_validation_samples_per_repeat=session_llm_validation_samples_per_repeat,
        llm_test_samples_per_repeat=session_llm_test_samples_per_repeat,
        llm_max_calls=session_llm_max_calls,
        split_mode=session_split_mode or SESSION_SPLIT_CONFIG["default_mode"],
    )


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Powered Malicious Traffic Detection - Full Pipeline"
    )
    parser.add_argument("--phase", nargs="+", type=int, default=None,
                        help="Phase(s) to run: 0=download, 1=extract, "
                             "2=local ensembles, 3=classical ML, "
                             "4=LLM, 5=analysis, 6=adversarial, 7=session suite")
    parser.add_argument("--provider", default="openai",
                        choices=["anthropic", "openai"])
    parser.add_argument("--experiment", default="all",
                        choices=["all", "4a", "4b", "4c", "4d", "4e"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts without making API calls")
    parser.add_argument("--compact", action="store_true",
                        help="Phase 4: use compact JSON formatting + "
                             "statistical session profiles + "
                             "embedding-based few-shot retrieval")
    parser.add_argument("--rebuild-db", action="store_true",
                        help="Phase 1: delete traffic.db before re-extracting")
    # Phase 6 - adversarial
    parser.add_argument("--adv-phase", default="all",
                        choices=["all", "generate", "evaluate",
                                 "blackbox", "adaptive", "analyze"],
                        help="Phase 6 sub-phase (default: all)")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Phase 6: skip LLM evaluation (no API calls)")
    parser.add_argument("--session-mode", dest="session_mode", default="all",
                        choices=["all", "local", "llm", "finetune"],
                        help="Phase 7 subset to run (default: all)")
    parser.add_argument("--session-eval-mode", dest="session_eval_mode", default="balanced",
                        choices=["balanced", "deployment"],
                        help="Phase 7 evaluation mode: balanced scientific comparison "
                             "or deployment-style prevalence-faithful testing")
    parser.add_argument(
        "--session-split-mode",
        choices=SESSION_SPLIT_CONFIG["modes"],
        default=SESSION_SPLIT_CONFIG["default_mode"],
        help=(
            "Phase 7 leakage boundary: capture_disjoint_5fold is the primary unseen-capture "
            "protocol; within_capture_temporal is a secondary seen-capture upper bound"
        ),
    )
    parser.add_argument("--session-llm-context", dest="session_llm_context", default="both",
                        choices=["blind", "memory", "both"],
                        help="Phase 7 LLM context mode: blind prompts, training-split memory prompts, or both")
    parser.add_argument("--allow-large-llm-run", action="store_true",
                        help="Phase 7: explicitly allow large prompted LLM sweeps above the configured call threshold")
    parser.add_argument("--session-budget-profile", dest="session_budget_profile", default="full",
                        choices=sorted(SESSION_CONFIG.get("llm_budget_profiles", {"full": {}}).keys()),
                        help="Phase 7 LLM budget profile. paper_5k is the budgeted balanced+deployment design; paper_6k is a higher-depth deployment profile.")
    parser.add_argument("--session-feature-set", dest="session_feature_set", metavar="FEATURE_SET", default=None,
                        help="Phase 7 LLM feature filter: all, minimal, mercury, combined, or comma-separated values")
    parser.add_argument("--session-sample-unit", dest="session_sample_unit", metavar="SAMPLE_UNIT", default=None,
                        help="Phase 7 LLM sample-unit filter: all, session_sequence, behavior_window, packet_ablation, or comma-separated values")
    parser.add_argument("--session-window-seconds", dest="session_window_seconds", metavar="SECONDS", default=None,
                        help="Phase 7 LLM behavior-window filter: all or comma-separated numeric seconds, e.g. 5.0")
    parser.add_argument("--session-repeat-limit", dest="session_repeat_limit", metavar="N", type=int, default=None,
                        help="Phase 7 LLM: use only the first N frozen repeats")
    parser.add_argument("--session-repeat-indices", dest="session_repeat_indices", metavar="INDICES", default=None,
                        help="Phase 7 LLM: comma-separated frozen fold indices, e.g. 0,1,2,3,4")
    parser.add_argument("--session-llm-samples-per-repeat", dest="session_llm_samples_per_repeat", metavar="N", type=int, default=None,
                        help="Phase 7 LLM balanced mode: test samples per repeat")
    parser.add_argument("--session-llm-validation-samples-per-repeat", dest="session_llm_validation_samples_per_repeat", metavar="N", type=int, default=None,
                        help="Phase 7 LLM deployment mode: validation samples per repeat")
    parser.add_argument("--session-llm-test-samples-per-repeat", dest="session_llm_test_samples_per_repeat", metavar="N", type=int, default=None,
                        help="Phase 7 LLM deployment mode: test samples per repeat")
    parser.add_argument("--session-llm-max-calls", dest="session_llm_max_calls", metavar="N", type=int, default=None,
                        help="Phase 7 LLM: hard maximum estimated API calls for this run")
    parser.add_argument("--finetuned-model", default=None,
                        help="Phase 7: evaluate a specific fine-tuned OpenAI model id")
    parser.add_argument("--start-finetune-job", action="store_true",
                        help="Phase 7: upload exported corpora and start an OpenAI fine-tuning job")
    args = parser.parse_args()

    print("=" * 70)
    print("LLM-Powered Malicious Traffic Detection")
    print("Side-Channel Features x Foundation Model Reasoning")
    print("Covering Gap 1 (LLM over minimal features)")
    print("         Gap 2 (Zero-shot novel attack detection)")
    print("         Gap 5 (Adversarial robustness of LLM vs classical ML)")
    print("=" * 70)

    phases = args.phase or [0, 1, 2, 3, 4, 5]

    if 0 in phases:
        run_phase_0()
    if 1 in phases:
        run_phase_1(rebuild_db=args.rebuild_db)
    if 2 in phases:
        run_phase_2()
    if 3 in phases:
        run_phase_3()
    if 4 in phases:
        run_phase_4(args.provider, args.experiment,
                    args.dry_run, args.compact)
    if 5 in phases:
        run_phase_5()
    if 6 in phases:
        run_phase_6(adv_phase=args.adv_phase,
                    provider=args.provider,
                    skip_llm=args.skip_llm,
                    dry_run=args.dry_run,
                    compact=args.compact)
    if 7 in phases:
        run_phase_7(provider=args.provider,
                    dry_run=args.dry_run,
                    session_mode=args.session_mode,
                    finetuned_model=args.finetuned_model,
                    start_finetune_job=args.start_finetune_job,
                    session_eval_mode=args.session_eval_mode,
                    session_llm_context=args.session_llm_context,
                    allow_large_llm_run=args.allow_large_llm_run,
                    session_budget_profile=args.session_budget_profile,
                    session_feature_set=args.session_feature_set,
                    session_sample_unit=args.session_sample_unit,
                    session_window_seconds=args.session_window_seconds,
                    session_repeat_indices=args.session_repeat_indices,
                    session_repeat_limit=args.session_repeat_limit,
                    session_llm_samples_per_repeat=args.session_llm_samples_per_repeat,
                    session_llm_validation_samples_per_repeat=args.session_llm_validation_samples_per_repeat,
                    session_llm_test_samples_per_repeat=args.session_llm_test_samples_per_repeat,
                    session_llm_max_calls=args.session_llm_max_calls,
                    session_split_mode=args.session_split_mode)

    print("\n" + "=" * 70)
    print("Pipeline complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
