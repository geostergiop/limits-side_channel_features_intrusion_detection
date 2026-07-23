#!/usr/bin/env python3
"""
Phase 4: LLM-Based Classification Experiments (THE NOVEL CONTRIBUTION).

Experiments:
  4A — Zero-Shot Classification (Gap 1)
  4B — Few-Shot Classification (Gap 1)  [embedding-based retrieval in compact mode]
  4C — Chain-of-Thought with Explainability (Gap 1 + practical value)
  4D — Leave-One-Family-Out / Zero-Shot Novel Attack Detection (Gap 2)
       [embedding-based retrieval in compact mode]
  4E — Session-Level Windowed Analysis (Gap 1 extension)
       [statistical profile in compact mode — replaces raw packet dump]

Formatting modes
----------------
  verbose (default)  natural-language labels, ~28 tokens per packet
  compact            JSON array + statistical profile, ~8 tokens per packet
                     for session windows.  Use --compact to activate.

Embedding-based few-shot retrieval
-----------------------------------
  When --compact is active, experiments 4B and 4D retrieve the k nearest
  examples by cosine similarity over the 5-feature vector instead of
  sampling randomly.  Requires sentence-transformers or falls back to
  sklearn NearestNeighbors on raw features.
"""

import re
import sys
import os
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix
)
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import (
    LLM_CONFIG, SIDE_CHANNEL_FEATURES, RESULTS_DIR, DB_PATH,
    FAMILY_GROUPS, FAMILY_TO_GROUP
)
from src.database import get_db

# Feature column order used everywhere — single source of truth
FEATURE_COLS = ["packet_size", "payload_size", "payload_ratio",
                "ratio_to_prev", "time_diff"]


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Unified client for Anthropic Claude and OpenAI GPT APIs.
    Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables.
    """

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.total_tokens = 0
        self.total_calls = 0

        if provider == "anthropic":
            try:
                import anthropic
            except ImportError:
                raise RuntimeError("pip install anthropic")
            api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Run: export ANTHROPIC_API_KEY='sk-ant-...'"
                )
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = LLM_CONFIG["anthropic_model"]
        elif provider == "openai":
            try:
                import openai
            except ImportError:
                raise RuntimeError("pip install openai")
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. "
                    "Run: export OPENAI_API_KEY='sk-...'"
                )
            self.client = openai.OpenAI(api_key=api_key)
            self.model = LLM_CONFIG["openai_model"]
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _openai_supports_temperature(self) -> bool:
        """GPT-5-family models use Responses API reasoning controls instead."""
        return not str(self.model).startswith("gpt-5")

    def _openai_chat_uses_completion_token_param(self) -> bool:
        """Newer reasoning/chat models reject legacy Chat Completions max_tokens."""
        model = str(self.model).lower()
        return model.startswith(("gpt-5", "o1", "o3", "o4"))

    def _openai_effective_max_tokens(self, requested_max_tokens: int) -> int:
        """Reasoning models need enough completion budget for hidden tokens plus JSON."""
        if not self._openai_chat_uses_completion_token_param():
            return int(requested_max_tokens)
        minimum = int(LLM_CONFIG.get("openai_min_completion_tokens", requested_max_tokens))
        return max(int(requested_max_tokens), minimum)

    def _openai_responses_kwargs(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        kwargs = {
            "model": self.model,
            "max_output_tokens": max_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}],
                },
            ],
        }
        if self._openai_supports_temperature():
            kwargs["temperature"] = LLM_CONFIG["temperature"]
        else:
            reasoning_effort = LLM_CONFIG.get("openai_reasoning_effort")
            text_verbosity = LLM_CONFIG.get("openai_text_verbosity")
            if reasoning_effort:
                kwargs["reasoning"] = {"effort": reasoning_effort}
            if text_verbosity:
                kwargs["text"] = {"verbosity": text_verbosity}
        return kwargs

    def _openai_chat_kwargs(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        token_param = "max_completion_tokens" if self._openai_chat_uses_completion_token_param() else "max_tokens"
        kwargs[token_param] = max_tokens
        if self._openai_supports_temperature():
            kwargs["temperature"] = LLM_CONFIG["temperature"]
        return kwargs

    def classify(self, system_prompt: str, user_prompt: str,
                 max_retries: int = 3,
                 max_tokens: int = None) -> dict:
        """
        Send prompt to LLM, return parsed result dict:
          {prediction: 0|1, confidence: float, reasoning: str,
           tokens: int, latency_ms: float, raw_response: str}

        max_tokens overrides LLM_CONFIG["max_tokens"] for this call only.
        Use a higher value (e.g. 1024) for chain-of-thought prompts that
        need to complete step-by-step reasoning before outputting JSON.
        """
        _max_tokens = max_tokens if max_tokens is not None else LLM_CONFIG["max_tokens"]
        if self.provider == "openai":
            _max_tokens = self._openai_effective_max_tokens(int(_max_tokens))

        for attempt in range(max_retries):
            try:
                t0 = time.time()

                if self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=_max_tokens,
                        temperature=LLM_CONFIG["temperature"],
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    text   = response.content[0].text
                    tokens = response.usage.input_tokens + response.usage.output_tokens

                elif self.provider == "openai":
                    # Prefer the Responses API when available; fall back to Chat
                    # Completions for compatibility with older client builds.
                    if hasattr(self.client, "responses"):
                        try:
                            response = self.client.responses.create(
                                **self._openai_responses_kwargs(system_prompt, user_prompt, _max_tokens)
                            )
                            text = getattr(response, "output_text", "") or ""
                            usage = getattr(response, "usage", None)
                            input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage is not None else 0
                            output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage is not None else 0
                            tokens = input_tokens + output_tokens
                        except Exception:
                            response = self.client.chat.completions.create(
                                **self._openai_chat_kwargs(system_prompt, user_prompt, _max_tokens)
                            )
                            text = response.choices[0].message.content or ""
                            tokens = int(getattr(response.usage, "total_tokens", 0) or 0)
                    else:
                        response = self.client.chat.completions.create(
                            **self._openai_chat_kwargs(system_prompt, user_prompt, _max_tokens)
                        )
                        text = response.choices[0].message.content or ""
                        tokens = int(getattr(response.usage, "total_tokens", 0) or 0)

                latency = (time.time() - t0) * 1000
                self.total_tokens += tokens
                self.total_calls  += 1

                result = self._parse_response(text)
                result["tokens"]       = tokens
                result["latency_ms"]   = latency
                result["raw_response"] = text
                return result

            except Exception as e:
                err_str = str(e).lower()
                # Auth errors will never resolve on retry — fail immediately.
                if any(kw in err_str for kw in
                       ("api_key", "auth_token", "authentication",
                        "authorization", "403", "401")):
                    raise RuntimeError(
                        f"Authentication failed - check your API key: {e}"
                    ) from e
                if attempt < max_retries - 1:
                    wait = LLM_CONFIG["retry_delay_seconds"] * (attempt + 1)
                    print(f"    [RETRY] {e} - waiting {wait}s...")
                    time.sleep(wait)
                else:
                    return {
                        "prediction": -1, "confidence": 0.0,
                        "reasoning": f"ERROR: {e}",
                        "tokens": 0, "latency_ms": 0, "raw_response": ""
                    }

    def _parse_response(self, text: str) -> dict:
        """
        Parse LLM text into {prediction, confidence, reasoning}.

        Uses a stack-based JSON extractor so that reasoning fields containing
        curly braces (common in CoT responses) do not break the match.
        Tries candidates from last to first — CoT puts the JSON at the END.

        Falls back to keyword scanning restricted to the final 200 characters,
        which avoids CoT step-by-step analysis text (that mentions malicious
        patterns as negative examples) poisoning the verdict.
        """
        # ── 1. Stack-based JSON extraction ────────────────────────────────────
        candidates: list[str] = []
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        candidates.append(text[start : i + 1])
                        start = -1

        data = None
        for candidate in reversed(candidates):      # last match first = CoT-safe
            if '"classification"' not in candidate:
                continue
            try:
                data = json.loads(candidate)
                break
            except (json.JSONDecodeError, ValueError):
                pass

        if data is not None and isinstance(data, dict):
            clf  = str(data.get("classification", "")).lower().strip()
            pred = 1 if clf in ["malicious", "1", "true", "attack"] else 0
            conf = float(data.get("confidence", 0.5))
            conf = max(0.0, min(1.0, conf))
            return {"prediction": pred, "confidence": conf,
                    "reasoning": data.get("reasoning", text)}

        # ── 2. Keyword scan — verdict window only ─────────────────────────────
        # For CoT text the step-by-step analysis is above; the conclusion is at
        # the end.  Scanning only the last ~200 chars avoids false positives
        # from phrases like "this does NOT resemble C&C beaconing".
        verdict = text[-200:].lower() if len(text) > 200 else text.lower()
        full    = text.lower()

        def _keyword_predict(region: str) -> int:
            if any(w in region for w in ["malicious", "attack", "botnet",
                                          "malware", "suspicious"]):
                if "not malicious" in region or region.lstrip().startswith("normal"):
                    return 0
                return 1
            if any(w in region for w in ["normal", "benign", "legitimate", "clean"]):
                return 0
            return -1

        prediction = _keyword_predict(verdict)
        if prediction == -1:
            prediction = _keyword_predict(full)

        confidence = 0.5
        conf_match = re.search(r'(\d{1,3})%', text)
        if conf_match:
            pct = int(conf_match.group(1))
            confidence = max(0.0, min(1.0, pct / 100.0))

        return {"prediction": prediction, "confidence": confidence,
                "reasoning": text}

    def get_stats(self) -> dict:
        return {
            "total_calls":  self.total_calls,
            "total_tokens": self.total_tokens,
            "model":        self.model,
            "provider":     self.provider,
        }


# ============================================================================
# FEATURE FORMATTERS
# ============================================================================

SYSTEM_PROMPT_BASE = """You are a network security analyst specializing in malicious traffic detection.
You analyze TCP packet side-channel characteristics to determine if network traffic is malicious or benign.

You will receive 5 side-channel features extracted from TCP packets:
1. Packet Size (Ps): Total packet size in bytes
2. Payload Size (PAs): TCP data segment size in bytes
3. Payload Ratio (Pr): Ratio of payload to total packet (PAs/Ps)
4. Ratio to Previous Packet (Rpp): Current packet size / previous packet size (0 for first packet)
5. Time Difference (Td): Time elapsed since previous packet in seconds (0 for first packet)

These features have been shown effective for detecting malware C&C traffic, botnet communication,
ransomware, reverse shells, and defacement attacks — without requiring deep packet inspection."""

# Compact system prompt for SINGLE-PACKET experiments (4A, 4B, 4C, 4D).
# Adds only the short JSON-array format note — keeps total prompt tokens
# smaller than the verbose variant despite the extra format line.
SYSTEM_PROMPT_COMPACT_PACKET = SYSTEM_PROMPT_BASE + \
    "\n\nFeatures are supplied as a compact JSON array: [Ps, PAs, Pr, Rpp, Td]"

# Compact system prompt for SESSION-LEVEL experiments (4E).
# Includes the full 31-value statistical profile column description, which
# is worthwhile here because the profile replaces hundreds of packet rows.
SYSTEM_PROMPT_COMPACT_SESSION = SYSTEM_PROMPT_BASE + """

Features are supplied as a 31-value statistical profile JSON array:
  [Ps_mean, Ps_std, Ps_min, Ps_max, Ps_p25, Ps_p75,
   PAs_mean, PAs_std, PAs_min, PAs_max, PAs_p25, PAs_p75,
   Pr_mean, Pr_std, Pr_min, Pr_max, Pr_p25, Pr_p75,
   Rpp_mean, Rpp_std, Rpp_min, Rpp_max, Rpp_p25, Rpp_p75,
   Td_mean, Td_std, Td_min, Td_max, Td_p25, Td_p75,
   n_packets]"""

# Backwards-compatible alias (used in dry-run and tests)
SYSTEM_PROMPT_COMPACT = SYSTEM_PROMPT_COMPACT_PACKET


def format_packet_verbose(row) -> str:
    """Natural-language format (~28 tokens). Original behaviour."""
    return (
        f"Packet Size: {row['packet_size']} bytes | "
        f"Payload Size: {row['payload_size']} bytes | "
        f"Payload Ratio: {row['payload_ratio']:.4f} | "
        f"Ratio to Previous: {row['ratio_to_prev']:.4f} | "
        f"Time Diff: {row['time_diff']:.6f}s"
    )


def format_packet_compact(row) -> str:
    """
    Compact JSON-array format (~8 tokens per packet).
    Encodes the same 5 values as a flat array — no label tokens wasted.
    [Ps, PAs, Pr, Rpp, Td]
    """
    return json.dumps([
        int(row["packet_size"]),
        int(row["payload_size"]),
        round(float(row["payload_ratio"]),  4),
        round(float(row["ratio_to_prev"]),  4),
        round(float(row["time_diff"]),       6),
    ], separators=(",", ":"))


def format_packet_features(row, compact: bool = False) -> str:
    """Route to verbose or compact formatter."""
    return format_packet_compact(row) if compact else format_packet_verbose(row)


def compute_session_profile(packets_df: pd.DataFrame) -> list:
    """
    Reduce a window of N packets to 31 statistics — one list per feature
    (mean, std, min, max, p25, p75) × 5 features + n_packets.

    This replaces ~N*28 verbose tokens with ~80 compact tokens regardless
    of window size, giving the LLM distributional shape rather than raw rows.

    The packet DataFrame must have columns matching FEATURE_COLS.
    """
    stats = []
    for col in FEATURE_COLS:
        vals = packets_df[col].values.astype(float)
        stats.extend([
            round(float(np.mean(vals)),   4),
            round(float(np.std(vals)),    4),
            round(float(np.min(vals)),    4),
            round(float(np.max(vals)),    4),
            round(float(np.percentile(vals, 25)), 4),
            round(float(np.percentile(vals, 75)), 4),
        ])
    stats.append(len(packets_df))
    return stats


def format_session_verbose(packets: list[dict]) -> str:
    """Original verbose session format — one line per packet."""
    lines = [f"Session with {len(packets)} packets:"]
    for i, pkt in enumerate(packets):
        lines.append(f"  Packet {i+1}: {format_packet_verbose(pkt)}")
    return "\n".join(lines)


def format_session_compact(packets_df: pd.DataFrame) -> str:
    """
    Compact statistical profile — replaces a raw 50-row packet dump with
    a 31-element JSON array (~80 tokens regardless of window size).
    """
    profile = compute_session_profile(packets_df)
    return json.dumps(profile, separators=(",", ":"))


# ============================================================================
# EMBEDDING INDEX  (for similarity-based few-shot retrieval)
# ============================================================================

class EmbeddingIndex:
    """
    Nearest-neighbour index over the 5 raw side-channel features.

    Primary backend: sentence-transformers (if installed) — encodes the
    compact JSON string into a semantic embedding space.
    Fallback: sklearn NearestNeighbors on standardised raw features.

    Usage:
        idx = EmbeddingIndex(example_df)
        neighbours = idx.query(query_row, k=5)  # returns DataFrame slice
    """

    def __init__(self, df: pd.DataFrame):
        """Build the index over the provided DataFrame (the example pool)."""
        self.df = df.reset_index(drop=True)
        X_raw = df[FEATURE_COLS].values.astype(float)

        # Replace NaN / Inf that would break distance computation
        X_raw = np.nan_to_num(X_raw, nan=0.0, posinf=1e6, neginf=0.0)

        self._use_sentence_transformers = False
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            # Encode compact JSON strings for each example
            texts = [format_packet_compact(row) for _, row in df.iterrows()]
            self._embeddings = self._st_model.encode(
                texts, batch_size=64, show_progress_bar=False,
                normalize_embeddings=True
            )
            self._use_sentence_transformers = True
        except Exception:
            pass

        # Always build the raw-feature fallback index
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X_raw)
        self._nn = NearestNeighbors(metric="cosine")
        self._nn.fit(X_scaled)
        self._X_scaled = X_scaled

    def query(self, row, k: int) -> pd.DataFrame:
        """
        Return up to k most similar examples from the pool.
        Guarantees the returned set is balanced (half malicious / half normal)
        where the pool supports it.
        """
        k = min(k, len(self.df))

        if self._use_sentence_transformers:
            q_text = format_packet_compact(row)
            q_emb  = self._st_model.encode(
                [q_text], normalize_embeddings=True, show_progress_bar=False
            )
            # Cosine similarity = dot product when embeddings are L2-normalised
            sims    = (self._embeddings @ q_emb.T).flatten()
            # Retrieve 4× k candidates, then balance
            top_idx = np.argsort(-sims)[:k * 4]
        else:
            q_raw = np.array([[row[c] for c in FEATURE_COLS]], dtype=float)
            q_raw = np.nan_to_num(q_raw, nan=0.0, posinf=1e6, neginf=0.0)
            q_scaled = self._scaler.transform(q_raw)
            n_cands = min(k * 4, len(self.df))
            _, indices = self._nn.kneighbors(q_scaled, n_neighbors=n_cands)
            top_idx = indices[0]

        candidates = self.df.iloc[top_idx]

        # Balance: take k//2 malicious + k//2 normal (ceiling for odd k)
        half = k // 2
        mal  = candidates[candidates["is_malicious"] == 1].head(half + k % 2)
        norm = candidates[candidates["is_malicious"] == 0].head(half)

        balanced = pd.concat([mal, norm])
        # If one class is under-represented fill from the other
        if len(balanced) < k:
            remainder = k - len(balanced)
            extra = candidates[~candidates.index.isin(balanced.index)].head(remainder)
            balanced = pd.concat([balanced, extra])

        return balanced.head(k)


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

PROMPT_ZERO_SHOT = """Analyze the following network traffic features and classify as MALICIOUS or NORMAL.

{features}

Respond with a JSON object:
{{"classification": "malicious" or "normal", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""


PROMPT_FEW_SHOT = """Here are examples of classified network traffic:

{examples}

Now classify the following:

{features}

Respond with a JSON object:
{{"classification": "malicious" or "normal", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""


PROMPT_COT = """Analyze the following network traffic step by step.

{features}

Think through this systematically:
1. Examine the payload ratio — what does it suggest about the packet content?
2. Examine the packet size — is it consistent with normal web/email traffic?
3. Examine the timing (Td) — are there signs of automated/periodic communication?
4. Examine the ratio to previous packet — are there unusual size changes?
5. Consider the overall pattern — does this resemble C&C beaconing, data exfiltration, scanning, or normal browsing?

Then provide your classification as JSON:
{{"classification": "malicious" or "normal", "confidence": 0.0-1.0, "reasoning": "your step-by-step analysis"}}"""


PROMPT_SESSION_VERBOSE = """Analyze the following complete network session and determine if it represents malicious activity.

{session}

Look for patterns across the packet sequence:
- Periodic timing that suggests C&C beaconing
- Unusual payload ratios (very small payloads = heartbeat, very large = exfiltration)
- Size ratio anomalies between consecutive packets
- Overall session behavior patterns

Respond with JSON:
{{"classification": "malicious" or "normal", "confidence": 0.0-1.0, "reasoning": "your analysis of the session pattern"}}"""


PROMPT_SESSION_COMPACT = """Analyze the statistical profile of the following network session.

Profile (31 values):
  [Ps_mean, Ps_std, Ps_min, Ps_max, Ps_p25, Ps_p75,
   PAs_mean, PAs_std, PAs_min, PAs_max, PAs_p25, PAs_p75,
   Pr_mean, Pr_std, Pr_min, Pr_max, Pr_p25, Pr_p75,
   Rpp_mean, Rpp_std, Rpp_min, Rpp_max, Rpp_p25, Rpp_p75,
   Td_mean, Td_std, Td_min, Td_max, Td_p25, Td_p75,
   n_packets]

{session}

Interpret these statistics for malicious patterns:
- Low Td_mean + low Td_std → automated periodic beaconing
- High Pr_mean (>0.9) across many packets → bulk data transfer / exfiltration
- Very low PAs with low variance → heartbeat / C&C keepalive
- High Rpp_std → irregular packet sizes, possible scanning or evasion

Respond with JSON:
{{"classification": "malicious" or "normal", "confidence": 0.0-1.0, "reasoning": "your analysis"}}"""


# ============================================================================
# DATA LOADING
# ============================================================================

def load_test_samples(conn, n: int, encrypted_only: bool = False,
                      family_filter: str = None,
                      exclude_families: list = None) -> pd.DataFrame:
    """
    Load balanced test samples: n/2 malicious rows + n/2 normal rows,
    each independently randomised.

    Two separate queries are used (instead of a parenthesised UNION ALL)
    because SQLite does not support compound SELECT statements whose first
    token is '(' — even in versions that partially implement the syntax.
    """
    conditions: list[str] = []
    params: list = []

    if encrypted_only:
        conditions.append("s.is_encrypted = 1")
    if family_filter:
        conditions.append("(s.malware_family = ? OR s.is_malicious = 0)")
        params.append(family_filter)
    if exclude_families:
        pholders = ",".join("?" * len(exclude_families))
        conditions.append(f"(s.malware_family NOT IN ({pholders}) OR s.is_malicious = 0)")
        params.extend(exclude_families)

    where  = "WHERE " + " AND ".join(conditions) if conditions else ""
    and_kw = "AND" if where else "WHERE"
    half   = n // 2

    select_cols = """
        p.packet_size, p.payload_size, p.payload_ratio,
        p.ratio_to_prev, p.time_diff, p.is_malicious,
        s.malware_family, s.id AS session_id, p.id AS packet_id
    """
    base = (
        f"SELECT {select_cols}"
        f" FROM packets p INNER JOIN sessions s ON (p.session_id = s.id)"
        f" {where} {and_kw}"
    )

    df_mal  = pd.read_sql_query(
        f"{base} p.is_malicious = 1 ORDER BY RANDOM() LIMIT {half}",
        conn, params=params if params else None
    )
    df_norm = pd.read_sql_query(
        f"{base} p.is_malicious = 0 ORDER BY RANDOM() LIMIT {half}",
        conn, params=params if params else None
    )
    return pd.concat([df_mal, df_norm], ignore_index=True)


# ============================================================================
# EXPERIMENT 4A — ZERO-SHOT
# ============================================================================

def experiment_4a_zero_shot(client: LLMClient, conn,
                             compact: bool = False) -> list[dict]:
    """
    Experiment 4A: Zero-Shot Classification.
    No examples — LLM relies purely on general knowledge.
    """
    print(f"\n{'='*70}")
    print(f"Experiment 4A: Zero-Shot Classification (Gap 1) "
          f"[{'compact' if compact else 'verbose'}]")
    print(f"{'='*70}")

    n  = LLM_CONFIG["zero_shot_sample_size"]
    df = load_test_samples(conn, n)

    if len(df) < 10:
        print("[SKIP] Not enough data.")
        return []

    sys_prompt = SYSTEM_PROMPT_COMPACT if compact else SYSTEM_PROMPT_BASE
    results    = []
    y_true, y_pred = [], []

    for count, (_, row) in enumerate(df.iterrows(), 1):
        feat_text = format_packet_features(row, compact=compact)
        prompt    = PROMPT_ZERO_SHOT.format(features=feat_text)

        result = client.classify(sys_prompt, prompt)

        if result["prediction"] >= 0:
            y_true.append(int(row["is_malicious"]))
            y_pred.append(result["prediction"])

        results.append({
            "experiment":   "4A_zero_shot",
            "compact":      compact,
            "packet_id":    int(row.get("packet_id", 0)),
            "ground_truth": int(row["is_malicious"]),
            "prediction":   result["prediction"],
            "confidence":   result["confidence"],
            "reasoning":    result["reasoning"][:500],
            "tokens":       result["tokens"],
            "latency_ms":   result["latency_ms"],
            "family":       row.get("malware_family", ""),
        })

        if count % 50 == 0:
            acc = accuracy_score(y_true, y_pred) if y_pred else 0
            print(f"  Processed {count}/{len(df)}: Running Acc={acc:.4f}")

        time.sleep(60.0 / LLM_CONFIG["requests_per_minute"])

    if y_pred:
        print(f"\n  4A Results ({len(y_pred)} valid predictions):")
        print(f"    Accuracy:  {accuracy_score(y_true, y_pred):.4f}")
        print(f"    Precision: {precision_score(y_true, y_pred, zero_division=0):.4f}")
        print(f"    Recall:    {recall_score(y_true, y_pred, zero_division=0):.4f}")
        print(f"    F1:        {f1_score(y_true, y_pred, zero_division=0):.4f}")
        total_tok = sum(r["tokens"] for r in results)
        print(f"    Tokens:    {total_tok:,}  (~${total_tok*0.000003:.2f})")

    return results


# ============================================================================
# EXPERIMENT 4B — FEW-SHOT
# ============================================================================

def experiment_4b_few_shot(client: LLMClient, conn,
                            compact: bool = False) -> list[dict]:
    """
    Experiment 4B: Few-Shot Classification.
    Vary k in [1, 3, 5, 10].

    compact=False  examples chosen randomly (original behaviour)
    compact=True   examples chosen by nearest-neighbour similarity over the
                   5-feature vector (EmbeddingIndex)
    """
    print(f"\n{'='*70}")
    print(f"Experiment 4B: Few-Shot Classification (Gap 1) "
          f"[{'compact+embedding' if compact else 'verbose'}]")
    print(f"{'='*70}")

    n  = LLM_CONFIG["few_shot_sample_size"]
    # Load a larger pool so the index has enough examples
    pool_size = max(n + 200, 500)
    df = load_test_samples(conn, pool_size)

    if len(df) < 30:
        print("[SKIP] Not enough data.")
        return []

    sys_prompt  = SYSTEM_PROMPT_COMPACT if compact else SYSTEM_PROMPT_BASE
    all_results = []

    # load_test_samples returns [mal_rows, norm_rows] concatenated.
    # A naive head(n) split would consume all malicious rows first, leaving an
    # all-normal example pool and an imbalanced (mal-heavy) test set.
    # Shuffle first to guarantee both splits are balanced across classes.
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # Split pool: first n rows are test, remaining rows are the example pool.
    # This prevents data leakage where a test sample could be its own nearest neighbour.
    test_df    = df.head(n).reset_index(drop=True)
    example_df = df.iloc[n:].reset_index(drop=True)

    # Build embedding index once over example_df only (reused across k values)
    if compact:
        print("  Building embedding index over example pool...")
        emb_index = EmbeddingIndex(example_df)
        print(f"  Index backend: "
              f"{'sentence-transformers' if emb_index._use_sentence_transformers else 'sklearn-cosine'}")

    for k in LLM_CONFIG["few_shot_k_values"]:
        print(f"\n  --- k={k} shots ---")

        if not compact:
            # Original random selection from example pool (not test rows)
            examples_mal  = example_df[example_df["is_malicious"] == 1].head(k // 2 + k % 2)
            examples_norm = example_df[example_df["is_malicious"] == 0].head(k // 2)
            static_example_df = pd.concat([examples_mal, examples_norm])

            static_lines = []
            for _, ex in static_example_df.iterrows():
                label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
                static_lines.append(f"[{label}] {format_packet_verbose(ex)}")
            static_examples_text = "\n".join(static_lines)

        y_true, y_pred = [], []

        for _, row in test_df.iterrows():
            if compact:
                # Per-query: retrieve k nearest neighbours, excluding the query itself
                neighbour_df = emb_index.query(row, k=k)
                example_lines = []
                for _, ex in neighbour_df.iterrows():
                    label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
                    example_lines.append(
                        f"[{label}] {format_packet_compact(ex)}"
                    )
                examples_text = "\n".join(example_lines)
                feat_text     = format_packet_compact(row)
            else:
                examples_text = static_examples_text
                feat_text     = format_packet_verbose(row)

            prompt = PROMPT_FEW_SHOT.format(
                examples=examples_text, features=feat_text
            )
            result = client.classify(sys_prompt, prompt)

            if result["prediction"] >= 0:
                y_true.append(int(row["is_malicious"]))
                y_pred.append(result["prediction"])

            all_results.append({
                "experiment":    f"4B_few_shot_k{k}",
                "compact":       compact,
                "k":             k,
                "ground_truth":  int(row["is_malicious"]),
                "prediction":    result["prediction"],
                "confidence":    result["confidence"],
                "tokens":        result["tokens"],
                "latency_ms":    result["latency_ms"],
            })

            time.sleep(60.0 / LLM_CONFIG["requests_per_minute"])

        if y_pred:
            total_tok = sum(r["tokens"] for r in all_results
                            if r.get("k") == k)
            print(f"    k={k}: Acc={accuracy_score(y_true, y_pred):.4f}  "
                  f"F1={f1_score(y_true, y_pred, zero_division=0):.4f}  "
                  f"tokens={total_tok:,}")

    return all_results


# ============================================================================
# EXPERIMENT 4C — CHAIN-OF-THOUGHT
# ============================================================================

def experiment_4c_cot(client: LLMClient, conn,
                      compact: bool = False) -> list[dict]:
    """
    Experiment 4C: Chain-of-Thought with Explainability.
    """
    print(f"\n{'='*70}")
    print(f"Experiment 4C: Chain-of-Thought Reasoning "
          f"[{'compact' if compact else 'verbose'}]")
    print(f"{'='*70}")

    n  = LLM_CONFIG["cot_sample_size"]
    df = load_test_samples(conn, n)

    if len(df) < 10:
        print("[SKIP] Not enough data.")
        return []

    sys_prompt  = SYSTEM_PROMPT_COMPACT if compact else SYSTEM_PROMPT_BASE
    results     = []
    y_true, y_pred = [], []

    for count, (_, row) in enumerate(df.iterrows(), 1):
        feat_text = format_packet_features(row, compact=compact)
        prompt    = PROMPT_COT.format(features=feat_text)

        # CoT reasoning + JSON comfortably exceeds 512 tokens; use 1024 so the
        # classification JSON is never truncated before the response ends.
        result = client.classify(sys_prompt, prompt, max_tokens=1024)

        if result["prediction"] >= 0:
            y_true.append(int(row["is_malicious"]))
            y_pred.append(result["prediction"])

        results.append({
            "experiment":   "4C_cot",
            "compact":      compact,
            "ground_truth": int(row["is_malicious"]),
            "prediction":   result["prediction"],
            "confidence":   result["confidence"],
            "reasoning":    result["reasoning"],   # full reasoning preserved
            "tokens":       result["tokens"],
            "latency_ms":   result["latency_ms"],
            "family":       row.get("malware_family", ""),
        })

        if count % 25 == 0:
            acc = accuracy_score(y_true, y_pred) if y_pred else 0
            print(f"  Processed {count}/{len(df)}: Running Acc={acc:.4f}")

        time.sleep(60.0 / LLM_CONFIG["requests_per_minute"])

    if y_pred:
        total_tok = sum(r["tokens"] for r in results)
        print(f"\n  4C Results: Acc={accuracy_score(y_true, y_pred):.4f}  "
              f"F1={f1_score(y_true, y_pred, zero_division=0):.4f}  "
              f"tokens={total_tok:,}")

    return results


# ============================================================================
# EXPERIMENT 4D — LEAVE-ONE-FAMILY-OUT
# ============================================================================

def experiment_4d_lofo(client: LLMClient, conn,
                       compact: bool = False) -> list[dict]:
    """
    Experiment 4D: Leave-One-Family-Out — Zero-Shot Novel Attack Detection.

    compact=False  examples from other families, chosen randomly
    compact=True   examples retrieved by similarity (EmbeddingIndex),
                   using only packets from families other than held-out
    """
    print(f"\n{'='*70}")
    print(f"Experiment 4D: Leave-One-Family-Out (GAP 2) "
          f"[{'compact+embedding' if compact else 'verbose'}]")
    print(f"{'='*70}")

    cur = conn.execute(
        "SELECT DISTINCT malware_family FROM sessions "
        "WHERE malware_family != '' AND is_malicious = 1"
    )
    families = [r[0] for r in cur.fetchall()]

    if len(families) < 2:
        print("[SKIP] Need at least 2 families.")
        return []

    sys_prompt_novel = SYSTEM_PROMPT_COMPACT if compact else SYSTEM_PROMPT_BASE
    sys_prompt_novel += """

IMPORTANT: You are testing traffic from a potentially novel attack type
that you have not seen before. The examples provided are from DIFFERENT
attack types. Use your general understanding of malicious traffic patterns
to make your classification."""

    all_results = []

    for held_out in families:
        print(f"\n  --- Held-out: {held_out} ---")

        n_per   = LLM_CONFIG["lofo_sample_per_family"]
        test_df = load_test_samples(conn, n_per, family_filter=held_out)

        if len(test_df) < 10:
            print(f"    [SKIP] Not enough data for {held_out}")
            continue

        # Load example pool from OTHER families
        example_query = """
            SELECT p.packet_size, p.payload_size, p.payload_ratio,
                   p.ratio_to_prev, p.time_diff, p.is_malicious
            FROM packets p INNER JOIN sessions s ON (p.session_id = s.id)
            WHERE s.malware_family != ?
              AND (s.malware_family != '' OR s.is_malicious = 0)
            ORDER BY RANDOM() LIMIT 500
        """
        example_pool = pd.read_sql_query(
            example_query, conn, params=[held_out]
        )

        if compact:
            emb_index = EmbeddingIndex(example_pool)
        else:
            # 3 malicious + 3 normal, explicitly balanced so the LLM always
            # sees both classes regardless of pool composition.
            static_mal  = example_pool[example_pool["is_malicious"] == 1].head(3)
            static_norm = example_pool[example_pool["is_malicious"] == 0].head(3)
            static_examples = pd.concat([static_mal, static_norm])
            static_lines    = []
            for _, ex in static_examples.iterrows():
                label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
                static_lines.append(f"[{label}] {format_packet_verbose(ex)}")
            static_text = "\n".join(static_lines)

        y_true, y_pred = [], []

        for _, row in test_df.iterrows():
            if compact:
                neighbour_df  = emb_index.query(row, k=6)
                example_lines = []
                for _, ex in neighbour_df.iterrows():
                    label = "MALICIOUS" if ex["is_malicious"] else "NORMAL"
                    example_lines.append(f"[{label}] {format_packet_compact(ex)}")
                examples_text = "\n".join(example_lines)
                feat_text     = format_packet_compact(row)
            else:
                examples_text = static_text
                feat_text     = format_packet_verbose(row)

            prompt = PROMPT_FEW_SHOT.format(
                examples=examples_text, features=feat_text
            )
            result = client.classify(sys_prompt_novel, prompt)

            if result["prediction"] >= 0:
                y_true.append(int(row["is_malicious"]))
                y_pred.append(result["prediction"])

            all_results.append({
                "experiment":       "4D_lofo",
                "compact":          compact,
                "held_out_family":  held_out,
                "ground_truth":     int(row["is_malicious"]),
                "prediction":       result["prediction"],
                "confidence":       result["confidence"],
                "reasoning":        result["reasoning"][:300],
                "tokens":           result["tokens"],
            })

            time.sleep(60.0 / LLM_CONFIG["requests_per_minute"])

        if y_pred:
            acc = accuracy_score(y_true, y_pred)
            f1  = f1_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            tok = sum(r["tokens"] for r in all_results
                      if r.get("held_out_family") == held_out)
            print(f"    {held_out}: Acc={acc:.4f}  F1={f1:.4f}  "
                  f"Recall={rec:.4f}  tokens={tok:,}")

    return all_results


# ============================================================================
# EXPERIMENT 4E — SESSION WINDOW
# ============================================================================

def experiment_4e_session_window(client: LLMClient, conn,
                                  compact: bool = False) -> list[dict]:
    """
    Experiment 4E: Session-Level Windowed Analysis.

    Uses one fixed, balanced session cohort across all window sizes so the
    comparison is not confounded by different samples.  Each session must have at
    least max(window_sizes) packets.  Real per-call latency is stored for every
    result row.

    compact=False  raw packet rows in natural language (~28 tok × window_size)
    compact=True   31-value statistical profile (~80 tok regardless of window)
    """
    print(f"\n{'='*70}")
    print(f"Experiment 4E: Session-Level Windowed Analysis "
          f"[{'compact/profile' if compact else 'verbose'}]")
    print(f"{'='*70}")

    sys_prompt = SYSTEM_PROMPT_COMPACT_SESSION if compact else SYSTEM_PROMPT_BASE
    all_results: list[dict] = []

    window_sizes = list(LLM_CONFIG["window_sizes"])
    max_window = max(window_sizes)
    half_n = LLM_CONFIG["session_sample_size"] // 2
    pkt_count_filter = (
        f"(SELECT COUNT(*) FROM packets p WHERE p.session_id = s.id) >= {max_window}"
    )

    sessions_mal = pd.read_sql_query(
        f"SELECT s.id, s.is_malicious, s.malware_family FROM sessions s "
        f"WHERE s.is_malicious = 1 AND {pkt_count_filter} "
        f"ORDER BY RANDOM() LIMIT {half_n}",
        conn,
    )
    sessions_norm = pd.read_sql_query(
        f"SELECT s.id, s.is_malicious, s.malware_family FROM sessions s "
        f"WHERE s.is_malicious = 0 AND {pkt_count_filter} "
        f"ORDER BY RANDOM() LIMIT {half_n}",
        conn,
    )
    cohort = pd.concat([sessions_mal, sessions_norm], ignore_index=True)
    cohort = cohort.sample(frac=1, random_state=42).reset_index(drop=True)

    if len(cohort) < 10:
        print(f"  [SKIP] Not enough sessions with {max_window}+ packets")
        return []

    cohort_ids = sorted(int(x) for x in cohort["id"].tolist())
    cohort_hash = hashlib.sha256(",".join(map(str, cohort_ids)).encode("utf-8")).hexdigest()[:16]
    print(f"  Cohort size: {len(cohort)} sessions | max_window={max_window} | cohort_hash={cohort_hash}")

    packet_cache: dict[int, pd.DataFrame] = {}
    pkt_query = """
        SELECT packet_size, payload_size, payload_ratio, ratio_to_prev, time_diff
        FROM packets WHERE session_id = ?
        ORDER BY packet_idx LIMIT ?
    """
    for sess_id in cohort_ids:
        pkts = pd.read_sql_query(pkt_query, conn, params=[sess_id, max_window])
        if len(pkts) < max_window:
            continue
        packet_cache[int(sess_id)] = pkts

    # In rare race conditions a qualifying session may vanish from the cache.
    cohort = cohort[cohort["id"].isin(packet_cache.keys())].reset_index(drop=True)
    if len(cohort) < 10:
        print("  [SKIP] Cached packet windows too small after filtering.")
        return []

    for window_size in window_sizes:
        print(f"\n  --- Window size: {window_size} packets ---")
        y_true: list[int] = []
        y_pred: list[int] = []
        token_sum = 0
        latency_sum = 0.0

        for _, sess in cohort.iterrows():
            sess_id = int(sess["id"])
            pkts_full = packet_cache.get(sess_id)
            if pkts_full is None or len(pkts_full) < window_size:
                continue
            pkts = pkts_full.head(window_size)

            if compact:
                session_text = format_session_compact(pkts)
                prompt_template = PROMPT_SESSION_COMPACT
            else:
                session_text = format_session_verbose(pkts.to_dict("records"))
                prompt_template = PROMPT_SESSION_VERBOSE

            prompt = prompt_template.format(session=session_text)
            result = client.classify(sys_prompt, prompt)

            if result["prediction"] >= 0:
                y_true.append(int(sess["is_malicious"]))
                y_pred.append(result["prediction"])

            token_sum += int(result.get("tokens", 0) or 0)
            latency_sum += float(result.get("latency_ms", 0.0) or 0.0)

            all_results.append({
                "experiment": f"4E_session_w{window_size}",
                "compact": compact,
                "window_size": window_size,
                "session_id": sess_id,
                "ground_truth": int(sess["is_malicious"]),
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "tokens": result["tokens"],
                "latency_ms": result["latency_ms"],
                "family": sess.get("malware_family", ""),
                "cohort_hash": cohort_hash,
                "cohort_size": int(len(cohort)),
                "max_window": int(max_window),
            })

            time.sleep(60.0 / LLM_CONFIG["requests_per_minute"])

        if y_pred:
            avg_latency = latency_sum / max(len(cohort), 1)
            print(
                f"    w={window_size}: Acc={accuracy_score(y_true, y_pred):.4f}  "
                f"F1={f1_score(y_true, y_pred, zero_division=0):.4f}  "
                f"n={len(y_pred)}  tokens={token_sum:,}  avg_latency={avg_latency:.0f}ms"
            )

    return all_results


# ============================================================================
# COMPARISON REPORTING
# ============================================================================

def _local_summary_rows(results: list[dict], prefix: str) -> list[dict]:
    summaries = [
        row for row in results
        if row.get("record_type") == "summary"
        and str(row.get("experiment", "")).startswith(prefix)
        and "error" not in row
    ]
    if summaries:
        return summaries
    return [
        row for row in results
        if str(row.get("experiment", "")).startswith(prefix)
        and "error" not in row
    ]


def compare_with_classical(llm_results: list[dict], classical_path: Path):
    """Print a side-by-side comparison table against local ML baselines."""
    print(f"\n{'='*70}")
    print("COMPARATIVE ANALYSIS: Local ML vs LLM")
    print(f"{'='*70}")

    selected_path: Path | None = None
    if classical_path.exists():
        selected_path = classical_path
    else:
        phase2_path = RESULTS_DIR / "phase2_local_ml_results.json"
        if phase2_path.exists():
            selected_path = phase2_path

    if selected_path is None:
        print("[SKIP] No local ML results. Run Phase 2 or Phase 3 first.")
        return

    with open(selected_path) as f:
        classical: list[dict] = json.load(f)

    # Best local baseline on E1
    e1_candidates = _local_summary_rows(classical, "E1_full_mixed_")
    e1_best = max(e1_candidates, key=lambda x: x["accuracy"], default=None)

    zs = [r for r in llm_results
          if r.get("experiment") == "4A_zero_shot" and r.get("prediction", -1) >= 0]

    if e1_best and zs:
        y_true = [r["ground_truth"] for r in zs]
        y_pred = [r["prediction"]   for r in zs]
        print(f"\n  Best local baseline ({e1_best['algorithm']}):")
        print(
            f"    Accuracy: {e1_best['accuracy']:.4f}"
            + (
                f" +/- {e1_best.get('accuracy_std', 0):.4f}"
                if "accuracy_std" in e1_best else ""
            )
            + f"  F1: {e1_best.get('f1_1', 0):.4f}"
        )
        print(f"\n  LLM Zero-Shot (4A):")
        print(f"    Accuracy: {accuracy_score(y_true, y_pred):.4f}  "
              f"F1: {f1_score(y_true, y_pred, zero_division=0):.4f}")

    # LOFO comparison
    lofo_cl = _local_summary_rows(classical, "E4_LOFO_")
    lofo_capture = [
        r for r in lofo_cl
        if "capture_repeated_group_holdout" in str(r.get("experiment", ""))
    ]
    if lofo_capture:
        lofo_cl = lofo_capture
    lofo_llm = [r for r in llm_results
                if r.get("experiment") == "4D_lofo"
                and r.get("prediction", -1) >= 0]

    if lofo_cl and lofo_llm:
        print(f"\n  Leave-One-Family-Out comparison:")
        families = sorted(set(r.get("held_out_family", "") for r in lofo_cl))
        rows = []
        for fam in families:
            if not fam:
                continue
            cl_r = [r for r in lofo_cl if r.get("held_out_family") == fam]
            best_cl = max(cl_r, key=lambda x: x.get("accuracy", 0), default={})
            cl_acc = best_cl.get("accuracy", 0.0)
            cl_algo = best_cl.get("algorithm", "N/A")

            llm_r = [r for r in lofo_llm if r.get("held_out_family") == fam]
            if llm_r:
                llm_acc = accuracy_score(
                    [r["ground_truth"] for r in llm_r],
                    [r["prediction"]   for r in llm_r]
                )
            else:
                llm_acc = 0.0

            rows.append([
                fam,
                (
                    f"{cl_algo}: {cl_acc:.4f}"
                    + (
                        f" +/- {best_cl.get('accuracy_std', 0):.4f}"
                        if "accuracy_std" in best_cl else ""
                    )
                ) if cl_algo != "N/A" else "N/A",
                f"{llm_acc:.4f}",
                "LLM" if llm_acc > cl_acc else cl_algo,
            ])
        print(tabulate(rows,
                       headers=["Family", "Best Local", "LLM Acc", "Winner"],
                       tablefmt="grid"))


# ============================================================================
# CORE RUNNER
# ============================================================================

def run(provider: str = LLM_CONFIG.get("default_provider", "openai"), experiment: str = "all",
        dry_run: bool = False, compact: bool = False) -> None:
    """
    Execute LLM experiments.  Called by run_all.py or main() — never touches
    sys.argv.

    Args:
        provider:   "anthropic" or "openai"
        experiment: "all" or one of "4a"–"4e"
        dry_run:    print sample prompts without making API calls
        compact:    use compact JSON formatting + statistical profiles +
                    embedding-based few-shot retrieval
    """
    mode_tag = "compact" if compact else "verbose"
    print(f"LLM Traffic Detection Experiments")
    print(f"Provider:   {provider}")
    print(f"Experiment: {experiment}")
    print(f"Mode:       {mode_tag}")

    conn = get_db()

    cur = conn.execute("SELECT COUNT(*) FROM packets")
    pkt_count = cur.fetchone()[0]
    if pkt_count < 100:
        print(f"\n[ERROR] Only {pkt_count} packets in database.")
        print("Run feature_extraction.py first.")
        conn.close()
        return

    print(f"Database: {pkt_count:,} packets")

    if dry_run:
        df = load_test_samples(conn, 3)
        for _, row in df.iterrows():
            sys_p = SYSTEM_PROMPT_COMPACT if compact else SYSTEM_PROMPT_BASE
            feat  = format_packet_features(row, compact=compact)
            print(f"\n--- Sample prompt ({mode_tag}) ---")
            print(f"System: {sys_p[:200]}...")
            print(f"User:   {PROMPT_ZERO_SHOT.format(features=feat)}")
            print(f"Truth:  {'MALICIOUS' if row['is_malicious'] else 'NORMAL'}")
        conn.close()
        return

    client = LLMClient(provider=provider)

    experiment_map = {
        "4a": experiment_4a_zero_shot,
        "4b": experiment_4b_few_shot,
        "4c": experiment_4c_cot,
        "4d": experiment_4d_lofo,
        "4e": experiment_4e_session_window,
    }

    run_list    = list(experiment_map.keys()) if experiment == "all" else [experiment.lower()]
    all_results = []

    for exp_key in run_list:
        results = experiment_map[exp_key](client, conn, compact=compact)
        all_results.extend(results)

    # Suffix results file with mode so verbose and compact runs don't overwrite
    suffix       = f"{provider}_{mode_tag}"
    results_path = RESULTS_DIR / f"llm_results_{suffix}.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")

    stats = client.get_stats()
    total_tokens = stats["total_tokens"]
    print(f"\nAPI Usage:")
    print(f"  Model:        {stats['model']}")
    print(f"  Total calls:  {stats['total_calls']:,}")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Approx cost:  ~${total_tokens * 0.000003:.2f}")

    compare_with_classical(all_results,
                           RESULTS_DIR / "classical_ml_results.json")
    conn.close()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LLM-Powered Malicious Traffic Detection Experiments"
    )
    parser.add_argument("--experiment", default="all",
                        choices=["all", "4a", "4b", "4c", "4d", "4e"])
    parser.add_argument("--provider", default=LLM_CONFIG.get("default_provider", "openai"),
                        choices=["anthropic", "openai"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without making API calls")
    parser.add_argument("--compact", action="store_true",
                        help="Use compact JSON format + statistical profiles "
                             "+ embedding-based few-shot retrieval")
    args = parser.parse_args()
    run(provider=args.provider, experiment=args.experiment,
        dry_run=args.dry_run, compact=args.compact)


if __name__ == "__main__":
    main()
