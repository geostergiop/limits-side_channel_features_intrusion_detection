#!/usr/bin/env python3
"""
Experiment 5C: Black-Box LLM Evasion via Query-Based Search.

Strategies
----------
1. Random Search      — uniform sampling within ε budget, first evasion wins.
2. Coordinate Hill-Climbing — try ±step per feature; keep steps that succeed or
   that reduce malicious-confidence; escalate step size on stalls.
3. Transfer Attack    — evaluate CART/KNN adversarial samples directly on LLM;
   measures transferability without additional LLM queries.

LLM interface
-------------
llm_classify_fn(x_raw) → int               (0 = normal, 1 = malicious)
llm_classify_conf_fn(x_raw) → (int, float) (prediction, confidence)

Both are constructed from LLMClient + format_packet_features in evaluate.py.

Rate-limit note
---------------
Every call to llm_classify_fn costs one API call.  The query_budget param
is a hard cap per sample; callers should pass budgets from ADV_CONFIG.
"""

import sys
import hashlib
import json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1 — Random Search
# ─────────────────────────────────────────────────────────────────────────────

def random_search_evasion(x_malicious: np.ndarray,
                           threat_model: ThreatModel,
                           llm_classify_fn,
                           epsilon: float,
                           max_queries: int = 20,
                           rng: np.random.Generator = None) -> dict:
    """
    Try random perturbations within the ε budget against the LLM.

    For each attempt:
      1. Sample uniform Δ[f] ∈ [−max_delta[f], +max_delta[f]] per feature.
      2. Add to x_malicious.
      3. Enforce physical constraints.
      4. Query LLM.
      5. Return first sample that gets classified as normal.

    Parameters
    ----------
    x_malicious      : shape (5,) raw feature vector (ground-truth malicious)
    threat_model     : ThreatModel
    llm_classify_fn  : callable(x_raw: np.ndarray) → int
    epsilon          : perturbation budget
    max_queries      : maximum number of LLM API calls
    rng              : optional numpy RNG for reproducibility

    Returns
    -------
    {
      "evaded":             bool,
      "queries_used":       int,
      "best_perturbation":  np.ndarray or None (raw adversarial features),
      "perturbation_cost":  {"l2": float, "linf": float},
    }
    """
    if rng is None:
        rng = np.random.default_rng()

    max_delta_arr = threat_model.get_max_delta_array(epsilon)
    x_orig = x_malicious.astype(float)

    best_perturbation = None
    queries_used = 0

    for _ in range(max_queries):
        delta = rng.uniform(-max_delta_arr, max_delta_arr)
        x_cand = threat_model.enforce_constraints(x_orig + delta)

        # Enforce budget after constraint adjustment
        if not threat_model.within_budget(x_orig, x_cand, epsilon):
            # Reproject: clamp each feature to budget
            per_delta = np.clip(x_cand - x_orig, -max_delta_arr, max_delta_arr)
            x_cand = threat_model.enforce_constraints(x_orig + per_delta)

        queries_used += 1
        pred = int(llm_classify_fn(x_cand))

        if pred == 0:
            best_perturbation = x_cand
            dist = threat_model.perturbation_distance(x_orig, x_cand)
            return {
                "evaded":            True,
                "queries_used":      queries_used,
                "best_perturbation": best_perturbation,
                "perturbation_cost": {"l2": dist["l2"], "linf": dist["linf"]},
            }

    return {
        "evaded":            False,
        "queries_used":      queries_used,
        "best_perturbation": None,
        "perturbation_cost": {"l2": 0.0, "linf": 0.0},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2 — Coordinate-Wise Hill Climbing
# ─────────────────────────────────────────────────────────────────────────────

def hill_climbing_evasion(x_malicious: np.ndarray,
                           threat_model: ThreatModel,
                           llm_classify_conf_fn,
                           epsilon: float,
                           max_queries: int = 30,
                           step_fraction: float = 0.1) -> dict:
    """
    Coordinate-wise hill climbing against the LLM.

    The LLM returns (prediction, confidence).  Confidence drives the search:
    we seek to minimise the malicious-class confidence, treating it as a
    noisy surrogate gradient.

    Each iteration sweeps all 5 features (±step each).  We keep the trial
    that achieves the lowest malicious confidence.  Step size doubles when
    no improvement is found in a full sweep (escape local optima).

    Parameters
    ----------
    x_malicious          : shape (5,) raw feature vector
    threat_model         : ThreatModel
    llm_classify_conf_fn : callable(x_raw) → (int, float)
                           returns (prediction, malicious_confidence)
    epsilon              : perturbation budget
    max_queries          : hard query budget
    step_fraction        : initial step as fraction of max_delta per feature

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
    max_delta_arr = threat_model.get_max_delta_array(epsilon)
    x_orig = x_malicious.astype(float)
    x_curr = x_orig.copy()

    # Initial confidence (costs 1 query)
    pred_curr, conf_curr = llm_classify_conf_fn(x_curr)
    queries_used = 1
    trace = [{"query": 1, "pred": pred_curr, "conf": conf_curr, "step": None}]

    if pred_curr == 0:
        return {
            "evaded": True, "queries_used": queries_used,
            "best_perturbation": x_curr,
            "perturbation_cost": {"l2": 0.0, "linf": 0.0},
            "optimization_trace": trace,
        }

    # Per-feature step size (starts at step_fraction × budget)
    step = step_fraction * max_delta_arr
    n_features = len(x_orig)
    best_x = x_curr.copy()
    best_conf = conf_curr

    stall_rounds = 0
    max_step_doublings = 4

    while queries_used < max_queries:
        improved_this_round = False

        for f in range(n_features):
            if queries_used >= max_queries:
                break

            for sign in (+1.0, -1.0):
                if queries_used >= max_queries:
                    break

                x_trial = x_curr.copy()
                x_trial[f] = x_curr[f] + sign * step[f]

                # Budget clamp from x_orig
                x_trial[f] = np.clip(
                    x_trial[f],
                    x_orig[f] - max_delta_arr[f],
                    x_orig[f] + max_delta_arr[f],
                )
                x_trial = threat_model.enforce_constraints(x_trial)

                # After constraint enforcement, re-check budget
                if not threat_model.within_budget(x_orig, x_trial, epsilon):
                    continue

                pred_t, conf_t = llm_classify_conf_fn(x_trial)
                queries_used += 1
                trace.append({
                    "query": queries_used, "pred": pred_t,
                    "conf": conf_t, "step": {"feature": f, "sign": sign},
                })

                if pred_t == 0:
                    dist = threat_model.perturbation_distance(x_orig, x_trial)
                    return {
                        "evaded": True,
                        "queries_used": queries_used,
                        "best_perturbation": x_trial,
                        "perturbation_cost": {"l2": dist["l2"], "linf": dist["linf"]},
                        "optimization_trace": trace,
                    }

                # Use conf_t as score (lower malicious confidence = better)
                if conf_t < best_conf:
                    best_conf = conf_t
                    best_x = x_trial.copy()
                    improved_this_round = True

        if improved_this_round:
            x_curr = best_x.copy()
            stall_rounds = 0
        else:
            stall_rounds += 1
            if stall_rounds <= max_step_doublings:
                step = np.minimum(step * 2.0, max_delta_arr)
            else:
                break  # give up — no gradient signal

    return {
        "evaded": False,
        "queries_used": queries_used,
        "best_perturbation": None,
        "perturbation_cost": {"l2": 0.0, "linf": 0.0},
        "optimization_trace": trace,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 3 — Transfer Attack Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def transfer_attack_evaluation(X_cart_adversarial: np.ndarray,
                                X_knn_adversarial: np.ndarray,
                                llm_classify_fn,
                                y_true: np.ndarray) -> dict:
    """
    Evaluate transferability of CART- and KNN-crafted adversarial samples
    against the LLM.  No additional search queries — just a forward pass.

    A "transfer" occurs when an adversarial sample crafted for Model A also
    fools Model B (the LLM in this case).

    Low LLM transfer rate → evidence of LLM robustness against classical attacks.
    High LLM transfer rate → LLM equally vulnerable to simple perturbations.

    Parameters
    ----------
    X_cart_adversarial : (n_cart, 5) raw adversarial features from Exp 5A
    X_knn_adversarial  : (n_knn,  5) raw adversarial features from Exp 5B
    llm_classify_fn    : callable(x_raw) → int
    y_true             : (n,) ground-truth labels (should all be 1 = malicious)

    Returns
    -------
    {
      "cart_transfer_rate":   float,  — % of CART-adversarial that fool LLM
      "knn_transfer_rate":    float,  — % of KNN-adversarial that fool LLM
      "cart_llm_predictions": list[int],
      "knn_llm_predictions":  list[int],
    }
    """
    cart_preds: list[int] = []
    for x in X_cart_adversarial:
        cart_preds.append(int(llm_classify_fn(x)))

    knn_preds: list[int] = []
    for x in X_knn_adversarial:
        knn_preds.append(int(llm_classify_fn(x)))

    cart_arr = np.array(cart_preds, dtype=int)
    knn_arr  = np.array(knn_preds, dtype=int)

    cart_valid = cart_arr >= 0
    knn_valid = knn_arr >= 0

    # Transfer = LLM predicted 0 (normal) for a ground-truth malicious sample.
    # Invalid predictions (-1) are excluded from the rate denominator.
    cart_transfer = float((cart_arr[cart_valid] == 0).mean()) if np.any(cart_valid) else None
    knn_transfer  = float((knn_arr[knn_valid] == 0).mean()) if np.any(knn_valid) else None

    return {
        "cart_transfer_rate":   cart_transfer,
        "knn_transfer_rate":    knn_transfer,
        "cart_llm_predictions": cart_preds,
        "knn_llm_predictions":  knn_preds,
        "cart_valid_predictions": int(np.sum(cart_valid)),
        "cart_invalid_predictions": int(np.sum(~cart_valid)),
        "knn_valid_predictions": int(np.sum(knn_valid)),
        "knn_invalid_predictions": int(np.sum(~knn_valid)),
    }
