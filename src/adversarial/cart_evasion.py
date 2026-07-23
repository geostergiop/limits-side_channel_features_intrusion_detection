#!/usr/bin/env python3
"""
Experiment 5A: White-Box CART Evasion.

Strategy
--------
1. Extract every root-to-leaf path from the fitted DecisionTreeClassifier.
2. For each malicious sample, find the NORMAL leaf reachable with the
   minimum L2 perturbation in SCALED feature space.
3. Unscale the adversarial sample back to raw space.
4. Clamp per-feature deltas to the ε budget (raw IQR-based).
5. Enforce physical constraints (coupling: payload_ratio is recomputed).
6. Re-scale and re-classify to confirm evasion.

Key design note
---------------
The sklearn tree stores thresholds in SCALED feature space (the tree was
trained on StandardScaler-transformed data).  Path analysis therefore
operates in scaled space; budget checks and physical constraints are
applied in raw space after inverse-transforming the adversarial point.
"""

import sys
from pathlib import Path

import numpy as np
from sklearn.tree import _tree

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES


# Sentinel used by sklearn for leaf nodes
_LEAF_FLAG = _tree.TREE_UNDEFINED  # == -2


def extract_tree_paths(tree_model) -> list[dict]:
    """
    DFS enumeration of all root-to-leaf paths in a fitted
    DecisionTreeClassifier.

    Returns a list of dicts, one per leaf:
      {
        "leaf_node":    int   — sklearn node index,
        "leaf_class":   int   — predicted class (0=normal, 1=malicious),
        "leaf_samples": int   — training samples reaching this leaf,
        "path":         list  — [(feature_idx, threshold, "left"|"right"), ...]
      }

    Left branch:  feature[node] <= threshold
    Right branch: feature[node] >  threshold
    """
    tree = tree_model.tree_
    paths: list[dict] = []

    def _dfs(node: int, path: list) -> None:
        if tree.feature[node] == _LEAF_FLAG:  # leaf
            # tree.value shape: (n_outputs=1, n_classes)
            leaf_class = int(np.argmax(tree.value[node][0]))
            paths.append({
                "leaf_node":    node,
                "leaf_class":   leaf_class,
                "leaf_samples": int(tree.n_node_samples[node]),
                "path":         list(path),  # copy — path is mutated by caller
            })
            return

        feat   = int(tree.feature[node])
        thresh = float(tree.threshold[node])

        path.append((feat, thresh, "left"))       # feature <= threshold
        _dfs(tree.children_left[node], path)
        path.pop()

        path.append((feat, thresh, "right"))      # feature > threshold
        _dfs(tree.children_right[node], path)
        path.pop()

    _dfs(0, [])
    return paths


def find_evasion_path(tree_model, x_scaled: np.ndarray) -> dict | None:
    """
    Find the minimum-cost perturbation (in SCALED space) to move a sample
    from its current leaf to the nearest NORMAL leaf.

    Algorithm
    ---------
    For each normal (class-0) leaf, compute the required feature ranges
    along the path:
        lo[f] < x[f] <= hi[f]
    where the lower bound is strict (right splits: x > thresh) and the
    upper bound is inclusive (left splits: x <= thresh).

    The minimum change to put x into the feasible region is computed
    per-feature independently, then summed as L2 cost.

    Returns
    -------
    dict with keys:
        "target_leaf":          leaf node index
        "x_adversarial":        np.ndarray (5,) in SCALED space
        "required_perturbations": {feat_idx: delta, ...}
        "perturbation_cost_l2": float
        "perturbation_cost_linf": float
        "n_features_changed":   int
    None if no normal leaf is reachable (e.g., sample is already normal or
    the tree has no normal leaves).
    """
    n_features = len(x_scaled)
    paths = extract_tree_paths(tree_model)

    best: dict | None = None
    best_cost = float("inf")

    for path_info in paths:
        if path_info["leaf_class"] != 0:
            continue  # only consider normal leaves

        # Required range for each feature: lo[f] < x[f] <= hi[f]
        lo = np.full(n_features, -np.inf)
        hi = np.full(n_features, np.inf)
        feasible = True

        for (feat, thresh, direction) in path_info["path"]:
            if direction == "left":              # x[feat] <= thresh
                hi[feat] = min(hi[feat], thresh)
            else:                                # x[feat] >  thresh
                lo[feat] = max(lo[feat], thresh)

            # Feasibility: need lo[f] < x[f] <= hi[f], so must have lo[f] < hi[f]
            if lo[feat] >= hi[feat]:
                feasible = False
                break

        if not feasible:
            continue

        # Compute minimum per-feature perturbation to enter feasible region
        x_new = x_scaled.copy().astype(float)
        perturbs: dict[int, float] = {}

        for f in range(n_features):
            val = float(x_scaled[f])

            if val <= lo[f]:
                # Need val > lo[f] (strict) → move just past lo
                new_val = lo[f] + 1e-7
                x_new[f] = new_val
                perturbs[f] = new_val - val
            elif val > hi[f]:
                # Need val <= hi[f] → move to hi (inclusive boundary OK)
                new_val = hi[f]
                x_new[f] = new_val
                perturbs[f] = new_val - val
            else:
                # Already in (lo[f], hi[f]] — no change needed
                perturbs[f] = 0.0

        cost_l2   = float(np.sqrt(sum(d ** 2 for d in perturbs.values())))
        cost_linf = float(max(abs(d) for d in perturbs.values()))
        n_changed = sum(1 for d in perturbs.values() if abs(d) > 1e-10)

        if cost_l2 < best_cost:
            best_cost = cost_l2
            best = {
                "target_leaf":            path_info["leaf_node"],
                "x_adversarial":          x_new,
                "required_perturbations": perturbs,
                "perturbation_cost_l2":   cost_l2,
                "perturbation_cost_linf": cost_linf,
                "n_features_changed":     n_changed,
            }

    return best


def generate_cart_adversarial(tree_model, X_malicious_raw: np.ndarray,
                               threat_model: ThreatModel,
                               epsilon: float,
                               scaler) -> dict:
    """
    Generate adversarial samples that evade CART classification.

    Parameters
    ----------
    tree_model       : fitted sklearn DecisionTreeClassifier (trained on scaled data)
    X_malicious_raw  : (n_samples, 5) raw feature matrix of ground-truth malicious samples
    threat_model     : ThreatModel initialised with raw training data
    epsilon          : perturbation budget (fraction of IQR per feature)
    scaler           : fitted StandardScaler

    Pipeline per sample
    -------------------
    1. Scale to SCALED space — path analysis uses SCALED thresholds.
    2. find_evasion_path() → x_adv_scaled (minimum SCALED perturbation).
    3. Inverse-transform → x_adv_raw.
    4. Per-feature budget check (raw IQR × epsilon).
       If over-budget → clamp each feature delta to max_delta[f].
    5. enforce_constraints() → fix payload_ratio coupling.
    6. Re-scale + re-predict → confirm evasion succeeded.

    Returns
    -------
    {
      "X_adversarial":    (n_samples, 5) raw adversarial features,
      "evasion_success":  (n_samples,) bool array,
      "perturbation_costs": list of per-sample dicts,
      "evasion_rate":     float,
      "avg_features_changed": float,
    }
    """
    max_delta_arr = threat_model.get_max_delta_array(epsilon)
    X_malicious_scaled = scaler.transform(X_malicious_raw)

    X_adversarial:      list[np.ndarray] = []
    evasion_success:    list[bool]       = []
    perturbation_costs: list[dict]       = []

    for x_raw, x_scaled in zip(X_malicious_raw, X_malicious_scaled):
        # Skip if sample is already classified as normal — nothing to evade
        pred_orig = int(tree_model.predict(x_scaled.reshape(1, -1))[0])
        if pred_orig == 0:
            X_adversarial.append(x_raw.copy())
            evasion_success.append(True)
            perturbation_costs.append(
                {"l2": 0.0, "linf": 0.0, "n_features_changed": 0,
                 "evaded": True, "note": "already_normal"})
            continue

        evasion = find_evasion_path(tree_model, x_scaled)

        if evasion is None:
            # Tree has no reachable normal leaf
            X_adversarial.append(x_raw.copy())
            evasion_success.append(False)
            perturbation_costs.append(
                {"l2": 0.0, "linf": 0.0, "n_features_changed": 0,
                 "evaded": False, "note": "no_normal_leaf"})
            continue

        # Unscale adversarial point to raw space
        x_adv_raw = scaler.inverse_transform(
            evasion["x_adversarial"].reshape(1, -1))[0]

        # Per-feature budget clamp (raw space)
        per_delta = x_adv_raw - x_raw
        clamped   = np.clip(per_delta, -max_delta_arr, max_delta_arr)
        x_adv_raw = x_raw + clamped

        # Enforce physical constraints (recomputes payload_ratio)
        x_adv_raw = threat_model.enforce_constraints(x_adv_raw)

        # Re-scale and re-classify to confirm evasion
        x_adv_scaled = scaler.transform(x_adv_raw.reshape(1, -1))
        pred_adv = int(tree_model.predict(x_adv_scaled)[0])
        evaded   = pred_adv == 0

        dist = threat_model.perturbation_distance(x_raw, x_adv_raw)
        X_adversarial.append(x_adv_raw)
        evasion_success.append(evaded)
        perturbation_costs.append({
            **dist,
            "n_features_changed": evasion["n_features_changed"],
            "evaded": evaded,
        })

    X_adv_arr    = np.array(X_adversarial)
    evasion_arr  = np.array(evasion_success)
    n = len(evasion_arr)

    return {
        "X_adversarial":         X_adv_arr,
        "evasion_success":       evasion_arr,
        "perturbation_costs":    perturbation_costs,
        "evasion_rate":          float(evasion_arr.mean()) if n > 0 else 0.0,
        "avg_features_changed":  float(np.mean(
            [c.get("n_features_changed", 0) for c in perturbation_costs]
        )) if n > 0 else 0.0,
    }
