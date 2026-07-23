#!/usr/bin/env python3
"""Validate Session-paper tables against frozen result artifacts."""

from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MANUSCRIPT = ROOT / "limits3_session.tex"

FEATURES = ("minimal", "mercury", "combined")
UNITS = (
    ("session_sequence", "Session"),
    ("behavior_window_1s", "1-s window"),
    ("behavior_window_5s", "5-s window"),
    ("behavior_window_30s", "30-s window"),
    ("packet_ablation", "Packet"),
)
LLM_UNITS = (
    ("session_sequence", "Session", ("blind", "memory")),
    ("behavior_window_5s", "5-s window", ("blind", "memory")),
    ("packet_ablation", "Packet", ("blind",)),
)


def _load(name: str) -> list[dict]:
    with (RESULTS / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _local_key(row: dict) -> tuple[str, str, str]:
    unit = row["sample_unit"]
    if unit == "behavior_window":
        unit = f"behavior_window_{int(row['window_seconds'])}s"
    return row["evaluation_mode"], row["feature_set"], unit


def _llm_key(row: dict) -> tuple[str, str, str, str]:
    unit = row["sample_unit"]
    if unit == "behavior_window":
        unit = f"behavior_window_{int(row['window_seconds'])}s"
    return (
        row["evaluation_mode"],
        row["feature_set"],
        unit,
        row["llm_context_mode"],
    )


def _validate_local_grid(tex: str) -> None:
    rows = _load("session_local_results_balanced.json") + _load(
        "session_local_results_deployment.json"
    )
    winners: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        if row.get("record_type") != "summary":
            continue
        key = _local_key(row)
        if key not in winners or row["f1_1"] > winners[key]["f1_1"]:
            winners[key] = row

    assert len(winners) == 30, len(winners)
    for feature in FEATURES:
        for unit_key, unit_label in UNITS:
            balanced = winners[("balanced", feature, unit_key)]
            deployment = winners[("deployment", feature, unit_key)]
            fragment = (
                f" & {unit_label} & {balanced['algorithm']} & "
                f"${100 * balanced['f1_1']:.2f} \\pm {100 * balanced['f1_1_std']:.2f}$ & "
                f"{deployment['algorithm']}: "
                f"${100 * deployment['f1_1']:.2f} \\pm {100 * deployment['f1_1_std']:.2f}$"
            )
            assert fragment in tex, fragment


def _validate_llm_grid(tex: str) -> None:
    balanced_rows = _load("session_llm_results_balanced_paper_5k.json")
    deployment_rows = _load("session_llm_results_deployment_paper_6k.json")
    summaries = {
        _llm_key(row): row
        for row in balanced_rows + deployment_rows
        if row.get("record_type") == "summary"
    }
    thresholds: dict[tuple[str, str, str, str], dict[int, float]] = defaultdict(dict)
    for row in deployment_rows:
        if row.get("record_type"):
            continue
        thresholds[_llm_key(row)][row["repeat_index"]] = row["selected_threshold"]

    assert len(summaries) == 30, len(summaries)
    assert len(thresholds) == 15, len(thresholds)
    for feature in FEATURES:
        for unit_key, unit_label, contexts in LLM_UNITS:
            for context in contexts:
                balanced = summaries[("balanced", feature, unit_key, context)]
                deployment = summaries[("deployment", feature, unit_key, context)]
                values = list(
                    thresholds[("deployment", feature, unit_key, context)].values()
                )
                assert len(values) == 5, (feature, unit_key, context, values)
                context_label = "B" if context == "blind" else "M"
                fragment = (
                    f" & {unit_label} & {context_label} & "
                    f"${100 * balanced['f1_1']:.1f} \\pm {100 * balanced['f1_1_std']:.1f}$ & "
                    f"${100 * deployment['f1_1']:.1f} \\pm {100 * deployment['f1_1_std']:.1f}$ & "
                    f"{statistics.mean(values):.3f} [{min(values):.3f}, {max(values):.3f}]"
                )
                assert fragment in tex, fragment


def _validate_document_structure(tex: str) -> None:
    environment_stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{([^}]+)\}", tex):
        action, environment = match.groups()
        if action == "begin":
            environment_stack.append(environment)
        else:
            assert environment_stack, f"unexpected end of {environment}"
            assert environment_stack.pop() == environment, environment
    assert not environment_stack, environment_stack

    labels = []
    for line in tex.splitlines():
        if "\\label{" in line:
            labels.append(line.split("\\label{", 1)[1].split("}", 1)[0])
    assert len(labels) == len(set(labels)), "duplicate LaTeX labels"
    references = re.findall(r"\\(?:ref|pageref|eqref)\{([^}]+)\}", tex)
    missing_references = sorted(set(references) - set(labels))
    assert not missing_references, missing_references

    brace_depth = 0
    for raw_line in tex.splitlines():
        line = re.split(r"(?<!\\)%", raw_line, maxsplit=1)[0]
        for index, character in enumerate(line):
            escaped = index > 0 and line[index - 1] == "\\"
            if character == "{" and not escaped:
                brace_depth += 1
            elif character == "}" and not escaped:
                brace_depth -= 1
                assert brace_depth >= 0, raw_line
    assert brace_depth == 0, brace_depth

    required_figures = (
        "session_headline_f1.pdf",
        "session_llm_family_detection.pdf",
        "session_runtime_latency.pdf",
    )
    for figure in required_figures:
        assert (ROOT / "figures" / figure).is_file(), figure
        assert figure in tex, figure

    assert "\texttt" not in tex, "tab escape found before ext text"
    assert "NDSS" not in tex, "stale conference name"
    assert "Mercyry" not in tex, "misspelled Mercury"
    assert "packet-based packet" not in tex, "duplicated packet wording"


def main() -> None:
    tex = MANUSCRIPT.read_text(encoding="utf-8")
    _validate_local_grid(tex)
    _validate_llm_grid(tex)
    _validate_document_structure(tex)
    print("Session manuscript tables and figures match the frozen artifacts.")


if __name__ == "__main__":
    main()
