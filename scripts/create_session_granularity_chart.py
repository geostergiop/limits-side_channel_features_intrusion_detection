#!/usr/bin/env python3
"""Create README comparison charts from published Phase 7 summaries."""

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
PDF_METADATA = {
    "Creator": "scripts/create_session_granularity_chart.py",
    "CreationDate": None,
    "ModDate": None,
}

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
LLM_SUPPLEMENTAL_FILE = (
    PUBLISHED / "session_llm_author_supplied_window_sweep.summary.json"
)
INPUT_REQUIREMENTS_FILE = PUBLISHED / "session_input_requirements.summary.json"
PHASE4E_FILE = PUBLISHED / "phase4e_openai_session_windows.summary.json"
FEATURE_STYLES = {
    "minimal": {
        "label": "Minimal (5)",
        "color": "#1c6b70",
        "marker": "o",
        "linestyle": "-",
    },
    "mercury": {
        "label": "Mercury-style (20)",
        "color": "#b5533c",
        "marker": "s",
        "linestyle": "--",
    },
    "combined": {
        "label": "Combined (25)",
        "color": "#8b6e1e",
        "marker": "^",
        "linestyle": "-.",
    },
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


def _cell_label(detector: str, granularity: str, value: float) -> str:
    if np.isnan(value):
        return "not run"
    suffix = (
        "*"
        if detector == "GPT-5.4" and granularity in ("30 s", "1 s")
        else ""
    )
    return f"{100 * value:.1f}{suffix}"


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

    supplemental_records = _records(LLM_SUPPLEMENTAL_FILE)
    for row in supplemental_records:
        if row.get("record_type") != "author_supplied_f1":
            raise ValueError("Unexpected supplemental GPT record type")
        mode = str(row.get("evaluation_mode"))
        feature = str(row.get("feature_set"))
        granularity = _granularity(row)
        model = str(row.get("model"))
        value = float(row["reported_f1_1"])
        key = (mode, feature, model, granularity)
        if (
            mode not in MODES
            or feature not in FEATURES
            or model != "GPT-5.4"
            or granularity not in ("30 s", "1 s")
            or not 0.0 <= value <= 1.0
        ):
            raise ValueError(f"Invalid supplemental GPT record: {row}")
        if key in values:
            raise ValueError(
                f"Supplemental GPT record duplicates archived result: {key}"
            )
        values[key] = value

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
        for granularity in GRANULARITIES
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
                detector = DETECTORS[detector_index]
                granularity = GRANULARITIES[granularity_index]
                value = matrix[detector_index, granularity_index]
                label = _cell_label(detector, granularity, value)
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
        ax.set_xlabel("Full-session representation (finer bins to right)")
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
        f"{feature_label}: capture-disjoint F1 by full-session representation",
        fontsize=16,
        fontweight="bold",
        color="#173b38",
        y=1.16,
    )
    fig.text(
        0.5,
        1.075,
        "All representations cover complete sessions; 30/5/1 s denote behavior-bin "
        "widths. *30/1 s GPT values are author-supplied F1-only results.",
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
    fig.savefig(pdf_path, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)
    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")


def render_llm_degradation(
    values: dict[tuple[str, str, str, str], float],
) -> None:
    """Render GPT serialization-sensitivity curves for both protocols."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 9,
            "axes.titlesize": 11,
            "figure.facecolor": "#fbfaf7",
            "axes.facecolor": "#fbfaf7",
        }
    )
    label_offsets = {
        "balanced": {"minimal": -13, "mercury": 9, "combined": 9},
        "deployment": {"minimal": 9, "mercury": -14, "combined": 9},
    }
    x = np.arange(len(GRANULARITIES))
    x_labels = ("Whole\nsession", "30 s", "5 s", "1 s")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.7), sharey=True)
    fig.subplots_adjust(
        left=0.075,
        right=0.985,
        bottom=0.14,
        top=0.72,
        wspace=0.045,
    )
    handles = []
    for mode_index, mode in enumerate(MODES):
        ax = axes[mode_index]
        for feature in FEATURES:
            style = FEATURE_STYLES[feature]
            series = np.array(
                [
                    100 * values[(mode, feature, "GPT-5.4", granularity)]
                    for granularity in GRANULARITIES
                ]
            )
            line = ax.plot(
                x,
                series,
                color=style["color"],
                marker=style["marker"],
                linestyle=style["linestyle"],
                linewidth=2.4,
                markersize=6.5,
                markeredgecolor="#fbfaf7",
                markeredgewidth=0.8,
                label=style["label"],
            )[0]
            if mode_index == 0:
                handles.append(line)

            for point_index, value in enumerate(series):
                granularity = GRANULARITIES[point_index]
                suffix = "*" if granularity in ("30 s", "1 s") else ""
                ax.annotate(
                    f"{value:.1f}{suffix}",
                    (point_index, value),
                    xytext=(0, label_offsets[mode][feature]),
                    textcoords="offset points",
                    ha="center",
                    va="center",
                    fontsize=8.2,
                    fontweight="bold",
                    color=style["color"],
                    bbox={
                        "boxstyle": "round,pad=0.16",
                        "facecolor": "#fbfaf7",
                        "edgecolor": "none",
                        "alpha": 0.78,
                    },
                )

        losses = [
            100
            * (
                values[(mode, feature, "GPT-5.4", "Whole")]
                - values[(mode, feature, "GPT-5.4", "1 s")]
            )
            for feature in FEATURES
        ]
        ax.text(
            0.02,
            0.035,
            "Whole encoding to 1 s-bin loss: "
            f"Minimal {losses[0]:.1f} pp | Mercury {losses[1]:.1f} pp | "
            f"Combined {losses[2]:.1f} pp",
            transform=ax.transAxes,
            fontsize=8.2,
            color="#3f423f",
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "#eeece5",
                "edgecolor": "#c7c2b7",
                "linewidth": 0.7,
            },
        )
        ax.set_xticks(x, x_labels)
        ax.set_xlim(-0.15, len(GRANULARITIES) - 0.85)
        ax.set_ylim(0, 100)
        ax.set_yticks(np.arange(0, 101, 20))
        ax.grid(axis="y", color="#d6d2c9", linewidth=0.7, alpha=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel("Full-session representation (finer bins to right)")
        ax.set_title(
            "Balanced evaluation (50.00% malicious)"
            if mode == "balanced"
            else "Deployment GPT subset (49.36% malicious)"
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#827d73")
        ax.spines["bottom"].set_color("#827d73")
        ax.tick_params(length=0, color="#827d73")

    axes[0].set_ylabel("Malicious-class F1 (%)")
    fig.suptitle(
        "GPT-5.4 F1 across complete-session encodings",
        fontsize=16,
        fontweight="bold",
        color="#173b38",
        y=0.965,
    )
    fig.text(
        0.5,
        0.91,
        "Every point covers the complete session; 30/5/1 s denote bin widths, "
        "not capture prefixes. *Author-supplied F1-only result.",
        ha="center",
        fontsize=9.4,
        color="#4b4a46",
    )
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.865),
        ncol=3,
        frameon=False,
        handlelength=3.0,
        columnspacing=2.2,
    )

    FIGURES.mkdir(parents=True, exist_ok=True)
    png_path = FIGURES / "session_llm_context_degradation.png"
    pdf_path = FIGURES / "session_llm_context_degradation.pdf"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)
    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")


def render_production_input_tradeoff() -> None:
    """Render projected prefix input growth beside Phase 4E prefix evidence."""
    requirements = json.loads(INPUT_REQUIREMENTS_FILE.read_text(encoding="utf-8"))
    phase4e = json.loads(PHASE4E_FILE.read_text(encoding="utf-8"))
    projection = requirements["production_prefix_projection"]
    if projection["status"] != "data_volume_projection_not_detector_accuracy_experiment":
        raise ValueError("Unexpected production-prefix projection status")

    raw_by_context = {
        row["context"]: row for row in projection["raw_context_records"]
    }
    value_by_key = {
        (row["feature_set"], row["context"]): float(
            row["numeric_metadata_values"]["mean"]
        )
        for row in projection["feature_records"]
    }
    contexts = ("1 s", "5 s", "30 s", "Whole")
    x = np.arange(len(contexts))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 9,
            "axes.titlesize": 11,
            "figure.facecolor": "#fbfaf7",
            "axes.facecolor": "#fbfaf7",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.7))
    fig.subplots_adjust(
        left=0.07,
        right=0.985,
        bottom=0.17,
        top=0.72,
        wspace=0.17,
    )

    ax = axes[0]
    for feature in FEATURES:
        style = FEATURE_STYLES[feature]
        series = np.asarray(
            [value_by_key[(feature, context)] for context in contexts], dtype=float
        )
        ax.plot(
            x,
            series,
            color=style["color"],
            marker=style["marker"],
            linestyle=style["linestyle"],
            linewidth=2.4,
            markersize=6.5,
            markeredgecolor="#fbfaf7",
            markeredgewidth=0.8,
            label=style["label"],
        )
        for point_index, value in enumerate(series):
            ax.annotate(
                f"{value:.1f}",
                (point_index, value),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8.1,
                fontweight="bold",
                color=style["color"],
            )

    x_labels = []
    for context in contexts:
        raw = raw_by_context[context]
        mean_packets = float(raw["packet_count"]["mean"])
        mean_kib = float(raw["observed_wire_bytes"]["mean"]) / 1024.0
        x_labels.append(f"{context}\n{mean_packets:.1f} pkt / {mean_kib:.1f} KiB wire")
    ax.set_xticks(x, x_labels)
    ax.set_xlim(-0.15, len(contexts) - 0.85)
    ax.set_ylim(0, 175)
    ax.set_yticks(np.arange(0, 176, 25))
    ax.set_ylabel("Mean numeric metadata values per decision")
    ax.set_xlabel("Projected observation prefix (increasing left to right)")
    ax.set_title("Projected bounded-prefix input (6,000 sessions)")
    ax.grid(axis="y", color="#d6d2c9", linewidth=0.7, alpha=0.8)
    ax.legend(loc="upper left", frameon=False)
    ax.text(
        0.02,
        0.035,
        "Projection only: no Phase 7 F1 is assigned to these prefixes",
        transform=ax.transAxes,
        fontsize=8.1,
        color="#3f423f",
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "#eeece5",
            "edgecolor": "#c7c2b7",
            "linewidth": 0.7,
        },
    )

    ax = axes[1]
    phase4e_styles = {
        "accuracy": ("Accuracy", "#2a5c82", "o", "-"),
        "precision_1": ("Precision", "#b5533c", "s", "--"),
        "f1_1": ("F1", "#8b6e1e", "^", "-."),
    }
    if phase4e.get("protocol", {}).get("capture_disjoint") is not False:
        raise ValueError("Phase 4E chart requires the documented weaker protocol")
    phase4e_rows = sorted(phase4e["records"], key=lambda row: row["window_size_packets"])
    packet_windows = [int(row["window_size_packets"]) for row in phase4e_rows]
    if packet_windows != [5, 10, 20, 50]:
        raise ValueError(f"Unexpected Phase 4E packet prefixes: {packet_windows}")
    if any(float(row["recall_1"]) != 1.0 for row in phase4e_rows):
        raise ValueError("Phase 4E recall callout no longer matches source records")
    if [int(phase4e_rows[0]["fp"]), int(phase4e_rows[-1]["fp"])] != [8, 100]:
        raise ValueError("Phase 4E false-positive callout no longer matches records")
    phase_x = np.arange(len(packet_windows))
    for metric, (label, color, marker, linestyle) in phase4e_styles.items():
        series = np.asarray([100 * float(row[metric]) for row in phase4e_rows])
        ax.plot(
            phase_x,
            series,
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=2.4,
            markersize=6.5,
            markeredgecolor="#fbfaf7",
            markeredgewidth=0.8,
            label=label,
        )
        offset = {"accuracy": 19, "precision_1": -15, "f1_1": 4}[metric]
        for point_index, value in enumerate(series):
            ax.annotate(
                f"{value:.1f}",
                (point_index, value),
                xytext=(0, offset),
                textcoords="offset points",
                ha="center",
                fontsize=8.1,
                fontweight="bold",
                color=color,
            )
    ax.set_xticks(phase_x, [str(value) for value in packet_windows])
    ax.set_xlim(-0.15, len(packet_windows) - 0.85)
    ax.set_ylim(0, 105)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_ylabel("Held-out metric (%)")
    ax.set_xlabel("First N packets retained from each session")
    ax.set_title("Phase 4E packet-prefix evidence (weaker protocol)")
    ax.grid(axis="y", color="#d6d2c9", linewidth=0.7, alpha=0.8)
    ax.legend(loc="upper right", frameon=False)
    ax.text(
        0.02,
        0.035,
        "Recall = 100% throughout; false positives rise from 8 to 100",
        transform=ax.transAxes,
        fontsize=8.1,
        color="#3f423f",
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "#eeece5",
            "edgecolor": "#c7c2b7",
            "linewidth": 0.7,
        },
    )

    for ax in axes:
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#827d73")
        ax.spines["bottom"].set_color("#827d73")
        ax.tick_params(length=0, color="#827d73")

    fig.suptitle(
        "Production observation scope: input growth and prefix evidence",
        fontsize=16,
        fontweight="bold",
        color="#173b38",
        y=0.965,
    )
    fig.text(
        0.5,
        0.905,
        "Left: data-volume projection on the deployment cohort. Right: measured "
        "Phase 4E results. The protocols are not pooled.",
        ha="center",
        fontsize=9.4,
        color="#4b4a46",
    )

    FIGURES.mkdir(parents=True, exist_ok=True)
    png_path = FIGURES / "session_production_input_tradeoff.png"
    pdf_path = FIGURES / "session_production_input_tradeoff.pdf"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)
    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")


def main() -> None:
    values = collect_values()
    render_llm_degradation(values)
    render_production_input_tradeoff()
    for feature in FEATURES:
        render_feature(values, feature)


if __name__ == "__main__":
    main()
