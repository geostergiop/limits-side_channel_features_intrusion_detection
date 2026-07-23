#!/usr/bin/env python3
"""
Experiment 5B: Gradient-Free KNN Evasion.

Strategy
--------
For each malicious sample, iteratively move it toward the nearest NORMAL
training-set neighbor, staying within the per-feature ε budget.

After each step the sample is re-classified with KNN.  The loop stops when:
  (a) the prediction flips to "normal" (evasion success), or
  (b) the maximum number of iterations is exhausted (evasion failure).

All distance computations and KNN queries use SCALED features (consistent
with how the KNN model was trained).  Perturbation budgets are checked in
RAW feature space (ε × IQR, same as every other adversarial module).

Key design notes
----------------
* "Budget from original" — the cumulative displacement of each feature
  from x_orig must not exceed max_delta[f] at any step.  Clamping is
  applied at each iteration so the constraint is never violated.
* We re-find the nearest normal neighbor at each iteration because
  moving the sample may bring it closer to a different normal neighbor.
* Physical constraints (payload_ratio coupling) are enforced in raw space
  after each move.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES


def find_nearest_normal_neighbor(knn_model,
                                  x_raw: np.ndarray,
                                  X_train_raw: np.ndarray,
                                  y_train: np.ndarray,
                                  scaler) -> np.ndarray:
    """
    Return the raw-feature vector of the nearest NORMAL training sample.

    Distance is computed in SCALED space (Euclidean, consistent with KNN
    model training).

    Parameters
    ----------
    knn_model   : fitted KNeighborsClassifier
    x_raw       : shape (5,) — current raw feature vector
    X_train_raw : shape (n_train, 5) — raw training features
    y_train     : shape (n_train,) — training labels (0=normal, 1=malicious)
    scaler      : fitted StandardScaler

    Returns
    -------
    Shape (5,) — raw features of the nearest normal training sample.
    Raises ValueError if no normal samples exist in the training set.
    """
    normal_mask  = y_train == 0
    X_normal_raw = X_train_raw[normal_mask]

    if len(X_normal_raw) == 0:
        raise ValueError("Training set contains no normal-class samples.")

    # Scale both query and candidates for Euclidean distance in model space
    x_scaled       = scaler.transform(x_raw.reshape(1, -1))
    X_normal_scaled = scaler.transform(X_normal_raw)

    # Squared Euclidean distances (no sqrt needed for argmin)
    dists_sq = np.sum((X_normal_scaled - x_scaled) ** 2, axis=1)
    nearest  = int(np.argmin(dists_sq))
    return X_normal_raw[nearest].copy()


def move_toward_target(x_curr: np.ndarray,
                        x_target: np.ndarray,
                        x_orig: np.ndarray,
                        max_delta_arr: np.ndarray) -> np.ndarray:
    """
    Move x_curr toward x_target, clamped so that the cumulative displacement
    from x_orig never exceeds max_delta_arr[f] for any feature f.

    For each feature f:
        full_step = x_target[f] − x_curr[f]
        allowed_lo = x_orig[f] − max_delta_arr[f]   (lower budget boundary)
        allowed_hi = x_orig[f] + max_delta_arr[f]   (upper budget boundary)
        x_next[f]  = clip(x_curr[f] + full_step, allowed_lo, allowed_hi)

    Parameters
    ----------
    x_curr       : shape (5,) — current perturbed point
    x_target     : shape (5,) — target (nearest normal neighbor)
    x_orig       : shape (5,) — original (unperturbed) point
    max_delta_arr: shape (5,) — per-feature budget bound

    Returns
    -------
    Shape (5,) — moved point within budget.
    """
    x_next = x_curr.copy().astype(float)
    for f in range(len(x_curr)):
        full_step   = x_target[f] - x_curr[f]
        allowed_lo  = x_orig[f] - max_delta_arr[f]
        allowed_hi  = x_orig[f] + max_delta_arr[f]
        x_next[f]   = np.clip(x_curr[f] + full_step, allowed_lo, allowed_hi)
    return x_next


def generate_knn_adversarial(knn_model,
                              X_malicious_raw: np.ndarray,
                              X_train_raw: np.ndarray,
                              y_train: np.ndarray,
                              threat_model: ThreatModel,
                              epsilon: float,
                              scaler,
                              max_iterations: int = 50) -> dict:
    """
    Generate adversarial samples against a KNN classifier.

    For each malicious sample x_orig:
      1. Find nearest normal training sample (NNN).
      2. Move x_curr toward NNN, staying within per-feature budget from x_orig.
      3. Enforce physical constraints.
      4. Re-classify with KNN on scaled features.
      5. If prediction flips → success.  If budget exhausted → failure.
      6. Re-find NNN from updated x_curr (it may have changed) and repeat.

    Parameters
    ----------
    knn_model        : fitted KNeighborsClassifier (trained on scaled data)
    X_malicious_raw  : (n_samples, 5) raw features — ground-truth malicious
    X_train_raw      : (n_train, 5) raw training features
    y_train          : (n_train,) training labels
    threat_model     : ThreatModel initialised from raw training data
    epsilon          : perturbation budget
    scaler           : fitted StandardScaler
    max_iterations   : iteration cap per sample

    Returns
    -------
    {
      "X_adversarial":       (n_samples, 5) raw adversarial features,
      "evasion_success":     (n_samples,) bool array,
      "perturbation_costs":  list of per-sample cost dicts,
      "evasion_rate":        float,
      "avg_features_changed": float,
    }
    """
    max_delta_arr = threat_model.get_max_delta_array(epsilon)

    X_adversarial:      list[np.ndarray] = []
    evasion_success:    list[bool]       = []
    perturbation_costs: list[dict]       = []

    for x_orig in X_malicious_raw:
        x_orig = x_orig.astype(float)

        # Skip if already classified as normal by KNN
        x_scaled_orig = scaler.transform(x_orig.reshape(1, -1))
        if int(knn_model.predict(x_scaled_orig)[0]) == 0:
            X_adversarial.append(x_orig.copy())
            evasion_success.append(True)
            perturbation_costs.append(
                {"l2": 0.0, "linf": 0.0, "n_features_changed": 0,
                 "iterations": 0, "evaded": True, "note": "already_normal"})
            continue

        x_curr = x_orig.copy()
        evaded = False
        n_iters = 0

        for iteration in range(max_iterations):
            n_iters = iteration + 1

            # Find nearest normal neighbor from current position
            x_target = find_nearest_normal_neighbor(
                knn_model, x_curr, X_train_raw, y_train, scaler
            )

            # Move toward target, clamped to per-feature budget from x_orig
            x_next = move_toward_target(x_curr, x_target, x_orig, max_delta_arr)

            # Enforce physical constraints in raw space
            x_next = threat_model.enforce_constraints(x_next)

            # Verify budget not violated after constraint enforcement
            if not threat_model.within_budget(x_orig, x_next, epsilon):
                # Constraint enforcement moved us out of budget; use x_curr
                break

            # Re-classify
            x_next_scaled = scaler.transform(x_next.reshape(1, -1))
            pred = int(knn_model.predict(x_next_scaled)[0])

            # Check for no progress (converged within numerical tolerance)
            no_progress = np.allclose(x_next, x_curr, atol=1e-9)

            x_curr = x_next

            if pred == 0:
                evaded = True
                break
            if no_progress:
                break

        dist = threat_model.perturbation_distance(x_orig, x_curr)
        n_changed = int(np.sum(np.abs(x_curr - x_orig) > 1e-10))

        X_adversarial.append(x_curr)
        evasion_success.append(evaded)
        perturbation_costs.append({
            **dist,
            "n_features_changed": n_changed,
            "iterations": n_iters,
            "evaded": evaded,
        })

    X_adv_arr   = np.array(X_adversarial)
    evasion_arr = np.array(evasion_success)
    n = len(evasion_arr)

    return {
        "X_adversarial":        X_adv_arr,
        "evasion_success":      evasion_arr,
        "perturbation_costs":   perturbation_costs,
        "evasion_rate":         float(evasion_arr.mean()) if n > 0 else 0.0,
        "avg_features_changed": float(np.mean(
            [c["n_features_changed"] for c in perturbation_costs]
        )) if n > 0 else 0.0,
    }
