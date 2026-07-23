#!/usr/bin/env python3
"""Create conference-neutral publication copies of frozen session artifacts.

The source artifacts remain immutable. This script changes only legacy naming
labels and paths; metric values, model metadata, predictions, split membership,
and row order are preserved. Hashes make the publication copies traceable
without exposing old conference-oriented filenames in the paper-facing inventory.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

ARTIFACTS = {
    "ndss_local_results_balanced.json": "session_local_results_balanced.json",
    "ndss_local_results_deployment.json": "session_local_results_deployment.json",
    "ndss_llm_results_balanced_paper_5k.json": "session_llm_results_balanced_paper_5k.json",
    "ndss_llm_results_deployment_paper_6k.json": "session_llm_results_deployment_paper_6k.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _conference_neutral(value):
    if isinstance(value, str):
        return value.replace("NDSS", "Session").replace("ndss", "session")
    if isinstance(value, list):
        return [_conference_neutral(item) for item in value]
    if isinstance(value, dict):
        return {
            _conference_neutral(key): _conference_neutral(item)
            for key, item in value.items()
        }
    return value


def main() -> None:
    provenance = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "normalization": "Conference labels/paths only; numerical/model/split fields unchanged.",
        "artifacts": [],
        "split_manifests": [],
    }
    manifest_pairs: dict[Path, Path] = {}
    for source_name, destination_name in ARTIFACTS.items():
        source = RESULTS / source_name
        destination = RESULTS / destination_name
        payload = json.loads(source.read_text(encoding="utf-8"))
        normalized = _conference_neutral(payload)
        for source_row, publication_row in zip(payload, normalized, strict=True):
            source_manifest = source_row.get("manifest_path")
            publication_manifest = publication_row.get("manifest_path")
            if source_manifest and publication_manifest:
                manifest_pairs[Path(source_manifest)] = Path(publication_manifest)
        destination.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        provenance["artifacts"].append(
            {
                "publication_file": destination_name,
                "rows": len(normalized),
                "source_sha256": _sha256(source),
                "publication_sha256": _sha256(destination),
            }
        )

    for source, destination in sorted(manifest_pairs.items(), key=lambda pair: str(pair[1])):
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(source.read_text(encoding="utf-8"))
        destination.write_text(
            json.dumps(_conference_neutral(payload), indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        provenance["split_manifests"].append(
            {
                "publication_file": str(destination.relative_to(ROOT)),
                "source_sha256": _sha256(source),
                "publication_sha256": _sha256(destination),
            }
        )

    manifest = RESULTS / "session_publication_artifact_provenance.json"
    manifest.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(ARTIFACTS)} publication artifacts, "
        f"{len(manifest_pairs)} split manifests, and {manifest.name}"
    )


if __name__ == "__main__":
    main()
