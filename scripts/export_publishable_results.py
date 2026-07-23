#!/usr/bin/env python3
"""Export compact, provenance-linked result summaries for publication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_DIR = RESULTS_DIR / "published"


@dataclass(frozen=True)
class ExportSpec:
    source_name: str
    output_name: str
    record_types: frozenset[str]


SPECS = (
    ExportSpec(
        "session_local_results_capture_disjoint_5fold_balanced.json",
        "session_local_capture_disjoint_5fold_balanced.summary.json",
        frozenset({"summary", "paired_difference_summary", "unsupported"}),
    ),
    ExportSpec(
        "session_local_results_capture_disjoint_5fold_deployment.json",
        "session_local_capture_disjoint_5fold_deployment.summary.json",
        frozenset({"summary", "paired_difference_summary", "unsupported"}),
    ),
    ExportSpec(
        "session_llm_results_capture_disjoint_5fold_balanced_paper_5k_custom_9149ef9b7f_openai_memory.json",
        "session_llm_capture_disjoint_5fold_balanced_expanded_openai_memory.summary.json",
        frozenset({"summary", "repeat_metrics", "family_summary"}),
    ),
    ExportSpec(
        "session_llm_results_capture_disjoint_5fold_deployment_paper_6k_custom_8da97f7973_openai_memory.json",
        "session_llm_capture_disjoint_5fold_deployment_expanded_openai_memory.summary.json",
        frozenset({"summary", "repeat_metrics", "family_summary"}),
    ),
    ExportSpec(
        "session_llm_results_capture_disjoint_5fold_balanced_paper_5k_custom_c27f8e02c3_openai_memory.json",
        "session_llm_capture_disjoint_5fold_balanced_pilot_openai_memory.summary.json",
        frozenset({"summary", "repeat_metrics", "family_summary"}),
    ),
    ExportSpec(
        "session_llm_results_capture_disjoint_5fold_deployment_paper_6k_custom_1568571713_openai_memory.json",
        "session_llm_capture_disjoint_5fold_deployment_pilot_openai_memory.summary.json",
        frozenset({"summary", "repeat_metrics", "family_summary"}),
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_result(spec: ExportSpec) -> Path:
    source_path = RESULTS_DIR / spec.source_name
    if not source_path.is_file():
        raise FileNotFoundError(f"Required result artifact is missing: {source_path}")

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"Expected a list of result records in {source_path}")

    records = [
        row for row in payload
        if str(row.get("record_type")) in spec.record_types
    ]
    found_types = {str(row.get("record_type")) for row in records}
    missing_types = spec.record_types - found_types
    if missing_types - {"unsupported"}:
        raise ValueError(
            f"{source_path.name} is missing required record types: {sorted(missing_types)}"
        )

    export_payload = {
        "schema_version": "publication_summary_v1",
        "source_artifact": source_path.name,
        "source_sha256": _sha256(source_path),
        "included_record_types": sorted(found_types),
        "source_record_count": len(payload),
        "published_record_count": len(records),
        "excluded_record_count": len(payload) - len(records),
        "records": records,
    }
    output_path = OUTPUT_DIR / spec.output_name
    output_path.write_text(
        json.dumps(export_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exported = [export_result(spec) for spec in SPECS]
    for path in exported:
        print(f"Exported {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
