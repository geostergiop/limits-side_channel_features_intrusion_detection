#!/usr/bin/env python3
"""
Entry point for all Gap 5 adversarial robustness experiments.

Research Question
-----------------
Is an LLM-based classifier more robust to adversarial traffic shaping than
classical ML (CART/KNN) when both use only the 5 ESORICS side-channel features?

Core Hypothesis
---------------
Decision trees make independent, axis-aligned splits — an attacker who knows
the thresholds can game one feature at a time.  An LLM reasons about the
*joint distribution* of features as a narrative, detecting inconsistencies
that isolated threshold checks miss.  At session level, even if individual
packets are perturbed to look normal, temporal patterns (beaconing periodicity,
size oscillation) remain anomalous and the LLM catches them.

Phases
------
  generate  — Generate adversarial samples for all ε values (no LLM needed)
  evaluate  — Evaluate all classifiers on generated samples (LLM optional)
  blackbox  — Run black-box LLM attacks (Exp 5C/5E — expensive, ~$17 total)
  session   — Session-level consistency experiments (Exp 5D)
  analyze   — Generate figures and LaTeX tables from saved results
  all       — All phases in sequence

Prerequisites
-------------
  - Phase 3 (classical_ml.py) must have been run to populate the database.
  - ANTHROPIC_API_KEY or OPENAI_API_KEY must be set for LLM phases.

Usage
-----
  # Run everything
  python src/adversarial_experiments.py

  # Generate only (fast, no API calls)
  python src/adversarial_experiments.py --phase generate

  # Classical evaluation only
  python src/adversarial_experiments.py --phase evaluate --skip-llm

  # Full LLM evaluation (expensive)
  export ANTHROPIC_API_KEY="sk-ant-..."
  python src/adversarial_experiments.py --phase evaluate --provider anthropic

  # Preview without running
  python src/adversarial_experiments.py --dry-run

Estimated API cost
------------------
  Exp 5A/5B LLM eval : ~$3.00   (1000 calls)
  Exp 5C black-box   : ~$6.00   (2000 calls)
  Exp 5D session     : ~$0.30   (100 calls)
  Exp 5E adaptive    : ~$7.50   (2500 calls)
  Total              : ~$17.00
"""

import sys
import argparse
import json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import DB_PATH, ADV_CONFIG, RESULTS_DIR
from src.database import get_db
from src.classical_ml import train_for_adversarial
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES
from src.adversarial import (
    cart_evasion,
    knn_evasion,
    black_box_search,
    session_perturbation,
    adaptive_adversary,
)
from src.adversarial import generate_adversarial, evaluate as adv_evaluate

ADV_DIR = RESULTS_DIR / "adversarial"


# ─────────────────────────────────────────────────────────────────────────────
# Phase dispatchers
# ─────────────────────────────────────────────────────────────────────────────

def phase_generate(args) -> None:
    """Phase 1: Generate all adversarial sample CSVs."""
    generate_adversarial.main(
        epsilon_values=args.epsilon,
        n_samples=args.n_samples,
        dry_run=args.dry_run,
    )


def phase_evaluate(args) -> None:
    """Phase 2: Evaluate CART, KNN, and LLM on generated samples."""
    adv_evaluate.main(
        provider=args.provider,
        epsilon_values=args.epsilon,
        skip_llm=args.skip_llm,
        dry_run=args.dry_run,
        compact=not args.verbose,
    )


def phase_blackbox(args) -> None:
    """
    Phase 3: Black-box LLM attacks (Exp 5C — random search, hill climbing).

    Applies black-box search strategies against the LLM for each ε,
    using samples from the CART adversarial CSVs as starting points.
    Results saved to results/adversarial/blackbox_results.json.
    """
    print(f"\n{'='*70}")
    print("Gap 5: Black-Box LLM Attack (Exp 5C)")
    print(f"{'='*70}\n")

    if args.dry_run:
        print("[DRY-RUN] Would run random search + hill climbing vs LLM.")
        return

    from src.llm_experiments import LLMClient

    conn   = get_db(DB_PATH)
    models = train_for_adversarial(conn)
    threat = ThreatModel(models["X_train"], FEATURE_NAMES)

    try:
        llm_client = LLMClient(provider=args.provider)
    except Exception as e:
        print(f"[ERROR] LLM init failed: {e}")
        conn.close()
        return

    classify_fn      = adv_evaluate._build_classify_fn(llm_client, compact=True)
    classify_conf_fn = adv_evaluate._build_classify_conf_fn(llm_client, compact=True)

    all_bb: dict = {}
    budget_rand  = ADV_CONFIG["query_budget_random"]
    budget_hill  = ADV_CONFIG["query_budget_hillclimb"]

    for eps in args.epsilon:
        df = adv_evaluate.load_adversarial_csv("cart", eps)
        if df is None:
            print(f"  [SKIP] No CART adversarial CSV for epsilon={eps}. Run --phase generate first.")
            continue

        adv_cols = [f"adv_{c}" for c in FEATURE_NAMES]
        X_adv    = df[adv_cols].values[:50]  # cap at 50 samples per epsilon
        rng      = np.random.default_rng(42)

        rs_results:  list[dict] = []
        hc_results:  list[dict] = []

        print(f"\n  epsilon={eps} - {len(X_adv)} samples")
        for i, x in enumerate(X_adv):
            # Random search
            rs = black_box_search.random_search_evasion(
                x, threat, classify_fn, eps,
                max_queries=budget_rand, rng=rng,
            )
            rs_results.append(rs)

            # Hill climbing (uses confidence feedback)
            hc = black_box_search.hill_climbing_evasion(
                x, threat, classify_conf_fn, eps,
                max_queries=budget_hill,
            )
            hc_results.append(hc)

            if (i + 1) % 10 == 0:
                rs_er = sum(r["evaded"] for r in rs_results) / len(rs_results)
                hc_er = sum(r["evaded"] for r in hc_results) / len(hc_results)
                print(f"    [{i+1}/{len(X_adv)}] "
                      f"RS evasion={rs_er:.2%}  HC evasion={hc_er:.2%}")

        all_bb[eps] = {
            "random_search_evasion_rate": float(
                sum(r["evaded"] for r in rs_results) / len(rs_results)
            ) if rs_results else 0.0,
            "hill_climbing_evasion_rate": float(
                sum(r["evaded"] for r in hc_results) / len(hc_results)
            ) if hc_results else 0.0,
            "random_search_mean_queries": float(
                np.mean([r["queries_used"] for r in rs_results])
            ) if rs_results else 0.0,
            "hill_climbing_mean_queries": float(
                np.mean([r["queries_used"] for r in hc_results])
            ) if hc_results else 0.0,
        }

    out = ADV_DIR / "blackbox_results.json"
    with open(out, "w") as fh:
        json.dump({str(k): v for k, v in all_bb.items()}, fh, indent=2)
    print(f"\nBlack-box results saved to: {out}")
    conn.close()


def phase_adaptive(args) -> None:
    """
    Phase 4: Adaptive adversary with query complexity analysis (Exp 5E).

    Measures queries-to-evasion for CART (simulated query-only), KNN,
    and LLM.  The asymmetry in query cost is the main robustness metric.
    """
    print(f"\n{'='*70}")
    print("Gap 5: Adaptive Adversary Query Complexity (Exp 5E)")
    print(f"{'='*70}\n")

    if args.dry_run:
        print("[DRY-RUN] Would measure query complexity for all classifiers.")
        return

    conn   = get_db(DB_PATH)
    models = train_for_adversarial(conn)
    cart   = models["cart"]
    knn    = models["knn"]
    scaler = models["scaler"]
    X_train = models["X_train"]
    y_train = models["y_train"]
    X_test  = models["X_test"]
    y_test  = models["y_test"]
    threat  = ThreatModel(X_train, FEATURE_NAMES)

    rng    = np.random.default_rng(42)
    mal_idx = np.where(y_test == 1)[0]
    chosen  = rng.choice(mal_idx, size=min(50, len(mal_idx)), replace=False)
    X_mal   = X_test[chosen]

    # CART query function (simulated query-only access)
    def cart_query(x_raw: np.ndarray) -> int:
        x_s = scaler.transform(x_raw.reshape(1, -1))
        return int(cart.predict(x_s)[0])

    # KNN query function
    def knn_query(x_raw: np.ndarray) -> int:
        x_s = scaler.transform(x_raw.reshape(1, -1))
        return int(knn.predict(x_s)[0])

    all_adaptive: dict = {}

    for eps in args.epsilon:
        cart_res: list[dict] = []
        knn_res:  list[dict] = []
        llm_res:  list[dict] = []

        print(f"\n  epsilon={eps}")

        for x_orig in X_mal:
            # CART adaptive (binary search simulation)
            rc = adaptive_adversary.adaptive_cart_attack(
                x_orig, cart_query, threat, eps
            )
            cart_res.append(rc)

            # KNN adaptive
            rk = knn_evasion.generate_knn_adversarial(
                knn, x_orig.reshape(1, -1), X_train, y_train, threat, eps, scaler
            )
            # Represent as single-result dict
            knn_res.append({
                "evaded":       bool(rk["evasion_success"][0]),
                "queries_used": int(rk["perturbation_costs"][0].get("iterations", 0)),
            })

        # LLM adaptive (expensive - only run if not skip_llm)
        if not args.skip_llm:
            from src.llm_experiments import LLMClient
            try:
                llm_client = LLMClient(provider=args.provider)
                classify_conf_fn = adv_evaluate._build_classify_conf_fn(
                    llm_client, compact=True
                )
                for x_orig in X_mal[:20]:  # cap at 20 for cost
                    rl = adaptive_adversary.adaptive_llm_attack(
                        x_orig, classify_conf_fn, threat, eps,
                        query_budget=ADV_CONFIG["query_budget_adaptive"],
                        rng=rng,
                    )
                    llm_res.append({
                        "evaded":       rl["evaded"],
                        "queries_used": rl["queries_used"],
                    })
            except Exception as e:
                print(f"    [LLM ERROR] {e}")

        comparison = adaptive_adversary.compare_query_complexity(
            cart_res, knn_res, llm_res or [],
            cost_per_llm_query_usd=ADV_CONFIG["estimated_cost_per_query_usd"],
        )
        all_adaptive[eps] = comparison

        from tabulate import tabulate as tab
        print(tab(
            [[clf,
              f"{v.get('evasion_rate', 0):.2%}",
              v.get("median_q", "--"),
              v.get("mean_q", "--"),
              v.get("cost_usd_per_evasion", "--")]
             for clf, v in comparison.items()],
            headers=["Classifier", "Evasion Rate", "Median Q", "Mean Q", "Cost/Evasion"],
            tablefmt="grid",
        ))

    out = ADV_DIR / "query_complexity.json"
    with open(out, "w") as fh:
        json.dump({str(k): v for k, v in all_adaptive.items()}, fh, indent=2,
                  default=str)
    print(f"\nQuery complexity results saved to: {out}")
    conn.close()


def phase_analyze(args) -> None:
    """
    Phase 5: Generate figures and LaTeX tables from saved JSON results.
    Does NOT make any API calls.
    """
    print(f"\n{'='*70}")
    print("Gap 5: Analysis - Generating Figures and Tables")
    print(f"{'='*70}\n")

    evasion_file = ADV_DIR / "evasion_rates.json"
    if not evasion_file.exists():
        print("[SKIP] evasion_rates.json not found. Run --phase evaluate first.")
        return

    with open(evasion_file) as fh:
        all_results = {float(k): v for k, v in json.load(fh).items()}

    adv_evaluate.generate_evasion_rate_curves(all_results)
    latex = adv_evaluate.generate_latex_table(all_results)
    latex_path = ADV_DIR / "table_evasion.tex"
    latex_path.write_text(latex)
    print(f"LaTeX table written to {latex_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gap 5: Adversarial Robustness Experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase", default="all",
        choices=["all", "generate", "evaluate", "blackbox", "adaptive", "analyze"],
        help="Which experiment phase to run (default: all)",
    )
    parser.add_argument(
        "--epsilon", type=float, nargs="+",
        default=ADV_CONFIG["epsilon_values"],
        help="Perturbation budget values (IQR fractions)",
    )
    parser.add_argument(
        "--n-samples", type=int,
        default=ADV_CONFIG["n_adversarial_samples"],
        help="Adversarial samples per epsilon per method",
    )
    parser.add_argument(
        "--provider", default="openai",
        choices=["anthropic", "openai"],
        help="LLM provider for classification",
    )
    parser.add_argument(
        "--query-budget", type=int,
        default=ADV_CONFIG["query_budget_adaptive"],
        help="Max LLM queries per sample for black-box attacks",
    )
    parser.add_argument(
        "--skip-llm", action="store_true",
        help="Skip LLM evaluation phases (no API calls)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Use verbose LLM formatting (default: compact)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without executing experiments",
    )
    args = parser.parse_args()

    dispatch = {
        "generate": phase_generate,
        "evaluate": phase_evaluate,
        "blackbox": phase_blackbox,
        "adaptive": phase_adaptive,
        "analyze":  phase_analyze,
    }

    if args.phase == "all":
        for phase_name in ["generate", "evaluate", "blackbox", "adaptive", "analyze"]:
            print(f"\n{'#'*70}")
            print(f"# Running phase: {phase_name.upper()}")
            print(f"{'#'*70}")
            dispatch[phase_name](args)
    else:
        dispatch[args.phase](args)


if __name__ == "__main__":
    main()
