#!/usr/bin/env python3
"""
Master adversarial sample generator (Gap 5).

Pipeline
--------
1. Connect to database; load malicious + normal samples.
2. Train CART and KNN via classical_ml.train_for_adversarial().
3. Build ThreatModel from raw training data (IQR computation).
4. For each ε in ADV_CONFIG["epsilon_values"]:
   a. Sample X_malicious from test set (ground-truth malicious).
   b. generate_cart_adversarial() → save CSV.
   c. generate_knn_adversarial()  → save CSV.
5. Load sessions; generate session-level perturbations → save JSON.
6. Print summary statistics table.

Output files (all in results/adversarial/adversarial_samples/):
  cart_adversarial_eps{ε}.csv   — 5 features + original_label + evaded_cart
  knn_adversarial_eps{ε}.csv    — same format
  session_adversarial_eps{ε}.json — session-level perturbed packets

Usage
-----
  python src/adversarial/generate_adversarial.py
  python src/adversarial/generate_adversarial.py --n-samples 100 --dry-run
"""

import sys
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from configs.config import DB_PATH, ADV_CONFIG, RESULTS_DIR, SIDE_CHANNEL_FEATURES
from src.database import get_db
from src.classical_ml import train_for_adversarial
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES
from src.adversarial import cart_evasion, knn_evasion, session_perturbation

ADV_SAMPLES_DIR = RESULTS_DIR / "adversarial" / "adversarial_samples"
ADV_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _eps_tag(epsilon: float) -> str:
    """Format epsilon as a filename-safe string, e.g. 0.10 → 'eps0.10'."""
    return f"eps{epsilon:.2f}"


def _sample_malicious(X_test: np.ndarray, y_test: np.ndarray,
                       n: int, rng: np.random.Generator) -> np.ndarray:
    """Return up to n malicious samples from the test set (random subset)."""
    mal_idx = np.where(y_test == 1)[0]
    chosen  = rng.choice(mal_idx, size=min(n, len(mal_idx)), replace=False)
    return X_test[chosen]


def _save_csv(X_orig: np.ndarray, X_adv: np.ndarray,
               evasion_success: np.ndarray,
               prefix: str, epsilon: float) -> Path:
    """Save adversarial feature CSV with metadata columns."""
    cols = FEATURE_NAMES
    rows = []
    for i in range(len(X_orig)):
        row = {f"orig_{c}": X_orig[i, j] for j, c in enumerate(cols)}
        row.update({f"adv_{c}": X_adv[i, j] for j, c in enumerate(cols)})
        row["original_label"] = 1   # all samples are ground-truth malicious
        row["evaded"]         = int(evasion_success[i])
        rows.append(row)

    df  = pd.DataFrame(rows)
    out = ADV_SAMPLES_DIR / f"{prefix}_{_eps_tag(epsilon)}.csv"
    df.to_csv(out, index=False)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main generation pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main(epsilon_values: list = None,
         n_samples: int = None,
         dry_run: bool = False) -> None:

    epsilons = epsilon_values or ADV_CONFIG["epsilon_values"]
    n_adv    = n_samples      or ADV_CONFIG["n_adversarial_samples"]
    n_sess   = ADV_CONFIG["n_session_samples"]
    min_pkts = ADV_CONFIG["min_session_length"]

    print(f"\n{'='*70}")
    print("Gap 5: Adversarial Sample Generation")
    print(f"  epsilon values : {epsilons}")
    print(f"  n samples: {n_adv} per epsilon per method")
    print(f"  dry_run  : {dry_run}")
    print(f"{'='*70}\n")

    conn = get_db(DB_PATH)
    rng  = np.random.default_rng(42)

    # ── Step 1: Train CART and KNN ────────────────────────────────────────────
    print("[1/4] Training CART and KNN...")
    if dry_run:
        print("  [DRY-RUN] Skipping model training.")
        conn.close()
        return

    try:
        models = train_for_adversarial(conn)
    except ValueError as e:
        print(f"  [SKIP] {e}")
        conn.close()
        return

    cart   = models["cart"]
    knn    = models["knn"]
    scaler = models["scaler"]
    X_train = models["X_train"]
    y_train = models["y_train"]
    X_test  = models["X_test"]
    y_test  = models["y_test"]

    # ── Step 2: Build ThreatModel ─────────────────────────────────────────────
    print("[2/4] Building ThreatModel from training IQR...")
    threat = ThreatModel(X_train, FEATURE_NAMES)
    for name in FEATURE_NAMES:
        print(f"  IQR({name}) = {threat.iqr[name]:.4f}")

    # ── Step 3: Generate per-ε adversarial samples ────────────────────────────
    print(f"\n[3/4] Generating adversarial samples ({len(epsilons)} epsilon values)...")

    summary_rows = []

    for eps in epsilons:
        tag = _eps_tag(eps)
        X_mal = _sample_malicious(X_test, y_test, n_adv, rng)
        n_actual = len(X_mal)
        print(f"\n  epsilon={eps} - {n_actual} malicious samples")

        # CART evasion
        cart_res = cart_evasion.generate_cart_adversarial(
            cart, X_mal, threat, eps, scaler
        )
        cart_csv = _save_csv(
            X_mal, cart_res["X_adversarial"], cart_res["evasion_success"],
            "cart_adversarial", eps
        )
        print(f"    CART evasion rate: {cart_res['evasion_rate']:.2%}  -> {cart_csv.name}")

        # KNN evasion
        knn_res = knn_evasion.generate_knn_adversarial(
            knn, X_mal, X_train, y_train, threat, eps, scaler
        )
        knn_csv = _save_csv(
            X_mal, knn_res["X_adversarial"], knn_res["evasion_success"],
            "knn_adversarial", eps
        )
        print(f"    KNN  evasion rate: {knn_res['evasion_rate']:.2%}  -> {knn_csv.name}")

        summary_rows.append([
            eps,
            f"{cart_res['evasion_rate']:.2%}",
            f"{cart_res['avg_features_changed']:.1f}",
            f"{knn_res['evasion_rate']:.2%}",
            f"{knn_res['avg_features_changed']:.1f}",
        ])

    print("\n" + tabulate(
        summary_rows,
        headers=["epsilon", "CART Evade%", "CART DeltaFeats", "KNN Evade%", "KNN DeltaFeats"],
        tablefmt="grid",
    ))

    # ── Step 4: Session-level perturbations ───────────────────────────────────
    print(f"\n[4/4] Generating session-level perturbations (n={n_sess})...")

    sessions = session_perturbation.load_malicious_sessions(
        conn, min_packets=min_pkts, max_sessions=n_sess
    )
    print(f"  Loaded {len(sessions)} sessions with >={min_pkts} packets")

    if sessions:
        for eps in epsilons:
            tag = _eps_tag(eps)
            sess_records = []

            for sess in sessions:
                pert = session_perturbation.perturb_session_per_packet(
                    sess["packets"], cart, threat, eps, scaler
                )
                sess_records.append({
                    "session_id":     sess["session_id"],
                    "malware_family": sess["malware_family"],
                    "is_encrypted":   sess["is_encrypted"],
                    "n_packets":      len(sess["packets"]),
                    "original_packets": sess["packets"].tolist(),
                    "perturbed_packets": pert.tolist(),
                })

            out_json = ADV_SAMPLES_DIR / f"session_adversarial_{tag}.json"
            with open(out_json, "w") as fh:
                json.dump(sess_records, fh)
            print(f"  epsilon={eps}: {len(sess_records)} sessions -> {out_json.name}")

    conn.close()
    print(f"\nAll adversarial samples saved to: {ADV_SAMPLES_DIR}")
    print("Next step: python src/adversarial/evaluate.py")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate adversarial samples for Gap 5 experiments"
    )
    parser.add_argument(
        "--epsilon", type=float, nargs="+",
        default=ADV_CONFIG["epsilon_values"],
        help="Perturbation budget values (IQR fractions)"
    )
    parser.add_argument(
        "--n-samples", type=int,
        default=ADV_CONFIG["n_adversarial_samples"],
        help="Adversarial samples per epsilon per method"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without running generation"
    )
    args = parser.parse_args()
    main(epsilon_values=args.epsilon, n_samples=args.n_samples, dry_run=args.dry_run)
