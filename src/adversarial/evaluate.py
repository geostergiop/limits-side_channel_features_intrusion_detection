#!/usr/bin/env python3
"""
Unified evaluation of all classifiers on adversarial samples (Gap 5).

For each ε and each adversarial source (CART-crafted, KNN-crafted):
  1. CART evasion rate on adversarial samples (cross-method transfer too)
  2. KNN evasion rate
  3. LLM zero-shot evasion rate
  4. LLM few-shot evasion rate
  5. LLM chain-of-thought evasion rate
  6. Session-level LLM detection (Exp 5D)
  7. Transfer attack evaluation (Exp 5C)

Outputs
-------
  results/adversarial/evasion_rates.json
  results/adversarial/query_complexity.json
  results/adversarial/session_consistency.json
  results/adversarial/reasoning_traces/  (LLM CoT traces)
  results/adversarial/figures/           (evasion-vs-ε curves, etc.)

Usage
-----
  python src/adversarial/evaluate.py --provider anthropic
  python src/adversarial/evaluate.py --provider openai --dry-run
  python src/adversarial/evaluate.py --skip-llm   # classical only, fast
"""

import sys
import json
import time
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
from src.adversarial import black_box_search, session_perturbation
from src.llm_experiments import (
    LLMClient,
    SYSTEM_PROMPT_COMPACT_PACKET,
    SYSTEM_PROMPT_COMPACT_SESSION,
    SYSTEM_PROMPT_BASE,
    PROMPT_ZERO_SHOT,
    PROMPT_FEW_SHOT,
    PROMPT_COT,
    PROMPT_SESSION_COMPACT,
    format_packet_compact,
    format_packet_verbose,
    format_session_compact,
    compute_session_profile,
)

ADV_DIR         = RESULTS_DIR / "adversarial"
ADV_SAMPLES_DIR = ADV_DIR / "adversarial_samples"
TRACES_DIR      = ADV_DIR / "reasoning_traces"
FIGURES_DIR     = ADV_DIR / "figures"
for d in [ADV_DIR, ADV_SAMPLES_DIR, TRACES_DIR, FIGURES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def _fmt_pct(value) -> str:
    return f"{value:.2%}" if value is not None else "--"


# ─────────────────────────────────────────────────────────────────────────────
# CSV loading helpers
# ─────────────────────────────────────────────────────────────────────────────

def _eps_tag(epsilon: float) -> str:
    return f"eps{epsilon:.2f}"


def load_adversarial_csv(source: str, epsilon: float) -> pd.DataFrame | None:
    """
    Load a previously generated adversarial CSV.

    source : "cart" or "knn"
    Returns DataFrame or None if file not found.
    """
    path = ADV_SAMPLES_DIR / f"{source}_adversarial_{_eps_tag(epsilon)}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_session_json(epsilon: float) -> list[dict] | None:
    path = ADV_SAMPLES_DIR / f"session_adversarial_{_eps_tag(epsilon)}.json"
    if not path.exists():
        return None
    with open(path) as fh:
        return json.load(fh)


# ─────────────────────────────────────────────────────────────────────────────
# Classical evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_on_classical(X_adversarial_raw: np.ndarray,
                           y_true: np.ndarray,
                           cart_model, knn_model, scaler) -> dict:
    """
    Evaluate CART and KNN on adversarial samples.

    X_adversarial_raw : (n, 5) raw features (perturbed)
    y_true            : (n,) ground-truth labels (should be all 1)

    Returns
    -------
    {
      "cart_evasion_rate": float,   — fraction where CART predicts 0
      "knn_evasion_rate":  float,
      "cart_predictions":  list[int],
      "knn_predictions":   list[int],
    }
    """
    X_scaled = scaler.transform(X_adversarial_raw)
    cart_preds = cart_model.predict(X_scaled)
    knn_preds  = knn_model.predict(X_scaled)

    # Evasion = classifier predicts "normal" (0) for a malicious sample
    cart_evasion = float((cart_preds == 0).mean())
    knn_evasion  = float((knn_preds  == 0).mean())

    return {
        "cart_evasion_rate": cart_evasion,
        "knn_evasion_rate":  knn_evasion,
        "cart_predictions":  cart_preds.tolist(),
        "knn_predictions":   knn_preds.tolist(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM evaluation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(x_raw: np.ndarray) -> dict:
    """Convert raw feature array to a dict matching format_packet_* expectations."""
    return {
        "packet_size":   x_raw[0],
        "payload_size":  x_raw[1],
        "payload_ratio": x_raw[2],
        "ratio_to_prev": x_raw[3],
        "time_diff":     x_raw[4],
    }


def _build_classify_fn(llm_client: LLMClient, compact: bool = True):
    """
    Return a callable (x_raw → int) that classifies a single raw packet.
    Used for black-box search strategies.
    """
    sys_prompt = (SYSTEM_PROMPT_COMPACT_PACKET if compact else SYSTEM_PROMPT_BASE)

    def _classify(x_raw: np.ndarray) -> int:
        row = _row_to_dict(x_raw)
        feat_str = format_packet_compact(row) if compact else format_packet_verbose(row)
        prompt   = PROMPT_ZERO_SHOT.format(features=feat_str)
        result   = llm_client.classify(sys_prompt, prompt)
        return result["prediction"]

    return _classify


def _build_classify_conf_fn(llm_client: LLMClient, compact: bool = True):
    """
    Return a callable (x_raw → (int, float)) with confidence, for hill climbing.
    """
    sys_prompt = (SYSTEM_PROMPT_COMPACT_PACKET if compact else SYSTEM_PROMPT_BASE)

    def _classify_conf(x_raw: np.ndarray) -> tuple[int, float]:
        row = _row_to_dict(x_raw)
        feat_str = format_packet_compact(row) if compact else format_packet_verbose(row)
        prompt   = PROMPT_ZERO_SHOT.format(features=feat_str)
        result   = llm_client.classify(sys_prompt, prompt)
        pred     = int(result["prediction"])
        conf_raw = float(result.get("confidence", 0.5) or 0.5)
        if pred < 0:
            return pred, 0.5
        # confidence: malicious-class confidence when pred=1, 1-conf when pred=0
        mal_conf = conf_raw if pred == 1 else (1.0 - conf_raw)
        return pred, float(mal_conf)

    return _classify_conf


def _build_batch_prompt(feat_strs: list[str], mode: str,
                        example_rows: list[dict], fmt_fn) -> str:
    """
    Build a single prompt that asks the LLM to classify N packets at once.
    Returns a prompt requesting a JSON array with one object per packet.
    Only used for zero_shot and few_shot modes (not chain_of_thought, which
    requires per-sample reasoning to remain scientifically valid).
    """
    header_lines = []
    if mode == "few_shot" and example_rows:
        ex_lines = []
        for ex in example_rows[:5]:
            label = "MALICIOUS" if ex.get("is_malicious", 0) == 1 else "NORMAL"
            ex_lines.append(f"[{label}] {fmt_fn(ex)}")
        header_lines.append("Reference examples:\n" + "\n".join(ex_lines) + "\n")

    header_lines.append(
        f"Classify each of the following {len(feat_strs)} network packets independently."
    )
    header_lines.append(
        'Return a JSON array with exactly one object per packet:\n'
        '[{"classification": "malicious"/"normal", "confidence": 0.0-1.0, '
        '"reasoning": "brief"}, ...]'
    )
    packet_lines = [f"Packet {i + 1}: {fs}" for i, fs in enumerate(feat_strs)]
    return "\n".join(header_lines) + "\n\n" + "\n".join(packet_lines)


def _parse_batch_response(text: str, expected: int) -> list[int] | None:
    """
    Extract a JSON array of classifications from a batch LLM response.
    Returns list[int] of length `expected`, or None on any parse failure.

    Tries all '[' positions from rightmost to leftmost against the last ']'
    so that preamble text like "classify [each] packet: [...]" doesn't cause
    the wrong slice to be fed to json.loads.
    """
    end = text.rfind(']')
    if end == -1:
        return None

    # Collect every '[' that appears before `end`, try rightmost first.
    starts = [i for i, ch in enumerate(text) if ch == '[' and i < end]
    if not starts:
        return None

    for start in reversed(starts):
        try:
            arr = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(arr, list) or len(arr) != expected:
            continue
        preds = []
        ok = True
        for item in arr:
            if not isinstance(item, dict):
                ok = False
                break
            clf = str(item.get("classification", "")).lower()
            preds.append(1 if clf in ["malicious", "1", "true", "attack"] else 0)
        if ok:
            return preds

    return None


def evaluate_on_llm(X_adversarial_raw: np.ndarray,
                     y_true: np.ndarray,
                     llm_client: LLMClient,
                     mode: str = "zero_shot",
                     compact: bool = True,
                     example_rows: list[dict] = None,
                     save_traces: bool = True,
                     trace_tag: str = "",
                     batch_size: int = 10) -> dict:
    """
    Evaluate LLM on adversarial samples.

    Parameters
    ----------
    X_adversarial_raw : (n, 5) raw perturbed features
    y_true            : (n,) ground-truth labels
    llm_client        : LLMClient instance
    mode              : "zero_shot", "few_shot", or "chain_of_thought"
    compact           : use compact JSON format
    example_rows      : list of row dicts for few-shot examples
    save_traces       : save LLM reasoning to disk for CoT mode
    trace_tag         : filename prefix for saved traces
    batch_size        : samples per API call for zero_shot/few_shot (default 10).
                        chain_of_thought always uses batch_size=1 to preserve
                        per-sample reasoning for scientific validity.

    Returns
    -------
    {
      "llm_evasion_rate": float,
      "predictions":      list[int],
      "reasoning_samples": list[str],  (subset)
    }
    """
    sys_prompt = (SYSTEM_PROMPT_COMPACT_PACKET if compact else SYSTEM_PROMPT_BASE)
    fmt_fn     = format_packet_compact if compact else format_packet_verbose

    # CoT must remain per-sample (reasoning quality depends on single-sample focus)
    effective_batch = 1 if mode == "chain_of_thought" else max(1, batch_size)

    predictions: list[int] = []
    reasoning_samples: list[str] = []
    n = len(X_adversarial_raw)

    i = 0
    while i < n:
        batch_x = X_adversarial_raw[i : i + effective_batch]

        # ── Batched path (zero_shot / few_shot) ───────────────────────────────
        if effective_batch > 1:
            feat_strs = [fmt_fn(_row_to_dict(x)) for x in batch_x]
            batch_prompt = _build_batch_prompt(feat_strs, mode, example_rows or [], fmt_fn)
            result = llm_client.classify(sys_prompt, batch_prompt)
            batch_preds = _parse_batch_response(
                result.get("raw_response", ""), len(batch_x)
            )

            if batch_preds is not None:
                predictions.extend(batch_preds)
                # Capture the batch response as a single reasoning sample
                if len(reasoning_samples) < 5:
                    reasoning_samples.append(result.get("reasoning", ""))
                i += len(batch_x)
                continue

            # Batch parse failed — fall through to individual calls for this batch
            for x_raw in batch_x:
                row      = _row_to_dict(x_raw)
                feat_str = fmt_fn(row)
                if mode == "few_shot" and example_rows:
                    ex_lines = [
                        f"Features: {fmt_fn(ex)}\nLabel: "
                        f"{'MALICIOUS' if ex.get('is_malicious', 0) == 1 else 'NORMAL'}"
                        for ex in example_rows[:5]
                    ]
                    user_prompt = PROMPT_FEW_SHOT.format(
                        examples="\n\n".join(ex_lines), features=feat_str
                    )
                else:
                    user_prompt = PROMPT_ZERO_SHOT.format(features=feat_str)
                res = llm_client.classify(sys_prompt, user_prompt)
                predictions.append(res["prediction"])
                if len(reasoning_samples) < 5:
                    reasoning_samples.append(res.get("reasoning", ""))
            i += len(batch_x)
            continue

        # ── Per-sample path (chain_of_thought, or batch_size=1) ──────────────
        x_raw    = batch_x[0]
        row      = _row_to_dict(x_raw)
        feat_str = fmt_fn(row)

        if mode == "zero_shot":
            user_prompt = PROMPT_ZERO_SHOT.format(features=feat_str)

        elif mode == "few_shot":
            if not example_rows:
                user_prompt = PROMPT_ZERO_SHOT.format(features=feat_str)
            else:
                ex_lines = []
                for ex in example_rows[:5]:
                    label = "MALICIOUS" if ex.get("is_malicious", 0) == 1 else "NORMAL"
                    ex_lines.append(f"Features: {fmt_fn(ex)}\nLabel: {label}")
                examples_str = "\n\n".join(ex_lines)
                user_prompt = PROMPT_FEW_SHOT.format(
                    examples=examples_str, features=feat_str
                )

        elif mode == "chain_of_thought":
            user_prompt = PROMPT_COT.format(features=feat_str)

        else:
            raise ValueError(f"Unknown mode: {mode}")

        # CoT needs more tokens — step-by-step reasoning can exceed 512 tokens
        # before reaching the final JSON classification.
        call_max_tokens = 1024 if mode == "chain_of_thought" else None
        result = llm_client.classify(sys_prompt, user_prompt,
                                     max_tokens=call_max_tokens)
        predictions.append(result["prediction"])

        if len(reasoning_samples) < 5:
            reasoning_samples.append(result.get("reasoning", ""))

        # Save CoT traces to disk for qualitative analysis
        if mode == "chain_of_thought" and save_traces and trace_tag:
            trace_file = TRACES_DIR / f"{trace_tag}_sample_{i:04d}.txt"
            trace_file.write_text(
                f"Features: {feat_str}\n\nReasoning:\n{result.get('raw_response', '')}",
                encoding="utf-8",
            )

        i += 1

    preds_arr = np.array(predictions, dtype=int)
    valid_mask = preds_arr >= 0
    evasion_rate = float((preds_arr[valid_mask] == 0).mean()) if np.any(valid_mask) else None

    return {
        "llm_evasion_rate":  evasion_rate,
        "predictions":       predictions,
        "reasoning_samples": reasoning_samples,
        "n_valid":           int(np.sum(valid_mask)),
        "n_invalid":         int(np.sum(~valid_mask)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Session-level LLM evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _build_session_classify_fn(llm_client: LLMClient):
    """Return callable(packets_raw: np.ndarray) → int for session classification."""
    def _classify_session(packets_raw: np.ndarray) -> int:
        df = pd.DataFrame(packets_raw, columns=FEATURE_NAMES)
        sess_str = format_session_compact(df)
        prompt = PROMPT_SESSION_COMPACT.format(session=sess_str)
        result = llm_client.classify(SYSTEM_PROMPT_COMPACT_SESSION, prompt)
        return int(result["prediction"])
    return _classify_session


# ─────────────────────────────────────────────────────────────────────────────
# Figures
# ─────────────────────────────────────────────────────────────────────────────

def generate_evasion_rate_curves(all_results: dict) -> None:
    """
    Generate evasion-rate-vs-ε plots for all classifiers.
    Saves to results/adversarial/figures/.
    Requires matplotlib; skips gracefully if unavailable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [SKIP] matplotlib not installed - figures not generated.")
        return

    epsilons = sorted(all_results.keys())
    sources  = ["cart", "knn"]

    for source in sources:
        fig, ax = plt.subplots(figsize=(8, 5))
        classifiers = ["cart", "knn", "llm_zero_shot", "llm_few_shot", "llm_cot"]
        labels      = ["CART", "KNN", "LLM-ZS", "LLM-FS", "LLM-CoT"]
        markers     = ["o", "s", "^", "D", "v"]

        for clf, label, marker in zip(classifiers, labels, markers):
            rates = []
            for eps in epsilons:
                key = f"{source}_{_eps_tag(eps)}"
                r   = all_results.get(eps, {}).get(f"source_{source}", {})
                rate = r.get(clf, {}).get("evasion_rate", None)
                rates.append(rate)

            valid = [(e, r) for e, r in zip(epsilons, rates) if r is not None]
            if valid:
                xs, ys = zip(*valid)
                ax.plot(xs, ys, marker=marker, label=label, linewidth=2)

        ax.set_xlabel("Perturbation Budget ε (fraction of IQR)", fontsize=12)
        ax.set_ylabel("Evasion Rate", fontsize=12)
        ax.set_title(f"Evasion Rate vs ε — {source.upper()}-crafted adversarial samples")
        ax.set_ylim(-0.05, 1.05)
        ax.legend()
        ax.grid(True, alpha=0.3)

        out = FIGURES_DIR / f"evasion_vs_epsilon_{source}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Figure saved: {out.name}")


def generate_latex_table(all_results: dict) -> str:
    """Generate LaTeX booktabs table for the paper."""
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{Adversarial evasion rates by classifier and budget $\varepsilon$}",
        r"  \label{tab:adversarial_evasion}",
        r"  \begin{tabular}{llrrrrr}",
        r"    \toprule",
        r"    $\varepsilon$ & Source & CART & KNN & LLM-ZS & LLM-FS & LLM-CoT \\",
        r"    \midrule",
    ]
    for eps in sorted(all_results.keys()):
        for source in ["cart", "knn"]:
            r = all_results[eps].get(f"source_{source}", {})

            def _pct(d: dict, k: str) -> str:
                v = d.get(k, {}).get("evasion_rate")
                return f"{v * 100:.1f}" if v is not None else "--"

            lines.append(
                f"    {eps:.2f} & {source.upper()} & "
                f"{_pct(r, 'cart')} & {_pct(r, 'knn')} & "
                f"{_pct(r, 'llm_zero_shot')} & {_pct(r, 'llm_few_shot')} & "
                f"{_pct(r, 'llm_cot')} \\\\"
            )
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluation pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main(provider: str = "openai",
         epsilon_values: list = None,
         skip_llm: bool = False,
         dry_run: bool = False,
         compact: bool = True) -> None:

    epsilons = epsilon_values or ADV_CONFIG["epsilon_values"]
    llm_n    = ADV_CONFIG["llm_eval_sample_size"]
    few_k    = ADV_CONFIG["llm_few_shot_k"]

    print(f"\n{'='*70}")
    print("Gap 5: Adversarial Evaluation")
    print(f"  provider : {provider}  |  skip_llm: {skip_llm}  |  dry_run: {dry_run}")
    print(f"  epsilon values : {epsilons}")
    print(f"{'='*70}\n")

    conn = get_db(DB_PATH)

    # Train models (needed for classical evaluation and session perturbation)
    print("[1/5] Training CART and KNN...")
    if dry_run:
        print("  [DRY-RUN] Skipping.")
        conn.close()
        return

    try:
        models = train_for_adversarial(conn)
    except ValueError as e:
        print(f"  [SKIP] {e}")
        conn.close()
        return

    cart    = models["cart"]
    knn     = models["knn"]
    scaler  = models["scaler"]
    X_train = models["X_train"]
    y_train = models["y_train"]

    threat = ThreatModel(X_train, FEATURE_NAMES)

    # LLM client
    llm_client = None
    if not skip_llm:
        print(f"[2/5] Initialising LLM client ({provider})...")
        try:
            llm_client = LLMClient(provider=provider)
        except Exception as e:
            print(f"  [WARN] LLM init failed: {e}. Continuing without LLM.")
            skip_llm = True

    # Few-shot examples (load some clean training samples)
    example_rows: list[dict] = []
    if not skip_llm:
        from src.llm_experiments import load_test_samples
        df_ex = load_test_samples(conn, n=few_k * 2)
        if len(df_ex) > 0:
            example_rows = df_ex.head(few_k).to_dict("records")

    # ── Per-ε evaluation ──────────────────────────────────────────────────────
    print(f"\n[3/5] Evaluating {len(epsilons)} epsilon values...")
    all_results: dict = {}
    summary_rows: list = []

    for eps in epsilons:
        tag = _eps_tag(eps)
        print(f"\n  epsilon = {eps}")
        all_results[eps] = {}

        for source in ("cart", "knn"):
            df_adv = load_adversarial_csv(source, eps)
            if df_adv is None:
                print(f"    [SKIP] {source} adversarial CSV not found for epsilon={eps}. "
                      "Run generate_adversarial.py first.")
                continue

            adv_cols = [f"adv_{c}" for c in FEATURE_NAMES]
            X_adv    = df_adv[adv_cols].values
            y_true   = df_adv["original_label"].values
            n_eval   = min(llm_n, len(X_adv))
            X_adv_sub = X_adv[:n_eval]
            y_sub     = y_true[:n_eval]

            # Classical classifiers
            cl_res = evaluate_on_classical(X_adv_sub, y_sub, cart, knn, scaler)

            result_entry: dict = {
                "cart": {"evasion_rate": cl_res["cart_evasion_rate"]},
                "knn":  {"evasion_rate": cl_res["knn_evasion_rate"]},
            }

            row = [eps, source.upper(),
                   f"{cl_res['cart_evasion_rate']:.2%}",
                   f"{cl_res['knn_evasion_rate']:.2%}"]

            # LLM evaluations
            for mode in ("zero_shot", "few_shot", "chain_of_thought"):
                if skip_llm:
                    result_entry[f"llm_{mode}"] = {"evasion_rate": None}
                    row.append("--")
                    continue

                llm_res = evaluate_on_llm(
                    X_adv_sub, y_sub,
                    llm_client=llm_client,
                    mode=mode,
                    compact=compact,
                    example_rows=example_rows if mode == "few_shot" else None,
                    save_traces=(mode == "chain_of_thought"),
                    trace_tag=f"{source}_{tag}",
                    batch_size=10,   # 10 samples per API call for zs/fs modes
                )
                result_entry[f"llm_{mode}"] = {
                    "evasion_rate": llm_res["llm_evasion_rate"],
                    "n_valid": llm_res["n_valid"],
                    "n_invalid": llm_res["n_invalid"],
                }
                row.append(_fmt_pct(llm_res["llm_evasion_rate"]))

            all_results[eps][f"source_{source}"] = result_entry
            summary_rows.append(row)

    print("\n" + tabulate(
        summary_rows,
        headers=["epsilon", "Source", "CART Evade%", "KNN Evade%",
                 "LLM-ZS Evade%", "LLM-FS Evade%", "LLM-CoT Evade%"],
        tablefmt="grid",
    ))

    # ── Session-level evaluation ───────────────────────────────────────────────
    print("\n[4/5] Session-level evaluation (Exp 5D)...")
    session_results: dict = {}

    if not skip_llm:
        llm_session_fn = _build_session_classify_fn(llm_client)
        sessions = session_perturbation.load_malicious_sessions(
            conn,
            min_packets=ADV_CONFIG["min_session_length"],
            max_sessions=ADV_CONFIG["n_session_samples"],
        )
        print(f"  Loaded {len(sessions)} sessions")

        if sessions:
            for eps in epsilons:
                pert_list = []
                for sess in sessions:
                    pert = session_perturbation.perturb_session_per_packet(
                        sess["packets"], cart, threat, eps, scaler
                    )
                    pert_list.append(pert)

                sess_eval = session_perturbation.evaluate_session_consistency(
                    sessions, pert_list, cart, scaler, llm_session_fn
                )
                session_results[eps] = sess_eval
                print(
                    f"  epsilon={eps}: CART per-pkt evasion={sess_eval['cart_per_packet_evasion_rate']:.2%}  "
                    f"CART session det={sess_eval['cart_session_detection_rate']:.2%}  "
                    f"LLM session det={_fmt_pct(sess_eval['llm_session_detection_rate'])}  "
                    f"(valid={sess_eval.get('llm_valid_sessions', 0)}, invalid={sess_eval.get('llm_invalid_sessions', 0)})"
                )
    else:
        print("  [SKIP] LLM not available.")

    # ── Transfer attack ────────────────────────────────────────────────────────
    print("\n[5/5] Transfer attack evaluation (Exp 5C)...")
    transfer_results: dict = {}

    if not skip_llm:
        llm_fn = _build_classify_fn(llm_client, compact=compact)
        for eps in epsilons:
            df_cart = load_adversarial_csv("cart", eps)
            df_knn  = load_adversarial_csv("knn",  eps)
            if df_cart is None or df_knn is None:
                continue

            adv_cols  = [f"adv_{c}" for c in FEATURE_NAMES]
            X_cart    = df_cart[adv_cols].values
            X_knn     = df_knn[adv_cols].values
            y_t       = np.ones(len(X_cart), dtype=int)

            n_t = min(50, len(X_cart), len(X_knn))  # small budget for transfer
            tr  = black_box_search.transfer_attack_evaluation(
                X_cart[:n_t], X_knn[:n_t], llm_fn, y_t[:n_t]
            )
            transfer_results[eps] = tr
            print(
                f"  ε={eps}: CART→LLM transfer={_fmt_pct(tr['cart_transfer_rate'])}  "
                f"KNN→LLM transfer={_fmt_pct(tr['knn_transfer_rate'])}  "
                f"(invalid: CART={tr.get('cart_invalid_predictions', 0)}, KNN={tr.get('knn_invalid_predictions', 0)})"
            )

    # ── Save all results ───────────────────────────────────────────────────────
    out_evasion = ADV_DIR / "evasion_rates.json"
    with open(out_evasion, "w") as fh:
        json.dump({str(k): v for k, v in all_results.items()}, fh, indent=2)

    out_session = ADV_DIR / "session_consistency.json"
    with open(out_session, "w") as fh:
        json.dump({str(k): v for k, v in session_results.items()}, fh, indent=2)

    out_transfer = ADV_DIR / "transfer_results.json"
    with open(out_transfer, "w") as fh:
        json.dump({str(k): v for k, v in transfer_results.items()}, fh, indent=2)

    print(f"\nResults saved to {ADV_DIR}/")

    # ── LaTeX table ────────────────────────────────────────────────────────────
    if all_results:
        latex = generate_latex_table(all_results)
        (ADV_DIR / "table_evasion.tex").write_text(latex)
        print(f"LaTeX table saved to {ADV_DIR / 'table_evasion.tex'}")

    # ── Figures ────────────────────────────────────────────────────────────────
    generate_evasion_rate_curves(all_results)

    conn.close()
    print("\nEvaluation complete.")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate classifiers on Gap 5 adversarial samples"
    )
    parser.add_argument("--provider", default="openai",
                        choices=["anthropic", "openai"])
    parser.add_argument("--epsilon", type=float, nargs="+",
                        default=ADV_CONFIG["epsilon_values"])
    parser.add_argument("--skip-llm", action="store_true",
                        help="Evaluate only CART/KNN (no API calls)")
    parser.add_argument("--verbose", action="store_true",
                        help="Use verbose LLM formatting instead of compact")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    main(
        provider=args.provider,
        epsilon_values=args.epsilon,
        skip_llm=args.skip_llm,
        dry_run=args.dry_run,
        compact=not args.verbose,
    )
