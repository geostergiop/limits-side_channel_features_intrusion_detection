#!/usr/bin/env python3
"""
Phase 5: Analysis & Reporting.

Generates:
  - Comparative tables (Classical ML vs LLM)
  - Per-experiment breakdown
  - LaTeX-ready output
  - Explainability analysis of LLM reasoning traces
  - Cost/efficiency analysis
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix
)
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import RESULTS_DIR


def load_results(name_or_path) -> list[dict]:
    path = name_or_path if isinstance(name_or_path, Path) else (RESULTS_DIR / name_or_path)
    if not path.exists():
        print(f"[WARN] {path} not found")
        return []
    with open(path) as f:
        return json.load(f)


def pick_latest_result_file(prefix: str) -> Path | None:
    candidates = sorted(RESULTS_DIR.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def resolve_local_baseline_file(path: Path | None = None) -> Path | None:
    """
    Resolve a single local-baseline result file.

    Default behaviour intentionally avoids merging Phase 2 and Phase 3 outputs,
    because they may come from different runs or different random samples.
    """
    if path is not None:
        return path

    preferred = RESULTS_DIR / "classical_ml_results.json"
    if preferred.exists():
        return preferred

    fallback = RESULTS_DIR / "phase2_local_ml_results.json"
    if fallback.exists():
        return fallback

    return None


def _local_summary_rows(results: list[dict], experiment_prefix: str | None = None) -> list[dict]:
    summaries = [
        row for row in results
        if row.get("record_type") == "summary" and "error" not in row
    ]
    if experiment_prefix is not None:
        summaries = [
            row for row in summaries
            if str(row.get("experiment", "")).startswith(experiment_prefix)
        ]
    if summaries:
        return summaries

    legacy = [row for row in results if "error" not in row]
    if experiment_prefix is not None:
        legacy = [
            row for row in legacy
            if str(row.get("experiment", "")).startswith(experiment_prefix)
        ]
    return legacy


def _fmt_local_metric(row: dict, key: str) -> str:
    if f"{key}_std" in row:
        return f"{row.get(key, 0):.4f} +/- {row.get(f'{key}_std', 0):.4f}"
    return f"{row.get(key, 0):.4f}"


def _fmt_local_metric_latex(row: dict, key: str) -> str:
    if f"{key}_std" in row:
        return f"{row.get(key, 0):.4f} $\\pm$ {row.get(f'{key}_std', 0):.4f}"
    return f"{row.get(key, 0):.4f}"


def _fmt_local_ci(row: dict, key: str) -> str:
    low = row.get(f"{key}_ci95_low")
    high = row.get(f"{key}_ci95_high")
    if low is None or high is None:
        return "N/A"
    return f"[{low:.4f}, {high:.4f}]"


def compute_metrics(results: list[dict]) -> dict:
    """Compute standard metrics from a list of result dicts."""
    valid = [r for r in results if r.get("prediction", -1) >= 0]
    if not valid:
        return {}
    
    y_true = [r["ground_truth"] for r in valid]
    y_pred = [r["prediction"] for r in valid]
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    return {
        "n": len(valid),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "avg_confidence": np.mean([r.get("confidence", 0) for r in valid]),
        "avg_tokens": np.mean([r.get("tokens", 0) for r in valid]),
        "avg_latency_ms": np.mean([r.get("latency_ms", 0) for r in valid]),
    }


def generate_comparison_table(classical: list, llm: list) -> str:
    """Generate the main comparison table for the paper."""
    rows = []
    
    # Classical ML results (E1)
    for r in _local_summary_rows(classical, "E1_full_mixed_"):
        rows.append([
            f"Local-{r['algorithm']}",
            f"{r['experiment']} ({r.get('split_type', 'holdout')})",
            _fmt_local_metric(r, "accuracy"),
            _fmt_local_ci(r, "accuracy"),
            _fmt_local_metric(r, "f1_1"),
            f"{r.get('train_time_s', 0):.1f}s",
            "N/A",
        ])
    
    # LLM results by experiment
    exp_groups = defaultdict(list)
    for r in llm:
        exp_groups[r.get("experiment", "unknown")].append(r)
    
    for exp_name, exp_results in sorted(exp_groups.items()):
        metrics = compute_metrics(exp_results)
        if not metrics:
            continue
        
        total_tokens = sum(r.get("tokens", 0) for r in exp_results)
        total_cost_approx = total_tokens * 0.000003  # rough estimate
        
        rows.append([
            f"LLM", exp_name,
            f"{metrics['accuracy']:.4f}",
            "N/A",
            f"{metrics['f1']:.4f}",
            f"{metrics['avg_latency_ms']:.0f}ms/call",
            f"~${total_cost_approx:.2f}"
        ])
    
    headers = ["Method", "Experiment", "Accuracy", "Accuracy CI95", "F1(mal)", "Time", "Cost"]
    return tabulate(rows, headers=headers, tablefmt="grid")


def generate_lofo_table(classical: list, llm: list) -> str:
    """Generate the LOFO comparison table (Gap 2 evidence)."""
    # Group by held-out family
    cl_by_fam = defaultdict(list)
    for r in _local_summary_rows(classical, "E4_LOFO_"):
        cl_by_fam[r.get("held_out_family", "")].append(r)
    
    llm_by_fam = defaultdict(list)
    for r in llm:
        if r.get("experiment") == "4D_lofo" and r.get("prediction", -1) >= 0:
            llm_by_fam[r.get("held_out_family", "")].append(r)
    
    all_families = sorted(set(cl_by_fam.keys()) | set(llm_by_fam.keys()))
    
    rows = []
    for fam in all_families:
        if not fam:
            continue
        
        # Best classical for this family
        cl_results = cl_by_fam.get(fam, [])
        best_cl = max(cl_results, key=lambda x: x.get("accuracy", 0),
                      default={})
        cl_acc = best_cl.get("accuracy", 0)
        cl_algo = best_cl.get("algorithm", "N/A")
        cl_f1 = best_cl.get("f1_1", 0)
        
        # LLM for this family
        llm_fam = llm_by_fam.get(fam, [])
        llm_metrics = compute_metrics(llm_fam) if llm_fam else {}
        llm_acc = llm_metrics.get("accuracy", 0)
        llm_f1 = llm_metrics.get("f1", 0)
        
        winner = "LLM" if llm_acc > cl_acc else cl_algo if cl_acc > 0 else "N/A"
        
        rows.append([
            fam, 
            f"{cl_algo}: {_fmt_local_metric(best_cl, 'accuracy')}" if cl_acc else "N/A",
            _fmt_local_metric(best_cl, "f1_1") if cl_f1 else "N/A",
            f"{llm_acc:.4f}" if llm_acc else "N/A",
            f"{llm_f1:.4f}" if llm_f1 else "N/A",
            winner
        ])
    
    headers = ["Held-Out Family", "Best ML (Acc)", "ML F1", 
               "LLM Acc", "LLM F1", "Winner"]
    return tabulate(rows, headers=headers, tablefmt="grid")


def generate_latex_tables(classical: list, llm: list) -> str:
    """Generate LaTeX-formatted tables for the paper."""
    latex = []
    
    # Main comparison table
    latex.append(r"\begin{table}[ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Comparison of Local ML Baselines vs LLM-based Classification}")
    latex.append(r"\label{tab:comparison}")
    latex.append(r"\begin{tabular}{lcccccc}")
    latex.append(r"\hline")
    latex.append(r"Method & Accuracy & Precision & Recall & F1 & TP Rate & FP Rate \\")
    latex.append(r"\hline")
    
    # Add local-baseline rows
    for r in _local_summary_rows(classical, "E1_full_mixed_"):
        tpr = r.get("recall_1", 0)
        fpr = 1.0 - r.get("recall_0", 0)
        split_tag = str(r.get("split_type", "")).replace("_repeated_group_holdout", "")
        latex.append(
            f"{r['algorithm']}-{split_tag} & {_fmt_local_metric_latex(r, 'accuracy')} & "
            f"{_fmt_local_metric_latex(r, 'precision_1')} & {_fmt_local_metric_latex(r, 'recall_1')} & "
            f"{_fmt_local_metric_latex(r, 'f1_1')} & {tpr:.4f} & {fpr:.4f} \\\\"
        )
    
    # Add LLM rows
    for exp_name in ["4A_zero_shot", "4C_cot", "4D_lofo"]:
        exp_results = [r for r in llm if r.get("experiment") == exp_name]
        m = compute_metrics(exp_results)
        if m:
            tpr = m["tp"] / (m["tp"] + m["fn"]) if (m["tp"] + m["fn"]) > 0 else 0
            fpr = m["fp"] / (m["fp"] + m["tn"]) if (m["fp"] + m["tn"]) > 0 else 0
            label = exp_name.replace("_", r"\_")
            latex.append(
                f"LLM-{label} & {m['accuracy']:.4f} & "
                f"{m['precision']:.4f} & {m['recall']:.4f} & "
                f"{m['f1']:.4f} & {tpr:.4f} & {fpr:.4f} \\\\"
            )
    
    latex.append(r"\hline")
    latex.append(r"\end{tabular}")
    latex.append(r"\end{table}")
    
    return "\n".join(latex)


def analyze_reasoning_traces(llm_results: list) -> str:
    """Analyze the explainability of LLM reasoning traces."""
    cot_results = [r for r in llm_results 
                   if r.get("experiment") == "4C_cot" and "reasoning" in r]
    
    if not cot_results:
        return "No CoT results available."
    
    lines = ["", "=" * 70, "Explainability Analysis (Experiment 4C)", "=" * 70]
    
    # Categorize reasoning patterns
    patterns = {
        "timing_analysis": 0,
        "size_analysis": 0,
        "ratio_analysis": 0,
        "beaconing_detection": 0,
        "exfiltration_mention": 0,
        "c2_mention": 0,
    }
    
    correct_with_good_reasoning = 0
    total_correct = 0
    
    for r in cot_results:
        reasoning = r.get("reasoning", "").lower()
        is_correct = r["prediction"] == r["ground_truth"]
        
        if is_correct:
            total_correct += 1
        
        if "timing" in reasoning or "time diff" in reasoning or "periodic" in reasoning:
            patterns["timing_analysis"] += 1
        if "size" in reasoning or "bytes" in reasoning:
            patterns["size_analysis"] += 1
        if "ratio" in reasoning or "payload ratio" in reasoning:
            patterns["ratio_analysis"] += 1
        if "beacon" in reasoning:
            patterns["beaconing_detection"] += 1
        if "exfiltrat" in reasoning:
            patterns["exfiltration_mention"] += 1
        if "c2" in reasoning or "c&c" in reasoning or "command and control" in reasoning:
            patterns["c2_mention"] += 1
    
    lines.append(f"\nTotal CoT samples: {len(cot_results)}")
    lines.append(f"Correct predictions: {total_correct}/{len(cot_results)} "
                 f"({100*total_correct/len(cot_results):.1f}%)")
    lines.append(f"\nReasoning pattern frequency:")
    for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(cot_results)
        lines.append(f"  {pattern:30s}: {count:>4d} ({pct:.1f}%)")
    
    # Sample reasoning traces
    lines.append(f"\n--- Sample Correct Classifications ---")
    correct_mal = [r for r in cot_results 
                   if r["prediction"] == 1 and r["ground_truth"] == 1][:2]
    correct_norm = [r for r in cot_results
                    if r["prediction"] == 0 and r["ground_truth"] == 0][:2]
    
    for r in correct_mal + correct_norm:
        label = "MALICIOUS" if r["ground_truth"] else "NORMAL"
        lines.append(f"\n  [{label}] Confidence: {r['confidence']:.2f}")
        lines.append(f"  Reasoning: {r['reasoning'][:300]}...")
    
    return "\n".join(lines)


def main(classical_results: Path | None = None, llm_results: Path | None = None):
    print("=" * 70)
    print("LLM Traffic Detection - Analysis & Reporting")
    print("=" * 70)

    classical_path = resolve_local_baseline_file(classical_results)
    classical = load_results(classical_path) if classical_path else []

    llm_path = llm_results or pick_latest_result_file("llm_results_")
    llm = load_results(llm_path) if llm_path else []

    if classical_path is not None and classical_path.exists():
        print(f"Using local baseline results: {classical_path.name}")
    if llm_path is not None and Path(llm_path).exists():
        print(f"Using LLM results:       {Path(llm_path).name}")

    if not classical and not llm:
        print("[ERROR] No results found. Run experiments first.")
        return

    # Main comparison table
    if classical and llm:
        print("\n" + generate_comparison_table(classical, llm))

    # LOFO table (Gap 2)
    if classical and llm:
        lofo_table = generate_lofo_table(classical, llm)
        if lofo_table:
            print("\n" + lofo_table)

    # Explainability analysis
    if llm:
        print(analyze_reasoning_traces(llm))

    # LaTeX output
    if classical and llm:
        latex = generate_latex_tables(classical, llm)
        latex_path = RESULTS_DIR / "tables.tex"
        with open(latex_path, "w") as f:
            f.write(latex)
        print(f"\nLaTeX tables saved to: {latex_path}")

    # Summary statistics
    if llm:
        total_tokens = sum(r.get("tokens", 0) for r in llm)
        total_calls = len([r for r in llm if r.get("tokens", 0) > 0])
        print(f"\nTotal API calls: {total_calls}")
        print(f"Total tokens:    {total_tokens}")
        print(f"Approx cost:     ${total_tokens * 0.000003:.2f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze classical and LLM experiment outputs")
    parser.add_argument("--classical-results", type=Path, default=None,
                        help="Path to a local baseline JSON file (default: classical_ml_results.json, or Phase 2 if Phase 3 is missing)")
    parser.add_argument("--llm-results", type=Path, default=None,
                        help="Path to a specific llm_results_*.json file (default: newest matching file)")
    args = parser.parse_args()
    main(classical_results=args.classical_results, llm_results=args.llm_results)
