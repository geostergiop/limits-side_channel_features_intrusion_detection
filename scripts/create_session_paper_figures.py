#!/usr/bin/env python3
"""Create compact USENIX-paper figures from frozen Session result artifacts."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

BLUE = "#1f4e79"
GOLD = "#c69214"
INK = "#20262e"
GRID = "#d8dde3"


def _load(name: str) -> list[dict]:
    with (RESULTS / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _unit_group(row: dict) -> str:
    return "packet" if row["sample_unit"] == "packet_ablation" else "session"


def _save(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _style_axis(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(INK)
    ax.tick_params(colors=INK, labelsize=7)
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)


def headline_figure(local_rows: list[dict], llm_rows: list[dict]) -> None:
    local = {}
    llm = {}
    for mode in ("balanced", "deployment"):
        for unit in ("session", "packet"):
            local[(mode, unit)] = max(
                row["f1_1"]
                for row in local_rows
                if row.get("record_type") == "summary"
                and row["evaluation_mode"] == mode
                and _unit_group(row) == unit
            )
            llm[(mode, unit)] = max(
                row["f1_1"]
                for row in llm_rows
                if row.get("record_type") == "summary"
                and row["evaluation_mode"] == mode
                and _unit_group(row) == unit
            )

    expected = {
        ("balanced", "session"): (0.8428, 0.6683),
        ("balanced", "packet"): (0.8204, 0.5601),
        ("deployment", "session"): (0.7917, 0.5725),
        ("deployment", "packet"): (0.8251, 0.5067),
    }
    for key, (expected_local, expected_llm) in expected.items():
        assert round(local[key], 4) == expected_local, (key, local[key])
        assert round(llm[key], 4) == expected_llm, (key, llm[key])

    keys = list(expected)
    labels = ["Balanced\nsession/window", "Balanced\npacket", "Deployment\nsession/window", "Deployment\npacket"]
    local_values = [100 * local[key] for key in keys]
    llm_values = [100 * llm[key] for key in keys]
    x = np.arange(len(labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(6.9, 2.45))
    local_bars = ax.bar(x - width / 2, local_values, width, color=BLUE, edgecolor=INK,
                        linewidth=0.5, label="Local ML", zorder=3)
    llm_bars = ax.bar(x + width / 2, llm_values, width, color=GOLD, edgecolor=INK,
                      linewidth=0.5, hatch="//", label="Prompted LLM", zorder=3)
    ax.set_ylabel("Best malicious-class $F_1$ (percent)", fontsize=8, color=INK)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper center")
    _style_axis(ax)
    for bars in (local_bars, llm_bars):
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=6.5, color=INK)
    fig.tight_layout()
    _save(fig, "session_headline_f1")


def family_figure(llm_rows: list[dict]) -> None:
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in llm_rows:
        if row.get("record_type") or row.get("ground_truth") != 1:
            continue
        key = (row["evaluation_mode"], row["malware_family"])
        counts[key][0] += int(row["prediction"] == 1)
        counts[key][1] += 1

    families = [
        "BitCoinMiner",
        "Dridex",
        "Hancitor",
        "TrojanDownloader",
        "Website_5.8.88.175",
    ]
    labels = [
        "BitCoinMiner",
        "Dridex",
        "Hancitor",
        "TrojanDownloader",
        "Website 5.8.88.175",
    ]
    expected_support = {
        ("balanced", "BitCoinMiner"): (109, 243),
        ("balanced", "Dridex"): (52, 162),
        ("balanced", "Hancitor"): (3, 12),
        ("balanced", "TrojanDownloader"): (103, 243),
        ("balanced", "Website_5.8.88.175"): (20, 171),
        ("deployment", "BitCoinMiner"): (76, 102),
        ("deployment", "Dridex"): (271, 321),
        ("deployment", "Hancitor"): (0, 0),
        ("deployment", "TrojanDownloader"): (15, 15),
        ("deployment", "Website_5.8.88.175"): (578, 852),
    }
    for key, expected in expected_support.items():
        assert tuple(counts[key]) == expected, (key, counts[key])

    balanced = [100 * counts[("balanced", family)][0] / counts[("balanced", family)][1]
                for family in families]
    deployment = [
        math.nan if counts[("deployment", family)][1] == 0
        else 100 * counts[("deployment", family)][0] / counts[("deployment", family)][1]
        for family in families
    ]
    y = np.arange(len(families))
    height = 0.36

    fig, ax = plt.subplots(figsize=(6.9, 2.7))
    bal_bars = ax.barh(y - height / 2, balanced, height, color=BLUE, edgecolor=INK,
                       linewidth=0.5, label="Balanced", zorder=3)
    dep_bars = ax.barh(y + height / 2, deployment, height, color=GOLD, edgecolor=INK,
                       linewidth=0.5, hatch="//", label="Deployment", zorder=3)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xlabel("Configuration-level malicious detection rate (percent)", fontsize=8, color=INK)
    ax.legend(frameon=False, fontsize=7, ncol=2, loc="upper right")
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=INK, labelsize=7)
    for index, bar in enumerate(bal_bars):
        support = counts[("balanced", families[index])][1]
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.1f} (n={support})", va="center", fontsize=6, color=INK)
    for index, bar in enumerate(dep_bars):
        support = counts[("deployment", families[index])][1]
        if support:
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                    f"{bar.get_width():.1f} (n={support})", va="center", fontsize=6, color=INK)
        else:
            ax.text(1, y[index] + height / 2, "not observed", va="center", fontsize=6,
                    color=INK, style="italic")
    fig.tight_layout()
    _save(fig, "session_llm_family_detection")


def runtime_figure(local_rows: list[dict], llm_rows: list[dict]) -> None:
    local = defaultdict(list)
    llm = defaultdict(list)
    for row in local_rows:
        if row.get("record_type") != "repeat":
            continue
        local[(row["evaluation_mode"], _unit_group(row))].append(
            1000 * row["predict_time_s"] / row["n_test_samples"]
        )
    for row in llm_rows:
        if row.get("record_type"):
            continue
        llm[(row["evaluation_mode"], _unit_group(row))].append(row["latency_ms"])

    keys = [
        ("balanced", "session"),
        ("balanced", "packet"),
        ("deployment", "session"),
        ("deployment", "packet"),
    ]
    local_values = [statistics.median(local[key]) for key in keys]
    llm_values = [statistics.median(llm[key]) for key in keys]
    expected_local = [0.002912, 0.002603, 0.002897, 0.002572]
    expected_llm = [1502.6, 1490.2, 1467.5, 1437.2]
    for actual, expected in zip(local_values, expected_local):
        assert abs(actual - expected) < 0.000001, (actual, expected)
    for actual, expected in zip(llm_values, expected_llm):
        assert abs(actual - expected) < 0.1, (actual, expected)

    labels = ["Balanced\nsession/window", "Balanced\npacket", "Deployment\nsession/window", "Deployment\npacket"]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(6.9, 2.7))
    ax.bar(x - width / 2, local_values, width, color=BLUE, edgecolor=INK,
           linewidth=0.5, label="Local ML", zorder=3)
    ax.bar(x + width / 2, llm_values, width, color=GOLD, edgecolor=INK,
           linewidth=0.5, hatch="//", label="Prompted LLM", zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(0.001, 10000)
    ax.set_ylabel("Median prediction latency (ms/sample, log scale)", fontsize=7.5, color=INK)
    ax.set_xticks(x, labels)
    ax.legend(frameon=False, fontsize=7, ncol=2, loc="center", bbox_to_anchor=(0.5, 0.43))
    _style_axis(ax)
    for index, (local_value, llm_value) in enumerate(zip(local_values, llm_values)):
        ax.text(index - width / 2, local_value * 1.4, f"{local_value:.4f}", ha="center",
                va="bottom", fontsize=5.8, color=INK, rotation=90)
        ax.text(index + width / 2, llm_value * 1.12, f"{llm_value:.0f}", ha="center",
                va="bottom", fontsize=6.2, color=INK)
    fig.tight_layout()
    _save(fig, "session_runtime_latency")


def main() -> None:
    local_rows = _load("session_local_results_balanced.json") + _load(
        "session_local_results_deployment.json"
    )
    llm_rows = _load("session_llm_results_balanced_paper_5k.json") + _load(
        "session_llm_results_deployment_paper_6k.json"
    )
    headline_figure(local_rows, llm_rows)
    family_figure(llm_rows)
    runtime_figure(local_rows, llm_rows)
    print("Wrote Session paper figures to", FIGURES)


if __name__ == "__main__":
    main()
