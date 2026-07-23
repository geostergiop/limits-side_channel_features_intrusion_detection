# NDSS Upgrade Architecture

## Goals

This NDSS branch extends the original packet-side-channel study in four ways:

1. Add Mercury-style metadata and combined feature configurations alongside
   the original minimal five-feature configuration.
2. Promote session-sequence and behavior-window experiments to first-class
   evaluation units instead of relying primarily on single-packet prompting.
3. Report deployment-oriented metrics, especially runtime and absolute
   detection accuracy.
4. Introduce a fine-tuned language model baseline so the LLM side is not
   limited to zero-shot or few-shot prompting.
5. Add blind and memory-enabled LLM variants so prompted models can be compared
   with and without labeled training-split context.

## Design Principles

- Reuse frozen manifests and grouped repeated holdout wherever possible.
- Keep the original ESORICS-style phases intact for reproducibility.
- Add an NDSS suite as a new major experiment layer instead of silently
  changing historical phase semantics.
- Use the same feature builders and prompt builders across zero-shot,
  fine-tuned, and local baselines.
- Support two explicit evaluation modes:
  - `balanced`: class-balanced cohorts for apples-to-apples scientific
    comparison.
  - `deployment`: prevalence-faithful cohorts, validation-only threshold
    selection, and one-shot evaluation on the imbalanced test split.

## New Components

### 1. Feature Layer

File: `src/ndss_dataset.py`

- Defines three reviewer-facing feature sets:
  - `minimal`: the original five side-channel features.
  - `mercury`: Mercury-style metadata available from the current project
    schema, including direction, protocol, ports, service-port hints,
    encryption hint, packet position, elapsed time, direction changes, and
    packet/payload deltas.
  - `combined`: the original five minimal features plus the Mercury-style
    metadata fields.
- The current extractor does not store full Mercury TLS/DTLS/SSH/HTTP/TCP
  fingerprint strings or raw protocol feature strings. Those are documented as
  out of scope for this branch unless the database schema and extractor are
  extended to persist them.

### 2. Sample Builders

File: `src/ndss_dataset.py`

- Builds deterministic frozen cohorts of sessions.
- Materializes three sample units:
  - `packet_ablation`: packet-level ablation retained for comparison only.
  - `session_sequence`: whole-session ordered segment profiles.
  - `behavior_window`: complete sessions represented as ordered fixed-duration
    behavior windows.
- Cohort selection supports:
  - balanced class sampling for scientific comparison.
  - natural-prevalence sampling for deployment claims.
- Session and window samples are converted into fixed-length tabular profiles
  for local ML and serialized ordered segment summaries for LLM prompts.

### 3. NDSS Local Baselines

File: `src/ndss_experiments.py`

- Reuses the grouped repeated holdout protocol and manifest storage.
- Trains configurable local baselines on NDSS session/window profile samples.
- In deployment mode, uses grouped train/validation/test splits, applies
  XGBoost/LightGBM early stopping on validation only, chooses decision
  thresholds on validation only, and evaluates once on the imbalanced test
  split.
- Reports mean, standard deviation, confidence intervals, and throughput-style
  inference metrics.

### 4. NDSS LLM Experiments

File: `src/ndss_experiments.py`

- Uses the same frozen manifests as the local baselines.
- Evaluates:
  - packet ablation on the minimal feature set,
  - whole-session sequence classification,
  - behavior-window classification.
- Whole sessions are represented as ordered segment summaries so the LLM sees
  the complete session behavior, not a single packet or an arbitrary prefix.
- In deployment mode, chooses the LLM decision threshold from validation-set
  confidence scores only, then applies that threshold once on the imbalanced
  test subset.
- Prompted LLMs support:
  - `blind`: no labeled examples or family context beyond the prompt.
  - `memory`: labeled training-split class counts, malicious family counts, and
    sampled ground-truth examples are prepended to validation/test prompts.
- Invalid LLM outputs are counted as wrong predictions in aggregate metrics and
  reported through `invalid_count`.

### 5. Fine-Tuned LLM Baseline

File: `src/ndss_finetune.py`

- Exports training/validation JSONL corpora from the same frozen manifests.
- Supports OpenAI fine-tuning job creation when an API key is available.
- Supports evaluation of a supplied fine-tuned model ID with the same prompt
  format used by zero-shot NDSS experiments.
- Fine-tuned model evaluation is restricted to the held-out test split from the
  same frozen repeat used to export the training/validation corpus, avoiding
  leakage across repeated-holdout test partitions.

### 6. NDSS Orchestration

Files: `src/ndss_experiments.py`, `run_all.py`

- Adds a new NDSS suite entry point so the original phases remain reproducible.
- Produces separate NDSS result files and a deployment-focused markdown report.

## Experiment Matrix

### Local Models

- Feature sets: `minimal`, `mercury`, `combined`
- Units: `packet_ablation`, `session_sequence`, `behavior_window`
- Algorithms: RF, XGB, LGBM, CART, KNN

### LLM Models

- Feature sets: `minimal`, `mercury`, `combined`
- Packet ablation: blind mode only
- Whole-session classification: blind and memory modes
- Behavior-window classification: blind and memory modes

### Fine-Tuned LLM

- Training data: frozen NDSS manifests
- Input format: same prompt family as the zero-shot NDSS sequence experiments
- Evaluation: same grouped repeated holdout test partitions

## Validation Plan

- Syntax validation for all modified modules.
- Deterministic cohort checks for session and window builders.
- Manifest reuse checks for NDSS sample units.
- Balanced-vs-deployment mode checks to verify that packet/session prevalence
  changes only when explicitly requested.
- Fine-tuned evaluation leakage checks confirming evaluation stays on the
  exported repeat's held-out test split.
- LLM invalid-output accounting checks.
- Smoke tests for local ML on session/window profiles.
- Export validation for fine-tuning JSONL corpora.
- Report generation validation for runtime and accuracy tables.
