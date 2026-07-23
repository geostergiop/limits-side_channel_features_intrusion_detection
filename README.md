# LLM-Powered Malicious Traffic Detection via Side-Channel Features

**Version 5.0.0** — April 2026

## Research Overview

This project investigates whether a general-purpose LLM can reason over minimal
TCP side-channel features to classify network traffic as malicious or benign —
without deep-packet inspection, payload access, or prior training on the target
attack type.

Three open gaps are addressed:

**Gap 1 — LLM as a classifier:** Can an LLM match or exceed CART/KNN when given
only the 5 side-channel features (packet size, payload size, payload ratio,
ratio-to-previous, time difference)?

**Gap 2 — Zero-shot novel attack detection:** Can an LLM generalise to a
malware family it has never seen, using only these 5 features, without
retraining?

**Gap 3 — Adversarial robustness:** Is an LLM-based classifier more robust to
adversarial traffic shaping than classical ML (CART/KNN)? Decision trees make
independent, axis-aligned splits — an attacker who knows the thresholds can
game one feature at a time. An LLM reasons about the *joint distribution* of
features as a narrative, detecting inconsistencies that isolated threshold
checks miss.

---
## Experiment Output Summaries

This section summarizes the latest output logs.

**Phase 2 local tree-ensemble baselines** (RF, XGB, LGBM)
across session holdout, capture holdout, and leave-one-family-out (LOFO).

- **Session holdout is consistently strong**:
  - E1 full mixed: RF 0.9894, XGB 0.9857, LGBM 0.9880 accuracy
  - E2 limited 20k: all ~0.986–0.988 accuracy
  - E3 encrypted-only: all ~0.993–0.994 accuracy
- **Capture holdout is more variable**:
  - E1 full mixed remains high (~0.97–0.98)
  - E2 limited 20k drops sharply (~0.70–0.72), with very high malicious recall
    but many false positives
  - E3 encrypted-only is strongest for RF (0.9954), while XGB/LGBM show lower
    malicious recall
- **LOFO generalisation**:
  - Session-holdout LOFO is mostly good, with hardest families including Dridex
    and Website_5.8.88.175
  - Capture-holdout LOFO is substantially harder (~0.65–0.75 accuracy range)

**Full pipeline for Phases 3–6**: classical ML, LLM
experiments, comparative analysis, and adversarial robustness.

- **Phase 3 classical ML**:
  - Best models are CART/KNN, repeatedly near ~0.98–0.99 accuracy in E1/E2
    holdouts, with strong encrypted session performance as well
  - LR/LDA/NB are weaker; SVC is unstable in the larger settings
- **Phase 4 LLM experiments**:
  - 4A zero-shot: Acc 0.508, F1 0.201
  - 4B few-shot improves with k (best at k=10: Acc 0.680, F1 0.593)
  - 4C CoT: Acc 0.570, F1 0.538
  - 4E session windows: best at window=5 (Acc 0.960, F1 0.962), then degrades
    as window size increases
  - API usage for phase 4 run: 3,200 calls, ~2.61M tokens, ~$7.83
- **Phase 5 adversarial robustness**:
  - Classical models (especially KNN) remain relatively resistant in evaluation
    (single-digit to low-double-digit evasion in many settings)
  - LLM zero-shot is highly vulnerable (roughly ~67–77% evasion across tested ε)
  - LLM few-shot improves robustness vs zero-shot; CoT sits in between
  - Transfer and black-box attacks can achieve high LLM evasion rates
  - At session level, LLM detection remains high (98–99%) while CART drops at
    higher perturbation budgets

---

## Version 5.0 Highlights

The main changes are:

- **Grouped holdout for classical ML and adversarial training.** Phase 3 no longer
  splits individual packets at random. Train/test separation is now performed by
  **session** or by **capture** (`dataset_id`) using repeated grouped holdout and
  selecting a class-balanced disjoint split.
- **Malware-family labelling for local pcaps.** Local `mnt/attack_pcap/*.pcap`
  datasets now inherit family labels from `configs/config.py` mappings or filename
  inference, which enables Leave-One-Family-Out evaluation on the packaged corpus
  when at least two named families are present.
- **Correct adversarial accounting.** `prediction == -1` is now treated as
  **invalid**, excluded from evasion-rate numerators and denominators, and reported
  explicitly as invalid-count metadata.
- **Improved flow/session boundaries.** Phase 1 now rotates flows on inactivity
  timeout, fresh TCP SYN reuse, and post-FIN/RST closure grace periods. This
  prevents unrelated connections that reuse the same 5-tuple from being merged into
  one synthetic session.
- **Experiment 4E fixed-cohort evaluation.** Session-window analysis now samples a
  single balanced cohort once, reuses that same cohort across all window sizes, and
  records real `latency_ms` for every LLM call together with a cohort hash.
- **OpenAI is now the default provider.** All top-level examples use OpenAI first.
  Anthropic remains optional and supported.

---

## Session-Based Experiments

Phase 7 is the reviewer-response experiment suite. It intentionally separates
three questions that should not be mixed:

- Which feature set is being tested?
- Is the test cohort class-balanced or prevalence-faithful?
- Is the LLM blind, memory-enabled, or fine-tuned?

### What Every Phase 7 Run Tests

Phase 7 uses frozen grouped split manifests under
`results/split_manifests/session_protocol_v1/`. If a matching manifest already exists, it is
reused rather than regenerated. The default Session grouping is by capture
(`dataset_id`), so train, validation, and test data do not share the same
capture.

Every Session run can evaluate three feature configurations:

- `minimal`: the original five side-channel features from the first version.
- `mercury`: Mercury-style metadata available from this project's current SQLite
  schema, such as direction, protocol, ports, service hints, encryption hint,
  timing, and packet deltas.
- `combined`: the original five features plus the Mercury-style metadata fields.

The current database does not persist full Cisco Mercury fingerprint strings for
TLS, SSH, HTTP, TCP options, or raw protocol feature strings. The `mercury`
configuration is therefore a Mercury-style metadata baseline over fields actually
extracted by this project.

Every feature configuration is evaluated over the Session sample units:

- `session_sequence`: a session-level row/prompt that gives the model packet
  behavior across a session, not just one isolated packet.
- `behavior_window`: a time-window row/prompt for behavior that may only become
  visible over a window, such as beaconing-like periodicity. Window sizes come
  from `NDSS_CONFIG["behavior_window_seconds"]`.
- `packet_ablation`: an individual-packet ablation retained only to show how much
  performance changes when the model is forced back to the original weaker
  packet-level framing.

### Evaluation Modes

Phase 7 has two independent controls. `--session-eval-mode` controls prevalence:

- `balanced`: class-balanced cohorts for apples-to-apples scientific comparison.
- `deployment`: prevalence-faithful cohorts for deployment-oriented claims. In this
  mode, thresholds are chosen on validation data only and then applied once on the
  imbalanced test split.

`--session-split-mode` controls the leakage boundary:

- `capture_disjoint_5fold` is the primary protocol. Each of the five malware
  captures is the dedicated test capture in one fold; benign captures are also
  assigned to test so every benign capture is covered. Train, validation, and test
  capture IDs are pairwise disjoint.
- `within_capture_temporal` is a secondary seen-capture upper bound. Within every
  capture, the earliest 60% of sessions train the model, the next 20% calibrate it,
  and the latest 20% are tested. It does **not** support unseen-capture or unseen-
  family claims.

The split mode and evaluation mode are orthogonal. For example,
`capture_disjoint_5fold + balanced` tests controlled unseen-capture generalization,
whereas `capture_disjoint_5fold + deployment` tests unseen-capture generalization
at natural held-out-capture prevalence.

Use `balanced` when answering: "Does an LLM or local model perform better when
malicious and benign classes are deliberately controlled?" This is the cleanest
scientific comparison because each method sees the same balanced train,
validation, and test splits.

Use `deployment` when answering: "What happens at the corpus-natural held-out-capture prevalence?"
This mode is the one to cite for deployment claims, false-positive burden,
absolute accuracy, and threshold-sensitive behavior. For local models and LLMs,
the decision threshold is selected only on validation data and then evaluated
once on the held-out imbalanced test split.

Here, "prevalence-faithful" means faithful to the sampled corpus and held-out
captures, not to an assumed enterprise-network base rate. The current corpus can
contain far more malicious sessions than a production network. Report each fold's
observed support/prevalence and do not extrapolate precision to a different base
rate without a separate prevalence-adjustment analysis.

### Flag Reference

| Flag | Values | Meaning |
| --- | --- | --- |
| `--session-mode` | `local`, `llm`, `finetune`, `all` | Chooses which experiment family runs. `local` runs RF/XGB/LGBM/CART/KNN. `llm` runs prompted LLM inference. `finetune` exports fine-tune corpora and can evaluate a supplied fine-tuned model. `all` runs local models, prompted LLMs, and fine-tune corpus export in one command. |
| `--session-eval-mode` | `balanced`, `deployment` | Chooses controlled class balance or natural held-out-capture prevalence. Deployment thresholds are selected on validation only under the configured FPR ceiling. |
| `--session-split-mode` | `capture_disjoint_5fold`, `within_capture_temporal` | Chooses unseen-capture generalization or the explicitly weaker seen-capture temporal upper bound. Never aggregate these protocols. |
| `--session-llm-context` | `blind`, `memory`, `both` | Applies only to `--session-mode llm` or `all`. `blind` gives the LLM only task instructions plus the held-out sample. `memory` prepends training-split class/family summaries and labeled examples as context. `both` runs both variants in the same result file. |
| `--provider` | `openai`, `anthropic` | Chooses the prompted LLM provider. OpenAI is the default in the examples. |
| `--session-budget-profile` | `full`, `paper_5k`, `paper_6k` | Chooses the prompted LLM scope. `paper_5k` and `paper_6k` use the five frozen family folds (`0` through `4`). |
| `--dry-run` | flag | Prints representative LLM prompts and coverage warnings without making API calls. Use it with `--session-mode llm`; it does not write result or report files. |
| `--allow-large-llm-run` | flag | Required for Phase 7 prompted LLM sweeps whose estimated API-call count exceeds `NDSS_CONFIG["llm_large_run_call_threshold"]`. This prevents accidentally launching tens of thousands of calls. |

### Output Files

Phase 7 writes protocol-qualified files. Old `ndss_*.json` artifacts are not
loaded by this implementation and must not be combined with redesigned results:

- `results/session_local_results_<split>_<evaluation>.json`: local fold rows,
  robust summaries, unsupported cells, and paired differences.
- `results/session_llm_results_<split>_<evaluation>_<profile>_<provider>_<context>.json`: prompted or
  fine-tuned sample rows, fold summaries, family detection, and paired context
  differences.
- `results/session_report_<split>_<evaluation>_<profile>_<provider>_<context>.md`: fold support,
  prevalence, median/IQR/min/max, runtime, family, and paired-comparison tables.
- `results/finetune/session_protocol_v1/*.jsonl` and `*.json`: fine-tuning train,
  validation, test, and metadata exports.
- `results/split_manifests/session_protocol_v1/*.json`: immutable protocol
  manifests. Feature sets share a manifest whenever cohort semantics are identical.

Runs that execute local models or LLM inference write a fresh result file for
the selected `--session-mode`, `--session-eval-mode`, and split mode. If you want blind and
memory-enabled LLMs compared in the same JSON/report, use the context mode
`both`. If you run `blind` and `memory` as separate commands, the later command
writes only the selected context rows for that evaluation mode.

### Recommended Reviewer Run Sequence

### Budgeted Prompted-LLM Design

Use `--session-budget-profile paper_5k` for the reviewer-ready balanced prompted
LLM run when API budget matters. This profile is intentionally not the full
factorial sweep. It evaluates:

- Feature sets: `minimal`, `mercury`, and `combined`.
- Sample units: `session_sequence`, complete sessions represented as ordered
  `behavior_window` sequences at `5.0` seconds, and `packet_ablation` as a
  blind-only ablation. Session and behavior-window eligibility both use a
  six-packet minimum so Hancitor is represented with meaningful support.
- Contexts: `blind` and `memory` for session/window samples; `blind` only for
  packet ablation.
- Folds: frozen fold indices `0,1,2,3,4`; each is tied to one dedicated held-out
  malware capture/family by the manifest.
- Balanced mode: `26` held-out test samples per fold.
- Deployment mode under `paper_5k`: `15` validation samples plus `27` held-out
  test samples per fold.
- Deployment mode under `paper_6k`: `25` validation samples plus `55` held-out
  test samples per fold.

Expected API-call counts:

- Balanced budgeted run: `15 variants x 5 folds x 26 = 1,950` calls.
- Deployment budgeted run: `15 variants x 5 folds x (15 + 27) = 3,150` calls.
- Both together: `5,100` calls.
- Higher-depth deployment run: `15 variants x 5 folds x (25 + 55) = 6,000`
  calls with `--session-budget-profile paper_6k`.

API price and retry behavior can change, so the code enforces call-count preflight
rather than promising a currency cost. Budgeted outputs remain separate:

- `results/session_llm_results_capture_disjoint_5fold_balanced_paper_5k_openai_both.json`
- `results/session_llm_results_capture_disjoint_5fold_deployment_paper_5k_openai_both.json`
- `results/session_llm_results_capture_disjoint_5fold_deployment_paper_6k_openai_both.json`
- matching `.partial.json` checkpoint files during execution
- `results/session_report_capture_disjoint_5fold_balanced_paper_5k_openai_both.md`
- `results/session_report_capture_disjoint_5fold_deployment_paper_5k_openai_both.md`
- `results/session_report_capture_disjoint_5fold_deployment_paper_6k_openai_both.md`

Balanced `paper_5k` is the mode to cite for malware-family detection-rate
coverage because it uses family-stratified malicious sampling and records
per-family summary rows. Deployment `paper_6k` is the preferred mode to cite for
prevalence/threshold behavior after the balanced run because it scores more
validation and test samples per fold. Every family has one dedicated test fold;
still check `LLM Family Coverage Audit`, support, and
`missing_malicious_families` before making an all-family claim about a narrowed
or interrupted run.

#### 1. Preview LLM Prompts Without API Calls

Use this before spending money on prompted LLM experiments:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode llm --session-llm-context memory --dry-run
```

What it tests: prompt construction, feature rendering, session/window formatting,
and memory-context formatting.

What it outputs: representative prompts and coverage warnings in the console.
It does not make API calls and, for `--ndss-mode llm`, does not write result or
report files.

#### 2. Run Local Baselines With Balanced Scientific Comparison

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode local
```

What it tests: RF, XGBoost, LightGBM, CART, and KNN over `minimal`, `mercury`,
and `combined` features, across session, behavior-window, and packet-ablation
sample units, using class-balanced grouped train/validation/test splits.

Why run it: this is the apples-to-apples local baseline for scientific
comparison. It answers whether richer metadata improves classical baselines and
which local model is strongest when class prevalence is controlled.

What it outputs: `results/session_local_results_capture_disjoint_5fold_balanced.json`
and a protocol-qualified Session report.

API key: not required. These models run locally.

#### 3. Run Local Baselines With Deployment Prevalence

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode local
```

What it tests: the same local models, feature sets, and sample units as step 2,
but on prevalence-faithful grouped splits. Thresholds are selected on validation
data only and then applied once to the imbalanced test split.

Why run it: this is the local-model evidence for deployment claims. It exposes
false-positive burden, threshold sensitivity, absolute detection accuracy, and
runtime throughput under a more realistic class distribution.

What it outputs: `results/session_local_results_capture_disjoint_5fold_deployment.json`
and a protocol-qualified Session report.

API key: not required.

#### 4. Run Blind and Memory-Enabled LLMs With Balanced Scientific Comparison

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode llm --provider openai --session-llm-context both --session-budget-profile paper_5k
```

What it tests: prompted LLM classification over the same feature sets and sample
units as the local baselines, using balanced held-out evaluation samples. `blind`
is the original zero-shot/few-instruction style. `memory` adds training-split
class/family summaries and labeled examples as structured context before the
held-out sample. Memory mode is intentionally skipped for `packet_ablation`
because packet-level prompts are retained only as an ablation.

Why run it: this compares blind and memory-enabled LLM behavior under controlled
balanced conditions, matching the scientific comparison used for local models.

What it outputs: `results/session_llm_results_capture_disjoint_5fold_balanced_paper_5k_openai_both.json`
and its matching Session report.

API key: required for the selected provider.

Cost / runtime warning: with `paper_5k`, this balanced command is about `1,950`
API calls and writes to the protocol-qualified `session_llm_results_*.json`. The
the exhaustive sweep is substantially larger and requires
`--allow-large-llm-run`.

#### 5. Run Blind LLMs With Deployment Prevalence

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode llm --provider openai --session-llm-context blind --session-budget-profile paper_6k
```

What it tests: the deployment version of the original blind prompted LLM
baseline. The LLM scores validation samples first, the threshold is selected on
validation scores, and that threshold is then applied to the imbalanced test
sample.

Why run it: this isolates the strictest "LLM used blind" deployment baseline.
It is useful when responding to the reviewer concern that blind LLM prompting is
too weak or unrealistic.

What it outputs: `results/session_llm_results_capture_disjoint_5fold_deployment_paper_6k_openai_blind.json`
and its matching report, containing blind-context
LLM rows only.

API key: required.

#### 6. Run Memory-Enabled LLMs With Deployment Prevalence

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode llm --provider openai --session-llm-context memory --session-budget-profile paper_6k
```

What it tests: the same deployment protocol as step 5, but the LLM receives
training-split context before each held-out validation/test sample. This is the
content/memory-enabled LLM variation requested by the reviewer.

Why run it: this directly tests whether structured exposure to benign/malicious
families and examples improves LLM deployment performance compared with blind
prompting.

What it outputs: `results/session_llm_results_capture_disjoint_5fold_deployment_paper_6k_openai_memory.json`
and its matching report, containing memory-context
LLM rows only.

API key: required.

Recommended shortcut: if you want blind and memory-enabled deployment results in
the same JSON/report, run this single combined command instead of separate steps
5 and 6:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode llm --provider openai --session-llm-context both --session-budget-profile paper_6k
```

Deployment `both` is larger than balanced mode because each fold scores a
validation subset for threshold selection plus a held-out test subset. With
`paper_6k`, it is capped at about `6,000` estimated API calls. The original
exhaustive deployment sweep is substantially larger and requires
`--allow-large-llm-run`.

#### 7. Export the Fine-Tuning Corpus

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode finetune
```

What it tests: no model inference is run by default. This exports train,
validation, and held-out test JSONL files from a frozen grouped split using the
configured fine-tune sample unit and feature set.

Why run it: this prepares the supervised LLM baseline requested by the reviewer,
without mixing in-context prompting with supervised local-model training.

What it outputs: `results/finetune/session_protocol_v1/*_train.jsonl`,
matching validation/test JSONL files, and a
metadata JSON file.

API key: not required unless `--start-finetune-job` is also supplied.

#### 8. Start an OpenAI Fine-Tuning Job

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode finetune --start-finetune-job
```

What it tests: uploads the exported corpus and starts the OpenAI fine-tuning job.

What it outputs: the same corpus files as step 7 plus job metadata in the
fine-tune metadata JSON.

API key: `OPENAI_API_KEY` is required.

#### 9. Evaluate a Fine-Tuned OpenAI Model

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode finetune --finetuned-model ft:your-model-id
```

What it tests: the supplied fine-tuned model on the held-out test split from the
same frozen fold used to export the fine-tuning train/validation files. This
avoids leakage across capture-disjoint partitions.

What it outputs: a protocol-qualified `results/session_llm_results_*.json`, its
matching Session report, and fine-tune metadata.

API key: `OPENAI_API_KEY` is required.

### Full-Suite Shortcuts

These commands are convenient after the stepwise runs are understood, but they
are more expensive because `--session-mode all` runs local models, prompted LLMs,
and fine-tune corpus export together.

Balanced full suite:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode balanced --session-mode all --provider openai --session-llm-context both --session-budget-profile paper_5k
```

Deployment full suite:

```powershell
python run_all.py --phase 7 --session-split-mode capture_disjoint_5fold --session-eval-mode deployment --session-mode all --provider openai --session-llm-context both --session-budget-profile paper_6k
```

### Secondary Temporal Upper Bound

Run the secondary protocol separately; never merge it with capture-disjoint rows:

```powershell
python run_all.py --phase 7 --session-split-mode within_capture_temporal --session-eval-mode balanced --session-mode local
```

This tests later sessions from every capture after training on earlier sessions
from those same captures. The output is
`results/session_local_results_within_capture_temporal_balanced.json`. Its
supported interpretation is a seen-capture temporal upper bound. Because every
malware family maps to one capture, it cannot establish generalization to unseen
captures or malware families.

### Eligibility

Both whole-session `session_sequence` and `behavior_window` cohorts use a
six-packet minimum. In the current corpus this retains 11,247 eligible Hancitor
sessions instead of the six sessions that survived the former eight-packet rule.
Eligibility is embedded in manifest identity and cohort hashing, so old
eight-packet manifests cannot be loaded for these runs.

### API Key Configuration

The project reads provider keys from environment variables.

For the current PowerShell session:

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

To persist them for your Windows user profile:

```powershell
setx OPENAI_API_KEY "sk-..."
setx ANTHROPIC_API_KEY "sk-ant-..."
```

Notes:

- `OPENAI_API_KEY` is required for OpenAI prompted runs and for starting OpenAI fine-tuning jobs.
- `ANTHROPIC_API_KEY` is required only when you run Phase 4 or Phase 7 with `--provider anthropic`.
- There is no API key to configure for the local Session models; RF, XGBoost, LightGBM, CART, and KNN run locally.
