# GPT-5.4 Session Detection: Cross-Generation Results Audit

## Technical Summary

The completed capture-disjoint experiments show a real and substantial increase
in prompted-LLM session-level detection relative to the legacy single-packet
experiments. They do not, however, establish that GPT-5.4 alone caused the
increase. Model, prediction unit, prompt representation, in-context supervision,
split difficulty, thresholding, and aggregation all changed together.

The strongest expanded GPT-5.4 result is memory-enabled minimal whole-session
detection under the deployment protocol: pooled accuracy 0.9036, precision
0.8951, recall 0.9116, and malicious F1 0.9033 over 1,100 budgeted test sessions.
The strongest balanced result is combined whole-session detection: pooled
accuracy 0.8558 and F1 0.8441 over 520 sessions. These results are internally
consistent with the raw prediction rows.

The apparent parity with local ML is aggregation-dependent. In balanced combined
whole-session testing, GPT-5.4 has pooled F1 0.8441 versus 0.8812 for local RF,
but median fold F1 remains 0.8352 versus 0.9624. In deployment minimal
whole-session testing, GPT-5.4 has pooled F1 0.9033 versus 0.8318 for RF, but RF
beats GPT-5.4 on four of five held-out malware captures. GPT-5.4 wins the Website
fold by a large margin, and that single cross-capture failure reverses the pooled
ranking.

The correct paper-level conclusion is therefore not that GPT-5.4 has reached or
surpassed supervised local detection. The defensible conclusion is that
memory-conditioned GPT-5.4 can be competitive on aggregated session metadata,
exhibits complementary cross-family behavior, and sharply narrows the pooled gap
under selected representations. Local ML remains substantially stronger by
median family-fold performance, wins most matched deployment folds, and is
approximately 22,000 to 1.8 million times faster.

**Assessment:** the result artifacts are internally sound and usable with
caveats. The current manuscript needs revision before submission because its
headline session values describe an earlier protocol, and the legacy LLM archive
does not record a model identifier.

## Evidence and Protocol Boundaries

### Current Capture-Disjoint Suite

The primary artifacts are the expanded memory-only GPT-5.4 runs and the complete
local folds:

- Balanced GPT-5.4: 3 feature sets x 2 representations x 5 folds x 104 test
  sessions = 3,120 predictions.
- Deployment GPT-5.4: 3 feature sets x 2 representations x 5 folds x
  (100 validation + 220 test) = 9,600 API calls, with 6,600 persisted test
  predictions.
- Balanced local ML: 75 model/representation/feature summaries and 375 full-fold
  evaluations.
- Deployment local ML: 60 supported summaries and 300 full-fold evaluations;
  deployment packet ablation is correctly unsupported for all feature sets.

The split contains seven benign captures and five malware captures. Each malware
family occurs in exactly one capture. Consequently, the five test folds are both
capture-disjoint and malware-family-disjoint, but capture identity, collection
environment, and family identity cannot be separated statistically.

Balanced local folds contain 428 benign and 428 malicious sessions per family.
Balanced GPT-5.4 evaluates 52 benign and 52 malicious sessions per family and
configuration. Deployment local ML evaluates all 6,000 held-out sessions across
the five folds. Deployment GPT-5.4 evaluates 220 sessions per fold while
preserving each fold's corpus prevalence approximately.

### Representation Is Not Identical Across Detector Classes

Both detector classes derive from the same payload-free base metadata, but they
do not receive the same tensor. Local whole-session models receive six aggregate
statistics per base feature plus packet count and duration: 32 minimal, 122
Mercury-style, or 152 combined columns. Local behavior-window models receive
seven additional aggregate window descriptors.

GPT-5.4 receives named JSON features and up to 32 ordered segments. Each segment
contains packet count, temporal coverage, and per-feature mean and standard
deviation. Whole-session sequences use contiguous packet blocks; behavior-window
sequences use ordered five-second windows, with long sessions compressed into
ordered bins. This gives GPT-5.4 explicit temporal order and semantic field names
that are absent from the local tabular profiles. Claims should therefore say
"the same underlying metadata," not "identical features."

### Memory and Calibration

Every current GPT-5.4 request is memory-enabled. The prompt contains four benign
and four malicious examples selected from that fold's training split, training
class counts, and up to eight observed training-family counts. The held-out
family does not occur in training because it is represented by only one malware
capture. This is leakage-free in the implemented split, but it is in-context
supervision rather than zero-shot inference or parameter fine-tuning.

Balanced evaluation uses a fixed confidence-derived threshold of 0.5. Deployment
uses 100 validation calls per fold and configuration, then maximizes validation
recall subject to validation FPR <= 0.05. The score is derived from the LLM's
reported class and self-reported confidence; it is not a calibrated model
probability or token logit.

## Current GPT-5.4 Results

`Median F1` is the median over five held-out family/capture folds. `Pooled F1`
combines test confusion counts. `Fold range` is the observed minimum and maximum,
not a confidence interval.

### Balanced Evaluation

| Representation | Features | Pooled accuracy | Pooled precision | Pooled recall | Median F1 | Pooled F1 | Fold range |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Whole session | Combined | 0.8558 | 0.9186 | 0.7808 | **0.8352** | **0.8441** | 0.7000-1.0000 |
| Whole session | Mercury | 0.7981 | 0.9058 | 0.6654 | 0.7229 | 0.7672 | 0.6667-0.9804 |
| Whole session | Minimal | 0.7000 | 0.8714 | 0.4692 | 0.4946 | 0.6100 | 0.0000-0.9388 |
| Five-second windows | Combined | 0.7135 | 0.7247 | 0.6885 | 0.7126 | 0.7061 | 0.4045-0.9630 |
| Five-second windows | Mercury | 0.6538 | 0.6754 | 0.5923 | 0.6182 | 0.6311 | 0.5055-0.8367 |
| Five-second windows | Minimal | 0.6635 | 0.7401 | 0.5038 | 0.6972 | 0.5995 | 0.0000-0.8842 |

The best fold is Hancitor under combined whole-session prompting, with F1 1.0000.
The worst folds are Hancitor under minimal whole-session and minimal window
prompting, both with F1 0.0000. Minimal whole-session Hancitor nevertheless has
fold PR-AUC 0.9953. GPT-5.4 ranks those samples correctly but assigns scores below
the fixed 0.5 operating threshold. This is a calibration failure rather than a
ranking failure.

For the best balanced configuration, family-level detection rates and Wilson 95%
intervals are:

| Held-out family | Detected / malicious | Detection rate | Wilson 95% interval |
| --- | ---: | ---: | ---: |
| BitCoinMiner | 47 / 52 | 0.9038 | [0.7939, 0.9582] |
| Dridex | 38 / 52 | 0.7308 | [0.5975, 0.8323] |
| Hancitor | 52 / 52 | 1.0000 | [0.9312, 1.0000] |
| TrojanDownloader | 38 / 52 | 0.7308 | [0.5975, 0.8323] |
| Website | 28 / 52 | 0.5385 | [0.4050, 0.6666] |

### Deployment Evaluation

| Representation | Features | Pooled accuracy | Pooled precision | Pooled recall | Median F1 | Pooled F1 | Fold range |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Whole session | Minimal | **0.9036** | 0.8951 | **0.9116** | **0.9097** | **0.9033** | 0.7170-0.9852 |
| Whole session | Combined | 0.7927 | **0.9619** | 0.6041 | 0.8758 | 0.7421 | 0.1287-0.9748 |
| Whole session | Mercury | 0.7627 | 0.9548 | 0.5451 | 0.7094 | 0.6940 | 0.5000-0.9431 |
| Five-second windows | Minimal | 0.7955 | 0.8427 | 0.7201 | 0.7260 | 0.7766 | 0.0000-0.9941 |
| Five-second windows | Combined | 0.5218 | 0.5515 | 0.1676 | 0.0808 | 0.2571 | 0.0000-0.6190 |
| Five-second windows | Mercury | 0.5300 | 0.5956 | 0.1492 | 0.0619 | 0.2386 | 0.0000-0.6533 |

The strongest deployment result is minimal whole-session prompting. The worst
configurations are Mercury and combined five-second windows. Their validation-
selected thresholds range from 0.76 to 0.999, suppressing most malicious test
predictions after capture shift. Observed zero-F1 folds include TrojanDownloader
for minimal windows and BitCoinMiner for both Mercury and combined windows.

For minimal whole-session GPT-5.4, family-level detection is consistently high:

| Held-out family | Detected / malicious | Detection rate | Wilson 95% interval |
| --- | ---: | ---: | ---: |
| BitCoinMiner | 57 / 63 | 0.9048 | [0.8074, 0.9556] |
| Dridex | 56 / 58 | 0.9655 | [0.8827, 0.9905] |
| Hancitor | 136 / 160 | 0.8500 | [0.7865, 0.8971] |
| TrojanDownloader | 80 / 92 | 0.8696 | [0.7857, 0.9238] |
| Website | 166 / 170 | 0.9765 | [0.9411, 0.9908] |

### Calibration Accounts for Part of the Deployment Gain

| Representation / features | Raw-verdict F1 | Validation-calibrated F1 | Change |
| --- | ---: | ---: | ---: |
| Session / minimal | 0.7734 | 0.9033 | **+0.1298** |
| Session / combined | 0.6979 | 0.7421 | +0.0442 |
| Session / Mercury | 0.6682 | 0.6940 | +0.0258 |
| Window / minimal | 0.7176 | 0.7766 | +0.0589 |
| Window / combined | 0.5396 | 0.2571 | **-0.2826** |
| Window / Mercury | 0.5172 | 0.2386 | **-0.2786** |

The best deployment improvement is therefore not solely a better raw GPT-5.4
verdict. Validation calibration increases minimal whole-session pooled recall
from 0.676 to 0.912. Conversely, calibration fails to transfer for rich
five-second-window representations and reduces their F1 by approximately 0.28.

All selected thresholds obey the validation FPR ceiling, but held-out test FPR
does not. Minimal whole-session GPT-5.4 has pooled test FPR 0.1041, including
0.2484 on BitCoinMiner, despite validation FPRs no greater than 0.05. Thus, the
deployment protocol correctly prevents test-label threshold tuning, but does not
demonstrate an operational 5% false-positive rate on unseen captures.

## Matched Local-ML Comparison

Local configurations are selected descriptively by median fold F1 within each
matched feature/representation cell, then by pooled F1 when medians tie. This is
not independent model selection and should not be used for a formal superiority
test.

| Mode | Representation / features | Local model | Local median / pooled / worst F1 | GPT-5.4 median / pooled / worst F1 |
| --- | --- | --- | ---: | ---: |
| Balanced | Session / minimal | KNN | 0.9712 / 0.8794 / 0.4615 | 0.4946 / 0.6100 / 0.0000 |
| Balanced | Session / Mercury | RF | 0.9624 / 0.8811 / 0.4714 | 0.7229 / 0.7672 / 0.6667 |
| Balanced | Session / combined | RF | 0.9624 / 0.8812 / 0.4714 | **0.8352 / 0.8441 / 0.7000** |
| Balanced | Window / minimal | CART | 0.9662 / 0.8812 / 0.4714 | 0.6972 / 0.5995 / 0.0000 |
| Balanced | Window / Mercury | RF | 0.9624 / 0.8813 / 0.4714 | 0.6182 / 0.6311 / 0.5055 |
| Balanced | Window / combined | KNN | 0.9638 / 0.8846 / 0.4698 | 0.7126 / 0.7061 / 0.4045 |
| Deployment | Session / minimal | RF | **0.9863 / 0.8318 / 0.3807** | **0.9097 / 0.9033 / 0.7170** |
| Deployment | Session / Mercury | RF | 0.9519 / 0.8250 / 0.3748 | 0.7094 / 0.6940 / 0.5000 |
| Deployment | Session / combined | RF | 0.9535 / 0.8300 / 0.3727 | 0.8758 / 0.7421 / 0.1287 |
| Deployment | Window / minimal | RF | 0.9939 / 0.8358 / 0.3807 | 0.7260 / 0.7766 / 0.0000 |
| Deployment | Window / Mercury | RF | 0.9519 / 0.8203 / 0.3761 | 0.0619 / 0.2386 / 0.0000 |
| Deployment | Window / combined | RF | 0.9535 / 0.8300 / 0.3767 | 0.0808 / 0.2571 / 0.0000 |

Balanced session/Mercury has a median tie between RF and XGB. Balanced
session/combined ties RF, XGB, LGBM, and CART. Deployment combined session and
window cells tie RF and LGBM. Pooled F1 is used above only to display one tied
row reproducibly.

Across all local candidates, the highest balanced median is 0.9713 for minimal
packet RF, with pooled F1 0.9012 and worst-fold F1 0.7300. The lowest balanced
local median is 0.8393 for minimal five-second-window KNN, whose worst fold is
0.0230. The highest deployment median is 0.9939 for minimal five-second-window
RF, but its worst fold is only 0.3807. The lowest deployment local median is
0.8203 for Mercury whole-session LGBM. These ranges show that local ML is not
uniformly stable under the five held-out captures, even when its median is near
one.

### The Deployment Reversal Is a Website-Fold Effect

| Held-out family | GPT-5.4 F1 / recall / n | RF F1 / recall / n | Fold winner |
| --- | ---: | ---: | --- |
| BitCoinMiner | 0.7170 / 0.9048 / 220 | 0.7739 / 0.9971 / 1,124 | RF |
| Dridex | 0.8682 / 0.9655 / 220 | 0.9907 / 0.9815 / 1,297 | RF |
| Hancitor | 0.9097 / 0.8500 / 220 | 1.0000 / 1.0000 / 1,519 | RF |
| TrojanDownloader | 0.9302 / 0.8696 / 220 | 0.9863 / 0.9969 / 736 | RF |
| Website | **0.9852 / 0.9765 / 220** | 0.3807 / 0.2351 / 1,324 | **GPT-5.4** |

The models are not evaluated on equal denominators in this table: GPT-5.4 uses a
deterministic budgeted subset, while RF uses every held-out session. Raw local
predictions were not persisted, so RF cannot currently be rescored on the exact
GPT-5.4 subset and a paired test cannot be performed. The pooled GPT-5.4 advantage
must therefore be reported as descriptive, not as statistical equivalence or
superiority.

## Legacy Results and the Apparent Improvement

### Legacy OpenAI Packet and Prefix Experiments

The archived result rows do not contain a `model` field. They should be called
the legacy OpenAI archive until provider logs resolve the served model. The
current manuscript is internally contradictory: one paragraph identifies
GPT-5.4 and another identifies GPT-4o for the same cluster.

| Legacy experiment | Unit and context | n | Accuracy | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 4A zero-shot | One packet, minimal | 500 | 0.5080 | 0.5345 | 0.1240 | 0.2013 |
| 4B k=1 | One packet, one example | 300 | 0.5067 | 0.5294 | 0.1200 | 0.1957 |
| 4B k=3 | One packet, three examples | 300 | 0.5400 | 0.5714 | 0.3200 | 0.4103 |
| 4B k=5 | One packet, five examples | 300 | 0.6100 | 0.6571 | 0.4600 | 0.5412 |
| 4B k=10 | One packet, ten examples | 300 | 0.6800 | 0.8140 | 0.4667 | 0.5932 |
| 4C chain-of-thought | One packet, minimal | 200 | 0.5700 | 0.5814 | 0.5000 | 0.5376 |
| 4D LOFO | One packet, held-out family | 500 | 0.6180 | 0.6311 | 0.5680 | 0.5979 |
| 4E first 5 packets | Session prefix, minimal | 200 | **0.9600** | 0.9259 | 1.0000 | **0.9615** |
| 4E first 10 packets | Session prefix, minimal | 200 | 0.5950 | 0.5525 | 1.0000 | 0.7117 |
| 4E first 20 packets | Session prefix, minimal | 200 | 0.5050 | 0.5025 | 1.0000 | 0.6689 |
| 4E first 50 packets | Session prefix, minimal | 200 | 0.5000 | 0.5000 | 1.0000 | 0.6667 |

Current GPT-5.4 is dramatically better than legacy packet classification, but it
does not exceed every legacy result. The 4E five-packet prefix has F1 0.9615.
That result is not robust: at 20 packets the model labels 199 of 200 sessions
malicious, and at 50 packets it labels all 200 malicious. The cohort is random,
balanced, restricted to sessions with at least 50 packets, omits Hancitor, and has
no capture-disjoint train/validation/test protocol. It is an instability example,
not a stronger deployment baseline.

### Legacy Local ML

| Legacy local experiment | Best model | Accuracy | F1 |
| --- | --- | ---: | ---: |
| E1 full mixed, session-group holdout | CART | 0.9898 | 0.9827 |
| E1 full mixed, capture holdout | KNN | 0.9785 | 0.9655 |
| E2 20k, session-group holdout | CART | 0.9848 | 0.9748 |
| E2 20k, capture holdout | CART | 0.9840 | 0.9738 |
| E3 encrypted, session-group holdout | KNN | 0.9946 | 0.9137 |
| E3 encrypted, capture holdout | KNN | 0.9879 | 0.6048 |
| E4 LOFO, best per-family session holdout | CART/KNN | 0.8521-0.9862 | 0.8284-0.9862 |
| E4 LOFO, best per-family capture holdout | CART | 0.6748-0.7580 | 0.7167-0.8043 |

Legacy local models classify packet rows, even when packet assignment is grouped
by session or capture. Their apparent advantage over 4A-4D mixes hundreds of
thousands of supervised packet labels with zero/few-shot decisions on individual,
often ambiguous packets. The current local task is harder: every test fold holds
out a designated malware capture/family, and every prediction represents a whole
session. Thus, convergence arises from both an LLM increase and a stricter local
baseline, not from an isolated model-generation improvement.

## Why the New Results Are Higher and More Similar

### 1. Whole-Session Evidence Removes Packet Ambiguity

An isolated ACK, handshake packet, or small encrypted application packet is not
intrinsically malicious. Legacy 4A-4D therefore ask the LLM to infer a session
label from an observation with weak conditional information. The current
sequence contains packet counts, duration, direction, ports, timing, size
distributions, and ordered behavioral changes over the complete session. This is
a more appropriate unit for beaconing, staged download, and C2 behavior.

### 2. Structured Serialization Favors Semantic Reasoning

The new prompt names every feature and presents an ordered hierarchy of session,
segment, and temporal attributes. GPT-5.4 can map labels such as service port,
direction switch, inter-arrival timing, and encryption hint to pretrained network
concepts. The legacy packet prompt exposes five scalar values with little
behavioral context. It is plausible that GPT-5.4's prior knowledge contributes,
but the experiment does not isolate that factor from representation design.

### 3. Memory Adds Supervision on the Exact Representation

Current requests receive eight labeled examples serialized in the same feature
space as the query. Legacy zero-shot receives none, while legacy k-shot examples
are individual packets. Memory also provides training class and family counts.
This can calibrate both the class boundary and expected output behavior without
changing model weights. Because no current blind run exists on the same frozen
samples, its contribution cannot be estimated under the redesigned protocol.

### 4. Validation Calibration Materially Changes Decisions

Minimal whole-session deployment F1 rises from 0.7734 on the raw LLM verdict to
0.9033 after validation-only thresholding. Rich-window F1 falls by approximately
0.28 under the same procedure. The result is therefore an operating-point result,
not only a raw classification result. High balanced PR-AUC with zero F1 on
Hancitor provides the same evidence: ranking can be excellent while the chosen
threshold is unusable.

### 5. The New Split Penalizes Local Capture-Specific Learning

Old session-group holdout can place sessions from the same capture environment in
both training and test. Even the old single capture holdout is one random split,
not a systematic five-family evaluation. The new protocol holds out every
malware capture once. Local models can therefore lose shortcuts tied to ports,
capture timing, host behavior, or collection environment. Their median remains
high, but the Website fold exposes severe distribution shift.

### 6. Pooled Scores Hide Complementary Failure Modes

In balanced combined whole-session testing, RF wins Dridex and
TrojanDownloader, ties Hancitor, nearly ties BitCoinMiner, and loses Website.
In deployment minimal whole-session testing, RF wins four families and loses
Website. Averaging these folds makes the detectors appear similar even though
their error sets are structurally different. No equivalence claim is justified
without paired predictions and a prespecified non-inferiority margin.

### 7. Minimal Features Transfer Better in Deployment

Combined metadata helps GPT-5.4 under balanced fixed-threshold evaluation, where
ports, direction, and timing provide useful discrimination. Under deployment
shift, minimal whole-session features are much more robust. Mercury-style service
and port hints can encode capture-specific conditions; validation then selects
high thresholds that fail on a new capture. This interpretation is consistent
with the observed threshold collapse, but remains a hypothesis because each
family has only one capture.

### 8. Compression Avoids the Legacy Long-Prefix Failure

Legacy 4E serializes raw packet prefixes and becomes nearly all-malicious as the
prefix grows. The current whole-session representation compresses long sessions
to at most 32 ordered segments. This controls context length and presents stable
summary statistics rather than an increasingly long raw packet list. The design
is more coherent, but it also constitutes a major protocol change.

## Operational Interpretation

High F1 in this deployment mode is not equivalent to production readiness. The
budgeted deployment test pool is 49.36% malicious, and the complete experimental
cohort is 52.95% malicious. Those are corpus prevalences, not enterprise-network
base rates. Minimal whole-session GPT-5.4 has pooled held-out test FPR 10.41% and
RF has 7.37%. If those rates remained constant at a hypothetical 1% malware base
rate, positive predictive value would be only about 8.1% for GPT-5.4 and 9.4%
for RF. At 0.1% prevalence, the illustrative values fall below 1.1%. This
extrapolation is not a measured result; it demonstrates why absolute test FPR and
base rate must accompany F1.

GPT-5.4 requires approximately 1.72-1.86 seconds per remote decision. Selected
local models process approximately 13,000-969,000 sessions per second, excluding
shared feature-extraction cost. The prompted LLM may be useful as a second-stage
analyst or disagreement resolver, but these measurements do not support inline
high-volume deployment.

## Threats to Validity and Required Paper Corrections

1. **Model provenance:** current artifacts explicitly record `gpt-5.4`; legacy
   LLM rows record no model. Resolve the contradiction in `limits2.tex` with API
   logs before attributing a generational gain.
2. **Stale manuscript values:** `limits3_session.tex` reports earlier session
   headlines such as local F1 0.8428 and GPT-5.4 F1 0.6683/0.5725. They must not
   be combined with or presented as the completed capture-disjoint results.
3. **No current blind control:** all expanded redesigned GPT-5.4 rows are
   memory-enabled. The effect of memory cannot be isolated from the redesign.
4. **No completed matched fine-tuned baseline:** the code supports export and
   evaluation, but the audited result set contains no fine-tuned LLM result.
5. **Unequal test denominators:** local models use full folds; GPT-5.4 uses
   budgeted subsets. Persist and evaluate local predictions on the exact LLM
   sample keys before formal paired comparison.
6. **Five non-independent domains:** five folds correspond to five specific
   malware families and captures. Standard deviation across them measures domain
   heterogeneity, not repeat noise, and n=5 is too small for broad population
   claims.
7. **Family-capture confounding:** one capture per family prevents separating
   malware-family generalization from capture-environment generalization.
8. **Confidence-derived thresholds:** self-reported LLM confidence is not a
   calibrated probability. Threshold transfer must be evaluated explicitly.
9. **Multiple comparisons:** best configurations are selected across features,
   representations, algorithms, and contexts. Rankings are descriptive and may
   contain winner's-curse bias.
10. **Production prevalence:** the deployment mode preserves this corpus's
    prevalence, not an operational malware base rate.

## Publication-Safe Conclusion

Under a frozen five-fold capture/family-disjoint protocol, memory-conditioned
GPT-5.4 achieves strong session-level detection from payload-free metadata. Its
best balanced configuration reaches pooled F1 0.8441, within 0.0371 of matched
local RF, while its best deployment configuration reaches pooled F1 0.9033.
However, local RF retains higher median fold F1, wins four of five matched
deployment families, and is orders of magnitude faster. GPT-5.4's pooled
deployment lead is driven by markedly better transfer to the Website capture,
whereas local RF fails conservatively.

These findings support complementary behavior and a substantially narrowed gap,
not universal LLM superiority or statistical equivalence. The improvement over
legacy packet prompting is jointly explained by session-level evidence,
structured temporal serialization, training-only memory, validation calibration,
and a redesigned split that removes capture overlap. A causal claim about GPT-5.4
itself requires a fixed-protocol model ablation with identical samples, prompts,
threshold rules, and paired local predictions.

## Audit Record

- Recomputed every current GPT-5.4 fold metric from raw predictions: exact match.
- Recomputed every local pooled F1 from repeat confusion counts: exact match.
- Duplicate prediction keys: zero.
- Invalid current LLM outputs: zero.
- Recorded current model identifiers: `gpt-5.4` only.
- Context modes in expanded redesigned artifacts: `memory` only.
- Feature-set sample IDs within each representation/fold: identical.
- Recorded deployment validation-FPR violations: zero.
- Targeted split tests: 14 passed.

Primary sources:

- `session_llm_results_capture_disjoint_5fold_balanced_paper_5k_custom_9149ef9b7f_openai_memory.json`
- `session_llm_results_capture_disjoint_5fold_deployment_paper_6k_custom_8da97f7973_openai_memory.json`
- `session_local_results_capture_disjoint_5fold_balanced.json`
- `session_local_results_capture_disjoint_5fold_deployment.json`
- `results.zip` (`llm_results_openai_verbose.json`, `classical_ml_results.json`)
- `src/ndss_dataset.py`, `src/ndss_experiments.py`, and `src/ndss_prompts.py`
