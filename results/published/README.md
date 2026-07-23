# Published Result Summaries

These six files are compact exports of the primary capture-disjoint Phase 7
session experiments. Raw prediction rows, prompts, rationales, API checkpoints,
SQLite databases, split manifests, and packet captures are excluded.

| File group | Scope |
|---|---|
| `session_local_*_balanced` | Full held-out folds, balanced test cohorts, five local classifiers |
| `session_local_*_deployment` | Full held-out folds, corpus-prevalence test cohorts, validation-selected thresholds |
| `session_llm_*_pilot_*` | Original budget-profile GPT-5.4 memory runs |
| `session_llm_*_expanded_*` | Higher-depth GPT-5.4 memory runs used for the current headline comparison |

Every JSON document records its source artifact name and SHA-256 digest. LLM
exports retain summary, held-out-fold, and malware-family records. Local exports
retain summaries, paired comparisons, and unsupported-status records. The source
artifacts are intentionally not required to inspect the published metrics.

The expanded whole-session headline results are:

| Evaluation | Detector / features | Pooled malicious F1 |
|---|---|---:|
| Balanced | GPT-5.4 / combined | 84.41% |
| Balanced | Random Forest / combined | 88.12% |
| Deployment | GPT-5.4 / minimal | 90.33% |
| Deployment | Random Forest / minimal | 83.18% |

These are five-capture pooled values, not per-family guarantees. Consult the
fold-level records before citing them; capture heterogeneity is substantial.

Claude Sonnet 4.6 is supported by the code, but no provider-identified Sonnet
session artifact was present in the result archive used for these exports. It is
therefore not assigned metrics in this directory.

Regenerate the compact exports after running experiments:

```powershell
python scripts/export_publishable_results.py
```
