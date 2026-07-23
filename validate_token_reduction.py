#!/usr/bin/env python3
"""
Token-cost validation script.

Measures the actual token reduction achieved by compact formatting compared
to verbose formatting across all prompt types, WITHOUT making any API calls.

Runs entirely offline using tiktoken (OpenAI tokenizer, a close proxy for
Claude as well) or falls back to a simple whitespace-word count.

Usage:
    python validate_token_reduction.py
    python validate_token_reduction.py --n 1000   # sample size
"""

import sys
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from configs.config import DB_PATH, LLM_CONFIG
from src.database import get_db
from src.llm_experiments import (
    FEATURE_COLS,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_COMPACT_PACKET,
    SYSTEM_PROMPT_COMPACT_SESSION,
    PROMPT_ZERO_SHOT, PROMPT_FEW_SHOT, PROMPT_COT,
    PROMPT_SESSION_VERBOSE, PROMPT_SESSION_COMPACT,
    format_packet_verbose, format_packet_compact,
    format_session_verbose, format_session_compact,
    compute_session_profile,
    load_test_samples,
)

# ---------------------------------------------------------------------------
# Tokenizer — tiktoken preferred, word-count fallback
# ---------------------------------------------------------------------------

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / Claude proxy

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))

    TOKENIZER = "tiktoken/cl100k_base"
except ImportError:
    def count_tokens(text: str) -> int:
        """Rough word-count proxy (~1.3 tokens per word on average)."""
        return max(1, int(len(text.split()) * 1.3))

    TOKENIZER = "word-count proxy (pip install tiktoken for exact counts)"


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------

def measure_packet_prompt(row, sys_verbose: str, sys_compact: str) -> dict:
    """Compare verbose vs compact for a single-packet zero-shot prompt."""
    feat_v = format_packet_verbose(row)
    feat_c = format_packet_compact(row)

    prompt_v = PROMPT_ZERO_SHOT.format(features=feat_v)
    prompt_c = PROMPT_ZERO_SHOT.format(features=feat_c)

    tok_v = count_tokens(sys_verbose + prompt_v)
    tok_c = count_tokens(sys_compact + prompt_c)

    return {"verbose": tok_v, "compact": tok_c,
            "saved": tok_v - tok_c,
            "pct_saved": 100.0 * (tok_v - tok_c) / tok_v if tok_v > 0 else 0}


def measure_cot_prompt(row, sys_verbose: str, sys_compact: str) -> dict:
    """Compare verbose vs compact for a chain-of-thought prompt."""
    feat_v = format_packet_verbose(row)
    feat_c = format_packet_compact(row)

    prompt_v = PROMPT_COT.format(features=feat_v)
    prompt_c = PROMPT_COT.format(features=feat_c)

    tok_v = count_tokens(sys_verbose + prompt_v)
    tok_c = count_tokens(sys_compact + prompt_c)

    return {"verbose": tok_v, "compact": tok_c,
            "saved": tok_v - tok_c,
            "pct_saved": 100.0 * (tok_v - tok_c) / tok_v if tok_v > 0 else 0}


def measure_few_shot_prompt(query_row, example_df: pd.DataFrame,
                            k: int,
                            sys_verbose: str, sys_compact: str) -> dict:
    """Compare verbose vs compact for a k-shot prompt."""
    # Verbose: first k rows as static examples
    ex_v_lines = []
    for _, ex in example_df.head(k).iterrows():
        label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
        ex_v_lines.append(f"[{label}] {format_packet_verbose(ex)}")

    # Compact: first k rows as compact examples
    ex_c_lines = []
    for _, ex in example_df.head(k).iterrows():
        label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
        ex_c_lines.append(f"[{label}] {format_packet_compact(ex)}")

    prompt_v = PROMPT_FEW_SHOT.format(
        examples="\n".join(ex_v_lines),
        features=format_packet_verbose(query_row)
    )
    prompt_c = PROMPT_FEW_SHOT.format(
        examples="\n".join(ex_c_lines),
        features=format_packet_compact(query_row)
    )

    tok_v = count_tokens(sys_verbose + prompt_v)
    tok_c = count_tokens(sys_compact + prompt_c)

    return {"verbose": tok_v, "compact": tok_c,
            "saved": tok_v - tok_c,
            "pct_saved": 100.0 * (tok_v - tok_c) / tok_v if tok_v > 0 else 0}


def measure_session_prompt(pkts: pd.DataFrame,
                            sys_verbose: str, sys_compact: str) -> dict:
    """Compare verbose (raw rows) vs compact (statistical profile)."""
    sess_v = format_session_verbose(pkts.to_dict("records"))
    sess_c = format_session_compact(pkts)

    prompt_v = PROMPT_SESSION_VERBOSE.format(session=sess_v)
    prompt_c = PROMPT_SESSION_COMPACT.format(session=sess_c)

    tok_v = count_tokens(sys_verbose + prompt_v)
    tok_c = count_tokens(sys_compact + prompt_c)

    return {"verbose": tok_v, "compact": tok_c,
            "saved": tok_v - tok_c,
            "pct_saved": 100.0 * (tok_v - tok_c) / tok_v if tok_v > 0 else 0,
            "n_packets": len(pkts)}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarise(label: str, measurements: list[dict]) -> None:
    if not measurements:
        print(f"  {label}: no data")
        return

    v_tok = [m["verbose"] for m in measurements]
    c_tok = [m["compact"] for m in measurements]
    pct   = [m["pct_saved"] for m in measurements]

    print(f"\n  {label}")
    print(f"    Samples:          {len(measurements)}")
    print(f"    Verbose  tokens:  mean={np.mean(v_tok):.0f}  "
          f"min={np.min(v_tok)}  max={np.max(v_tok)}")
    print(f"    Compact  tokens:  mean={np.mean(c_tok):.0f}  "
          f"min={np.min(c_tok)}  max={np.max(c_tok)}")
    print(f"    Saved    tokens:  mean={np.mean(pct):.1f}%  "
          f"min={np.min(pct):.1f}%  max={np.max(pct):.1f}%")

    # Extrapolate to full experiment run
    n_calls = {
        "4A zero-shot":     LLM_CONFIG["zero_shot_sample_size"],
        "4C chain-of-thought": LLM_CONFIG["cot_sample_size"],
        "4B few-shot (k=5)": LLM_CONFIG["few_shot_sample_size"],
        "4D LOFO":          LLM_CONFIG["lofo_sample_per_family"] * 10,
        "4E session w=50":  LLM_CONFIG["session_sample_size"],
    }
    for exp_label, n in n_calls.items():
        if label.split()[0].lower() in exp_label.lower():
            saved_total = int(np.mean(pct) / 100 * np.mean(v_tok) * n)
            cost_saved  = saved_total * 0.000003
            print(f"    Projected savings over {n} calls "
                  f"({exp_label}): ~{saved_total:,} tokens  (~${cost_saved:.2f})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Measure token reduction: verbose vs compact formatting"
    )
    parser.add_argument("--n", type=int, default=200,
                        help="Number of packets to sample (default 200)")
    args = parser.parse_args()

    print("=" * 70)
    print("Token Reduction Validation")
    print(f"Tokenizer: {TOKENIZER}")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"\n[ERROR] Database not found at {DB_PATH}")
        print("Run feature_extraction.py first.")
        sys.exit(1)

    conn = get_db()
    cur  = conn.execute("SELECT COUNT(*) FROM packets")
    pkt_count = cur.fetchone()[0]
    print(f"Database: {pkt_count:,} packets")

    n   = min(args.n, pkt_count)
    df  = load_test_samples(conn, n)

    if len(df) < 10:
        print("[ERROR] Not enough data in database for validation.")
        conn.close()
        sys.exit(1)

    # Two compact system prompts — packet-level experiments get the short one,
    # session-level (4E) gets the full profile-description variant.
    sys_v        = SYSTEM_PROMPT_BASE
    sys_c_pkt    = SYSTEM_PROMPT_COMPACT_PACKET
    sys_c_sess   = SYSTEM_PROMPT_COMPACT_SESSION

    print(f"\nSystem prompt sizes:")
    print(f"  Verbose:         {count_tokens(sys_v)} tokens")
    print(f"  Compact (packet): {count_tokens(sys_c_pkt)} tokens")
    print(f"  Compact (session):{count_tokens(sys_c_sess)} tokens")
    print(f"\nSampling {len(df)} packets for token measurement...")

    # --- 4A / 4C: single-packet prompts (use compact_packet system prompt) ---
    zs_measurements  = []
    cot_measurements = []
    for _, row in df.iterrows():
        zs_measurements.append(measure_packet_prompt(row, sys_v, sys_c_pkt))
        cot_measurements.append(measure_cot_prompt(row, sys_v, sys_c_pkt))

    # --- 4B: few-shot (k=5, use compact_packet system prompt) ---
    fs_measurements = []
    example_pool = df[df["is_malicious"] == 1].head(20)
    if len(example_pool) >= 5:
        for _, row in df.head(min(50, len(df))).iterrows():
            fs_measurements.append(
                measure_few_shot_prompt(row, example_pool, k=5,
                                        sys_verbose=sys_v,
                                        sys_compact=sys_c_pkt)
            )

    # --- 4E: session windows (use compact_session system prompt) ---
    sess_measurements: dict[int, list] = {}
    for window_size in LLM_CONFIG["window_sizes"]:
        sess_query = f"""
            SELECT s.id, s.is_malicious
            FROM sessions s
            WHERE (SELECT COUNT(*) FROM packets p WHERE p.session_id = s.id)
                  >= {window_size}
            ORDER BY RANDOM() LIMIT 30
        """
        sessions = pd.read_sql_query(sess_query, conn)
        measurements = []
        for _, sess in sessions.iterrows():
            pkt_query = """
                SELECT packet_size, payload_size, payload_ratio,
                       ratio_to_prev, time_diff
                FROM packets WHERE session_id = ?
                ORDER BY packet_idx LIMIT ?
            """
            pkts = pd.read_sql_query(
                pkt_query, conn, params=[int(sess["id"]), window_size]
            )
            if len(pkts) >= window_size:
                measurements.append(
                    measure_session_prompt(pkts.head(window_size),
                                          sys_v, sys_c_sess)
                )
        if measurements:
            sess_measurements[window_size] = measurements

    conn.close()

    # --- Print results ---
    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)

    summarise("4A zero-shot (single packet)", zs_measurements)
    summarise("4C chain-of-thought (single packet)", cot_measurements)
    summarise("4B few-shot k=5 (5 examples + query)", fs_measurements)

    for ws, meas in sorted(sess_measurements.items()):
        summarise(f"4E session w={ws} (statistical profile vs raw rows)", meas)

    # --- Overall summary ---
    all_pct = ([m["pct_saved"] for m in zs_measurements] +
               [m["pct_saved"] for m in cot_measurements] +
               [m["pct_saved"] for m in fs_measurements] +
               [m["pct_saved"] for m in sum(sess_measurements.values(), [])])
    if all_pct:
        print(f"\n{'='*70}")
        print(f"Overall average token reduction: {np.mean(all_pct):.1f}%")
        print(f"Range: {np.min(all_pct):.1f}% – {np.max(all_pct):.1f}%")

        # Cost projection for a full 4A run
        full_run_verbose_tok = int(
            np.mean([m["verbose"] for m in zs_measurements]) *
            LLM_CONFIG["zero_shot_sample_size"]
        )
        full_run_compact_tok = int(
            np.mean([m["compact"] for m in zs_measurements]) *
            LLM_CONFIG["zero_shot_sample_size"]
        )
        print(f"\nProjected 4A ({LLM_CONFIG['zero_shot_sample_size']} calls):")
        print(f"  Verbose:  {full_run_verbose_tok:>10,} tokens  "
              f"~${full_run_verbose_tok * 0.000003:.2f}")
        print(f"  Compact:  {full_run_compact_tok:>10,} tokens  "
              f"~${full_run_compact_tok * 0.000003:.2f}")
        print(f"  Savings:  {full_run_verbose_tok - full_run_compact_tok:>10,} tokens  "
              f"~${(full_run_verbose_tok - full_run_compact_tok) * 0.000003:.2f}")
        print("=" * 70)


if __name__ == "__main__":
    main()
