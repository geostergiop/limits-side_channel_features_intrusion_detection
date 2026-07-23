#!/usr/bin/env python3
"""
Experiment 5D: Session-Level Consistency Attack.

Core idea
---------
An attacker perturbs individual packet SIZES to evade per-packet CART
classification.  But the perturbations may create temporal INCONSISTENCIES
detectable by an LLM reasoning over the entire session sequence.

Example: padding packet sizes to look like web traffic (~1400 B) while
leaving the original 30-second C2 beaconing intervals intact.  Each packet
individually looks normal; the session-level pattern does not.

Perturbation pipeline
---------------------
1. Load complete malicious sessions (≥ min_packets packets each).
2. Perturb each packet's size independently using the CART evasion path
   (white-box: minimum cost to reach a normal leaf).
3. Recompute ratio_to_prev (Rpp) for all packets in the session because
   changing Ps[i] affects both Rpp[i] and Rpp[i+1] (cascading).
4. Leave time_diff (Td) UNCHANGED — the key inconsistency.
5. Evaluate per-packet CART vs. session-level LLM detection.

This is the strongest test of the LLM advantage hypothesis:
per-packet evasion is easy; session-level inconsistency detection is hard.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES
from src.adversarial import cart_evasion


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_malicious_sessions(conn,
                             min_packets: int = 10,
                             max_sessions: int = 200) -> list[dict]:
    """
    Load complete malicious sessions from the database.

    Only returns sessions with at least min_packets packets (to give the
    LLM enough temporal context to observe patterns).

    Parameters
    ----------
    conn        : sqlite3.Connection (row_factory = sqlite3.Row)
    min_packets : minimum packet count per session
    max_sessions: maximum number of sessions to return

    Returns
    -------
    List of dicts, one per session:
      {
        "session_id":     int,
        "malware_family": str,
        "is_encrypted":   bool,
        "packets":        np.ndarray, shape (n_packets, 5)  — raw features,
                          columns in FEATURE_NAMES order
      }
    """
    # Step 1: find qualifying session IDs (subquery is efficient at this scale)
    query_ids = """
        SELECT s.id, s.malware_family, s.is_encrypted
        FROM sessions s
        WHERE s.is_malicious = 1
          AND (SELECT COUNT(*) FROM packets WHERE session_id = s.id) >= ?
        ORDER BY RANDOM()
        LIMIT ?
    """
    rows = conn.execute(query_ids, (min_packets, max_sessions)).fetchall()

    sessions: list[dict] = []
    for row in rows:
        sess_id  = int(row["id"])
        family   = str(row["malware_family"] or "")
        encrypted = bool(row["is_encrypted"])

        # Step 2: load all packets for this session, ordered by position
        query_pkts = """
            SELECT packet_size, payload_size, payload_ratio,
                   ratio_to_prev, time_diff
            FROM packets
            WHERE session_id = ?
            ORDER BY packet_idx ASC
        """
        pkt_rows = conn.execute(query_pkts, (sess_id,)).fetchall()

        if len(pkt_rows) < min_packets:
            continue  # guard against race / row_factory differences

        packets = np.array(
            [[float(p["packet_size"]), float(p["payload_size"]),
              float(p["payload_ratio"]), float(p["ratio_to_prev"]),
              float(p["time_diff"])]
             for p in pkt_rows],
            dtype=float,
        )
        sessions.append({
            "session_id":     sess_id,
            "malware_family": family,
            "is_encrypted":   encrypted,
            "packets":        packets,
        })

    return sessions


# ─────────────────────────────────────────────────────────────────────────────
# Session-Level Perturbation
# ─────────────────────────────────────────────────────────────────────────────

def perturb_session_per_packet(session_packets: np.ndarray,
                                cart_model,
                                threat_model: ThreatModel,
                                epsilon: float,
                                scaler) -> np.ndarray:
    """
    Perturb each packet in a session independently to evade per-packet CART,
    then enforce session-level coupling constraints.

    Strategy
    --------
    For each packet i:
      1. Find the CART evasion path (minimum scaled-space perturbation).
      2. Unscale → budget clamp (raw space) → enforce physical constraints.
      3. Overwrite ONLY packet_size (Ps) and payload_size (PAs) columns.
         payload_ratio and ratio_to_prev are derived — they will be
         recomputed in Step 4.
      4. time_diff is intentionally left unchanged — this is the inconsistency
         the LLM can detect.

    After all packets are perturbed:
      5. enforce_session_constraints() recomputes Pr[i] and Rpp[i] for the
         entire session (cascading Rpp recalculation).

    Parameters
    ----------
    session_packets : (n_packets, 5) raw features, one row per packet
    cart_model      : fitted DecisionTreeClassifier (trained on scaled data)
    threat_model    : ThreatModel
    epsilon         : perturbation budget
    scaler          : fitted StandardScaler

    Returns
    -------
    (n_packets, 5) perturbed raw feature matrix with valid physical constraints.
    """
    n = len(session_packets)
    max_delta_arr = threat_model.get_max_delta_array(epsilon)

    perturbed = session_packets.copy().astype(float)

    for i in range(n):
        x_raw = session_packets[i]
        x_scaled = scaler.transform(x_raw.reshape(1, -1))[0]

        # Skip if already classified as normal
        if int(cart_model.predict(x_scaled.reshape(1, -1))[0]) == 0:
            continue

        evasion = cart_evasion.find_evasion_path(cart_model, x_scaled)
        if evasion is None:
            continue

        # Unscale adversarial point
        x_adv_raw = scaler.inverse_transform(
            evasion["x_adversarial"].reshape(1, -1)
        )[0]

        # Clamp per-feature delta to budget (raw space)
        per_delta = np.clip(
            x_adv_raw - x_raw, -max_delta_arr, max_delta_arr
        )
        x_adv_clamped = x_raw + per_delta

        # Write back only Ps (0) and PAs (1); keep Td (4) UNCHANGED
        perturbed[i, 0] = x_adv_clamped[0]  # packet_size
        perturbed[i, 1] = x_adv_clamped[1]  # payload_size
        # indices 2 (Pr), 3 (Rpp), 4 (Td) are intentionally NOT written here

    # Step 5: recompute Pr[i] and Rpp[i] for the whole session
    # (enforce_session_constraints also recomputes Td clamping, which is fine
    # since Td was untouched and is already in [0, 300])
    perturbed = threat_model.enforce_session_constraints(perturbed)

    return perturbed


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_session_consistency(original_sessions: list[dict],
                                  perturbed_sessions: list[np.ndarray],
                                  cart_model,
                                  scaler,
                                  llm_session_classify_fn) -> dict:
    """
    Compare CART (per-packet) vs. LLM (session-level) detection on
    perturbed sessions.

    CART session detection uses majority voting: if ≥50% of packets in a
    session are classified as malicious → session is malicious.

    Parameters
    ----------
    original_sessions        : list of session dicts from load_malicious_sessions
    perturbed_sessions       : list of (n_packets, 5) perturbed raw feature arrays
    cart_model               : fitted DecisionTreeClassifier (trained on scaled data)
    scaler                   : fitted StandardScaler
    llm_session_classify_fn  : callable(packets_raw: np.ndarray) → int
                               Takes (n_packets, 5) raw array, returns 0 or 1.
                               Should use compact session profile format for LLM.

    Returns
    -------
    {
      "cart_per_packet_evasion_rate":  float,  — % of individual packets that evade
      "cart_session_detection_rate":   float,  — % of sessions CART detects (majority vote)
      "llm_session_detection_rate":    float,  — % of sessions LLM detects
      "per_session_results":           list[dict],
    }
    """
    per_session: list[dict] = []

    for sess_info, pert_pkts in zip(original_sessions, perturbed_sessions):
        n_packets = len(pert_pkts)

        # CART: classify each perturbed packet
        pert_scaled = scaler.transform(pert_pkts)
        cart_preds  = cart_model.predict(pert_scaled)  # shape (n_packets,)

        n_cart_malicious = int(np.sum(cart_preds == 1))
        n_cart_normal    = n_packets - n_cart_malicious

        # Majority vote: session is malicious if > 50% packets are malicious
        cart_session_malicious = n_cart_malicious > n_cart_normal

        # LLM: session-level classification
        llm_pred = int(llm_session_classify_fn(pert_pkts))

        per_session.append({
            "session_id":            sess_info["session_id"],
            "malware_family":        sess_info["malware_family"],
            "n_packets":             n_packets,
            "cart_malicious_packets": n_cart_malicious,
            "cart_normal_packets":   n_cart_normal,
            "cart_session_pred":     int(cart_session_malicious),
            "llm_session_pred":      llm_pred,
            "cart_packet_evasion_rate": float(n_cart_normal / n_packets),
        })

    total = len(per_session)
    if total == 0:
        return {
            "cart_per_packet_evasion_rate":  0.0,
            "cart_session_detection_rate":   0.0,
            "llm_session_detection_rate":    0.0,
            "per_session_results":           [],
        }

    cart_per_pkt_evasion = float(np.mean(
        [r["cart_packet_evasion_rate"] for r in per_session]
    ))
    cart_session_det = float(np.mean(
        [r["cart_session_pred"] for r in per_session]
    ))
    llm_valid_preds = [r["llm_session_pred"] for r in per_session if r["llm_session_pred"] >= 0]
    llm_session_det = float(np.mean(llm_valid_preds)) if llm_valid_preds else None

    return {
        "cart_per_packet_evasion_rate":  cart_per_pkt_evasion,
        "cart_session_detection_rate":   cart_session_det,
        "llm_session_detection_rate":    llm_session_det,
        "llm_valid_sessions":            int(len(llm_valid_preds)),
        "llm_invalid_sessions":          int(total - len(llm_valid_preds)),
        "per_session_results":           per_session,
    }
