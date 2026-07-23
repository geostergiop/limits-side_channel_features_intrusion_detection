# Capture-Disjoint Session Experiment Consolidated Results

## Technical Summary

The expanded runs should be treated as the primary prompted-LLM evidence. The
earlier budgeted runs remain useful sensitivity checks, but their estimates moved
by as much as 0.214 absolute malicious-class F1 after increasing the sample budget.
The pilot and expanded selections also overlap only partially, so their rows must
not be pooled as independent observations.

- **Best balanced prompted-LLM configuration:** memory-enabled GPT-5.4 over
  combined whole-session features, with median fold accuracy 0.8269, median
  malicious F1 0.8352, and pooled F1 0.8441.
- **Best deployment prompted-LLM configuration:** memory-enabled GPT-5.4 over
  minimal whole-session features, with median fold accuracy 0.9227, median F1
  0.9097, and pooled F1 0.9033.
- **Best balanced session-focused local configuration:** minimal whole-session
  KNN, with median F1 0.9712 but pooled F1 0.8794 because the held-out Website
  capture is difficult.
- **Best deployment local median:** minimal five-second-window RF, with median F1
  0.9939. Its pooled F1 is only 0.8358 and its Website-fold F1 is 0.3807, so the
  median alone materially overstates cross-capture robustness.
- **Feature-set conclusion:** combined metadata helps GPT-5.4 in balanced
  whole-session testing, whereas minimal features are decisively best for GPT-5.4
  in deployment. Mercury-style fields do not provide a consistent advantage.
- **Representation conclusion:** whole-session prompts are substantially more
  dependable than five-second behavior-window prompts in deployment. Mercury and
  combined deployment windows collapse to pooled F1 0.2386 and 0.2571.
- **Family conclusion:** no detector dominates every held-out family. Local models
  are excellent on Dridex, Hancitor, and TrojanDownloader but fail badly on the
  Website capture. Minimal whole-session GPT-5.4 detects 97.65% of sampled Website
  sessions in deployment, but loses to local RF on the other four families.

The result artifacts identify the prompted model as **`gpt-5.4`**. These runs must
not be described as GPT-5.5 unless they are rerun with an artifact that records
that model identifier.

## Scope and Denominators

The primary protocol is `capture_disjoint_5fold`. Each malware capture/family is
held out exactly once, benign captures are distributed across folds, and train,
validation, and test capture IDs are pairwise disjoint. All session and behavior-
window cohorts use the six-packet eligibility threshold.

Balanced local models evaluate each of the five folds on 428 benign and 428
malicious sessions. The expanded balanced LLM run evaluates 104 sessions per fold
and variant, split 52/52, for 3,120 persisted test predictions:

`3 feature sets x 2 session representations x 5 folds x 104 test sessions`.

Deployment local models evaluate complete held-out folds:

| Fold | Held-out family | Benign | Malicious | Total | Malicious prevalence |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | BitCoinMiner | 779 | 345 | 1,124 | 30.69% |
| 1 | Dridex | 918 | 379 | 1,297 | 29.22% |
| 2 | Hancitor | 383 | 1,136 | 1,519 | 74.79% |
| 3 | TrojanDownloader | 410 | 326 | 736 | 44.29% |
| 4 | Website_5.8.88.175 | 333 | 991 | 1,324 | 74.85% |

The complete deployment cohort is 52.95% malicious. The expanded deployment LLM
run uses 100 validation and 220 test samples per fold and variant. It made 9,600
API calls, of which 6,600 are persisted held-out test predictions and 3,000 are
validation-only threshold calls. Equal per-fold test budgets yield 49.36% pooled
malicious prevalence; per-fold budgeted prevalence remains close to each source
fold at 28.64%, 26.36%, 72.73%, 41.82%, and 77.27%.

Local models cover RF, XGBoost, LightGBM, CART, and KNN over whole sessions,
one-/five-/30-second behavior windows, and a packet ablation where feasible. The
prompted-LLM runs summarized here use training-only memory, minimal/Mercury/
combined features, and either whole sessions or five-second behavior windows.

## Expanded GPT-5.4 Results

Metrics are reported as the median across five held-out-family folds. Pooled
metrics combine persisted test confusion counts and are included to expose effects
hidden by an unweighted median. `Worst F1` is the minimum family-fold F1.

### Balanced

| Representation | Features | Accuracy median | Pooled accuracy | F1 median | Pooled F1 | Precision median | Recall median | PR-AUC median | Worst F1 | Latency/call |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Whole session | Combined | 0.8269 | 0.8558 | **0.8352** | **0.8441** | 0.9744 | 0.7308 | 0.9135 | 0.7000 | 1.827 s |
| Whole session | Mercury | 0.7788 | 0.7981 | 0.7229 | 0.7672 | 0.9677 | 0.6154 | 0.8423 | 0.6667 | 1.773 s |
| Whole session | Minimal | 0.5865 | 0.7000 | 0.4946 | 0.6100 | 1.0000 | 0.4423 | 0.9745 | 0.0000 | 1.860 s |
| Five-second window | Combined | 0.7019 | 0.7135 | 0.7126 | 0.7061 | 0.6567 | 0.6538 | 0.6982 | 0.4045 | 1.778 s |
| Five-second window | Mercury | 0.5962 | 0.6538 | 0.6182 | 0.6311 | 0.5897 | 0.5577 | 0.7043 | 0.5055 | 1.833 s |
| Five-second window | Minimal | 0.6827 | 0.6635 | 0.6972 | 0.5995 | 0.6667 | 0.7308 | 0.7725 | 0.0000 | 1.835 s |

Minimal whole-session and minimal-window PR-AUC remain high despite poor F1 in
some folds. In particular, minimal whole-session Hancitor has PR-AUC 0.995 but
zero recall at the fixed 0.5 balanced threshold. This is a calibration/decision-
threshold failure, not an inability to rank Hancitor samples.

### Deployment

| Representation | Features | Accuracy median | Pooled accuracy | F1 median | Pooled F1 | Precision median | Recall median | PR-AUC median | Worst F1 | Latency/call |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Whole session | Minimal | 0.9227 | **0.9036** | **0.9097** | **0.9033** | 0.9784 | 0.9048 | 0.9841 | 0.7170 | 1.807 s |
| Whole session | Combined | 0.8818 | 0.7927 | 0.8758 | 0.7421 | 0.9508 | 0.7882 | 0.8978 | 0.1287 | 1.768 s |
| Whole session | Mercury | 0.7773 | 0.7627 | 0.7094 | 0.6940 | 0.9643 | 0.5529 | 0.9114 | 0.5000 | 1.734 s |
| Five-second window | Minimal | 0.8000 | 0.7955 | 0.7260 | 0.7766 | 0.6386 | 0.8413 | 0.7961 | 0.0000 | 1.733 s |
| Five-second window | Combined | 0.5864 | 0.5218 | 0.0808 | 0.2571 | 0.5000 | 0.0435 | 0.6248 | 0.0000 | 1.719 s |
| Five-second window | Mercury | 0.5864 | 0.5300 | 0.0619 | 0.2386 | 0.5326 | 0.0326 | 0.6170 | 0.0000 | 1.753 s |

All selected deployment thresholds satisfy the validation FPR ceiling of 5%.
However, validation-safe thresholds do not always transfer across captures. The
Mercury and combined window thresholds are often 0.90--0.999 and suppress nearly
all malicious predictions in several test folds. Combined whole-session Hancitor
similarly obtains PR-AUC 0.894 but only 6.88% recall after thresholding.

## Malware-Family Detection

Detection rate is malicious recall over the expanded prompted-LLM test subset.
Balanced support is 52 malicious sessions per family and variant.

### Balanced Detection Rate

| Representation / features | BitCoinMiner | Dridex | Hancitor | TrojanDownloader | Website |
| --- | ---: | ---: | ---: | ---: | ---: |
| Session / combined | **90.38%** | 73.08% | **100.00%** | 73.08% | **53.85%** |
| Session / Mercury | 61.54% | 67.31% | 96.15% | 57.69% | 50.00% |
| Session / minimal | 44.23% | **84.62%** | 0.00% | **88.46%** | 17.31% |
| Window / combined | 84.62% | 65.38% | **100.00%** | 59.62% | 34.62% |
| Window / Mercury | 51.92% | 65.38% | 78.85% | 55.77% | 44.23% |
| Window / minimal | 73.08% | 80.77% | 0.00% | 80.77% | 17.31% |

### Deployment Detection Rate

Support varies with held-out prevalence: BitCoinMiner 63, Dridex 58, Hancitor
160, TrojanDownloader 92, and Website 170 malicious test sessions per variant.

| Representation / features | BitCoinMiner | Dridex | Hancitor | TrojanDownloader | Website |
| --- | ---: | ---: | ---: | ---: | ---: |
| Session / minimal | **90.48%** | 96.55% | **85.00%** | **86.96%** | **97.65%** |
| Session / combined | 87.30% | **100.00%** | 6.88% | 76.09% | 78.82% |
| Session / Mercury | 73.02% | **100.00%** | 33.75% | 47.83% | 55.29% |
| Window / minimal | 84.13% | 96.55% | 71.25% | 0.00% | 98.82% |
| Window / combined | 0.00% | 89.66% | 3.13% | 4.35% | 17.65% |
| Window / Mercury | 0.00% | 84.48% | 2.50% | 3.26% | 14.71% |

## Local Baselines

The following table selects the best local algorithm by median malicious F1 for
each representation/feature cell matched to the prompted-LLM scope. Exact median
ties are broken by pooled F1 and are identified below; they are descriptive ties,
not evidence that one tied algorithm is statistically superior.

Across the additional local-only window durations, one-, five-, and 30-second
profiles produce broadly similar headline results for the strongest tree models;
there is no consistent duration winner across features and algorithms. Balanced
minimal packet ablation reaches median F1 0.9713, pooled F1 0.9012, and worst-fold
F1 0.7300 with RF, but it is a different prediction unit and cannot replace the
session analysis. Deployment packet ablation is unsupported as described below.

### Balanced Local Models

| Representation / features | Model | Accuracy median | F1 median | Worst F1 | Pooled F1 | Median throughput |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Session / minimal | KNN | 0.9720 | **0.9712** | 0.4615 | 0.8794 | 125,505/s |
| Window / minimal | CART | 0.9673 | 0.9662 | 0.4714 | 0.8812 | 969,048/s |
| Session / Mercury | RF | 0.9638 | 0.9624 | 0.4714 | 0.8811 | 13,007/s |
| Window / Mercury | RF | 0.9638 | 0.9624 | 0.4714 | 0.8813 | 14,554/s |
| Session / combined | RF | 0.9638 | 0.9624 | 0.4714 | 0.8812 | 14,206/s |
| Window / combined | KNN | 0.9650 | 0.9638 | 0.4698 | **0.8846** | 72,738/s |

### Deployment Local Models

| Representation / features | Model | Accuracy median | F1 median | Worst F1 | Pooled F1 | Median throughput |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Session / minimal | RF | 0.9878 | 0.9863 | 0.3807 | 0.8318 | 21,626/s |
| Window / minimal | RF | 0.9946 | **0.9939** | 0.3807 | **0.8358** | 18,758/s |
| Session / Mercury | RF | 0.9592 | 0.9519 | 0.3748 | 0.8250 | 18,687/s |
| Window / Mercury | RF | 0.9592 | 0.9519 | 0.3761 | 0.8203 | 21,702/s |
| Session / combined | RF | 0.9606 | 0.9535 | 0.3727 | 0.8300 | 21,472/s |
| Window / combined | RF | 0.9606 | 0.9535 | 0.3767 | 0.8300 | 17,234/s |

Balanced session/Mercury is tied between RF and XGB at median F1 0.9624.
Balanced session/combined is tied among RF, XGB, LGBM, and CART at 0.9624.
Deployment session/combined and window/combined are tied between RF and LGBM at
0.9535. The table uses pooled F1 only as a deterministic secondary display rule.

For the same minimal whole-session representation, local models beat GPT-5.4 on
four of five deployment families. The exception is Website: GPT-5.4 reaches F1
0.9852 and recall 0.9765 on its 220-sample budgeted test subset, while local RF
reaches F1 0.3807 and recall 0.2351 over the complete 1,324-session fold. This is
the strongest evidence of complementary behavior, but the unequal denominators
preclude declaring GPT-5.4 globally superior.

The validation FPR ceiling is an operating-point selection constraint, not a
guarantee on unseen captures. For minimal whole-session GPT-5.4, pooled held-out
test FPR is 0.1041 despite every validation FPR being at most 0.05; BitCoinMiner
alone reaches test FPR 0.2484. The corresponding full-fold RF test FPR is 0.0737.
Deployment claims must therefore report held-out test FPR as well as validation
FPR, recall, precision, and F1.

Deployment packet ablation is unsupported for all three feature sets because one
validation fold has only 60 malicious samples, below the prespecified support
floor of 100. These are correctly marked unsupported rather than scored.

## Pilot-to-Expanded Sensitivity

Absolute changes in median malicious F1 after the fourfold test-budget increase:

| Representation / features | Balanced change | Deployment change |
| --- | ---: | ---: |
| Session / combined | -0.0815 | +0.1615 |
| Session / Mercury | -0.0044 | +0.0118 |
| Session / minimal | +0.0401 | +0.0273 |
| Window / combined | +0.0811 | -0.0192 |
| Window / Mercury | -0.0182 | **-0.2140** |
| Window / minimal | +0.1139 | -0.0057 |

Only 114 of 780 pilot balanced prediction keys overlap the 3,120 expanded keys;
only 300 of 1,650 pilot deployment test keys overlap the 6,600 expanded keys.
Therefore, the expanded runs are larger deterministic resamples, not strict
supersets of the pilot runs. Report them as a sensitivity analysis, not as
independent replications or one pooled experiment.

## Runtime and Operational Implications

Expanded GPT-5.4 median latency is approximately 1.72--1.86 seconds per session
decision. Local model-only inference ranges from roughly 13,000 to 969,000
sessions per second for the selected cells, or about 0.001--0.069 ms per session.
Depending on the local algorithm, prompted API inference is approximately 22,000
to 1.8 million times slower. These figures exclude feature extraction and
network capture overhead for local models but include API latency for GPT-5.4.

The expanded balanced test predictions consume 11.57 million recorded tokens and
1.60 serial latency-hours. Expanded deployment test predictions consume 23.40
million recorded tokens and 3.21 serial latency-hours. Deployment validation-call
tokens and latency are not persisted, so total deployment API usage cannot be
reconstructed exactly from the result JSON.

## Integrity and Reporting Caveats

- All four final LLM JSON files are byte-identical to their `.partial.json`
  checkpoints.
- Every LLM artifact has six summaries, 30 fold metrics, and 30 family summaries.
- Prediction-key duplicates: zero. Invalid LLM responses: zero. Missing expected
  malware families: zero.
- Every recorded deployment validation FPR is at or below the configured 5% limit.
- Balanced and deployment manifests are distinct, but all algorithms and feature
  sets within a protocol reuse compatible frozen cohorts.
- Validation predictions used for deployment threshold selection are not stored as
  raw rows. Threshold, validation FPR, and strategy metadata are retained, but the
  threshold cannot be independently recomputed from the result artifact alone.
- The five malware families each originate from one capture. Consequently,
  held-out-capture and held-out-family effects remain confounded; five folds expose
  heterogeneity but do not estimate performance over a broad population of captures
  per family.
- The complete deployment cohort reflects corpus prevalence, not a typical
  production-network malware base rate. Deployment claims must use that wording.
- Fold medians should always be accompanied by pooled performance, per-family
  support, and minima. The large min--max spread is real cross-capture domain shift,
  not random repeat noise or an arithmetic error.
- Labels such as "best" are descriptive rankings across the prespecified candidate
  models on these five test folds. They are not an independently validated model-
  selection decision and should not be presented as one.

## Source Artifacts

Primary expanded LLM artifacts:

- `session_llm_results_capture_disjoint_5fold_balanced_paper_5k_custom_9149ef9b7f_openai_memory.json`
- `session_llm_results_capture_disjoint_5fold_deployment_paper_6k_custom_8da97f7973_openai_memory.json`

Pilot sensitivity artifacts:

- `session_llm_results_capture_disjoint_5fold_balanced_paper_5k_custom_c27f8e02c3_openai_memory.json`
- `session_llm_results_capture_disjoint_5fold_deployment_paper_6k_custom_1568571713_openai_memory.json`

Local artifacts:

- `session_local_results_capture_disjoint_5fold_balanced.json`
- `session_local_results_capture_disjoint_5fold_deployment.json`
