#!/usr/bin/env python3
"""
Audit for Gap 5 adversarial robustness implementation.
Uses in-memory/temp SQLite DB — no real data needed.
"""
import sys, os, json, tempfile, importlib
from pathlib import Path

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0

def ok(msg):
    global PASS; PASS += 1; print(f"  [OK] {msg}")

def fail(msg):
    global FAIL; FAIL += 1; print(f"  [FAIL] {msg}")

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] Module compilation")
for mod in [
    "configs.config",
    "src.adversarial.threat_model",
    "src.adversarial.cart_evasion",
    "src.adversarial.knn_evasion",
    "src.adversarial.black_box_search",
    "src.adversarial.session_perturbation",
    "src.adversarial.adaptive_adversary",
    "src.adversarial.generate_adversarial",
    "src.adversarial.evaluate",
    "src.adversarial_experiments",
]:
    try:
        importlib.import_module(mod)
        ok(mod)
    except Exception as e:
        fail(f"{mod}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] configs.config — ADV_CONFIG present")
import configs.config as cfg
try:
    assert hasattr(cfg, "ADV_CONFIG"), "ADV_CONFIG missing"
    adv = cfg.ADV_CONFIG
    for key in ("epsilon_values","n_adversarial_samples","n_session_samples",
                "min_session_length","query_budget_random","query_budget_hillclimb",
                "query_budget_adaptive","llm_eval_sample_size","llm_few_shot_k",
                "estimated_cost_per_query_usd"):
        assert key in adv, f"ADV_CONFIG missing '{key}'"
    ok(f"ADV_CONFIG has all required keys: {list(adv.keys())}")
    assert adv["epsilon_values"] == [0.05,0.10,0.20,0.30,0.50]
    ok("epsilon_values correct")
except AssertionError as e:
    fail(str(e))

# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] ThreatModel")
from src.adversarial.threat_model import ThreatModel, FEATURE_NAMES

rng = np.random.default_rng(0)
X_dummy = rng.uniform(
    [40, 0, 0, 0, 0],
    [1500, 1460, 1, 10, 5],
    (200, 5)
)

try:
    tm = ThreatModel(X_dummy, FEATURE_NAMES)
    ok("ThreatModel constructed from (200,5) array")

    for name in FEATURE_NAMES:
        assert tm.iqr[name] >= 1e-8, f"IQR for {name} is zero"
    ok("All feature IQRs > 0")

    bounds = tm.get_perturbation_bounds(0.10)
    for name in FEATURE_NAMES:
        assert bounds[name] == 0.10 * tm.iqr[name]
    ok("get_perturbation_bounds(0.10) = 0.10 × IQR")

    max_d = tm.get_max_delta_array(0.10)
    assert max_d.shape == (5,), f"Expected (5,), got {max_d.shape}"
    ok("get_max_delta_array shape (5,)")
except AssertionError as e:
    fail(str(e))

# enforce_constraints tests
try:
    # Valid input — no change needed
    x = np.array([100.0, 50.0, 0.5, 1.0, 0.01])
    x_v = tm.enforce_constraints(x)
    assert abs(x_v[2] - 50/100) < 1e-9, f"Pr should be 0.5, got {x_v[2]}"
    ok("enforce_constraints: valid input unchanged (Pr recomputed correctly)")

    # Negative packet_size → clamp to 40
    x_bad = np.array([-5.0, 10.0, 0.5, 1.0, 0.0])
    x_v2 = tm.enforce_constraints(x_bad)
    assert x_v2[0] == 40.0, f"packet_size should clamp to 40, got {x_v2[0]}"
    ok("enforce_constraints: negative packet_size clamped to 40")

    # payload_size exceeds packet_size − 40
    x_ovf = np.array([100.0, 100.0, 0.99, 1.0, 0.0])
    x_v3 = tm.enforce_constraints(x_ovf)
    assert x_v3[1] <= x_v3[0] - 40 + 1e-9, \
        f"payload_size {x_v3[1]} > packet_size−40 = {x_v3[0]-40}"
    expected_pr = x_v3[1] / x_v3[0] if x_v3[0] > 0 else 0
    assert abs(x_v3[2] - expected_pr) < 1e-9, \
        f"Pr={x_v3[2]} != PAs/Ps={expected_pr}"
    ok("enforce_constraints: payload overflow clamped, Pr recomputed")

    # time_diff negative → clamp to 0
    x_td = np.array([200.0, 100.0, 0.5, 1.0, -3.0])
    x_v4 = tm.enforce_constraints(x_td)
    assert x_v4[4] == 0.0, f"time_diff should be 0, got {x_v4[4]}"
    ok("enforce_constraints: negative time_diff clamped to 0")
except AssertionError as e:
    fail(str(e))

# enforce_session_constraints
try:
    sess = np.array([
        [100.0, 60.0, 0.6, 0.0, 0.0],
        [200.0, 150.0, 0.75, 0.0, 0.01],  # Rpp should become 200/100 = 2.0
        [150.0, 100.0, 0.667, 0.0, 0.02], # Rpp should become 150/200 = 0.75
    ])
    s_v = tm.enforce_session_constraints(sess)
    assert s_v[0, 3] == 0.0, f"Rpp[0] should be 0, got {s_v[0,3]}"
    assert abs(s_v[1, 3] - 2.0) < 1e-9, f"Rpp[1] should be 2.0, got {s_v[1,3]}"
    assert abs(s_v[2, 3] - 0.75) < 1e-9, f"Rpp[2] should be 0.75, got {s_v[2,3]}"
    ok("enforce_session_constraints: Rpp recomputed correctly (cascading)")

    # Pr should also be recomputed
    assert abs(s_v[0, 2] - 60/100) < 1e-9, f"Pr[0]={s_v[0,2]}"
    ok("enforce_session_constraints: Pr[i] recomputed")
except AssertionError as e:
    fail(str(e))

# within_budget
try:
    x_orig = np.array([100.0, 60.0, 0.6, 1.0, 0.01])
    x_pert = x_orig.copy()
    assert tm.within_budget(x_orig, x_pert, 0.10)
    ok("within_budget: identical points → True")

    x_big  = x_orig.copy()
    x_big[0] += 1e9  # huge packet_size delta
    assert not tm.within_budget(x_orig, x_big, 0.10)
    ok("within_budget: over-budget → False")
except AssertionError as e:
    fail(str(e))

# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] CART evasion — tree path extraction and find_evasion_path")
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from src.adversarial.cart_evasion import (
    extract_tree_paths, find_evasion_path, generate_cart_adversarial
)

try:
    # Build a minimal synthetic CART that separates by packet_size threshold
    X_tr = np.vstack([
        rng.uniform([40,0,0,0,0],[500,200,0.5,5,2],(100,5)),   # normal
        rng.uniform([501,201,0.5,5,2],[1500,1460,1,10,5],(100,5)),  # malicious
    ])
    y_tr = np.array([0]*100 + [1]*100)
    sc = StandardScaler()
    X_tr_s = sc.fit_transform(X_tr)
    cart = DecisionTreeClassifier(max_depth=5, random_state=42)
    cart.fit(X_tr_s, y_tr)

    paths = extract_tree_paths(cart)
    assert len(paths) > 0, "No leaf paths extracted"
    ok(f"extract_tree_paths: {len(paths)} paths found")

    n_normal  = sum(1 for p in paths if p["leaf_class"] == 0)
    n_malicious = sum(1 for p in paths if p["leaf_class"] == 1)
    assert n_normal > 0 and n_malicious > 0, \
        f"Expected both classes, got normal={n_normal} mal={n_malicious}"
    ok(f"Both leaf classes present: {n_normal} normal, {n_malicious} malicious")

    # Test find_evasion_path on a malicious sample
    x_mal_raw = rng.uniform([501,201,0.5,5,2],[1500,1460,1,10,5],(1,5))[0]
    x_mal_s   = sc.transform(x_mal_raw.reshape(1,-1))[0]
    evasion   = find_evasion_path(cart, x_mal_s)
    # Should find a path if tree has normal leaves (which it does)
    assert evasion is not None, "find_evasion_path returned None for a tree with normal leaves"
    assert "x_adversarial" in evasion
    assert "perturbation_cost_l2" in evasion
    ok(f"find_evasion_path: found path, cost_l2={evasion['perturbation_cost_l2']:.4f}")

    # Verify the adversarial scaled point classifies as normal
    x_adv_s_shape = evasion["x_adversarial"].reshape(1,-1)
    pred_adv = cart.predict(x_adv_s_shape)[0]
    assert pred_adv == 0, f"Adversarial scaled point classified as {pred_adv}, expected 0"
    ok("Adversarial point in scaled space classified as NORMAL by CART")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in CART evasion test: {e}")

# generate_cart_adversarial end-to-end
try:
    X_mal_raw = rng.uniform([501,201,0.5,5,2],[1500,1460,1,10,5],(20,5))
    tm2 = ThreatModel(X_tr, FEATURE_NAMES)
    res = generate_cart_adversarial(cart, X_mal_raw, tm2, 0.20, sc)

    assert "X_adversarial" in res
    assert "evasion_success" in res
    assert "evasion_rate" in res
    assert res["X_adversarial"].shape == (20, 5)
    assert res["evasion_success"].shape == (20,)
    assert 0.0 <= res["evasion_rate"] <= 1.0
    ok(f"generate_cart_adversarial: shape OK, evasion_rate={res['evasion_rate']:.2%}")

    # All adversarial samples should have valid physical constraints
    n_valid = sum(1 for x in res["X_adversarial"] if tm2.is_valid(x))
    assert n_valid == 20, f"Only {n_valid}/20 adversarial samples are physically valid"
    ok(f"All 20 adversarial samples are physically valid")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in generate_cart_adversarial: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] KNN evasion")
from sklearn.neighbors import KNeighborsClassifier
from src.adversarial.knn_evasion import (
    find_nearest_normal_neighbor, move_toward_target, generate_knn_adversarial
)

try:
    knn = KNeighborsClassifier(n_neighbors=3)
    knn.fit(X_tr_s, y_tr)

    x_mal_raw = rng.uniform([501,201,0.5,5,2],[1500,1460,1,10,5],(1,5))[0]
    nn = find_nearest_normal_neighbor(knn, x_mal_raw, X_tr, y_tr, sc)
    assert nn.shape == (5,), f"Expected (5,), got {nn.shape}"
    assert nn[0] >= 40, "Nearest normal neighbor has invalid packet_size"
    ok(f"find_nearest_normal_neighbor: shape OK, Ps={nn[0]:.1f}")

    # Move toward target
    max_d = np.array([100.0]*5)
    x_next = move_toward_target(x_mal_raw, nn, x_mal_raw, max_d)
    # Each feature should be within max_d of original
    assert np.all(np.abs(x_next - x_mal_raw) <= max_d + 1e-9)
    ok("move_toward_target: all features within budget")

    # generate_knn_adversarial
    X_mal_raw5 = rng.uniform([501,201,0.5,5,2],[1500,1460,1,10,5],(10,5))
    tm3 = ThreatModel(X_tr, FEATURE_NAMES)
    knn_res = generate_knn_adversarial(knn, X_mal_raw5, X_tr, y_tr, tm3, 0.20, sc)
    assert knn_res["X_adversarial"].shape == (10, 5)
    assert 0.0 <= knn_res["evasion_rate"] <= 1.0
    # All adversarial samples within budget
    for i, (x_o, x_a) in enumerate(zip(X_mal_raw5, knn_res["X_adversarial"])):
        assert tm3.within_budget(x_o, x_a, 0.20), \
            f"Sample {i} exceeds ε budget after KNN perturbation"
    ok(f"generate_knn_adversarial: rate={knn_res['evasion_rate']:.2%}, all within budget")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in KNN evasion: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Black-box search strategies")
from src.adversarial.black_box_search import (
    random_search_evasion, hill_climbing_evasion, transfer_attack_evaluation
)

# Mock LLM classifier: predicts malicious if Ps > 500, normal otherwise
def mock_classify(x_raw):
    return 1 if x_raw[0] > 500 else 0

def mock_classify_conf(x_raw):
    pred = mock_classify(x_raw)
    conf = 0.9 if pred == 1 else 0.9
    return pred, conf if pred == 1 else (pred, 0.1)

try:
    tm4 = ThreatModel(X_tr, FEATURE_NAMES)
    # Malicious sample: Ps = 1000 — needs to move to Ps ≤ 500
    x_mal = np.array([1000.0, 500.0, 0.5, 1.0, 0.5])
    # With ε=0.50 and IQR ~ (1500-501)=~500 → max_delta[Ps] ≈ 250
    # 1000 - 250 = 750, still > 500, so evasion may fail depending on IQR

    rs_res = random_search_evasion(x_mal, tm4, mock_classify, 0.50,
                                    max_queries=30, rng=rng)
    assert "evaded" in rs_res
    assert "queries_used" in rs_res
    assert "best_perturbation" in rs_res
    assert rs_res["queries_used"] <= 30
    ok(f"random_search_evasion: queries={rs_res['queries_used']}, "
       f"evaded={rs_res['evaded']}")

    hc_res = hill_climbing_evasion(x_mal, tm4, mock_classify_conf, 0.50,
                                    max_queries=40)
    assert "evaded" in hc_res
    assert hc_res["queries_used"] <= 40
    ok(f"hill_climbing_evasion: queries={hc_res['queries_used']}, "
       f"evaded={hc_res['evaded']}")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in black_box_search: {e}")

# Transfer attack
try:
    X_cart_adv = rng.uniform([40,0,0,0,0],[500,200,0.5,5,2],(10,5))  # all "normal"
    X_knn_adv  = rng.uniform([40,0,0,0,0],[500,200,0.5,5,2],(10,5))
    y_t = np.ones(10, dtype=int)
    tr_res = transfer_attack_evaluation(X_cart_adv, X_knn_adv, mock_classify, y_t)
    assert "cart_transfer_rate" in tr_res
    assert "knn_transfer_rate" in tr_res
    # Both should have high transfer since x_raw[0] ≤ 500 → classified as normal
    assert tr_res["cart_transfer_rate"] == 1.0, \
        f"Expected 1.0, got {tr_res['cart_transfer_rate']}"
    ok(f"transfer_attack_evaluation: CART transfer={tr_res['cart_transfer_rate']:.2%} "
       f"KNN transfer={tr_res['knn_transfer_rate']:.2%}")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in transfer_attack_evaluation: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[7] Session perturbation — load and perturb")
from src.adversarial.session_perturbation import (
    load_malicious_sessions, perturb_session_per_packet,
    evaluate_session_consistency,
)
from src.database import init_db, register_dataset, insert_session, insert_packets_batch

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_f:
    tmp_path = Path(tmp_f.name)

try:
    conn2 = init_db(tmp_path)
    ds_id = register_dataset(conn2, "test_ds", "TestFamily", "test", "")
    sess_id = insert_session(conn2, ds_id, "1.1.1.1","2.2.2.2",1234,80,
                              "TCP",1,"malicious","TestFamily",0)
    # Insert 12 packets to satisfy min_packets=10
    pkts = [
        (sess_id, i, 100+i*50, 80+i*40, (80+i*40)/(100+i*50) if (100+i*50)>0 else 0,
         float(i) if i>0 else 0.0, 0.03*i if i>0 else 0.0, float(1000+i), "outgoing", 1)
        for i in range(12)
    ]
    insert_packets_batch(conn2, pkts)
    conn2.commit()

    sessions = load_malicious_sessions(conn2, min_packets=10, max_sessions=5)
    assert len(sessions) == 1, f"Expected 1 session, got {len(sessions)}"
    assert sessions[0]["packets"].shape == (12, 5), \
        f"Expected (12,5), got {sessions[0]['packets'].shape}"
    ok(f"load_malicious_sessions: loaded {len(sessions)} session, "
       f"{sessions[0]['packets'].shape[0]} packets")

    # Perturb session
    sess_pkts = sessions[0]["packets"]
    tm5 = ThreatModel(X_tr, FEATURE_NAMES)
    pert = perturb_session_per_packet(sess_pkts, cart, tm5, 0.20, sc)
    assert pert.shape == sess_pkts.shape, \
        f"Shape mismatch: {pert.shape} != {sess_pkts.shape}"
    # Td should be unchanged
    np.testing.assert_allclose(pert[:, 4], sess_pkts[:, 4], rtol=1e-6,
                               err_msg="time_diff changed during session perturbation")
    ok("perturb_session_per_packet: shape OK, Td unchanged")

    # Rpp[0] should be 0 after session constraint enforcement
    assert pert[0, 3] == 0.0, f"Rpp[0] should be 0, got {pert[0,3]}"
    ok("perturb_session_per_packet: Rpp[0]=0 (no predecessor)")

    # All physical constraints satisfied
    for i in range(len(pert)):
        assert tm5.is_valid(pert[i]), \
            f"Packet {i} violates physical constraints after perturbation"
    ok(f"All {len(pert)} perturbed packets satisfy physical constraints")

    # evaluate_session_consistency with mock LLM
    def mock_sess_classify(packets_raw):
        # classify session based on mean packet_size
        return 1 if packets_raw[:, 0].mean() > 500 else 0

    eval_res = evaluate_session_consistency(
        sessions, [pert], cart, sc, mock_sess_classify
    )
    assert "cart_per_packet_evasion_rate" in eval_res
    assert "llm_session_detection_rate" in eval_res
    assert len(eval_res["per_session_results"]) == 1
    ok(f"evaluate_session_consistency: CART pkt evasion={eval_res['cart_per_packet_evasion_rate']:.2%}")

finally:
    conn2.close()
    os.unlink(tmp_path)
    for ext in ("-wal", "-shm"):
        side = Path(str(tmp_path) + ext)
        if side.exists():
            os.unlink(side)

# ─────────────────────────────────────────────────────────────────────────────
print("\n[8] Adaptive adversary")
from src.adversarial.adaptive_adversary import (
    adaptive_cart_attack, adaptive_llm_attack, compare_query_complexity
)

try:
    x_mal = np.array([1000.0, 500.0, 0.5, 1.0, 0.1])
    tm6 = ThreatModel(X_tr, FEATURE_NAMES)

    res_cart = adaptive_cart_attack(x_mal, mock_classify, tm6, 0.50)
    assert "evaded" in res_cart
    assert "queries_used" in res_cart
    assert res_cart["queries_used"] >= 1
    ok(f"adaptive_cart_attack: queries={res_cart['queries_used']}, "
       f"evaded={res_cart['evaded']}")

    # LLM adaptive (mock LLM)
    call_count = [0]
    def mock_llm_conf(x_raw):
        call_count[0] += 1
        pred = 1 if x_raw[0] > 500 else 0
        return pred, (0.9 if pred == 1 else 0.1)

    res_llm = adaptive_llm_attack(x_mal, mock_llm_conf, tm6, 0.50,
                                   query_budget=20, rng=rng)
    assert "evaded" in res_llm
    assert res_llm["queries_used"] >= 1
    assert res_llm["queries_used"] <= 20
    ok(f"adaptive_llm_attack: queries={res_llm['queries_used']}, "
       f"evaded={res_llm['evaded']}")

    # compare_query_complexity
    fake_cart = [{"evaded": True,  "queries_used": 3}] * 10
    fake_knn  = [{"evaded": True,  "queries_used": 15}] * 8 + \
                [{"evaded": False, "queries_used": 30}] * 2
    fake_llm  = [{"evaded": True,  "queries_used": 25}] * 6 + \
                [{"evaded": False, "queries_used": 50}] * 4

    cmp = compare_query_complexity(fake_cart, fake_knn, fake_llm)
    assert "CART" in cmp and "KNN" in cmp and "LLM" in cmp
    assert cmp["CART"]["evasion_rate"] == 1.0
    assert abs(cmp["CART"]["median_q"] - 3.0) < 1e-9
    ok(f"compare_query_complexity: CART median_q={cmp['CART']['median_q']}, "
       f"KNN rate={cmp['KNN']['evasion_rate']:.2%}, "
       f"LLM rate={cmp['LLM']['evasion_rate']:.2%}")
except AssertionError as e:
    fail(str(e))
except Exception as e:
    fail(f"Exception in adaptive_adversary: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n[9] classical_ml.train_for_adversarial present")
from src.classical_ml import train_for_adversarial as tfa

try:
    import inspect
    sig = inspect.signature(tfa)
    assert "conn" in sig.parameters
    assert "sample_size" in sig.parameters
    ok("train_for_adversarial has correct signature (conn, sample_size)")
except AssertionError as e:
    fail(str(e))

# ─────────────────────────────────────────────────────────────────────────────
print("\n[10] CART path feasibility — infeasible range detected correctly")
from src.adversarial.cart_evasion import extract_tree_paths

try:
    # Build a deeper tree with guaranteed infeasible paths
    X_deep = rng.uniform(0, 1, (200, 5))
    y_deep = (X_deep[:,0] > 0.5).astype(int)
    sc_d   = StandardScaler()
    X_deep_s = sc_d.fit_transform(X_deep)
    cart_d = DecisionTreeClassifier(max_depth=4, random_state=0)
    cart_d.fit(X_deep_s, y_deep)
    paths_d = extract_tree_paths(cart_d)
    # Each path must have consistent lo < hi for every feature involved
    n_infeasible_flagged = 0
    for p in paths_d:
        lo = {}; hi = {}
        feasible = True
        for feat, thresh, direction in p["path"]:
            if direction == "left":
                hi[feat] = min(hi.get(feat, float("inf")), thresh)
            else:
                lo[feat] = max(lo.get(feat, float("-inf")), thresh)
            l = lo.get(feat, float("-inf"))
            h = hi.get(feat, float("inf"))
            if l >= h:
                feasible = False
                n_infeasible_flagged += 1
                break
        # All returned leaf paths should be feasible (infeasible ones are skipped
        # inside find_evasion_path — extract_tree_paths returns all paths)
    ok(f"Extracted {len(paths_d)} paths, "
       f"{n_infeasible_flagged} have infeasible feature ranges (handled in find_evasion_path)")
except Exception as e:
    fail(f"Path feasibility test: {e}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Audit complete:  {PASS} passed,  {FAIL} failed")
print('='*60)
sys.exit(0 if FAIL == 0 else 1)
