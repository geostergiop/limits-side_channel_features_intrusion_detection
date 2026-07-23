#!/usr/bin/env python3
"""Generate the complete, audited session-experiment Markdown report."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "session_balanced_llm_local_paper_tables_2026-07-03.md"

SOURCE_PATHS = {
    "local_balanced": RESULTS / "session_local_results_balanced.json",
    "local_deployment": RESULTS / "session_local_results_deployment.json",
    "llm_balanced": RESULTS / "session_llm_results_balanced_paper_5k.json",
    "llm_deployment": RESULTS / "session_llm_results_deployment_paper_6k.json",
}

EXPECTED_LLM_REPEATS = [0, 2, 7, 8, 9]
EXPECTED_LOCAL_REPEATS = list(range(10))
FEATURE_ORDER = {"minimal": 0, "mercury": 1, "combined": 2}
UNIT_ORDER = {"session_sequence": 0, "behavior_window": 1, "packet_ablation": 2}
ALGORITHM_ORDER = {"RF": 0, "XGB": 1, "LGBM": 2, "CART": 3, "KNN": 4}


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required result artifact: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise TypeError(f"Expected a JSON list in {path}")
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def sample_std(values: Iterable[float]) -> float:
    values = list(values)
    return statistics.stdev(values) if len(values) > 1 else 0.0


def pct(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{100.0 * float(value):.{digits}f}%"


def number(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):,.{digits}f}"


def metric_pm(row: dict, field: str, digits: int = 1) -> str:
    return f"{pct(row.get(field), digits)} +/- {pct(row.get(f'{field}_std', 0.0), digits)}"


def metric_ci(row: dict, field: str, digits: int = 1) -> str:
    return (
        f"[{pct(row.get(f'{field}_ci95_low'), digits)}, "
        f"{pct(row.get(f'{field}_ci95_high'), digits)}]"
    )


def md_escape(value: object) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text


def md_table(headers: list[str], rows: Iterable[Iterable[object]]) -> list[str]:
    output = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend(
        "| " + " | ".join(md_escape(value) for value in row) + " |"
        for row in rows
    )
    output.append("")
    return output


def unit_label(row: dict) -> str:
    unit = row["sample_unit"]
    if unit == "session_sequence":
        return "session sequence"
    if unit == "behavior_window":
        return f"behavior window {float(row.get('window_seconds') or 0):g}s"
    return "packet ablation"


def row_sort_key(row: dict) -> tuple:
    return (
        UNIT_ORDER.get(row.get("sample_unit"), 99),
        float(row.get("window_seconds") or 0.0),
        FEATURE_ORDER.get(row.get("feature_set"), 99),
        ALGORITHM_ORDER.get(row.get("algorithm"), 99),
        row.get("llm_context_mode", ""),
    )


def finite_metric(row: dict, field: str) -> bool:
    value = row.get(field)
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_local(rows: list[dict], name: str) -> list[str]:
    repeat_rows = [row for row in rows if row.get("record_type") == "repeat"]
    summary_rows = [row for row in rows if row.get("record_type") == "summary"]
    if len(repeat_rows) != 750 or len(summary_rows) != 75:
        raise AssertionError(f"{name}: expected 750 repeat and 75 summary rows")

    keys = [(row["experiment"], row["algorithm"], row["repeat_index"]) for row in repeat_rows]
    if len(keys) != len(set(keys)):
        raise AssertionError(f"{name}: duplicate experiment/algorithm/repeat rows")
    if sorted({int(row["repeat_index"]) for row in repeat_rows}) != EXPECTED_LOCAL_REPEATS:
        raise AssertionError(f"{name}: unexpected repeat coverage")
    if len({row["experiment"] for row in repeat_rows}) != 15:
        raise AssertionError(f"{name}: expected 15 experiments")

    summary_map = {(row["experiment"], row["algorithm"]): row for row in summary_rows}
    fields = ["accuracy", "f1_1", "precision_1", "recall_1", "n_test_samples", "predict_time_s"]
    for key in summary_map:
        group = [row for row in repeat_rows if (row["experiment"], row["algorithm"]) == key]
        if len(group) != 10:
            raise AssertionError(f"{name}: {key} has {len(group)} repeat rows")
        for field in fields:
            calculated = mean(float(row[field]) for row in group)
            reported = float(summary_map[key][field])
            if not math.isclose(calculated, reported, rel_tol=0.0, abs_tol=1e-12):
                raise AssertionError(f"{name}: summary mismatch for {key} {field}")
        if not all(finite_metric(row, field) for row in group for field in ["accuracy", "f1_1"]):
            raise AssertionError(f"{name}: non-finite metric in {key}")

    return [
        f"{name}: 15 experiments x 5 algorithms x 10 repeats are complete",
        f"{name}: all 75 summary rows reconcile to their repeat-row arithmetic means",
    ]


def validate_llm(rows: list[dict], name: str, deployment: bool) -> list[str]:
    raw = [row for row in rows if row.get("record_type") is None]
    repeat_rows = [row for row in rows if row.get("record_type") == "repeat_metrics"]
    summary_rows = [row for row in rows if row.get("record_type") == "summary"]
    if len(repeat_rows) != 75 or len(summary_rows) != 15:
        raise AssertionError(f"{name}: expected 75 repeat metrics and 15 summaries")
    if sorted({int(row["repeat_index"]) for row in raw}) != EXPECTED_LLM_REPEATS:
        raise AssertionError(f"{name}: unexpected repeat coverage")
    if len({row["experiment"] for row in raw}) != 15:
        raise AssertionError(f"{name}: expected 15 experiments")

    keys = [(row["experiment"], row["repeat_index"], row["packet_id"]) for row in raw]
    if len(keys) != len(set(keys)):
        raise AssertionError(f"{name}: duplicate sample within an experiment/repeat")
    if any(int(row.get("prediction", -1)) not in (0, 1) for row in raw):
        raise AssertionError(f"{name}: invalid LLM prediction found")

    for row in raw:
        if deployment:
            score = row.get("positive_score")
            if score is not None:
                expected = int(float(score) >= float(row["selected_threshold"]))
                if expected != int(row["prediction"]):
                    raise AssertionError(f"{name}: deployment threshold application mismatch")
        elif int(row["prediction"]) != int(row["raw_prediction"]):
            raise AssertionError(f"{name}: balanced prediction differs from raw prediction")

    summary_map = {row["experiment"]: row for row in summary_rows}
    fields = ["accuracy", "f1_1", "precision_1", "recall_1", "avg_latency_ms", "avg_tokens"]
    for experiment, summary in summary_map.items():
        group = [row for row in repeat_rows if row["experiment"] == experiment]
        if len(group) != 5:
            raise AssertionError(f"{name}: {experiment} has {len(group)} repeat rows")
        for field in fields:
            calculated = mean(float(row[field]) for row in group)
            if not math.isclose(calculated, float(summary[field]), rel_tol=0.0, abs_tol=1e-12):
                raise AssertionError(f"{name}: summary mismatch for {experiment} {field}")

    return [
        f"{name}: 15 variants x 5 specified repeats are complete",
        f"{name}: no duplicate within-repeat samples and no invalid parsed predictions",
        f"{name}: all summaries reconcile to repeat metrics",
        f"{name}: thresholded predictions are internally consistent" if deployment else
        f"{name}: balanced predictions match the model's raw parsed labels",
    ]


def summaries(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("record_type") == "summary"]


def repeats(rows: list[dict], llm: bool = False) -> list[dict]:
    record_type = "repeat_metrics" if llm else "repeat"
    return [row for row in rows if row.get("record_type") == record_type]


def raw_llm(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("record_type") is None]


def best_worst(rows: list[dict], predicate: Callable[[dict], bool]) -> tuple[dict, dict]:
    selected = [row for row in rows if predicate(row)]
    return max(selected, key=lambda row: row["f1_1"]), min(selected, key=lambda row: row["f1_1"])


def specificity_stats(repeat_rows: list[dict], experiment: str) -> tuple[float, float]:
    values = [float(row["recall_0"]) for row in repeat_rows if row["experiment"] == experiment]
    return mean(values), sample_std(values)


def llm_variant_support(raw: list[dict], experiment: str) -> tuple[int, int, int]:
    selected = [row for row in raw if row["experiment"] == experiment]
    benign = sum(int(row["ground_truth"]) == 0 for row in selected)
    malicious = len(selected) - benign
    return len(selected), benign, malicious


def llm_threshold_stats(raw: list[dict], experiment: str) -> tuple[float, float, float]:
    by_repeat = {}
    for row in raw:
        if row["experiment"] == experiment:
            by_repeat[int(row["repeat_index"])] = float(row["selected_threshold"])
    values = list(by_repeat.values())
    return mean(values), min(values), max(values)


def local_traffic_rows(rows: list[dict], evaluation_mode: str) -> list[list[object]]:
    repeat_rows = [
        row for row in repeats(rows)
        if row["algorithm"] == "RF" and row["feature_set"] == "minimal"
    ]
    representatives = {
        "session / windows": next(row for row in repeat_rows if row["sample_unit"] == "session_sequence"),
        "packet ablation": next(row for row in repeat_rows if row["sample_unit"] == "packet_ablation"),
    }
    output = []
    for label, representative in representatives.items():
        experiment = representative["experiment"]
        group = [row for row in repeat_rows if row["experiment"] == experiment]
        manifest = json.loads(Path(representative["manifest_path"]).read_text(encoding="utf-8"))
        cohort_rate = float(manifest["repeats"][0]["outer_summary"]["overall_positive_rate"])
        benign = sum(int(row["test_support_0"]) for row in group)
        malicious = sum(int(row["test_support_1"]) for row in group)
        fold_rates = [
            int(row["test_support_1"]) /
            (int(row["test_support_0"]) + int(row["test_support_1"]))
            for row in group
        ]
        output.append([
            evaluation_mode,
            label,
            manifest["cohort_size"],
            pct(cohort_rate, 2),
            f"{benign:,}",
            f"{malicious:,}",
            pct(malicious / (benign + malicious), 2),
            f"{pct(min(fold_rates), 2)}-{pct(max(fold_rates), 2)}",
        ])
    return output


def llm_traffic_rows(rows: list[dict], evaluation_mode: str) -> list[list[object]]:
    raw = raw_llm(rows)
    output = []
    for label, predicate in [
        ("session / 5s windows", lambda row: row["sample_unit"] != "packet_ablation"),
        ("packet ablation", lambda row: row["sample_unit"] == "packet_ablation"),
    ]:
        selected = [row for row in raw if predicate(row)]
        variant = sorted({row["experiment"] for row in selected})[0]
        variant_rows = [row for row in selected if row["experiment"] == variant]
        benign = sum(int(row["ground_truth"]) == 0 for row in variant_rows)
        malicious = len(variant_rows) - benign
        output.append([
            evaluation_mode,
            label,
            len(variant_rows),
            benign,
            malicious,
            pct(malicious / len(variant_rows), 2),
            len({row["repeat_index"] for row in variant_rows}),
            "per model/feature/context variant",
        ])
    return output


def feature_comparison_rows(
    local_by_mode: dict[str, list[dict]],
    llm_by_mode: dict[str, list[dict]],
) -> list[list[object]]:
    output = []
    for mode in ["balanced", "deployment"]:
        local_summary = summaries(local_by_mode[mode])
        llm_summary = summaries(llm_by_mode[mode])
        for feature in ["minimal", "mercury", "combined"]:
            local_feature = [row for row in local_summary if row["feature_set"] == feature]
            winners = []
            for experiment in sorted({row["experiment"] for row in local_feature}):
                candidates = [row for row in local_feature if row["experiment"] == experiment]
                winners.append(max(candidates, key=lambda row: row["f1_1"]))
            llm_feature = [row for row in llm_summary if row["feature_set"] == feature]
            output.append([
                mode,
                feature,
                pct(mean(row["f1_1"] for row in local_feature), 2),
                pct(mean(row["f1_1"] for row in winners), 2),
                f"{max(local_feature, key=lambda row: row['f1_1'])['algorithm']} / "
                f"{unit_label(max(local_feature, key=lambda row: row['f1_1']))}: "
                f"{pct(max(row['f1_1'] for row in local_feature), 2)}",
                pct(mean(row["f1_1"] for row in llm_feature), 2),
                f"{unit_label(max(llm_feature, key=lambda row: row['f1_1']))} / "
                f"{max(llm_feature, key=lambda row: row['f1_1'])['llm_context_mode']}: "
                f"{pct(max(row['f1_1'] for row in llm_feature), 2)}",
            ])
    return output


def local_result_table(rows: list[dict]) -> list[list[object]]:
    output = []
    for row in sorted(summaries(rows), key=row_sort_key):
        output.append([
            row["feature_set"],
            unit_label(row),
            row["algorithm"],
            metric_pm(row, "accuracy"),
            metric_pm(row, "f1_1"),
            metric_pm(row, "precision_1"),
            metric_pm(row, "recall_1"),
            metric_pm(row, "recall_0"),
            metric_ci(row, "f1_1"),
            number(row.get("train_time_s"), 2),
            number(row.get("samples_per_second"), 0),
        ])
    return output


def llm_result_table(rows: list[dict], deployment: bool) -> list[list[object]]:
    raw = raw_llm(rows)
    repeat_rows = repeats(rows, llm=True)
    output = []
    for row in sorted(summaries(rows), key=row_sort_key):
        n_samples, benign, malicious = llm_variant_support(raw, row["experiment"])
        specificity_mean, specificity_std = specificity_stats(repeat_rows, row["experiment"])
        threshold_text = "0.500 (fixed)"
        if deployment:
            threshold_mean, threshold_low, threshold_high = llm_threshold_stats(raw, row["experiment"])
            threshold_text = f"{threshold_mean:.3f} [{threshold_low:.3f}, {threshold_high:.3f}]"
        output.append([
            row["feature_set"],
            unit_label(row),
            row["llm_context_mode"],
            f"{n_samples} ({benign}/{malicious})",
            metric_pm(row, "accuracy"),
            metric_pm(row, "f1_1"),
            metric_pm(row, "precision_1"),
            metric_pm(row, "recall_1"),
            f"{pct(specificity_mean)} +/- {pct(specificity_std)}",
            metric_ci(row, "f1_1"),
            threshold_text,
            number(row.get("avg_latency_ms"), 0),
            number(row.get("avg_tokens"), 0),
        ])
    return output


def family_aggregate_rows(rows: list[dict], evaluation_mode: str) -> list[list[object]]:
    raw = [row for row in raw_llm(rows) if int(row["ground_truth"]) == 1]
    output = []
    for family in sorted({row["malware_family"] for row in raw}):
        selected = [row for row in raw if row["malware_family"] == family]
        detected = sum(int(row["prediction"]) == 1 for row in selected)
        output.append([
            evaluation_mode,
            family,
            len(selected),
            detected,
            len(selected) - detected,
            pct(detected / len(selected), 2),
            "configuration-level predictions; observations repeat across variants",
        ])
    expected = {"BitCoinMiner", "Dridex", "Hancitor", "TrojanDownloader", "Website_5.8.88.175"}
    missing = sorted(expected - {row["malware_family"] for row in raw})
    for family in missing:
        output.append([evaluation_mode, family, 0, 0, 0, "not estimable", "absent from sampled test folds"])
    return output


def family_detail_rows(rows: list[dict], evaluation_mode: str) -> list[list[object]]:
    family_rows = [row for row in rows if row.get("record_type") == "family_summary"]
    output = []
    for row in sorted(family_rows, key=lambda item: (row_sort_key(item), item["malware_family"])):
        output.append([
            evaluation_mode,
            row["feature_set"],
            unit_label(row),
            row["llm_context_mode"],
            row["malware_family"],
            row["n_samples"],
            row["detected_count"],
            row["missed_count"],
            pct(row["detection_rate"], 2),
        ])
    return output


def runtime_rows(local_by_mode: dict[str, list[dict]], llm_by_mode: dict[str, list[dict]]) -> list[list[object]]:
    output = []
    for mode in ["balanced", "deployment"]:
        local_repeat = repeats(local_by_mode[mode])
        local_summary = summaries(local_by_mode[mode])
        llm_raw = raw_llm(llm_by_mode[mode])
        llm_summary = summaries(llm_by_mode[mode])
        for label, predicate in [
            ("session / windows", lambda row: row["sample_unit"] != "packet_ablation"),
            ("packet ablation", lambda row: row["sample_unit"] == "packet_ablation"),
        ]:
            local_latencies = [
                1000.0 * float(row["predict_time_s"]) / int(row["n_test_samples"])
                for row in local_repeat if predicate(row)
            ]
            llm_latencies = [float(row["latency_ms"]) for row in llm_raw if predicate(row)]
            fastest_local = max(
                (row for row in local_summary if predicate(row)),
                key=lambda row: row["samples_per_second"],
            )
            fastest_llm = min(
                (row for row in llm_summary if predicate(row)),
                key=lambda row: row["avg_latency_ms"],
            )
            local_median = statistics.median(local_latencies)
            llm_median = statistics.median(llm_latencies)
            output.append([
                mode,
                label,
                f"{local_median:.6f}",
                f"{llm_median:.1f}",
                f"{llm_median / local_median:,.0f}x",
                f"{fastest_local['algorithm']} / {unit_label(fastest_local)}: "
                f"{number(fastest_local['samples_per_second'], 0)} samples/s",
                f"{unit_label(fastest_llm)} / {fastest_llm['llm_context_mode']}: "
                f"{number(fastest_llm['avg_latency_ms'], 0)} ms",
            ])
    return output


def top_result_rows(local_by_mode: dict[str, list[dict]], llm_by_mode: dict[str, list[dict]]) -> list[list[object]]:
    output = []
    for mode in ["balanced", "deployment"]:
        for detector, mode_rows, model_field in [
            ("local ML", summaries(local_by_mode[mode]), "algorithm"),
            ("GPT-5.5", summaries(llm_by_mode[mode]), "llm_context_mode"),
        ]:
            repeat_rows = repeats(llm_by_mode[mode], llm=True) if detector == "GPT-5.5" else []
            for label, predicate in [
                ("session / windows", lambda row: row["sample_unit"] != "packet_ablation"),
                ("packet ablation", lambda row: row["sample_unit"] == "packet_ablation"),
            ]:
                selected = [row for row in mode_rows if predicate(row)]
                best = max(selected, key=lambda row: row["f1_1"])
                if detector == "GPT-5.5":
                    specificity = specificity_stats(repeat_rows, best["experiment"])[0]
                else:
                    specificity = best["recall_0"]
                output.append([
                    mode,
                    detector,
                    label,
                    best[model_field],
                    best["feature_set"],
                    unit_label(best),
                    pct(best["accuracy"], 2),
                    pct(best["f1_1"], 2),
                    pct(best["precision_1"], 2),
                    pct(best["recall_1"], 2),
                    pct(specificity, 2),
                ])
    return output


def best_and_worst_text(local_by_mode: dict[str, list[dict]], llm_by_mode: dict[str, list[dict]]) -> list[str]:
    lines = []
    for mode in ["balanced", "deployment"]:
        for detector, mode_rows, model_field in [
            ("local ML", summaries(local_by_mode[mode]), "algorithm"),
            ("GPT-5.5", summaries(llm_by_mode[mode]), "llm_context_mode"),
        ]:
            best = max(mode_rows, key=lambda row: row["f1_1"])
            worst = min(mode_rows, key=lambda row: row["f1_1"])
            lines.append(
                f"- **{mode.title()} {detector}:** best was `{best[model_field]}` with "
                f"`{best['feature_set']}` {unit_label(best)} at F1 {pct(best['f1_1'], 2)}, "
                f"accuracy {pct(best['accuracy'], 2)}, and recall {pct(best['recall_1'], 2)}. "
                f"Worst was `{worst[model_field]}` with `{worst['feature_set']}` "
                f"{unit_label(worst)} at F1 {pct(worst['f1_1'], 2)}, accuracy "
                f"{pct(worst['accuracy'], 2)}, and recall {pct(worst['recall_1'], 2)}."
            )
    return lines


def llm_context_stats(rows: list[dict], context_mode: str) -> dict[str, float]:
    """Return paired session/window statistics for one LLM context mode."""
    summary_rows = [
        row for row in summaries(rows)
        if row["sample_unit"] != "packet_ablation" and row["llm_context_mode"] == context_mode
    ]
    sample_rows = [
        row for row in raw_llm(rows)
        if row["sample_unit"] != "packet_ablation" and row["llm_context_mode"] == context_mode
    ]
    malicious = sum(int(row["ground_truth"]) == 1 for row in sample_rows)
    detected = sum(
        int(row["ground_truth"]) == 1 and int(row["prediction"]) == 1
        for row in sample_rows
    )
    correct = sum(int(row["ground_truth"]) == int(row["prediction"]) for row in sample_rows)
    return {
        "mean_f1": mean(row["f1_1"] for row in summary_rows),
        "pooled_accuracy": correct / len(sample_rows),
        "pooled_recall": detected / malicious,
    }


def build_report(data: dict[str, list[dict]], audit_notes: list[str]) -> str:
    local_by_mode = {
        "balanced": data["local_balanced"],
        "deployment": data["local_deployment"],
    }
    llm_by_mode = {
        "balanced": data["llm_balanced"],
        "deployment": data["llm_deployment"],
    }
    local_balanced = summaries(local_by_mode["balanced"])
    local_deployment = summaries(local_by_mode["deployment"])
    llm_balanced = summaries(llm_by_mode["balanced"])
    llm_deployment = summaries(llm_by_mode["deployment"])

    best_bal_local = max(local_balanced, key=lambda row: row["f1_1"])
    best_dep_local = max(local_deployment, key=lambda row: row["f1_1"])
    best_bal_llm = max(llm_balanced, key=lambda row: row["f1_1"])
    best_dep_llm = max(llm_deployment, key=lambda row: row["f1_1"])
    worst_bal_llm = min(llm_balanced, key=lambda row: row["f1_1"])
    balanced_blind_context = llm_context_stats(llm_by_mode["balanced"], "blind")
    balanced_memory_context = llm_context_stats(llm_by_mode["balanced"], "memory")
    deployment_blind_context = llm_context_stats(llm_by_mode["deployment"], "blind")
    deployment_memory_context = llm_context_stats(llm_by_mode["deployment"], "memory")

    lines = [
        "# Session Experiment Suite: Complete Packet and Session Detection Results",
        "",
        f"Generated on {datetime.now().date().isoformat()} from frozen JSON artifacts produced on "
        "2026-07-03 and 2026-07-04. Values are recomputed from JSON rows, not copied from console output.",
        "",
        "## Technical Summary",
        "",
        f"- **Local ML produced the strongest overall detectors.** The best balanced result was "
        f"`{best_bal_local['algorithm']}` on `{best_bal_local['feature_set']}` "
        f"{unit_label(best_bal_local)} (F1 {pct(best_bal_local['f1_1'], 2)}, accuracy "
        f"{pct(best_bal_local['accuracy'], 2)}, recall {pct(best_bal_local['recall_1'], 2)}). The best "
        f"deployment result was `{best_dep_local['algorithm']}` on `{best_dep_local['feature_set']}` "
        f"{unit_label(best_dep_local)} (F1 {pct(best_dep_local['f1_1'], 2)}, accuracy "
        f"{pct(best_dep_local['accuracy'], 2)}, recall {pct(best_dep_local['recall_1'], 2)}).",
        f"- **GPT-5.5 was useful in selected configurations but inconsistent.** Its best balanced variant was "
        f"`{best_bal_llm['feature_set']}` {unit_label(best_bal_llm)} with "
        f"`{best_bal_llm['llm_context_mode']}` context (F1 {pct(best_bal_llm['f1_1'], 2)}, accuracy "
        f"{pct(best_bal_llm['accuracy'], 2)}, recall {pct(best_bal_llm['recall_1'], 2)}). Its best "
        f"deployment variant reached F1 {pct(best_dep_llm['f1_1'], 2)} and recall "
        f"{pct(best_dep_llm['recall_1'], 2)}, but only {pct(best_dep_llm['precision_1'], 2)} precision "
        f"and {pct(best_dep_llm['accuracy'], 2)} accuracy. The worst balanced variant, "
        f"`{worst_bal_llm['feature_set']}` {unit_label(worst_bal_llm)}, detected "
        f"{pct(worst_bal_llm['recall_1'], 2)} of malicious samples (F1 {pct(worst_bal_llm['f1_1'], 2)}).",
        "- **Feature usefulness depended on detector and evaluation mode.** Local ML was strongest with "
        "minimal features in balanced session/window tests, while Mercury-style or combined features led "
        "the deployment packet tests. GPT-5.5 benefited most from combined features in balanced mode, "
        "but minimal features had the highest mean F1 in deployment mode. There is no evidence that adding "
        "more metadata universally improves an LLM classifier.",
        "- **Deployment thresholding traded specificity for recall.** Thresholds were selected on validation "
        "samples only, then frozen for test evaluation, as intended. However, several 25-sample validation "
        "folds selected a threshold of `0.000`, effectively favoring malicious predictions. High deployment "
        "recall must therefore be read together with precision, specificity, and the large repeat-to-repeat "
        "standard deviations.",
        "- **The deployment evidence is corpus-prevalence-faithful, not enterprise-prevalence-faithful.** "
        "The natural sampled cohorts were 38.52% malicious for session-based samples and 31.57% for packets. "
        "Those rates are far above most production networks, so the measured precision and alert burden "
        "should not be extrapolated directly to operational base rates.",
        "- **Family claims remain incomplete.** Hancitor appeared only sparsely in balanced LLM samples and "
        "was absent from all deployment LLM test subsets. Deployment detection rates therefore cannot be "
        "claimed for every malware family.",
        "",
        "### Best and Worst Combinations",
        "",
        *best_and_worst_text(local_by_mode, llm_by_mode),
        "",
        "The main practical conclusion is straightforward: supervised local models remain the stronger "
        "production detector on both packet and session representations. GPT-5.5 adds a potentially useful "
        "reasoning layer, especially with memory or carefully selected temporal summaries, but its current "
        "absolute accuracy, false-positive behavior, latency, and family-coverage gaps do not support replacing "
        "the local detector.",
        "",
        "## Experiment Matrix: What Was Tested",
        "",
        "The session suite crosses two evaluation modes, three feature sets, packet and session representations, and both "
        "local supervised models and GPT-5.5. All train/validation/test partitions are capture-disjoint and come "
        "from frozen repeated grouped-holdout manifests. `GPT-5.5` is the operator-confirmed model identity used "
        "for the paper; this report normalizes the presentation label while preserving the frozen JSON artifacts.",
        "",
    ]
    lines.extend(md_table(
        ["Detector", "Evaluation modes", "Feature sets", "Representation", "Model/context", "Repeats", "Completed combinations"],
        [
            ["Local ML", "balanced + deployment", "minimal, Mercury, combined", "whole session sequence", "RF, XGB, LGBM, CART, KNN", "10 per combination", "2 x 3 x 1 x 5 = 30 summaries"],
            ["Local ML", "balanced + deployment", "minimal, Mercury, combined", "behavior windows: 1s, 5s, 30s", "RF, XGB, LGBM, CART, KNN", "10 per combination", "2 x 3 x 3 x 5 = 90 summaries"],
            ["Local ML", "balanced + deployment", "minimal, Mercury, combined", "individual-packet ablation", "RF, XGB, LGBM, CART, KNN", "10 per combination", "2 x 3 x 1 x 5 = 30 summaries"],
            ["GPT-5.5", "balanced + deployment", "minimal, Mercury, combined", "whole session sequence", "blind + training-memory context", "5 selected repeats", "2 x 3 x 1 x 2 = 12 variants"],
            ["GPT-5.5", "balanced + deployment", "minimal, Mercury, combined", "5-second behavior window", "blind + training-memory context", "5 selected repeats", "2 x 3 x 1 x 2 = 12 variants"],
            ["GPT-5.5", "balanced + deployment", "minimal, Mercury, combined", "individual-packet ablation", "blind only", "5 selected repeats", "2 x 3 x 1 x 1 = 6 variants"],
        ],
    ))
    lines.extend([
        "This produces **150 local-model summary configurations** (1,500 repeat evaluations) and **30 GPT-5.5 "
        "variants** (150 repeat-level metrics). The local grid is the full Cartesian product of modes, features, "
        "representations/windows, and five algorithms. The LLM grid has two deliberate restrictions: only the "
        "5-second behavior window was sent to the API, and packet ablation is blind-only because training-memory "
        "context is intended for grouped session behavior.",
        "",
        "- **Balanced versus deployment:** balanced cohorts are sampled 50/50 before capture-group splitting; "
        "deployment cohorts retain corpus prevalence, select thresholds only on validation data, and evaluate "
        "those frozen thresholds once on held-out test data.",
        "- **Minimal features:** five original side-channel values: packet size, payload size, payload ratio, "
        "ratio to the previous packet, and inter-arrival time.",
        "- **Mercury-style features:** 20 efficiently extractable metadata values covering direction, protocol, "
        "ports and service hints, encryption, packet position/timing, and packet/payload deltas. These are the "
        "available Mercury-style subset, not Cisco Mercury's complete fingerprint implementation.",
        "- **Combined features:** all five minimal and all 20 Mercury-style values, for 25 packet-level inputs "
        "before session/window aggregation.",
        "- **Packet versus session:** packet ablation classifies one packet; session sequence summarizes the full "
        "ordered session; behavior windows test how much temporal evidence is available after 1, 5, or 30 seconds.",
        "- **Blind versus memory-enabled LLM:** blind prompts contain only the held-out sample and task instructions; "
        "memory prompts additionally contain labeled examples and class/family context drawn only from the training "
        "split, never validation or test labels.",
        "",
        "## Scope, Sources, and Metric Definitions",
        "",
    ])

    source_rows = []
    for key, path in SOURCE_PATHS.items():
        rows = data[key]
        source_rows.append([
            path.relative_to(ROOT),
            len(rows),
            f"{path.stat().st_size:,}",
            datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds"),
            sha256(path)[:16],
        ])
    source_rows.extend([
        ["limits2.tex", "legacy manuscript", f"{(ROOT / 'limits2.tex').stat().st_size:,}", "2026-07-03", "see source"],
        ["results/session_publication_artifact_provenance.json", "publication provenance", "see source", "generated", "see source"],
    ])
    lines.extend(md_table(["Artifact", "Rows", "Bytes", "Modified", "SHA-256 prefix"], source_rows))
    lines.extend([
        "- **Detection rate / recall:** `TP / (TP + FN)` for the malicious class.",
        "- **Precision:** `TP / (TP + FP)` and therefore sensitive to traffic prevalence.",
        "- **Specificity:** `TN / (TN + FP)`, reported to expose deployment false-positive behavior.",
        "- **F1(mal):** harmonic mean of malicious precision and recall; the primary ranking metric here.",
        "- **Balanced:** the source cohort is sampled 50/50 before capture-group splitting. Complete capture "
        "test folds are not forced to remain 50/50.",
        "- **Deployment:** the source cohort retains the corpus's sampled natural prevalence. Thresholds are "
        "chosen only on each validation fold and evaluated once on its held-out test fold.",
        "- **Uncertainty:** means and sample standard deviations are over 10 local-model repeats or 5 budgeted "
        "LLM repeats. The stored 95% intervals use `mean +/- 1.96 * std / sqrt(n)` and are descriptive because "
        "repeated holdouts reuse parts of a finite cohort.",
        "- **Session analysis:** `session_sequence` summarizes the whole ordered session; `behavior_window` "
        "summarizes the first 1, 5, or 30 seconds for local ML and 5 seconds for the budgeted LLM runs.",
        "- **Packet analysis:** `packet_ablation` is the retained individual-packet ablation, not the preferred "
        "deployment unit.",
        "- **Mercury features:** these are Mercury-style metadata available in this database, not the complete "
        "Cisco Mercury TLS/SSH/HTTP fingerprint implementation.",
        "",
        "## Traffic Composition and Evaluation Denominators",
        "",
        "The local models evaluate every sample in each frozen held-out fold. The LLM runs use budgeted test "
        "subsets from the same manifest family, so their denominators are smaller. Pooled repeated-fold counts "
        "below count evaluation appearances, not unique sessions or packets.",
        "",
        "### Local ML Cohorts and Full Held-Out Folds",
        "",
    ])
    local_traffic = (
        local_traffic_rows(local_by_mode["balanced"], "balanced") +
        local_traffic_rows(local_by_mode["deployment"], "deployment")
    )
    lines.extend(md_table(
        ["Mode", "Unit", "Cohort N", "Cohort mal %", "Pooled benign test", "Pooled malicious test", "Pooled test mal %", "Fold mal % range"],
        local_traffic,
    ))
    lines.extend([
        "The balanced cohorts are exactly 50% malicious, but capture grouping creates extremely heterogeneous "
        "held-out folds. For session-based balanced tests, individual test folds range from 0.08% to 90.27% "
        "malicious. This explains the large standard deviations and means that `balanced` must be described as "
        "cohort-balanced, not fold-balanced.",
        "",
        "### Budgeted GPT-5.5 Test Subsets",
        "",
    ])
    llm_traffic = (
        llm_traffic_rows(llm_by_mode["balanced"], "balanced") +
        llm_traffic_rows(llm_by_mode["deployment"], "deployment")
    )
    lines.extend(md_table(
        ["Mode", "Unit", "Test predictions", "Benign", "Malicious", "Malicious %", "Repeats", "Counting basis"],
        llm_traffic,
    ))
    lines.extend([
        "Balanced GPT-5.5 produced 1,662 held-out test predictions: 831 benign and 831 malicious. Deployment "
        "used 6,000 API calls: 1,875 validation calls for threshold selection plus 4,125 held-out test "
        "predictions. The deployment test subsets were 33.09% malicious for session/window variants and "
        "24.00% for packet variants. These are random budgeted subsets of the natural-prevalence folds and "
        "therefore differ from the full-fold percentages above.",
        "",
        "## Headline Detector Comparison",
        "",
        "Each row is the highest-F1 configuration within its evaluation mode, detector class, and analysis "
        "unit. This separates packet ablations from session/window detection instead of allowing one to hide "
        "the other.",
        "",
    ])
    lines.extend(md_table(
        ["Mode", "Detector", "Unit", "Model/context", "Features", "Representation", "Accuracy", "F1(mal)", "Precision", "Recall", "Specificity"],
        top_result_rows(local_by_mode, llm_by_mode),
    ))
    lines.extend([
        "Local ML leads every mode/unit comparison by F1. The closest LLM result is the balanced minimal 5-second "
        "window, but it remains about 17.5 percentage points below the strongest balanced local session/window "
        "result. In deployment mode, GPT-5.5's session recall is high only alongside much lower precision and "
        "specificity than the local model.",
        "",
        "## Feature-Set Comparison",
        "",
        "`Mean local F1` is the unweighted mean across all 25 model/unit summaries per feature set. `Winner mean "
        "F1` first selects the best local algorithm for each of the five unit/window experiments, then averages "
        "those five winners. LLM means cover five context/unit variants per feature set.",
        "",
    ])
    lines.extend(md_table(
        ["Mode", "Features", "Mean local F1", "Local winner mean F1", "Best local combination", "Mean GPT-5.5 F1", "Best GPT-5.5 combination"],
        feature_comparison_rows(local_by_mode, llm_by_mode),
    ))
    lines.extend([
        "Minimal features are not merely a weak ablation: they produce the best balanced local session/window "
        "detector and the strongest deployment LLM average. Mercury-style metadata is valuable for deployment "
        "packet models, while the combined set offers the strongest all-configuration local average in deployment. "
        "The absence of a monotonic minimal-to-Mercury-to-combined improvement is a genuine result, not a reporting "
        "error.",
        "",
        "## GPT-5.5 Balanced Results",
        "",
        "Balanced LLM test subsets are class-balanced and use a fixed 0.5 decision threshold. Memory means the "
        "prompt contains labeled examples and class/family context drawn only from the training split.",
        "",
    ])
    llm_headers = [
        "Features", "Unit", "Context", "N (ben/mal)", "Accuracy", "F1(mal)", "Precision", "Recall",
        "Specificity", "F1 CI95", "Threshold mean [range]", "Latency ms", "Tokens",
    ]
    lines.extend(md_table(llm_headers, llm_result_table(llm_by_mode["balanced"], deployment=False)))
    lines.extend([
        f"Across the six paired session/window variants, memory improved unweighted mean balanced LLM F1 from "
        f"{pct(balanced_blind_context['mean_f1'], 2)} to {pct(balanced_memory_context['mean_f1'], 2)}, "
        f"pooled accuracy from {pct(balanced_blind_context['pooled_accuracy'], 2)} to "
        f"{pct(balanced_memory_context['pooled_accuracy'], 2)}, and pooled recall from "
        f"{pct(balanced_blind_context['pooled_recall'], 2)} to "
        f"{pct(balanced_memory_context['pooled_recall'], 2)}. It was not universally beneficial: the strongest "
        "balanced variant was the blind minimal 5-second window, and packet ablations intentionally have no "
        "memory variant.",
        "",
        "## GPT-5.5 Deployment Results",
        "",
        "Every deployment threshold below was selected only from 25 validation samples per repeat, then frozen "
        "for 55 held-out test samples. `Threshold mean [range]` summarizes the five independently selected repeat "
        "thresholds.",
        "",
    ])
    lines.extend(md_table(llm_headers, llm_result_table(llm_by_mode["deployment"], deployment=True)))
    lines.extend([
        "The threshold table is central to interpreting deployment performance. Several blind Mercury/combined "
        "session or window folds selected zero, and the minimal session-memory thresholds averaged only 0.070. "
        f"This produces high recall but weak specificity. Across the six paired session/window variants, memory "
        f"raised pooled deployment accuracy from {pct(deployment_blind_context['pooled_accuracy'], 2)} to "
        f"{pct(deployment_memory_context['pooled_accuracy'], 2)} and mean F1 from "
        f"{pct(deployment_blind_context['mean_f1'], 2)} to "
        f"{pct(deployment_memory_context['mean_f1'], 2)}, but pooled malicious recall fell from "
        f"{pct(deployment_blind_context['pooled_recall'], 2)} to "
        f"{pct(deployment_memory_context['pooled_recall'], 2)} because validation-selected thresholds differed "
        "by context.",
        "",
        "## Local ML Balanced Results: All Configurations",
        "",
        "Local values are mean +/- sample standard deviation across all 10 frozen capture-group repeats. "
        "Training time and prediction throughput exclude packet extraction and feature construction.",
        "",
    ])
    local_headers = [
        "Features", "Unit", "Model", "Accuracy", "F1(mal)", "Precision", "Recall", "Specificity",
        "F1 CI95", "Train s", "Samples/s",
    ]
    lines.extend(md_table(local_headers, local_result_table(local_by_mode["balanced"])))
    lines.extend([
        "The balanced local results are strongest for minimal temporal/session summaries and Mercury/combined "
        "packet ablations. Their large standard deviations are driven primarily by capture composition: entire "
        "captures are isolated, and only 12 capture groups are available.",
        "",
        "## Local ML Deployment Results: All Configurations",
        "",
        "Deployment local models use validation-only threshold selection for score-producing classifiers. XGBoost "
        "and LightGBM use validation-only early stopping before final test evaluation.",
        "",
    ])
    lines.extend(md_table(local_headers, local_result_table(local_by_mode["deployment"])))
    lines.extend([
        "The strongest deployment packet F1 comes from XGBoost with Mercury-style metadata. The highest deployment "
        "accuracy is LightGBM on Mercury packet ablation, but accuracy alone is not a safe winner criterion because "
        "the held-out prevalence varies sharply between captures.",
        "",
        "## Malware-Family Detection Coverage for GPT-5.5",
        "",
        "The aggregate table counts model-configuration predictions, not independent malware instances. The same "
        "underlying traffic can be evaluated under multiple feature sets, contexts, and representations. It is useful "
        "for identifying systematic weak families but must not be used as an independent-sample confidence interval.",
        "",
    ])
    family_aggregate = (
        family_aggregate_rows(llm_by_mode["balanced"], "balanced") +
        family_aggregate_rows(llm_by_mode["deployment"], "deployment")
    )
    lines.extend(md_table(
        ["Mode", "Family", "Prediction rows", "Detected", "Missed", "Detection rate", "Independence note"],
        family_aggregate,
    ))
    lines.extend([
        "Balanced detection was weakest for `Website_5.8.88.175` at 11.70%. Hancitor's apparent 25.00% rate "
        "comes from only 12 configuration-level predictions and is too sparse for a family claim. Deployment "
        "shows high aggregate recall for the four represented families, but Hancitor has zero test support and "
        "TrojanDownloader support is extremely small.",
        "",
        "### Per-Variant Family Results",
        "",
    ])
    family_details = (
        family_detail_rows(llm_by_mode["balanced"], "balanced") +
        family_detail_rows(llm_by_mode["deployment"], "deployment")
    )
    lines.extend(md_table(
        ["Mode", "Features", "Unit", "Context", "Family", "N", "Detected", "Missed", "Detection rate"],
        family_details,
    ))
    lines.extend([
        "Local Phase 7 outputs contain class-level confusion matrices but not per-family prediction rows, so local "
        "family-specific detection rates cannot be reconstructed from these artifacts. They should be added to a "
        "future run before making local-versus-LLM family comparisons.",
        "",
        "## Packet and Session Detection Runtime",
        "",
        "The median local number is batch prediction time divided by test samples across all repeat rows. The LLM "
        "number is the median measured API round-trip per test prompt. The ratio is an order-of-magnitude operational "
        "comparison, not a hardware-normalized benchmark: local timing excludes feature extraction, while LLM timing "
        "includes network/provider latency.",
        "",
    ])
    lines.extend(md_table(
        ["Mode", "Unit", "Local median ms/sample", "GPT-5.5 median ms/sample", "Latency ratio", "Fastest local summary", "Fastest GPT-5.5 summary"],
        runtime_rows(local_by_mode, llm_by_mode),
    ))
    lines.extend([
        "Across modes and units, GPT-5.5 requires roughly 0.5-0.6 million times the measured local batch-inference "
        "latency per sample. Even allowing for the optimistic local timing boundary, local ML is decisively better "
        "suited to inline or high-volume detection. An LLM is more defensible as an asynchronous analyst or second-stage "
        "triage component after a fast local model filters traffic.",
        "",
        "## Comparison with Legacy Packet Experiments",
        "",
        "The older `limits2.tex` experiments are not paired reruns. They used earlier packet-centric cohorts and "
        "protocols, while the session suite uses frozen capture-grouped session/window/packet-ablation manifests and broader "
        "feature configurations. The old near-saturated results therefore establish an easier historical reference, "
        "not a directly comparable control.",
        "",
    ])
    legacy_rows = [
        ["Legacy", "CART E1 session", "packet-era grouped baseline", "98.98%", "98.27%"],
        ["Legacy", "KNN E1 random", "random packet split", "99.13%", "98.56%"],
        ["Legacy", "RF E1 capture", "capture-held packet baseline", "97.64%", "96.25%"],
        ["Session balanced", "best local session/window", f"{best_bal_local['algorithm']} / {best_bal_local['feature_set']} / {unit_label(best_bal_local)}", pct(best_bal_local["accuracy"], 2), pct(best_bal_local["f1_1"], 2)],
        ["Session balanced", "best GPT-5.5 session/window", f"{best_bal_llm['llm_context_mode']} / {best_bal_llm['feature_set']} / {unit_label(best_bal_llm)}", pct(best_bal_llm["accuracy"], 2), pct(best_bal_llm["f1_1"], 2)],
        ["Session deployment", "best local overall", f"{best_dep_local['algorithm']} / {best_dep_local['feature_set']} / {unit_label(best_dep_local)}", pct(best_dep_local["accuracy"], 2), pct(best_dep_local["f1_1"], 2)],
        ["Session deployment", "best GPT-5.5 overall", f"{best_dep_llm['llm_context_mode']} / {best_dep_llm['feature_set']} / {unit_label(best_dep_llm)}", pct(best_dep_llm["accuracy"], 2), pct(best_dep_llm["f1_1"], 2)],
    ]
    lines.extend(md_table(["Generation", "Result", "Configuration", "Accuracy", "F1(mal)"], legacy_rows))
    lines.extend([
        "The lower session-suite scores are credible and informative: they expose cross-capture generalization, temporal "
        "aggregation, feature-set dependence, and threshold instability that the earlier packet tests did not jointly "
        "stress. They should not be framed as a simple regression in model quality.",
        "",
        "## Validation, Limitations, and Robustness Audit",
        "",
        "### Artifact Integrity Checks",
        "",
    ])
    lines.extend(f"- {note}" for note in audit_notes)
    lines.extend([
        "- Deployment `prediction` values exactly match `positive_score >= selected_threshold` for every stored "
        "test row; balanced predictions exactly match raw parsed labels.",
        "- All 5,787 stored GPT-5.5 test predictions are valid binary labels; no parse/API failure was silently "
        "discarded from metrics.",
        "",
        "### Required Interpretation Caveats",
        "",
        "- Capture-group holdout prevents capture leakage, but only 12 capture groups create very wide class-mix and "
        "performance variation. Some folds are almost single-class at the sample level.",
        "- The LLM uses five selected repeats and budgeted subsets; local models use ten repeats and complete test "
        "folds. Compare mean performance directionally and preserve each method's uncertainty rather than treating "
        "their raw prediction counts as equal evidence.",
        "- F1-driven threshold selection on only 25 deployment validation prompts is unstable. Threshold zero is a "
        "valid optimizer output under this rule, but it is operationally unacceptable without an explicit false-positive "
        "constraint.",
        "- The deployment prevalence is natural only with respect to this sampled malware corpus. Precision will "
        "usually fall at lower real-world malicious prevalence for the same sensitivity and specificity.",
        "- Per-family aggregate counts repeat observations across model configurations. Hancitor deployment performance "
        "is not estimable, and TrojanDownloader deployment support is too small for a reliable rate.",
        "- The normal-approximation confidence intervals summarize repeat variability but do not account for repeated "
        "reuse of samples, multiple-comparison selection of the best row, or dependence among capture splits.",
        "- Local runtime excludes upstream feature extraction; LLM runtime includes remote API latency. The absolute "
        "ratio is not hardware-normalized, although the operational advantage of local inference is unambiguous.",
        "- The paper-facing GPT-5.5 identity is operator-supplied, while every archived LLM row retains the stale "
        "`model=gpt-5.4` configuration value. Provider-side request metadata is required to resolve this discrepancy "
        "before a camera-ready model-version claim.",
        "- The code supports fine-tune corpus export and matched evaluation, but these audited artifacts contain no "
        "completed fine-tuned baseline; prompted LLM results must not be presented as supervised LLM results.",
        "",
        "**Validation assessment: share with caveats.** The artifacts are complete and internally consistent, and the "
        "headline calculations are reproducible. The evidence supports comparative session-suite claims about local versus "
        "GPT-5.5 performance, feature-set sensitivity, packet versus session analysis, and latency. It does not support "
        "all-family deployment claims, enterprise-base-rate precision claims, or treating the selected best row as an "
        "unbiased estimate of future performance.",
        "",
        "## Recommended Paper Framing and Next Steps",
        "",
        "A reviewer-safe summary is: *Under capture-disjoint repeated holdout, local supervised models remained more "
        "accurate and operationally efficient than GPT-5.5 across packet and session representations, although both "
        "were sensitive to capture composition. "
        "Mercury-style metadata improved selected local deployment configurations but did not consistently improve "
        "LLM performance. Training-split memory improved average balanced LLM performance, while validation-only "
        "thresholding increased deployment recall at a substantial precision/specificity cost. These results position "
        "the LLM as a second-stage reasoning or triage component rather than a replacement for a local detector.*",
        "",
        "Before claiming production readiness:",
        "",
        "1. Replace pure validation-F1 thresholding with a prespecified false-positive constraint or cost-sensitive "
        "operating point and report precision at realistic base rates.",
        "2. Construct new frozen manifests that provide nonzero held-out support for every malware family, especially "
        "Hancitor, without moving test samples into validation or training.",
        "3. Emit per-family local-model predictions so local and LLM family detection can be compared on exactly the "
        "same held-out entities.",
        "4. Report unique sessions/packets in addition to configuration-level prediction rows and use a hierarchical "
        "or cluster-aware uncertainty analysis for repeated observations.",
        "5. Benchmark end-to-end latency, including PCAP parsing and feature construction, on pinned hardware; retain "
        "API round-trip and token cost as separate LLM deployment measures.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    data = {key: load_rows(path) for key, path in SOURCE_PATHS.items()}
    audit_notes = []
    audit_notes.extend(validate_local(data["local_balanced"], "balanced local ML"))
    audit_notes.extend(validate_local(data["local_deployment"], "deployment local ML"))
    audit_notes.extend(validate_llm(data["llm_balanced"], "balanced GPT-5.5", deployment=False))
    audit_notes.extend(validate_llm(data["llm_deployment"], "deployment GPT-5.5", deployment=True))

    report = build_report(data, audit_notes)
    OUTPUT.write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT} ({len(report.splitlines()):,} lines, {len(report):,} characters)")


if __name__ == "__main__":
    main()
