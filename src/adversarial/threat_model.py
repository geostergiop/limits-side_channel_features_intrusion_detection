#!/usr/bin/env python3
"""
Threat model for adversarial perturbation of TCP side-channel features.

Defines:
  - Physical constraints on each feature (hard bounds from TCP/IP spec)
  - Perturbation budget computation from training-data IQR
  - Constraint enforcement: clamp + coupling recomputation
  - Session-level constraint enforcement (cascading Rpp)
  - Distance utilities for budget checking
"""

import numpy as np

# Feature order must match SIDE_CHANNEL_FEATURES in configs/config.py
FEATURE_NAMES = [
    "packet_size",    # 0 — Ps
    "payload_size",   # 1 — PAs
    "payload_ratio",  # 2 — Pr = PAs / Ps
    "ratio_to_prev",  # 3 — Rpp = Ps[i] / Ps[i-1]
    "time_diff",      # 4 — Td = t[i] - t[i-1]
]
FEATURE_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}

# Hard physical bounds (min, max).  max=None means derived dynamically.
_HARD_BOUNDS: dict = {
    "packet_size":   (40.0,   65535.0),
    "payload_size":  (0.0,    None),      # dyn: max = packet_size - 40
    "payload_ratio": (0.0,    1.0),
    "ratio_to_prev": (0.0,    100.0),
    "time_diff":     (0.0,    300.0),
}

# Minimum IP+TCP header overhead in bytes
_HEADER_OVERHEAD = 40


class ThreatModel:
    """
    Encapsulates the adversarial threat model for TCP side-channel features.

    Parameters
    ----------
    X_train : np.ndarray, shape (n_samples, 5)
        RAW (unscaled) training features — used to compute per-feature IQR.
    feature_names : list[str]
        Must match FEATURE_NAMES order (["packet_size", ...]).

    Perturbation budget
    -------------------
    For each feature f and budget ε:
        max_delta[f] = ε × IQR(f_train)

    Physical constraints enforced after every perturbation:
        1. 40 ≤ packet_size ≤ 65535
        2. 0 ≤ payload_size ≤ packet_size − 40
        3. payload_ratio = payload_size / packet_size  (recomputed, NOT perturbed)
        4. 0 ≤ ratio_to_prev ≤ 100
        5. 0 ≤ time_diff ≤ 300
    Session-level: Rpp[i] = Ps[i] / Ps[i-1] for i > 0 (always recomputed).
    """

    def __init__(self, X_train: np.ndarray,
                 feature_names: list = FEATURE_NAMES) -> None:
        if X_train.shape[1] != len(feature_names):
            raise ValueError(
                f"X_train has {X_train.shape[1]} cols but "
                f"{len(feature_names)} feature_names given"
            )
        self.feature_names = list(feature_names)
        self.feature_idx = {name: i for i, name in enumerate(feature_names)}

        self.q1: dict[str, float] = {}
        self.q3: dict[str, float] = {}
        self.iqr: dict[str, float] = {}

        for i, name in enumerate(feature_names):
            col = X_train[:, i].astype(float)
            q1 = float(np.percentile(col, 25))
            q3 = float(np.percentile(col, 75))
            self.q1[name] = q1
            self.q3[name] = q3
            # Guard against zero IQR (constant features): use tiny floor
            self.iqr[name] = max(q3 - q1, 1e-8)

    # ------------------------------------------------------------------ #
    # Budget                                                               #
    # ------------------------------------------------------------------ #

    def get_perturbation_bounds(self, epsilon: float) -> dict[str, float]:
        """
        Return maximum allowed delta per feature for budget ε.

        max_delta[f] = ε × IQR(f_train)
        """
        return {name: epsilon * self.iqr[name] for name in self.feature_names}

    def get_max_delta_array(self, epsilon: float) -> np.ndarray:
        """Return max_delta as a numpy array aligned with FEATURE_NAMES."""
        bounds = self.get_perturbation_bounds(epsilon)
        return np.array([bounds[name] for name in self.feature_names])

    # ------------------------------------------------------------------ #
    # Constraint enforcement — single packet                              #
    # ------------------------------------------------------------------ #

    def enforce_constraints(self, x: np.ndarray) -> np.ndarray:
        """
        Enforce physical constraints on a single perturbed feature vector.

        Steps (order matters):
          1. Clamp packet_size to [40, 65535]
          2. Clamp payload_size to [0, packet_size − 40]
          3. Recompute payload_ratio = payload_size / packet_size
          4. Clamp ratio_to_prev to [0, 100]
          5. Clamp time_diff to [0, 300]

        NOTE: ratio_to_prev coupling across a session is handled by
        enforce_session_constraints(), not here.

        Args:
            x : shape (5,) — raw feature vector
        Returns:
            x_valid : shape (5,) — physically valid copy
        """
        x = np.array(x, dtype=float)

        # 1 — packet_size
        x[0] = np.clip(x[0], 40.0, 65535.0)

        # 2 — payload_size  (max = packet_size − header overhead)
        max_payload = max(0.0, x[0] - _HEADER_OVERHEAD)
        x[1] = np.clip(x[1], 0.0, max_payload)

        # 3 — payload_ratio (always derived, never independently perturbed)
        x[2] = (x[1] / x[0]) if x[0] > 0 else 0.0
        x[2] = np.clip(x[2], 0.0, 1.0)

        # 4 — ratio_to_prev
        x[3] = np.clip(x[3], 0.0, 100.0)

        # 5 — time_diff
        x[4] = np.clip(x[4], 0.0, 300.0)

        return x

    # ------------------------------------------------------------------ #
    # Constraint enforcement — full session                               #
    # ------------------------------------------------------------------ #

    def enforce_session_constraints(self, session: np.ndarray) -> np.ndarray:
        """
        Enforce constraints across a session of packets.

        After perturbing packet sizes, ratio_to_prev[i] = Ps[i] / Ps[i-1]
        must be recomputed for ALL packets because changing Ps[i] affects
        BOTH Rpp[i] (current) and Rpp[i+1] (next packet — cascading).

        Time differences (Td) are left untouched — the attacker modifying
        C2 payload sizes cannot easily alter protocol-level timing.

        Args:
            session : shape (n_packets, 5) — raw features, one row per packet
        Returns:
            session_valid : shape (n_packets, 5) with recomputed Pr and Rpp
        """
        session = np.array(session, dtype=float)
        n = len(session)

        for i in range(n):
            # Per-packet clamping (excluding Rpp, which is recalculated below)
            session[i, 0] = np.clip(session[i, 0], 40.0, 65535.0)
            max_payload = max(0.0, session[i, 0] - _HEADER_OVERHEAD)
            session[i, 1] = np.clip(session[i, 1], 0.0, max_payload)
            # Recompute Pr
            ps = session[i, 0]
            session[i, 2] = (session[i, 1] / ps) if ps > 0 else 0.0
            session[i, 2] = np.clip(session[i, 2], 0.0, 1.0)
            # Clamp Td
            session[i, 4] = np.clip(session[i, 4], 0.0, 300.0)

        # Recompute Rpp for all packets (cascading: Rpp[i] = Ps[i] / Ps[i-1])
        session[0, 3] = 0.0  # first packet has no predecessor
        for i in range(1, n):
            prev_ps = session[i - 1, 0]
            curr_ps = session[i, 0]
            session[i, 3] = (curr_ps / prev_ps) if prev_ps > 0 else 0.0
            session[i, 3] = np.clip(session[i, 3], 0.0, 100.0)

        return session

    # ------------------------------------------------------------------ #
    # Validity check                                                       #
    # ------------------------------------------------------------------ #

    def is_valid(self, x: np.ndarray) -> bool:
        """Return True if x satisfies all physical constraints."""
        x = np.asarray(x, dtype=float)
        ps, pas, pr, rpp, td = x
        if not (40.0 <= ps <= 65535.0):
            return False
        if not (0.0 <= pas <= ps - _HEADER_OVERHEAD):
            return False
        expected_pr = (pas / ps) if ps > 0 else 0.0
        if abs(pr - expected_pr) > 1e-6:
            return False
        if not (0.0 <= rpp <= 100.0):
            return False
        if not (0.0 <= td <= 300.0):
            return False
        return True

    # ------------------------------------------------------------------ #
    # Distance utilities                                                   #
    # ------------------------------------------------------------------ #

    def perturbation_distance(self, x_orig: np.ndarray,
                              x_pert: np.ndarray) -> dict:
        """
        Compute distances between original and perturbed feature vectors.

        Returns:
            {
              "l2":         float,
              "linf":       float,
              "per_feature": {name: delta, ...},
              "within_budget": bool (requires epsilon to be meaningful — always True here),
            }
        """
        diff = np.asarray(x_pert, dtype=float) - np.asarray(x_orig, dtype=float)
        return {
            "l2":          float(np.linalg.norm(diff)),
            "linf":        float(np.max(np.abs(diff))),
            "per_feature": {
                name: float(diff[i])
                for i, name in enumerate(self.feature_names)
            },
        }

    def within_budget(self, x_orig: np.ndarray, x_pert: np.ndarray,
                      epsilon: float) -> bool:
        """
        Return True if every feature's perturbation is within the epsilon budget.

        Check is per-feature:  |x_pert[f] - x_orig[f]| ≤ ε × IQR[f]
        """
        max_delta = self.get_max_delta_array(epsilon)
        return bool(np.all(np.abs(x_pert - x_orig) <= max_delta + 1e-10))
