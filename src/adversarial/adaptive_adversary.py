#!/usr/bin/env python3
"""
Experiment 5E: Adaptive Adversary with Query Feedback.

Measures the COST TO EVADE each classifier in terms of queries — the
fundamental practical asymmetry between classical ML and LLM defenses.

Classifiers
-----------
CART   — white-box tree-path evasion.  Adaptive simulation: binary-search
          each feature's threshold without tree access, then evade.
          Realistic query cost: O(n_features × log₂(IQR / precision)) ≈ 50 queries.

KNN    — gradient-free distance push.  Adaptive simulation: probe ±steps
          per feature to map local decision boundary, then push toward
          nearest normal region.

LLM    — coordinate hill climbing with confidence feedback.
          Each query costs ~$0.003 and ~1s.  The query budget is the
          primary defense cost metric.

KEY METRIC: queries_to_evasion — number of classifier queries needed
to successfully flip a malicious sample to "normal".  Higher = harder to evade.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# CART Adaptive Attack (query-only simulation)
# ─────────────────────────────────────────────────────────────────────────────

def adaptive_cart_attack(x_malicious: np.ndarray,
                          cart_query_fn,
                          threat_model: ThreatModel,
                          epsilon: float,
                          binary_search_steps: int = 8) -> dict:
    """
    Simulate an adaptive attacker against CART using only query feedback.

    Strategy — binary search per feature to locate decision boundary:
      For each feature f (independently):
        1. Probe current x (1 query, shared).
        2. Try x with f increased by max_delta[f] (1 query).
        3. Binary search in [x[f], x[f] + max_delta[f]] for the threshold
           that flips the classification (binary_search_steps queries per feature).
        4. Once thresholds located, attempt evasion using the findings.

    NOTE: True CART evasion (Exp 5A) uses white-box tree access = 1 effective
    query.  This simulation adds realistic per-feature probing cost.

    Parameters
    ----------
    x_malicious          : shape (5,) raw feature vector (ground-truth malicious)
    cart_query_fn        : callable(x_raw: np.ndarray) → int  (0 or 1)
    threat_model         : ThreatModel
    epsilon              : perturbation budget
    binary_search_steps  : probing resolution per feature

    Returns
    -------
    {
      "evaded":       bool,
      "queries_used": int,
      "best_perturbation": np.ndarray or None,
    }
    """
    max_delta_arr = threat_model.get_max_delta_array(epsilon)
    x_orig = x_malicious.astype(float)
    queries_used = 0

    # Initial classification (1 query)
    pred = int(cart_query_fn(x_orig))
    queries_used += 1
    if pred == 0:
        return {"evaded": True, "queries_used": queries_used,
                "best_perturbation": x_orig.copy()}

    # For each feature, probe positive and negative directions
    # to find which direction pushes toward "normal"
    direction = np.zeros(len(x_orig))

    for f in range(len(x_orig)):
        # payload_ratio (f=2) is always recomputed from Ps/PAs by
        # enforce_constraints — probing it directly has no effect.
        if f == 2:
            continue

        # Try +delta
        x_pos = x_orig.copy()
        x_pos[f] = x_orig[f] + max_delta_arr[f]
        x_pos = threat_model.enforce_constraints(x_pos)
        if threat_model.within_budget(x_orig, x_pos, epsilon):
            pred_pos = int(cart_query_fn(x_pos))
            queries_used += 1
            if pred_pos == 0:
                return {"evaded": True, "queries_used": queries_used,
                        "best_perturbation": x_pos}

        # Try −delta
        x_neg = x_orig.copy()
        x_neg[f] = x_orig[f] - max_delta_arr[f]
        x_neg = threat_model.enforce_constraints(x_neg)
        if threat_model.within_budget(x_orig, x_neg, epsilon):
            pred_neg = int(cart_query_fn(x_neg))
            queries_used += 1
            if pred_neg == 0:
                return {"evaded": True, "queries_used": queries_used,
                        "best_perturbation": x_neg}

        # Binary search: find threshold in [x_orig[f], x_orig[f] + max_delta[f]]
        # where the classification flips
        lo_f = x_orig[f]
        hi_f = x_orig[f] + max_delta_arr[f]

        for _ in range(binary_search_steps):
            mid_f = (lo_f + hi_f) / 2
            x_probe = x_orig.copy()
            x_probe[f] = mid_f
            x_probe = threat_model.enforce_constraints(x_probe)
            pred_probe = int(cart_query_fn(x_probe))
            queries_used += 1
            if pred_probe == 0:
                return {"evaded": True, "queries_used": queries_used,
                        "best_perturbation": x_probe}
            # Narrow the search: assume monotone response per feature
            if pred_probe == pred:
                lo_f = mid_f
            else:
                hi_f = mid_f

    return {"evaded": False, "queries_used": queries_used,
            "best_perturbation": None}


# ─────────────────────────────────────────────────────────────────────────────
# LLM Adaptive Attack
# ─────────────────────────────────────────────────────────────────────────────

def adaptive_llm_attack(x_malicious: np.ndarray,
                         llm_classify_conf_fn,
                         threat_model: ThreatModel,
                         epsilon: float,
                         query_budget: int = 50,
                         step_fractions: tuple = (0.1, 0.25, 0.5, 1.0),
                         rng: np.random.Generator = None) -> dict:
    """
    Adaptive adversary against the LLM using a two-phase strategy.

    Phase 1 — Coordinate descent with confidence signal (uses up to
    query_budget // 2 queries):
      Try ±step for each feature, keep moves that reduce malicious confidence.
      Escalate step size on stall.

    Phase 2 — Random restarts (remaining budget):
      If coordinate descent stalls, try random perturbations from the current
      best point to escape local optima.

    The optimization_trace records every query for post-hoc analysis.

    Parameters
    ----------
    x_malicious          : shape (5,) raw feature vector
    llm_classify_conf_fn : callable(x_raw) → (int prediction, float confidence)
                           confidence ∈ [0, 1] for malicious class
    threat_model         : ThreatModel
    epsilon              : perturbation budget
    query_budget         : maximum LLM API calls
    step_fractions       : step sizes as fractions of max_delta (tried in order)
    rng                  : optional numpy RNG

    Returns
    -------
    {
      "evaded":             bool,
      "queries_used":       int,
      "best_perturbation":  np.ndarray or None,
      "perturbation_cost":  {"l2": float, "linf": float},
      "optimization_trace": list[dict],
    }
    """
    if rng is None:
        rng = np.random.default_rng()

    max_delta_arr = threat_model.get_max_delta_array(epsilon)
    x_orig = x_malicious.astype(float)
    x_best = x_orig.copy()
    queries_used = 0
    trace: list[dict] = []

    def _query(x: np.ndarray) -> tuple[int, float]:
        nonlocal queries_used
        pred, conf = llm_classify_conf_fn(x)
        queries_used += 1
        trace.append({"query": queries_used, "pred": int(pred),
                       "conf": float(conf)})
        return int(pred), float(conf)

    def _project(x: np.ndarray) -> np.ndarray:
        """Clamp to budget and enforce physical constraints."""
        per_delta = np.clip(x - x_orig, -max_delta_arr, max_delta_arr)
        return threat_model.enforce_constraints(x_orig + per_delta)

    # Initial evaluation
    pred0, conf0 = _query(x_best)
    if pred0 == 0:
        return {"evaded": True, "queries_used": queries_used,
                "best_perturbation": x_best,
                "perturbation_cost": {"l2": 0.0, "linf": 0.0},
                "optimization_trace": trace}

    best_conf = conf0
    coord_budget = query_budget // 2  # reserve half for random restarts

    # ── Phase 1: Coordinate descent ──────────────────────────────────────────
    for step_frac in step_fractions:
        if queries_used >= coord_budget:
            break
        step = step_frac * max_delta_arr

        improved = True
        while improved and queries_used < coord_budget:
            improved = False
            for f in range(len(x_orig)):
                if queries_used >= coord_budget:
                    break
                # payload_ratio (f=2) is always recomputed by _project —
                # probing it directly has no effect.
                if f == 2:
                    continue
                for sign in (+1.0, -1.0):
                    x_trial = x_best.copy()
                    x_trial[f] += sign * step[f]
                    x_trial = _project(x_trial)

                    pred_t, conf_t = _query(x_trial)
                    if pred_t == 0:
                        dist = threat_model.perturbation_distance(x_orig, x_trial)
                        return {
                            "evaded": True,
                            "queries_used": queries_used,
                            "best_perturbation": x_trial,
                            "perturbation_cost": {"l2": dist["l2"], "linf": dist["linf"]},
                            "optimization_trace": trace,
                        }
                    if conf_t < best_conf:
                        best_conf = conf_t
                        x_best = x_trial.copy()
                        improved = True

    # ── Phase 2: Random restarts from current best ────────────────────────────
    while queries_used < query_budget:
        delta = rng.uniform(-max_delta_arr, max_delta_arr)
        x_rand = _project(x_best + delta)
        pred_r, conf_r = _query(x_rand)
        if pred_r == 0:
            dist = threat_model.perturbation_distance(x_orig, x_rand)
            return {
                "evaded": True,
                "queries_used": queries_used,
                "best_perturbation": x_rand,
                "perturbation_cost": {"l2": dist["l2"], "linf": dist["linf"]},
                "optimization_trace": trace,
            }
        if conf_r < best_conf:
            best_conf = conf_r
            x_best = x_rand.copy()

    return {
        "evaded": False,
        "queries_used": queries_used,
        "best_perturbation": None,
        "perturbation_cost": {"l2": 0.0, "linf": 0.0},
        "optimization_trace": trace,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Utility
# ─────────────────────────────────────────────────────────────────────────────

def compare_query_complexity(results_cart: list[dict],
                              results_knn:  list[dict],
                              results_llm:  list[dict],
                              cost_per_llm_query_usd: float = 0.003) -> dict:
    """
    Compare query complexity to evasion across all classifiers.

    For each classifier, compute:
      - Evasion rate (fraction of samples successfully evaded within budget)
      - Median / mean queries-to-evasion (over SUCCESSFUL evasions only)
      - Estimated cost per evasion (LLM only, in USD)

    Parameters
    ----------
    results_cart, results_knn, results_llm : lists of per-sample result dicts,
        each with keys "evaded" (bool) and "queries_used" (int).
    cost_per_llm_query_usd : API cost per LLM call (for cost estimation)

    Returns
    -------
    dict suitable for tabulate() display.
    """
    def _stats(results: list[dict]) -> dict:
        n = len(results)
        if n == 0:
            return {"evasion_rate": 0.0, "median_q": None,
                    "mean_q": None, "n_evaded": 0}
        n_evaded = sum(r["evaded"] for r in results)
        evasion_rate = n_evaded / n
        q_evaded = [r["queries_used"] for r in results if r["evaded"]]
        median_q = float(np.median(q_evaded)) if q_evaded else None
        mean_q   = float(np.mean(q_evaded))   if q_evaded else None
        return {
            "evasion_rate": evasion_rate,
            "n_evaded":     n_evaded,
            "n_total":      n,
            "median_q":     median_q,
            "mean_q":       mean_q,
        }

    cart_s = _stats(results_cart)
    knn_s  = _stats(results_knn)
    llm_s  = _stats(results_llm)

    # LLM cost estimate
    llm_cost = None
    if llm_s["mean_q"] is not None and llm_s["n_evaded"] > 0:
        llm_cost = round(llm_s["mean_q"] * cost_per_llm_query_usd, 4)

    return {
        "CART": {**cart_s, "cost_usd_per_evasion": "~0 (CPU)"},
        "KNN":  {**knn_s,  "cost_usd_per_evasion": "~0 (CPU)"},
        "LLM":  {**llm_s,  "cost_usd_per_evasion": f"${llm_cost:.4f}" if llm_cost else "N/A"},
    }
