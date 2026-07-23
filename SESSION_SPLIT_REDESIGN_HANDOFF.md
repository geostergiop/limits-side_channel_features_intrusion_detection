# Session Split Redesign and Eligibility Bug Fix

## Purpose

This document is an implementation handoff for correcting instability in the session-based experiments. The current balanced capture-grouped protocol can produce pathological test folds, including a fold with only one malicious sample among 1,292 test samples. This causes very large repeat-to-repeat standard deviations and makes model rankings unreliable.

The redesign must preserve two distinct research questions:

1. **Primary capture-disjoint evaluation:** Can a detector generalize to traffic from captures it never observed during training or validation?
2. **Secondary within-capture temporal evaluation:** Can a detector classify later sessions from capture environments already represented during training?

These protocols must never be merged into one aggregate result because the second permits capture-specific information to appear in both training and testing.

## Confirmed Eligibility Bug

### Historical behavior (fixed)

The pre-redesign `src/ndss_dataset.py::build_ndss_dataset()` selected the initial
session cohort using an eight-packet `session_min_packets` value for both
whole-session and behavior-window experiments. Later,
`build_behavior_window_samples()` accepted sessions using a six-packet
`behavior_window_min_packets` value.

Consequently, behavior-window sessions containing six or seven packets were
removed before the behavior-window builder could accept them. The implemented
protocol now selects eligibility by sample unit and sets both whole-session and
behavior-window minimums to six packets, superseding the original eight-packet
whole-session proposal so Hancitor has publishable held-out support.

### Observed impact

Eligible Hancitor sessions in the current database are:

| Eligibility threshold | Hancitor sessions |
|---:|---:|
| At least 8 packets | 6 |
| At least 6 packets | 11,247 |

The frozen balanced Mercury one-second cohort consequently contained approximately these malicious counts:

| Capture/family | Selected samples |
|---|---:|
| BitCoinMiner | 410 |
| TrojanDownloader | 390 |
| Website_5.8.88.175 | 1,793 |
| Dridex | 406 |
| Hancitor | 1 |

This is the direct cause of a balanced test fold containing one malicious Hancitor sample and 1,291 benign samples.

### Required fix

Select eligibility according to the requested sample unit before sampling session IDs:

```python
if spec.sample_unit == "behavior_window":
    min_packets = int(NDSS_CONFIG["behavior_window_min_packets"])
elif spec.sample_unit == "session_sequence":
    min_packets = int(NDSS_CONFIG["session_min_packets"])
elif spec.sample_unit == "packet_ablation":
    min_packets = 2
else:
    raise ValueError(f"Unknown sample_unit={spec.sample_unit!r}")
```

Do not silently reuse old manifests after this change. The cohort membership and cohort hash must change.

## Why the Existing Standard Deviations Are Large

The current split validator accepts a grouped split whenever both classes are present. It does not require meaningful class support. Global cohort balancing occurs before complete captures are assigned to train, validation, and test sets. Since captures differ sharply in size and class composition, a globally balanced cohort can still produce test prevalence from approximately 0.077% to 90.27% malicious.

For balanced Mercury one-second CART, the ten malicious-class F1 scores were:

```text
94.65, 31.68, 97.11, 96.51, 49.95,
51.73, 96.56, 50.00, 99.20, 58.65 percent
```

The reported `72.60 +/- 26.39%` is arithmetically correct, but it reflects unstable capture composition rather than a precise detector estimate.

Deployment XGB also showed validation-to-test instability. Validation-selected thresholds ranged from 0.038 to 0.735 while test F1 ranged from 48.95% to 99.01%. Validation and test captures are therefore not interchangeable domains.

## Required Protocol A: Capture-Disjoint Five-Fold Evaluation

This must become the primary protocol for unseen-capture claims.

### Fold construction

- Construct five deterministic outer folds because there are five malware captures.
- Hold out exactly one malware capture in each outer test fold.
- Assign one or two benign captures to each outer test fold so every benign capture is tested at least once.
- Use another malware capture and one or more benign captures for validation.
- Use all remaining captures for training.
- Ensure train, validation, and test capture IDs are pairwise disjoint.
- Freeze the complete assignment in a versioned manifest before training any model.
- Reuse the same manifest for every feature set, algorithm, and LLM context whenever the underlying cohort is compatible.

### Balanced evaluation

- Assign captures to folds first.
- Then construct a deterministic balanced test subset using only samples from the already assigned held-out captures.
- Use equal benign and malicious test support in every fold.
- Prefer a fixed prespecified per-class test count that is feasible in every fold.
- Use deterministic per-capture or per-family quotas to prevent the largest capture from dominating.
- Apply equivalent prespecified support rules to validation.
- Never search for folds based on model performance.

For a 6,000-session balanced cohort, an initial cohort allocation can use:

- 3,000 malicious sessions: 600 from each of five malware captures.
- 3,000 benign sessions: approximately 428 or 429 from each of seven benign captures.

The final per-fold balanced test size must be derived after capture assignment and must be identical across folds where possible.

### Deployment evaluation

- Keep complete held-out captures or a deterministic natural-prevalence sample from them.
- Do not rebalance deployment test data.
- Select thresholds using validation data only.
- Freeze each selected threshold before one test evaluation.
- Add a prespecified false-positive constraint or report recall at a validation-selected false-positive operating point.
- Also report threshold-free metrics such as PR-AUC and ROC-AUC.

### Reporting

- Report one row per held-out malware capture/family.
- Report test benign/malicious support and prevalence for every fold.
- Report macro-average performance across the five malware folds.
- Optionally report a support-weighted pooled metric, clearly labelled as secondary.
- Do not represent mean plus or minus standard deviation as an expected performance range.
- Report median, interquartile range, minimum, and maximum when repeated estimates remain useful.
- Compare algorithms through paired fold-level differences on identical manifests.
- Correct manuscript language that calls similar mean values "remarkably consistent" when fold variance is high.

## Required Protocol B: Within-Capture Temporal Evaluation

This is a secondary seen-capture upper bound. It must not replace Protocol A.

### Partitioning

For every capture independently:

- Sort sessions by their first packet timestamp.
- Assign the earliest 60% of sessions to training.
- Assign the next 20% to validation.
- Assign the latest 20% to testing.
- Define deterministic tie-breaking for equal timestamps, such as `session_id`.
- Keep every packet and every behavior window from one session in exactly one partition.
- Never split individual packets from the same session across partitions.

Random row splitting is not acceptable because temporally adjacent sessions may be highly correlated.

### Interpretation boundary

All outputs, filenames, tables, and manuscript text must call this protocol something explicit, such as:

```text
within_capture_temporal_session_holdout
```

The supported claim is:

> The detector classifies later sessions from capture environments represented during training.

The unsupported claims are:

- Generalization to unseen captures.
- Generalization to unseen malware families.
- Elimination of capture-specific shortcuts.

Because every malicious family corresponds to one capture, this protocol can learn indirect capture signatures even when `dataset_id` is not a feature.

## CLI and Configuration Changes

Add a split-mode parameter without changing the meaning of existing evaluation-mode parameters:

```text
--session-split-mode capture_disjoint_5fold
--session-split-mode within_capture_temporal
```

Recommended configuration structure:

```python
SESSION_SPLIT_CONFIG = {
    "default_mode": "capture_disjoint_5fold",
    "modes": [
        "capture_disjoint_5fold",
        "within_capture_temporal",
    ],
    "within_capture_train_fraction": 0.60,
    "within_capture_validation_fraction": 0.20,
    "within_capture_test_fraction": 0.20,
    "balanced_family_stratified": True,
    "minimum_test_support_per_class": None,  # Set after feasibility audit.
    "minimum_validation_support_per_class": None,
}
```

Do not overload `balanced` and `deployment`. Those specify evaluation prevalence; `session-split-mode` specifies the separation/generalization protocol.

## Manifest Requirements

Increment the manifest schema or introduce a protocol-specific schema. Every manifest must include:

- Split mode.
- Cohort hash and ordered sample identifiers.
- Eligibility thresholds used for the sample unit.
- Capture IDs and session IDs assigned to every partition.
- Per-partition class support and prevalence.
- Per-family support in validation and test.
- Temporal boundaries for within-capture partitions.
- Random seeds and deterministic quota rules.
- Explicit assertions that partitions are disjoint at the required level.

Old manifests must fail closed when their eligibility threshold, split mode, cohort hash, or schema does not match the requested experiment.

## Validation and Test Requirements

Add unit and integration tests covering at least the following cases.

### Eligibility tests

- Behavior-window cohort selection uses `behavior_window_min_packets`.
- Whole-session cohort selection uses `session_min_packets`.
- A six- or seven-packet session is included in both whole-session and
  behavior-window cohorts; a five-packet session is excluded from both.
- Cohort hashes change after eligibility changes.

### Capture-disjoint tests

- Train, validation, and test capture sets are pairwise disjoint.
- Every malware capture appears in exactly one outer test fold.
- Every benign capture appears in at least one outer test fold.
- Balanced folds meet the prespecified support constraint.
- No algorithm, feature set, threshold, or model output influences fold construction.
- Every algorithm receives identical fold membership for a compatible experiment cell.

### Within-capture tests

- Every capture contributes sessions to train, validation, and test when it has sufficient sessions.
- Session IDs are disjoint across partitions.
- All packets/windows from one session remain in one partition.
- Temporal order satisfies `max(train_time) <= min(validation_time)` and `max(validation_time) <= min(test_time)`, subject to deterministic timestamp tie handling.

### Result-integrity tests

- Stored summaries reconcile exactly with repeat-level confusion matrices.
- Thresholds are selected only from validation predictions.
- Test labels are not used for threshold selection, early stopping, or fold optimization.
- Missing family support produces an explicit incomplete/unsupported result rather than a silent zero.
- Parallel runs cannot overwrite manifests or mix result files from different split modes.

## Required Reruns

The eligibility and split changes invalidate the current session results. Do not compare newly generated rows with old rows as if they share a protocol.

Regenerate, in order:

1. Eligible session/window cohorts.
2. Frozen capture-disjoint and within-capture manifests.
3. Balanced local ML experiments.
4. Deployment local ML experiments.
5. Budgeted balanced LLM experiments.
6. Budgeted deployment LLM experiments.
7. Publication summaries, tables, figures, and manuscript values.

Use new protocol-qualified result filenames so old artifacts cannot be loaded accidentally.

## Acceptance Criteria

The redesign is complete only when all of the following hold:

- Hancitor is no longer reduced from 11,247 six-packet-eligible sessions to six
  eight-packet sessions in either session-based cohort.
- No balanced validation or test fold has negligible class support.
- Every malware family receives a dedicated capture-disjoint test fold.
- Within-capture results are visibly labelled as seen-capture upper bounds.
- Capture-disjoint and within-capture artifacts cannot be merged by downstream analysis without an explicit protocol filter.
- Local and LLM comparisons use compatible frozen manifests and disclose unequal test denominators where budgets differ.
- Paper tables expose fold support, prevalence, and variability rather than only selected winner means.
- Tests verify leakage boundaries and result arithmetic.

## Recommended Paper Framing

Use the capture-disjoint five-fold protocol for primary security and deployment claims. Use within-capture temporal results only as a secondary upper bound showing performance when the deployment environment is already represented during training.

If capture-disjoint variability remains large after the eligibility and fold fixes, report it as genuine cross-capture domain shift. Do not hide it by removing uncertainty or selecting easier folds.
