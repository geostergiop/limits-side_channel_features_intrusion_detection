# Payload-Free Malware Traffic Detection

This repository evaluates local supervised classifiers and prompted language
models on encrypted or payload-free network metadata. The primary protocol is
session based and capture disjoint: every test fold holds out one complete
malware capture and its associated family while training and validation use
different captures.

The public repository contains experiment code, tests, figures, and compact
result summaries. Packet captures, SQLite databases, split manifests, API
checkpoints, and prediction-level outputs are intentionally excluded.

## What Is Evaluated

Phase 7 is the current session experiment suite. It crosses three feature sets,
three observation units, two evaluation modes, and several detector families.

| Dimension | Configurations |
|---|---|
| Feature set | `minimal`, `mercury`, `combined` |
| Observation unit | whole `session_sequence`, fixed `behavior_window`, single-packet `packet_ablation` |
| Evaluation mode | `balanced`, `deployment` |
| Local detector | RF, XGBoost, LightGBM, CART, KNN |
| Prompted detector | OpenAI GPT-5.4 or Anthropic Claude Sonnet 4.6, blind or training-memory context |
| Supervised LLM | fine-tuning export, job creation, and held-out evaluation path |
| Primary split | `capture_disjoint_5fold` |
| Secondary split | `within_capture_temporal` seen-capture upper bound |

`packet_ablation` is retained only to compare against the original packet-level
design. Whole sessions and behavior windows are the primary deployment units.

### Feature Sets

`minimal` contains the original five side-channel fields: packet size, payload
size, payload ratio, size ratio to the preceding packet, and inter-arrival time.

`mercury` contains 20 efficiently derived Mercury-style metadata fields:
direction, direction change, TCP/UDP indicators, encrypted-session hint, source,
destination, and inferred service ports, well-known/ephemeral port indicators,
TLS/DNS/web service hints, normalized packet position, elapsed session time,
log inter-arrival time, packet-size delta, and payload-size delta.

These are **Mercury-style fields**, not Cisco Mercury fingerprints. The local
schema does not include raw TLS extensions, SSH fingerprints, HTTP fingerprints,
or TCP-option fingerprints. `combined` is the union of the 5 minimal and 20
Mercury-style fields.

### Evaluation Modes

`balanced` creates an equal benign/malicious held-out cohort in each frozen fold
and evaluates the fixed decision threshold. It is intended for controlled,
apples-to-apples scientific comparisons.

`deployment` retains the class prevalence in the eligible held-out capture
cohort. A threshold is selected **only on the validation partition** by
maximizing recall subject to the configured validation false-positive-rate
ceiling, then applied once to the test partition. This is prevalence faithful to
the study corpus, not to an enterprise network; the corpus itself is much more
malware dense than operational traffic.

## Current Audited Results

The table below reports whole-session results from the expanded, memory-enabled
GPT-5.4 runs and the corresponding full-fold Random Forest runs. Pooled F1 is
computed from confusion counts combined across the five held-out captures.

| Evaluation | Detector / features | Accuracy | Precision | Recall | Pooled malicious F1 | Median fold F1 |
|---|---|---:|---:|---:|---:|---:|
| Balanced | GPT-5.4 / combined | 85.58% | 91.86% | 78.08% | 84.41% | 83.52% |
| Balanced | RF / combined | 88.57% | 91.80% | 84.72% | 88.12% | 96.24% |
| Deployment | GPT-5.4 / minimal | 90.36% | 89.51% | 91.16% | 90.33% | 90.97% |
| Deployment | RF / minimal | 83.75% | 92.06% | 75.86% | 83.18% | 98.63% |

These aggregates conceal material capture/family heterogeneity. The RF won four
of five deployment family folds, while GPT-5.4 gained strongly on the held-out
Website capture. The expanded deployment LLM run also produced a pooled test FPR
of 10.41% even though thresholds targeted a 5% ceiling on validation data. This
validation-to-test shift is a central deployment finding, not evidence that the
constraint was enforced on test labels.

Local batch inference ranges from roughly 13,000 to 969,000 samples/s across
recorded configurations. GPT-5.4 required about 1.72-1.86 seconds per API call in
the expanded whole-session runs. These timings are not hardware-normalized, but
the order-of-magnitude operational difference is unambiguous.

Claude Sonnet 4.6 is supported and was used in complementary packet-era
experiments. However, the pre-replacement GitHub snapshot (`93208e275b62`)
contains only
`llm_results_openai_verbose.json`; it has no provider-specific Claude artifact.
Its 5-, 10-, and 50-packet window scores therefore cannot be relabeled as Claude
results in this release. Sonnet results should be cited only after exporting a
provider-identified artifact from a reproducible run.

Important scope limits:

- The current capture-disjoint corpus has seven benign and five malicious
  captures, with one malicious capture for each evaluated family.
- Sessions and behavior windows require at least six packets so Hancitor remains
  eligible.
- Local models evaluate complete held-out folds; prompted LLM results use frozen,
  family-aware budgeted subsets because API inference is costly.
- The expanded published prompted runs are memory-enabled GPT-5.4 runs. Blind
  prompting, Claude Sonnet 4.6, and a fine-tuning path exist in code, but no
  completed Sonnet session or fine-tuned model artifact is claimed in the six
  published summaries.
- Local and LLM inputs share base metadata and split manifests, but their tabular
  and textual representations are not byte-for-byte identical.

See [`results/published/README.md`](results/published/README.md) and the six
summary JSON files in `results/published/` for fold-level metrics, provenance,
and source-artifact hashes.

## Installation

Python 3.11 or newer is recommended. XGBoost and LightGBM are required for the
complete local suite; Phase 2 and Phase 7 fail clearly if requested algorithms
are unavailable.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

API credentials must be supplied through environment variables, never committed
to `configs/config.py`:

```powershell
$env:OPENAI_API_KEY = "your-openai-key"
$env:ANTHROPIC_API_KEY = "your-anthropic-key"
```

The provider and model defaults are configured in `configs/config.py` under
`LLM_CONFIG`. The checked-in defaults are OpenAI `gpt-5.4` and Anthropic
`claude-sonnet-4-6`. Anthropic documents that dateless 4.6 ID as a
[pinned model](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions),
not an evergreen alias. Select the provider with `--provider openai` or
`--provider anthropic`.

## Data Preparation

The dataset is not distributed through Git. Download the configured public CTU
captures and build the local database as follows:

```powershell
python run_all.py --phase 0
python run_all.py --phase 1 --rebuild-db
```

If `data/traffic.db` was already built from the same raw captures with the current
extractor and contains packet, session, capture, label, and family metadata, it
can be reused. Phase 7 derives session representations and frozen split manifests
from that database; it does not require a second extraction merely because the
session experiments are enabled.

Before spending API budget, validate the command and prompt construction:

```powershell
python run_all.py --phase 7 --session-mode llm --provider openai --dry-run
python run_all.py --phase 7 --session-mode llm --provider anthropic --dry-run
```

## Reproducing Phase 7

### Local Baselines

Balanced scientific comparison:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode local
```

Deployment-prevalence evaluation with validation-only threshold selection:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode local
```

The two local commands are read-only with respect to `data/traffic.db`, but they
write manifests and result files. Run them sequentially when first creating
manifests. Once manifests exist, parallel execution is normally safe because
manifest writes are locked and results use mode-specific filenames.

### Budgeted LLM Pilots

Balanced pilot, 780 calls for three feature sets, two session units, five folds,
and memory context:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode llm --provider openai --session-llm-context memory --session-budget-profile paper_5k --session-feature-set minimal,mercury,combined --session-sample-unit session_sequence,behavior_window
```

Deployment pilot, 2,400 calls including validation and test requests:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode llm --provider openai --session-llm-context memory --session-budget-profile paper_6k --session-feature-set minimal,mercury,combined --session-sample-unit session_sequence,behavior_window
```

To run the same matrix with Claude Sonnet 4.6, change only
`--provider openai` to `--provider anthropic`. Provider-specific result names
prevent an OpenAI run and an Anthropic run from overwriting each other.

### Expanded Published LLM Runs

Balanced expanded run, 3,120 held-out test calls:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode llm --provider openai --session-llm-context memory --session-budget-profile paper_5k --session-feature-set minimal,mercury,combined --session-sample-unit session_sequence,behavior_window --session-llm-samples-per-repeat 104 --session-llm-max-calls 5000
```

Deployment expanded run, 9,600 calls including 3,000 validation and 6,600 test
requests:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode llm --provider openai --session-llm-context memory --session-budget-profile paper_6k --session-feature-set minimal,mercury,combined --session-sample-unit session_sequence,behavior_window --session-llm-validation-samples-per-repeat 100 --session-llm-test-samples-per-repeat 220 --session-llm-max-calls 10000
```

Estimate calls before execution as:

```text
balanced = variants * folds * test_samples_per_fold
deployment = variants * folds * (validation_samples_per_fold + test_samples_per_fold)
```

Here, `variants = feature_sets * sample_units * window_settings * context_modes`.
`--session-llm-max-calls` is a hard preflight budget guard. Different profiles or
sample overrides produce distinct hashed output names. Repeating an identical
command resumes/reuses its checkpoint rather than intentionally creating a
duplicate run; preserve a complete `results/` directory before forcing a fresh
replicate.

### Blind, Memory, and Fine-Tuned LLMs

Use `--session-llm-context blind`, `memory`, or `both`. Memory examples are drawn
only from the fold's training partition; validation and test labels are never
inserted into prompts.

Prepare fine-tuning corpora without starting a provider job:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-mode finetune --provider openai
```

Starting a paid OpenAI fine-tuning job requires explicit confirmation through the
command flag:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-mode finetune --provider openai --start-finetune-job
```

Evaluate an existing fine-tuned model with `--finetuned-model MODEL_ID`. A
fine-tuned result is publishable only for the held-out fold associated with the
exported training corpus.

## Earlier Phases

Phases 2-6 remain available for reproducing the original packet-centric and
adversarial ablations:

```text
0  dataset acquisition
1  packet extraction and SQLite construction
2  RF/XGBoost/LightGBM grouped local baselines
3  CART, KNN, and other classical baselines
4  packet-era OpenAI or Claude prompted experiments
5  cross-model analysis
6  adversarial evaluation
7  capture-disjoint session experiment suite
```

Use `python run_all.py --help` for all controls.

## Results and Verification

Raw outputs are written under `results/` and ignored by Git. Export compact,
shareable summaries after new runs:

```powershell
python scripts/export_publishable_results.py
```

Run the source and protocol tests before interpreting results:

```powershell
python -m pytest -q
python -m compileall -q configs src run_all.py scripts tests
```

Repository layout:

```text
configs/                 model, feature, budget, and protocol settings
src/                     extraction and experiment implementations
src/adversarial/         Phase 6 perturbation and evasion code
tests/                   deterministic split and protocol regression tests
scripts/                 compact result exporter
results/published/       auditable summary JSONs only
figures/                 publication-facing aggregate figures
```

The repository does not claim that the current corpus represents production
base rates, that five held-out malware captures establish universal family
generalization, or that budgeted LLM subsets are equivalent to full-fold local
evaluation. Those limitations should remain explicit in any paper derived from
these artifacts.
