#!/usr/bin/env python3
"""
End-to-end audit for malware-traffic-experiment.
All checks use an in-memory or temp SQLite DB so the lifecycle is
completely contained within this script — no external DB is needed.
"""
import sys, os, json, tempfile, importlib
from pathlib import Path

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  [OK] {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {msg}")

# ─────────────────────────────────────────────────────────────
# CHECK 1: All modules compile without ImportError
# ─────────────────────────────────────────────────────────────
print("\n[1] Module compilation")
modules = [
    "configs.config",
    "src.database",
    "src.feature_extraction",
    "src.llm_experiments",
    "src.classical_ml",
]
for mod in modules:
    try:
        importlib.import_module(mod)
        ok(mod)
    except Exception as e:
        fail(f"{mod}: {e}")

# ─────────────────────────────────────────────────────────────
# CHECK 2: configs.config paths
# ─────────────────────────────────────────────────────────────
print("\n[2] configs.config paths")
import configs.config as cfg

try:
    assert cfg.PROJECT_ROOT.exists(), f"PROJECT_ROOT missing: {cfg.PROJECT_ROOT}"
    ok(f"PROJECT_ROOT = {cfg.PROJECT_ROOT}")
except AssertionError as e:
    fail(str(e))

for attr in ("MNT_DIR", "MNT_BENIGN_DIR", "MNT_ATTACK_DIR"):
    try:
        p = getattr(cfg, attr)
        assert p.parent.exists() or p.exists(), f"{attr} parent missing"
        ok(f"{attr} = {p}")
    except AttributeError:
        fail(f"cfg.{attr} not defined")
    except AssertionError as e:
        fail(str(e))

# ─────────────────────────────────────────────────────────────
# CHECK 3: database round-trip (temp file DB)
# ─────────────────────────────────────────────────────────────
print("\n[3] Database round-trip")
from src.database import init_db, get_db, register_dataset, insert_session, insert_packets_batch

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_f:
    tmp_path = Path(tmp_f.name)

try:
    conn = init_db(tmp_path)

    ds_id = register_dataset(conn, "test_ds", "TestFamily", "test", "")
    assert isinstance(ds_id, int) and ds_id > 0
    ok("register_dataset returns positive int")

    # Idempotent
    ds_id2 = register_dataset(conn, "test_ds", "TestFamily", "test", "")
    assert ds_id == ds_id2
    ok("register_dataset is idempotent")

    sess_id_mal  = insert_session(conn, ds_id, "1.1.1.1", "2.2.2.2", 1234, 80,
                                  "TCP", 1, "malicious", "TestFamily", 0)
    sess_id_norm = insert_session(conn, ds_id, "3.3.3.3", "4.4.4.4", 5678, 443,
                                  "TCP", 0, "normal", "", 0)
    conn.commit()

    # Insert 3 malicious + 3 normal packets (≥2 each so load_test_samples can work)
    mal_pkts = [
        (sess_id_mal, i, 100+i*10, 80+i*8, 0.8, 1.0 if i>0 else 0.0, 0.01*i if i>0 else 0.0,
         1000.0+i, "outgoing", 1)
        for i in range(3)
    ]
    norm_pkts = [
        (sess_id_norm, i, 200+i*5, 150+i*3, 0.75, 1.0 if i>0 else 0.0, 0.02*i if i>0 else 0.0,
         2000.0+i, "outgoing", 0)
        for i in range(3)
    ]
    insert_packets_batch(conn, mal_pkts + norm_pkts)
    conn.commit()

    cur = conn.execute("SELECT COUNT(*) FROM packets")
    n = cur.fetchone()[0]
    assert n == 6, f"Expected 6 packets, got {n}"
    ok(f"Inserted {n} packets")

    # get_db should re-open without re-initialising schema
    conn.close()
    conn = get_db(tmp_path)
    cur = conn.execute("SELECT COUNT(*) FROM packets")
    n2 = cur.fetchone()[0]
    assert n2 == 6, f"get_db lost data: {n2} packets"
    ok("get_db preserves data")

    # ─────────────────────────────────────────────────────────
    # CHECK 4: feature_extraction helpers
    # ─────────────────────────────────────────────────────────
    print("\n[4] Feature extraction helpers")
    from src.feature_extraction import (
        compute_side_channel_features,
        _normalize_session_key,
    )

    feats = compute_side_channel_features(100, 80, None, None, 1.0)
    assert feats == (100, 80, 0.8, 0.0, 0.0), f"First-packet features wrong: {feats}"
    ok("First-packet features correct (Rpp=0, Td=0)")

    feats2 = compute_side_channel_features(100, 80, 50, 0.5, 1.0)
    assert abs(feats2[3] - 2.0) < 1e-9, f"Rpp wrong: {feats2[3]}"
    assert abs(feats2[4] - 0.5) < 1e-9, f"Td wrong: {feats2[4]}"
    ok("Subsequent-packet features correct")

    k1 = _normalize_session_key("1.1.1.1", "2.2.2.2", 1000, 80, "TCP")
    k2 = _normalize_session_key("2.2.2.2", "1.1.1.1", 80, 1000, "TCP")
    assert k1 == k2, f"Normalisation broken: {k1} != {k2}"
    ok("Session key normalisation is bidirectional")

    # ─────────────────────────────────────────────────────────
    # CHECK 5: system prompts, formatters, session profile
    # ─────────────────────────────────────────────────────────
    print("\n[5] LLM formatters & system prompts")
    import numpy as np
    import pandas as pd
    from src.llm_experiments import (
        SYSTEM_PROMPT_BASE,
        SYSTEM_PROMPT_COMPACT_PACKET,
        SYSTEM_PROMPT_COMPACT_SESSION,
        SYSTEM_PROMPT_COMPACT,
        format_packet_verbose,
        format_packet_compact,
        format_session_verbose,
        format_session_compact,
        compute_session_profile,
        FEATURE_COLS,
    )

    # SYSTEM_PROMPT_COMPACT must be shorter than SYSTEM_PROMPT_COMPACT_SESSION
    assert len(SYSTEM_PROMPT_COMPACT_PACKET) < len(SYSTEM_PROMPT_COMPACT_SESSION), \
        "COMPACT_PACKET should be shorter than COMPACT_SESSION"
    ok("COMPACT_PACKET < COMPACT_SESSION length")

    # SYSTEM_PROMPT_COMPACT alias must equal COMPACT_PACKET
    assert SYSTEM_PROMPT_COMPACT == SYSTEM_PROMPT_COMPACT_PACKET
    ok("SYSTEM_PROMPT_COMPACT alias == COMPACT_PACKET")

    # Verbose format contains expected labels
    sample = {"packet_size": 100, "payload_size": 80, "payload_ratio": 0.8,
              "ratio_to_prev": 1.0, "time_diff": 0.01}
    v = format_packet_verbose(sample)
    assert "Packet Size" in v and "Payload" in v
    ok("format_packet_verbose has expected labels")

    # Compact format is valid JSON array with 5 elements
    c = format_packet_compact(sample)
    arr = json.loads(c)
    assert isinstance(arr, list) and len(arr) == 5
    ok("format_packet_compact produces 5-element JSON array")

    # Compact always ≤ verbose in tokens (rough word count)
    assert len(c.split()) <= len(v.split())
    ok("Compact format ≤ verbose format in word count")

    # Session profile: 31 values
    rng = np.random.default_rng(0)
    pkt_df = pd.DataFrame({
        col: rng.uniform(0, 1, 20) for col in FEATURE_COLS
    })
    profile = compute_session_profile(pkt_df)
    assert len(profile) == 31, f"Expected 31 profile values, got {len(profile)}"
    ok(f"Session profile: {len(profile)} values")

    profile_json = json.dumps(profile)
    json.loads(profile_json)  # must not raise
    ok("Session profile serialises to valid JSON")

    # ─────────────────────────────────────────────────────────
    # CHECK 6: load_test_samples (uses the OPEN temp DB conn)
    # ─────────────────────────────────────────────────────────
    print("\n[6] load_test_samples SQL fix")
    from src.llm_experiments import load_test_samples

    # conn is still open and has 3 mal + 3 norm packets
    df = load_test_samples(conn, 4)
    assert len(df) >= 2, f"Expected ≥2 rows, got {len(df)}"
    ok(f"load_test_samples returned {len(df)} rows (≥2 required)")

    # Confirm both classes present
    classes = set(df["is_malicious"].tolist())
    assert 0 in classes and 1 in classes, f"Missing class in: {classes}"
    ok("Both malicious and normal classes present")

    # Test with n=6 (3+3)
    df6 = load_test_samples(conn, 6)
    assert len(df6) == 6, f"Expected 6 rows, got {len(df6)}"
    ok(f"load_test_samples(n=6) returned {len(df6)} rows")

finally:
    try:
        conn.close()
    except Exception:
        pass
    os.unlink(tmp_path)
    # Also remove WAL/SHM sidecars if present
    for ext in ("-wal", "-shm"):
        side = Path(str(tmp_path) + ext)
        if side.exists():
            os.unlink(side)

# ─────────────────────────────────────────────────────────────
# CHECK 7: EmbeddingIndex (sklearn fallback, no sentence-transformers needed)
# ─────────────────────────────────────────────────────────────
print("\n[7] EmbeddingIndex (sklearn fallback)")
import numpy as np
import pandas as pd
from src.llm_experiments import EmbeddingIndex, FEATURE_COLS

rng = np.random.default_rng(42)
pool = pd.DataFrame({
    col: rng.uniform(0, 100, 20) for col in FEATURE_COLS
})
pool["is_malicious"] = [1, 0] * 10

try:
    idx = EmbeddingIndex(pool)
    query_row = pool.iloc[0]
    neighbours = idx.query(query_row, k=4)
    assert len(neighbours) == 4, f"Expected 4 neighbours, got {len(neighbours)}"
    ok(f"EmbeddingIndex.query returned {len(neighbours)} neighbours")
    # Should be balanced
    n_mal  = (neighbours["is_malicious"] == 1).sum()
    n_norm = (neighbours["is_malicious"] == 0).sum()
    assert n_mal > 0 and n_norm > 0, f"Not balanced: mal={n_mal} norm={n_norm}"
    ok(f"EmbeddingIndex balanced: {n_mal} mal / {n_norm} norm")
except Exception as e:
    fail(f"EmbeddingIndex: {e}")

# ─────────────────────────────────────────────────────────────
# CHECK 8: Token counts — compact < verbose for session window
# ─────────────────────────────────────────────────────────────
print("\n[8] Token counts: compact < verbose for 10-packet session")
from src.llm_experiments import (
    PROMPT_SESSION_VERBOSE, PROMPT_SESSION_COMPACT,
    format_session_verbose, format_session_compact,
)

rng = np.random.default_rng(7)
pkt_df10 = pd.DataFrame({col: rng.uniform(0, 100, 10) for col in FEATURE_COLS})
pkt_records = pkt_df10.to_dict("records")

sess_v = format_session_verbose(pkt_records)
sess_c = format_session_compact(pkt_df10)

prompt_v = len((SYSTEM_PROMPT_BASE          + PROMPT_SESSION_VERBOSE.format(session=sess_v)).split())
prompt_c = len((SYSTEM_PROMPT_COMPACT_SESSION + PROMPT_SESSION_COMPACT.format(session=sess_c)).split())

try:
    assert prompt_c < prompt_v, \
        f"Compact ({prompt_c} words) should be < verbose ({prompt_v} words) for 10-pkt session"
    ok(f"Session w=10: verbose={prompt_v} words, compact={prompt_c} words "
       f"(saving {100*(prompt_v-prompt_c)/prompt_v:.0f}%)")
except AssertionError as e:
    fail(str(e))

# ─────────────────────────────────────────────────────────────
# CHECK 9: validate_token_reduction imports cleanly
# ─────────────────────────────────────────────────────────────
print("\n[9] validate_token_reduction.py compiles")
try:
    import validate_token_reduction as vtr
    ok("validate_token_reduction imports ok")
    assert callable(vtr.measure_packet_prompt)
    assert callable(vtr.measure_session_prompt)
    ok("measure_packet_prompt and measure_session_prompt are callable")
except Exception as e:
    fail(f"validate_token_reduction: {e}")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Audit complete:  {PASS} passed,  {FAIL} failed")
print('='*60)
sys.exit(0 if FAIL == 0 else 1)
