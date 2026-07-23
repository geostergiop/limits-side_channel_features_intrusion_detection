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

We report pooled malicious-class F1 by summing the confusion counts from all five
held-out capture folds and then computing F1. This weights every evaluated sample
equally and avoids treating five heterogeneous malware captures as if they were
interchangeable repeated measurements. Fold-level results remain available in
the published JSON summaries and should accompany any pooled value.

### LLM Results

Table 1 reports every configuration in the expanded, memory-enabled GPT-5.4
session/window runs. Balanced cells contain 520 held-out decisions per variant
(104 per fold, equally divided by class). Deployment cells contain 1,100 test
decisions per variant (220 per fold, 49.36% malicious); their thresholds were
selected using separate validation requests and were never tuned on these test
labels.

| Evaluation | Context | Features | Test n | Accuracy | Precision | Recall | Pooled F1 | Mean s/query |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Balanced | Whole session | Minimal | 520 | 70.00% | 87.14% | 46.92% | 61.00% | 1.909 |
| Balanced | 5 s window | Minimal | 520 | 66.35% | 74.01% | 50.38% | 59.95% | 1.813 |
| Balanced | Whole session | Mercury-style | 520 | 79.81% | 90.58% | 66.54% | 76.72% | 1.799 |
| Balanced | 5 s window | Mercury-style | 520 | 65.38% | 67.54% | 59.23% | 63.11% | 1.875 |
| Balanced | Whole session | Combined | 520 | 85.58% | 91.86% | 78.08% | **84.41%** | 1.850 |
| Balanced | 5 s window | Combined | 520 | 71.35% | 72.47% | 68.85% | 70.61% | 1.823 |
| Deployment | Whole session | Minimal | 1,100 | 90.36% | 89.51% | 91.16% | **90.33%** | 1.802 |
| Deployment | 5 s window | Minimal | 1,100 | 79.55% | 84.27% | 72.01% | 77.66% | 1.742 |
| Deployment | Whole session | Mercury-style | 1,100 | 76.27% | 95.48% | 54.51% | 69.40% | 1.717 |
| Deployment | 5 s window | Mercury-style | 1,100 | 53.00% | 59.56% | 14.92% | 23.86% | 1.768 |
| Deployment | Whole session | Combined | 1,100 | 79.27% | 96.19% | 60.41% | 74.21% | 1.768 |
| Deployment | 5 s window | Combined | 1,100 | 52.18% | 55.15% | 16.76% | 25.71% | 1.722 |

Whole-session context is consistently preferable to the 5 s representation.
The balanced combined-feature loss is 13.80 percentage points of F1; the
deployment losses are 12.68 points for minimal, 45.54 points for Mercury-style,
and 48.50 points for combined metadata. The deployment failure is primarily a
recall collapse: Mercury-style and combined 5 s recall falls to 14.92% and
16.76%, respectively. Moreover, the best whole-session deployment run has a
10.41% pooled test FPR despite selecting thresholds under a 5% validation FPR
constraint. The discrepancy demonstrates capture shift between validation and
test; it does not imply that test labels influenced threshold selection.

The legacy Phase 4E archive used a different and weaker protocol: 200 balanced
sessions were sampled without a capture-disjoint train/validation/test boundary,
and each prompt received the first 5, 10, 20, or 50 packets. It is retained only
as a historical sensitivity check.

| Legacy packet window | Accuracy | Precision | Recall | F1 | Prediction behavior |
|---:|---:|---:|---:|---:|---|
| 5 packets | 96.00% | 92.59% | 100.00% | 96.15% | 8 false positives |
| 10 packets | 59.50% | 55.25% | 100.00% | 71.17% | 81 false positives |
| 20 packets | 50.50% | 50.25% | 100.00% | 66.89% | 99 false positives |
| 50 packets | 50.00% | 50.00% | 100.00% | 66.67% | all samples predicted malicious |

These legacy results do not establish that less context is harmful: the
five-packet prompt was the best legacy setting, while longer prompts collapsed
toward an all-malicious decision. They cannot be merged with the redesigned
time-window results because the units, cohorts, provider metadata, and leakage
controls differ. The recovered source is named
`llm_results_openai_verbose.json` and contains no model field; it therefore
cannot support a Claude Sonnet attribution. Claude Sonnet 4.6 remains executable
through the current provider path, but no provider-identified Sonnet session
artifact is claimed here.

### Local ML and Ensembles

The local suite evaluates complete held-out folds rather than budgeted subsets.
Table 2 gives the best model/feature combination at each granularity; the three
comparison figures below expose all five algorithms and all three feature sets,
including non-winning cells.

| Evaluation | Context | Best detector | Features | Accuracy | Precision | Recall | Pooled F1 |
|---|---|---|---|---:|---:|---:|---:|
| Balanced | Whole session | CART | Mercury-style | 89.56% | 93.34% | 85.19% | **89.08%** |
| Balanced | 30 s window | KNN | Combined | 88.95% | 92.63% | 84.63% | 88.45% |
| Balanced | 5 s window | KNN | Combined | 88.95% | 92.55% | 84.72% | 88.46% |
| Balanced | 1 s window | CART | Mercury-style | 89.28% | 93.39% | 84.53% | 88.74% |
| Balanced | Packet ablation | RF | Combined | 92.48% | 92.20% | 92.80% | **92.50%** |
| Deployment | Whole session | RF | Minimal | 83.75% | 92.06% | 75.86% | 83.18% |
| Deployment | 30 s window | RF | Minimal | 83.67% | 92.40% | 75.35% | 83.01% |
| Deployment | 5 s window | RF | Minimal | 84.20% | 92.91% | 75.95% | 83.58% |
| Deployment | 1 s window | CART | Combined | 85.30% | 92.08% | 79.04% | **85.06%** |
| Deployment | Packet ablation | -- | -- | -- | -- | -- | Unsupported |

Deployment packet ablation fails closed because fold 0 has only 60 malicious
validation samples, below the configured minimum support of 100. Reporting no
score is preferable to thresholding on an underpowered validation set. Across
the supported session/window cells, RF, XGBoost, and LightGBM are nearly
invariant to granularity: balanced F1 remains around 88% and deployment F1 around
80-84%. This stability is not universal. Balanced KNN falls to 75.08% with
minimal 5 s windows, while CART falls to approximately 76% for combined 30 s and
1 s windows. Thus, the evidence supports robustness for the ensembles and most
local configurations, not a blanket claim that every supervised learner is
immune to context reduction.

Across the 120 supported local session/window summary cells, throughput derived
from recorded test size and prediction time spans approximately 2.5 thousand to
1.47 million samples/s (median approximately 207 thousand), versus 1.72-1.91
seconds per remote GPT request. The measurements are not hardware-normalized,
but they establish that the prompted detector operates in a fundamentally
different latency regime.

### Cross-Model Comparison

The following figures order nominal temporal scope from largest to smallest on
the x-axis. Window duration is not a packet-count guarantee because traffic
intensity varies across sessions. Every cell reports pooled malicious F1; GPT
grey cells denote experiments that were not executed. In particular, GPT-5.4
was evaluated for whole sessions and 5 s windows only. The figures therefore
establish a whole-to-5 s loss but do not justify interpolation or a monotonic
claim at 30 s or 1 s.

#### Minimal Features

![Minimal-feature F1 by detector and context](figures/session_granularity_minimal.png)

[Vector PDF](figures/session_granularity_minimal.pdf). Minimal metadata is the
least sensitive balanced GPT configuration (61.00% to 59.95% F1), but deployment
F1 still falls from 90.33% to 77.66%. The local ensembles remain stable; the main
counterexample is balanced KNN at 5 s.

#### Mercury-Style Features

![Mercury-style F1 by detector and context](figures/session_granularity_mercury.png)

[Vector PDF](figures/session_granularity_mercury.pdf). Mercury-style context
raises whole-session GPT F1 over minimal features in balanced evaluation, but its
5 s deployment representation is brittle: F1 drops from 69.40% to 23.86%. Local
models remain tightly clustered, with no analogous systematic collapse.

#### Combined Features

![Combined-feature F1 by detector and context](figures/session_granularity_combined.png)

[Vector PDF](figures/session_granularity_combined.pdf). Combining both feature
families produces the strongest balanced whole-session GPT result (84.41%) but
does not protect against truncation. Deployment F1 falls from 74.21% to 25.71%,
whereas RF/XGBoost/LightGBM remain near their whole-session scores. CART's
isolated 30 s and 1 s balanced failures show why model-specific cells must remain
visible rather than reporting only the best local detector.

The most plausible mechanism is representation and calibration loss. A whole
session preserves long-range direction changes, packet-size transitions,
periodicity, and repeated service behavior. A 5 s slice can omit those events and
may resemble a benign connection prefix. GPT receives only a small budgeted set
of labeled memory examples and is not optimized on every training window; the
local models are fitted directly to all eligible supervised window profiles.
Short windows also shift score distributions across captures, weakening a
validation-selected threshold. These are evidence-consistent explanations, not
causal conclusions: a dedicated multi-window LLM sweep at 30 s and 1 s is needed
to isolate information loss from prompt representation and threshold transfer.

Important scope limits remain. The corpus contains seven benign and five
malicious captures, with one malicious capture per evaluated family. Sessions
and windows require at least six packets. Local and LLM inputs share base
metadata and split manifests, but their tabular and textual representations are
not byte-identical. Local models use full folds, whereas GPT uses frozen budgeted
subsets. Blind prompting, Sonnet 4.6, and fine-tuning paths exist in code but are
not represented by completed capture-disjoint artifacts in these tables.

See [`results/published/README.md`](results/published/README.md) for fold-level
records, provenance, and source-artifact hashes. Regenerate the three figures
with `python scripts/create_session_granularity_chart.py`.

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
scripts/                 compact result exporter and chart generator
results/published/       auditable summary JSONs only
figures/                 publication-facing aggregate figures
```

The repository does not claim that the current corpus represents production
base rates, that five held-out malware captures establish universal family
generalization, or that budgeted LLM subsets are equivalent to full-fold local
evaluation. Those limitations should remain explicit in any paper derived from
these artifacts.
