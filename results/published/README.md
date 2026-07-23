# Published Result Summaries

This directory contains compact, auditable exports of the primary session
experiments. Raw prediction-level JSON, API checkpoints, SQLite databases, split
manifests, and packet captures are intentionally excluded from the repository.

Each JSON document records the original artifact name and SHA-256 digest. LLM
exports preserve overall summaries, held-out fold metrics, and malware-family
detection summaries. Local-ML exports preserve overall summaries, paired model
comparisons, and unsupported-status records. No per-session feature vectors,
prompts, rationales, or predictions are published.

Regenerate the files after running the experiments:

```powershell
python scripts/export_publishable_results.py
```

The main interpretation and integrity review are in:

- `../session_consolidated_results_2026-07-18.md`
- `../gpt54_cross_generation_audit_2026-07-19.md`
