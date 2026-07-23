#!/usr/bin/env python3
"""
Focused audit harness for fixes [1] to [4].

Checks:
  [1] Grouped holdout splits are group-disjoint for session and capture modes.
  [2] Malware-family labels can be backfilled and LOFO runs on named families.
  [3] Invalid LLM predictions (-1) are excluded from adversarial/session rates.
  [4] Improved flow boundaries work for timeout / SYN reuse / FIN-close logic.
  [4E] Session-window LLM evaluation reuses one cohort across window sizes and
       records real latency.
"""

from __future__ import annotations

import sys
import tempfile
import importlib
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0


def ok(msg: str):
    global PASS
    PASS += 1
    print(f"  [OK] {msg}")


def fail(msg: str):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# [0] Imports
# ─────────────────────────────────────────────────────────────────────────────
print("\n[0] Module compilation")
for mod in [
    "src.splits",
    "src.classical_ml",
    "src.feature_extraction",
    "src.llm_experiments",
    "src.adversarial.black_box_search",
    "src.adversarial.session_perturbation",
]:
    try:
        importlib.import_module(mod)
        ok(mod)
    except Exception as e:
        fail(f"{mod}: {e}")

from src.database import init_db, register_dataset, insert_session, insert_packets_batch
from src.splits import group_holdout_split
from src.classical_ml import run_lofo_experiment
from src.feature_extraction import fix_existing_labels, sessionize_packet_records
from src.adversarial.black_box_search import transfer_attack_evaluation
from src.adversarial.session_perturbation import evaluate_session_consistency
from src.adversarial.evaluate import evaluate_on_llm
from src.llm_experiments import experiment_4e_session_window, LLM_CONFIG


# ─────────────────────────────────────────────────────────────────────────────
# [1] Grouped holdout split disjointness
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] Grouped holdout split disjointness")

groups_df = pd.DataFrame([
    # session  dataset  label  features...
    [101, 1, 0, 100,  50, 0.50, 1.0, 0.1],
    [101, 1, 0, 110,  55, 0.50, 1.1, 0.1],
    [102, 1, 1, 900, 820, 0.91, 1.0, 0.01],
    [102, 1, 1, 920, 840, 0.91, 1.0, 0.01],
    [103, 2, 0, 120,  60, 0.50, 0.9, 0.2],
    [103, 2, 0, 130,  65, 0.50, 1.0, 0.2],
    [104, 2, 1, 950, 860, 0.91, 1.1, 0.02],
    [104, 2, 1, 970, 880, 0.91, 1.0, 0.02],
    [105, 3, 0, 140,  70, 0.50, 1.0, 0.2],
    [105, 3, 0, 150,  75, 0.50, 1.0, 0.2],
    [106, 3, 1, 980, 890, 0.91, 1.0, 0.03],
    [106, 3, 1, 990, 900, 0.91, 1.0, 0.03],
    [107, 4, 0, 160,  80, 0.50, 1.0, 0.2],
    [107, 4, 0, 170,  85, 0.50, 1.0, 0.2],
    [108, 4, 1, 995, 905, 0.91, 1.0, 0.03],
    [108, 4, 1, 996, 906, 0.91, 1.0, 0.03],
], columns=[
    "session_id", "dataset_id", "is_malicious",
    "packet_size", "payload_size", "payload_ratio", "ratio_to_prev", "time_diff"
])

try:
    tr_s, te_s, sum_s = group_holdout_split(
        groups_df, group_col="session_id", label_col="is_malicious",
        test_size=0.25, random_state=42, n_trials=64,
    )
    assert not (set(tr_s["session_id"]) & set(te_s["session_id"]))
    ok("session holdout has no overlapping session_id values")
    assert set(tr_s["is_malicious"]) == {0, 1} and set(te_s["is_malicious"]) == {0, 1}
    ok("session holdout preserves both classes in train and test")
except Exception as e:
    fail(f"session holdout: {e}")

try:
    tr_c, te_c, sum_c = group_holdout_split(
        groups_df, group_col="dataset_id", label_col="is_malicious",
        test_size=0.25, random_state=42, n_trials=64,
    )
    assert not (set(tr_c["dataset_id"]) & set(te_c["dataset_id"]))
    ok("capture holdout has no overlapping dataset_id values")
    assert set(tr_c["is_malicious"]) == {0, 1} and set(te_c["is_malicious"]) == {0, 1}
    ok("capture holdout preserves both classes in train and test")
except Exception as e:
    fail(f"capture holdout: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# [2] Malware-family backfill + LOFO viability
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Malware-family backfill and LOFO viability")

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    tmp_db = Path(tmp.name)

try:
    conn = init_db(tmp_db)

    # Three benign captures so group-wise normal allocation can work.
    benign_ds = [
        register_dataset(conn, f"mnt-benign-b{i}", "", "normal", "")
        for i in range(1, 4)
    ]

    # Five attack captures, initially Unknown, matching config backfill mapping.
    attack_names = [
        "mnt-attack-2018-03-27_win23",
        "mnt-attack-2018-04-03_win10",
        "mnt-attack-2018-04-03_win12",
        "mnt-attack-2018-04-04_win16",
        "mnt-attack-2021-11-29_win5",
    ]
    attack_ds = [register_dataset(conn, name, "Unknown", "malware", "") for name in attack_names]

    def add_session_with_packets(dataset_id: int, is_malicious: int, malware_family: str,
                                 base_size: int, n_packets: int = 40):
        sid = insert_session(
            conn, dataset_id,
            "10.0.0.1", "10.0.0.2", 1234, 80, "tcp",
            is_malicious=is_malicious,
            label="test",
            malware_family=malware_family,
            is_encrypted=0,
        )
        rows = []
        for i in range(n_packets):
            ps = base_size + (i % 3)
            pas = max(0, ps - 40)
            pr = pas / ps if ps > 0 else 0.0
            rpp = 1.0 if i else 0.0
            td = 0.01 if i else 0.0
            rows.append((sid, i, ps, pas, pr, rpp, td, float(i), "outgoing", is_malicious))
        insert_packets_batch(conn, rows)

    for ds in benign_ds:
        for rep in range(4):
            add_session_with_packets(ds, 0, "", 120 + rep)

    for ds in attack_ds:
        for rep in range(4):
            add_session_with_packets(ds, 1, "Unknown", 980 + rep)

    conn.commit()

    updated = fix_existing_labels(conn)
    assert updated == 5, f"expected 5 dataset updates, got {updated}"
    ok("fix_existing_labels updates all 5 locally mapped attack captures")

    fams = [r[0] for r in conn.execute(
        "SELECT DISTINCT malware_family FROM sessions WHERE is_malicious = 1 ORDER BY malware_family"
    ).fetchall()]
    named_fams = [f for f in fams if f and f != "Unknown"]
    assert len(named_fams) == 5, f"expected 5 named families, got {named_fams}"
    ok("malicious sessions now carry 5 distinct named malware families")

    lofo = run_lofo_experiment(conn, group_by="capture", train_sample_size=600, test_sample_size=200)
    assert len(lofo) == 10, f"expected 10 LOFO rows (5 families × 2 algos), got {len(lofo)}"
    ok("LOFO executes successfully on the repaired family labels")

    lofo_fams = sorted(set(r["held_out_family"] for r in lofo))
    assert lofo_fams == sorted(named_fams), f"held-out families mismatch: {lofo_fams}"
    ok("LOFO covers the expected held-out malware families")

    conn.close()
finally:
    try:
        tmp_db.unlink(missing_ok=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# [3] Invalid prediction exclusion from adversarial/session metrics
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] Invalid prediction exclusion")

try:
    X_cart = np.array([[0,0,0,0,0], [1,0,0,0,0], [2,0,0,0,0], [3,0,0,0,0]], dtype=float)
    X_knn  = np.array([[10,0,0,0,0], [11,0,0,0,0], [12,0,0,0,0], [13,0,0,0,0]], dtype=float)
    pred_map = {0: 0, 1: -1, 2: 1, 3: -1, 10: 0, 11: 0, 12: -1, 13: 1}
    def llm_fn(x):
        return pred_map[int(x[0])]

    tr = transfer_attack_evaluation(X_cart, X_knn, llm_fn, np.ones(4, dtype=int))
    assert abs(tr["cart_transfer_rate"] - 0.5) < 1e-9
    assert abs(tr["knn_transfer_rate"] - (2/3)) < 1e-9
    ok("transfer rates exclude -1 predictions from the denominator")
    assert tr["cart_invalid_predictions"] == 2 and tr["knn_invalid_predictions"] == 1
    ok("transfer evaluation reports correct invalid-prediction counts")
except Exception as e:
    fail(f"transfer invalid handling: {e}")

try:
    class IdentityScaler:
        def transform(self, x):
            return x

    class AlwaysMaliciousModel:
        def predict(self, x):
            return np.ones(len(x), dtype=int)

    original_sessions = [
        {"session_id": 1, "malware_family": "FamA"},
        {"session_id": 2, "malware_family": "FamB"},
        {"session_id": 3, "malware_family": "FamC"},
    ]
    perturbed_sessions = [
        np.array([[101, 61, 0.6, 0.0, 0.0], [102, 62, 0.6, 1.0, 0.1]]),
        np.array([[201, 161, 0.8, 0.0, 0.0], [202, 162, 0.8, 1.0, 0.1]]),
        np.array([[301, 261, 0.87, 0.0, 0.0], [302, 262, 0.87, 1.0, 0.1]]),
    ]
    llm_preds = {101: -1, 201: 1, 301: -1}
    def llm_session_fn(pkts):
        return llm_preds[int(pkts[0, 0])]

    sess_eval = evaluate_session_consistency(
        original_sessions, perturbed_sessions,
        AlwaysMaliciousModel(), IdentityScaler(), llm_session_fn,
    )
    assert sess_eval["llm_valid_sessions"] == 1 and sess_eval["llm_invalid_sessions"] == 2
    ok("session consistency reports valid and invalid session counts correctly")
    assert abs(sess_eval["llm_session_detection_rate"] - 1.0) < 1e-9
    ok("session-level LLM detection rate ignores invalid session predictions")
except Exception as e:
    fail(f"session invalid handling: {e}")

try:
    class FakeLLMClient:
        def __init__(self, preds):
            self._preds = list(preds)
        def classify(self, *args, **kwargs):
            pred = self._preds.pop(0)
            return {
                "prediction": pred,
                "confidence": 0.7,
                "reasoning": "synthetic",
                "tokens": 5,
                "latency_ms": 12.0,
                "raw_response": "{}",
            }

    X_adv = np.array([
        [100, 60, 0.6, 0.0, 0.0],
        [101, 61, 0.6, 1.0, 0.1],
        [102, 62, 0.6, 1.0, 0.1],
    ], dtype=float)
    llm_eval = evaluate_on_llm(
        X_adv, np.ones(3, dtype=int),
        llm_client=FakeLLMClient([0, -1, 1]),
        mode="zero_shot",
        compact=True,
        batch_size=1,
    )
    assert llm_eval["n_valid"] == 2 and llm_eval["n_invalid"] == 1
    ok("packet-level LLM evaluation exposes valid/invalid counts")
    assert abs(llm_eval["llm_evasion_rate"] - 0.5) < 1e-9
    ok("packet-level LLM evasion rate ignores invalid predictions")
except Exception as e:
    fail(f"packet invalid handling: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# [4] Flow timeout and connection-boundary logic
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Flow timeout and connection-boundary logic")

base_key = ("1.1.1.1", "2.2.2.2", 1111, 80, "tcp")

def rec(ts: float, flags: int = 0, src_ip: str = "1.1.1.1", src_port: int = 1111):
    return {
        "base_key": base_key,
        "src_ip": src_ip,
        "dst_ip": "2.2.2.2",
        "src_port": src_port,
        "dst_port": 80,
        "proto": "tcp",
        "packet_size": 100,
        "payload_size": 60,
        "timestamp": float(ts),
        "is_encrypted": 0,
        "tcp_flags": int(flags),
    }

try:
    timeout_sessions = sessionize_packet_records([
        rec(0.0, flags=0x02), rec(0.5, flags=0x10), rec(200.0, flags=0x10),
    ])
    counts = [len(s["packets"]) for s in timeout_sessions]
    assert len(timeout_sessions) == 2 and counts == [2, 1]
    ok("idle timeout rotates long-gapped traffic into a new flow")
except Exception as e:
    fail(f"timeout flow split: {e}")

try:
    syn_reuse_sessions = sessionize_packet_records([
        rec(0.0, flags=0x02), rec(0.1, flags=0x10), rec(0.2, flags=0x02),
    ])
    counts = [len(s["packets"]) for s in syn_reuse_sessions]
    assert len(syn_reuse_sessions) == 2 and counts == [2, 1]
    ok("fresh SYN after prior activity rotates a reused TCP 5-tuple")
except Exception as e:
    fail(f"SYN reuse split: {e}")

try:
    syn_retx_sessions = sessionize_packet_records([
        rec(0.0, flags=0x02), rec(0.05, flags=0x02), rec(0.1, flags=0x10),
    ])
    assert len(syn_retx_sessions) == 1
    ok("SYN retransmission during initial handshake does not create a false split")
except Exception as e:
    fail(f"SYN retransmission handling: {e}")

try:
    post_close_sessions = sessionize_packet_records([
        rec(0.0, flags=0x02), rec(0.1, flags=0x10), rec(1.0, flags=0x01), rec(4.5, flags=0x10),
    ])
    counts = [len(s["packets"]) for s in post_close_sessions]
    assert len(post_close_sessions) == 2 and counts == [3, 1]
    ok("traffic after FIN/RST grace period becomes a new flow")
except Exception as e:
    fail(f"post-close split: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# [4E] Same cohort across window sizes + latency recording
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4E] Fixed cohort reuse and latency recording")

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    tmp_db_4e = Path(tmp.name)

try:
    conn = init_db(tmp_db_4e)
    ds_norm = register_dataset(conn, "norm_ds", "", "normal", "")
    ds_mal  = register_dataset(conn, "mal_ds",  "Dridex", "malware", "")

    def add_window_session(dataset_id: int, is_malicious: int, sess_idx: int, n_packets: int = 7):
        sid = insert_session(
            conn, dataset_id,
            f"10.0.0.{sess_idx}", f"10.0.1.{sess_idx}",
            1234 + sess_idx, 80, "tcp",
            is_malicious=is_malicious,
            label="test",
            malware_family=("Dridex" if is_malicious else ""),
            is_encrypted=0,
        )
        rows = []
        base = 900 if is_malicious else 120
        for i in range(n_packets):
            ps = base + i
            pas = max(0, ps - 40)
            pr = pas / ps
            rpp = (ps / (base + i - 1)) if i > 0 else 0.0
            td = 0.01 * i if i > 0 else 0.0
            rows.append((sid, i, ps, pas, pr, rpp, td, float(i), "outgoing", is_malicious))
        insert_packets_batch(conn, rows)
        return sid

    mal_ids = [add_window_session(ds_mal, 1, i) for i in range(1, 7)]
    norm_ids = [add_window_session(ds_norm, 0, i + 10) for i in range(1, 7)]
    conn.commit()

    class FakeSessionClient:
        def __init__(self):
            self.calls = 0
        def classify(self, *args, **kwargs):
            self.calls += 1
            return {
                "prediction": 1 if self.calls % 2 else 0,
                "confidence": 0.65,
                "reasoning": "synthetic",
                "tokens": 7,
                "latency_ms": 11.5,
                "raw_response": '{"classification": "malicious", "confidence": 0.65, "reasoning": "synthetic"}',
            }

    backup = {
        "window_sizes": list(LLM_CONFIG["window_sizes"]),
        "session_sample_size": LLM_CONFIG["session_sample_size"],
        "requests_per_minute": LLM_CONFIG["requests_per_minute"],
    }
    LLM_CONFIG["window_sizes"] = [3, 5, 7]
    LLM_CONFIG["session_sample_size"] = 10
    LLM_CONFIG["requests_per_minute"] = 10_000_000

    try:
        client = FakeSessionClient()
        res = experiment_4e_session_window(client, conn, compact=True)
    finally:
        LLM_CONFIG["window_sizes"] = backup["window_sizes"]
        LLM_CONFIG["session_sample_size"] = backup["session_sample_size"]
        LLM_CONFIG["requests_per_minute"] = backup["requests_per_minute"]

    assert len(res) == 30, f"expected 30 rows (10 sessions × 3 window sizes), got {len(res)}"
    ok("4E evaluates one fixed 10-session cohort across all requested window sizes")

    cohort_hashes = {r["cohort_hash"] for r in res}
    assert len(cohort_hashes) == 1
    ok("4E stores one stable cohort_hash shared by all window sizes")

    by_window = {}
    for r in res:
        by_window.setdefault(r["window_size"], set()).add(r["session_id"])
    window_sets = list(by_window.values())
    assert all(s == window_sets[0] for s in window_sets[1:])
    ok("4E reuses the same exact session IDs for every window size")

    assert all(float(r.get("latency_ms", 0.0)) > 0 for r in res)
    ok("4E records nonzero per-call latency for every session classification")

    conn.close()
finally:
    try:
        tmp_db_4e.unlink(missing_ok=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Focused audit complete:  {PASS} passed,  {FAIL} failed")
print('='*60)
sys.exit(0 if FAIL == 0 else 1)
