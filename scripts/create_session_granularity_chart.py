#!/usr/bin/env python3
"""Create the README comparison chart from published Phase 7 summaries."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "results" / "published"
FIGURES = ROOT / "figures"

MODES = ("balanced", "deployment")
FEATURES = ("minimal", "mercury", "combined")
DETECTORS = ("GPT-5.4", "RF", "XGB", "LGBM", "CART", "KNN")
GRANULARITIES = ("Whole", "30 s", "5 s", "1 s")

LOCAL_FILES = {
    mode: PUBLISHED / f"session_local_capture_disjoint_5fold_{mode}.summary.json"
    for mode in MODES
}
LLM_FILES = {
    mode: PUBLISHED
    / f"session_llm_capture_disjoint_5fold_{mode}_expanded_openai_memory.summary.json"
    for mode in MODES
}


def _records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError(f"Missing records list in {path}")
    return records


def _granularity(row: dict) -> str | None:
    if row.get("sample_unit") == "session_sequence":
        return "Whole"
    if row.get("sample_unit") != "behavior_window":
        return None
    seconds = float(row.get("window_seconds"))
    label = f"{seconds:g} s"
    return label if label in GRANULARITIES else None


def _pooled_f1(rows: list[dict]) -> float:
    tp = sum(int(row["tp"]) for row in rows)
    fp = sum(int(row["fp"]) for row in rows)
    fn = sum(int(row["fn"]) for row in rows)
    denominator = (2 * tp) + fp + fn
    if denominator == 0:
        raise ValueError("Cannot compute pooled F1 from an empty confusion matrix")
    return (2 * tp) / denominator


def collect_values() -> dict[tuple[str, str, str, str], float]:
    values: dict[tuple[str, str, str, str], float] = {}

    for mode, path in LOCAL_FILES.items():
        for row in _records(path):
            if row.get("record_type") != "summary":
                continue
            granularity = _granularity(row)
            detector = str(row.get("algorithm"))
            feature = str(row.get("feature_set"))
            pooled_f1 = row.get("pooled_f1_1")
            if (
                granularity in GRANULARITIES
                and detector in DETECTORS
                and feature in FEATURES
                and pooled_f1 is not None
            ):
                values[(mode, feature, detector, granularity)] = float(pooled_f1)

    for mode, path in LLM_FILES.items():
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in _records(path):
            if row.get("record_type") != "repeat_metrics":
                continue
            granularity = _granularity(row)
            feature = str(row.get("feature_set"))
            if granularity in GRANULARITIES and feature in FEATURES:
                groups[(feature, granularity)].append(row)
        for (feature, granularity), rows in groups.items():
            if len(rows) != 5:
                raise ValueError(
                    f"Expected five GPT folds for {mode}/{feature}/{granularity}; "
                    f"found {len(rows)}"
                )
            values[(mode, feature, "GPT-5.4", granularity)] = _pooled_f1(rows)

    expected_local = {
        (mode, feature, detector, granularity)
        for mode in MODES
        for feature in FEATURES
        for detector in DETECTORS[1:]
        for granularity in GRANULARITIES
    }
    missing_local = sorted(expected_local - values.keys())
    if missing_local:
        raise ValueError(f"Missing local result cells: {missing_local}")

    expected_llm = {
        (mode, feature, "GPT-5.4", granularity)
        for mode in MODES
        for feature in FEATURES
        for granularity in ("Whole", "5 s")
    }
    missing_llm = sorted(expected_llm - values.keys())
    if missing_llm:
        raise ValueError(f"Missing GPT result cells: {missing_llm}")

    return values


def render_feature(
    values: dict[tuple[str, str, str, str], float], feature: str
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 9,
            "axes.titlesize": 11,
            "figure.facecolor": "#f7f4ed",
            "axes.facecolor": "#f7f4ed",
        }
    )
    cmap = LinearSegmentedColormap.from_list(
        "security_f1", ("#b74b3f", "#e5c46b", "#0f6b63")
    )
    cmap.set_bad("#d8d5ce")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    image = None
    for mode_index, mode in enumerate(MODES):
        ax = axes[mode_index]
        matrix = np.full((len(DETECTORS), len(GRANULARITIES)), np.nan)
        for detector_index, detector in enumerate(DETECTORS):
            for granularity_index, granularity in enumerate(GRANULARITIES):
                matrix[detector_index, granularity_index] = values.get(
                    (mode, feature, detector, granularity), np.nan
                )

        image = ax.imshow(matrix, cmap=cmap, vmin=0.20, vmax=0.95, aspect="auto")
        for detector_index in range(len(DETECTORS)):
            for granularity_index in range(len(GRANULARITIES)):
                value = matrix[detector_index, granularity_index]
                label = "not run" if np.isnan(value) else f"{100 * value:.1f}"
                color = "#5b5852" if np.isnan(value) else (
                    "white" if value < 0.38 or value > 0.86 else "#1e2927"
                )
                ax.text(
                    granularity_index,
                    detector_index,
                    label,
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=8.3,
                    fontweight="bold" if not np.isnan(value) else "normal",
                )

        ax.axhline(0.5, color="#282725", linewidth=1.2)
        ax.set_xticks(range(len(GRANULARITIES)), GRANULARITIES)
        ax.set_yticks(range(len(DETECTORS)), DETECTORS)
        ax.set_xlabel("Nominal time horizon (decreasing left to right)")
        ax.set_title(f"{mode.capitalize()} evaluation")
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_color("#827d73")
            spine.set_linewidth(0.7)

    feature_label = {
        "minimal": "Minimal features (5)",
        "mercury": "Mercury-style features (20)",
        "combined": "Combined features (25)",
    }[feature]
    fig.suptitle(
        f"{feature_label}: capture-disjoint F1 by context granularity",
        fontsize=16,
        fontweight="bold",
        color="#173b38",
        y=1.16,
    )
    fig.text(
        0.5,
        1.075,
        "Pooled confusion-count F1 (%). Window duration decreases left to right; grey GPT cells were not executed.",
        ha="center",
        fontsize=9.5,
        color="#4b4a46",
    )
    if image is None:
        raise RuntimeError("No chart panels were rendered")
    colorbar = fig.colorbar(image, ax=axes, shrink=0.80, pad=0.018)
    colorbar.set_label("Pooled malicious F1")
    colorbar.set_ticks([0.2, 0.4, 0.6, 0.8, 0.95])

    FIGURES.mkdir(parents=True, exist_ok=True)
    png_path = FIGURES / f"session_granularity_{feature}.png"
    pdf_path = FIGURES / f"session_granularity_{feature}.pdf"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")


def main() -> None:
    values = collect_values()
    for feature in FEATURES:
        render_feature(values, feature)


if __name__ == "__main__":
    main()
