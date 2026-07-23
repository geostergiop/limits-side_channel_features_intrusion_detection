#!/usr/bin/env python3
"""
Phase 0: Data Acquisition from CTU Malware Capture Facility.

Downloads botnet pcap files and binetflow labeled files from
https://mcfp.felk.cvut.cz/publicDatasets/

For CTU-13 scenarios (42-54): downloads binetflow + botnet pcap
For extended scenarios: downloads botnet pcap only
"""

import os
import sys
import requests
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import (
    CTU_BASE_URL, CTU13_SCENARIOS, CTU_EXTENDED_SCENARIOS, RAW_DIR
)


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> bool:
    """Download a file with progress bar. Returns True on success."""
    if dest.exists():
        print(f"  [SKIP] Already exists: {dest.name}")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [DOWN] {url}")

    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                pbar.update(len(chunk))
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        if dest.exists():
            dest.unlink()
        return False


def discover_pcap_filename(scenario_name: str) -> str | None:
    """
    Try to discover the actual pcap filename inside a CTU scenario folder
    by fetching the directory listing. CTU scenarios have inconsistent naming.
    """
    index_url = f"{CTU_BASE_URL}/{scenario_name}/"
    try:
        resp = requests.get(index_url, timeout=30)
        resp.raise_for_status()
        # Simple parsing: look for .pcap links (not truncated, not .bz2)
        import re
        pcap_files = re.findall(r'href="([^"]*\.pcap)"', resp.text)
        # Filter out truncated versions
        pcap_files = [
            f for f in pcap_files
            if "truncated" not in f.lower() and ".bz2" not in f.lower()
        ]
        if pcap_files:
            # Prefer botnet-specific pcap
            botnet_pcaps = [f for f in pcap_files if "botnet" in f.lower()]
            return botnet_pcaps[0] if botnet_pcaps else pcap_files[0]
    except Exception:
        pass
    return None


def discover_binetflow_filename(scenario_name: str) -> str | None:
    """Discover binetflow labeled file in scenario folder."""
    index_url = f"{CTU_BASE_URL}/{scenario_name}/detailed-bidirectional-flow-labels/"
    try:
        resp = requests.get(index_url, timeout=30)
        resp.raise_for_status()
        import re
        files = re.findall(r'href="([^"]*\.binetflow[^"]*)"', resp.text)
        labeled = [f for f in files if "labeled" in f.lower()]
        return labeled[0] if labeled else (files[0] if files else None)
    except Exception:
        pass
    # Fallback: try root folder
    index_url = f"{CTU_BASE_URL}/{scenario_name}/"
    try:
        resp = requests.get(index_url, timeout=30)
        resp.raise_for_status()
        import re
        files = re.findall(r'href="([^"]*\.binetflow[^"]*)"', resp.text)
        labeled = [f for f in files if "labeled" in f.lower()]
        return labeled[0] if labeled else (files[0] if files else None)
    except Exception:
        pass
    return None


def download_ctu13_scenarios():
    """Download CTU-13 extended scenarios with binetflow labels + botnet pcaps."""
    print("\n" + "=" * 70)
    print("PHASE 0A: Downloading CTU-13 Extended Scenarios (labeled)")
    print("=" * 70)

    for scenario_name, meta in CTU13_SCENARIOS.items():
        print(f"\n--- {scenario_name} ({meta['family']}) ---")
        scenario_dir = RAW_DIR / scenario_name

        # 1. Download botnet pcap
        if "botnet_pcap" in meta:
            pcap_url = f"{CTU_BASE_URL}/{scenario_name}/{meta['botnet_pcap']}"
            pcap_dest = scenario_dir / meta["botnet_pcap"]
            download_file(pcap_url, pcap_dest)
        else:
            pcap_name = discover_pcap_filename(scenario_name)
            if pcap_name:
                pcap_url = f"{CTU_BASE_URL}/{scenario_name}/{pcap_name}"
                download_file(pcap_url, scenario_dir / pcap_name)

        # 2. Download binetflow labeled file
        binetflow_name = discover_binetflow_filename(scenario_name)
        if binetflow_name:
            # Could be in detailed-bidirectional-flow-labels/ or root
            for subdir in ["detailed-bidirectional-flow-labels/", ""]:
                url = f"{CTU_BASE_URL}/{scenario_name}/{subdir}{binetflow_name}"
                dest = scenario_dir / binetflow_name
                if download_file(url, dest):
                    break

        # 3. Save metadata
        meta_path = scenario_dir / "metadata.txt"
        if not meta_path.exists():
            with open(meta_path, "w") as f:
                for k, v in meta.items():
                    f.write(f"{k}: {v}\n")


def download_extended_scenarios():
    """Download extended CTU scenarios (pcap only, no flow labels)."""
    print("\n" + "=" * 70)
    print("PHASE 0B: Downloading Extended CTU Scenarios (pcap only)")
    print("=" * 70)

    for scenario_name, meta in CTU_EXTENDED_SCENARIOS.items():
        print(f"\n--- {scenario_name} ({meta['family']}) ---")
        scenario_dir = RAW_DIR / scenario_name

        # Discover and download pcap
        pcap_name = discover_pcap_filename(scenario_name)
        if pcap_name:
            pcap_url = f"{CTU_BASE_URL}/{scenario_name}/{pcap_name}"
            download_file(pcap_url, scenario_dir / pcap_name)
        else:
            print(f"  [WARN] Could not find pcap for {scenario_name}")

        # Save metadata
        meta_path = scenario_dir / "metadata.txt"
        if not meta_path.exists():
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_path, "w") as f:
                for k, v in meta.items():
                    f.write(f"{k}: {v}\n")


def main():
    print("LLM Traffic Detection - Dataset Acquisition")
    print(f"Target directory: {RAW_DIR}")

    download_ctu13_scenarios()
    download_extended_scenarios()

    # Summary
    print("\n" + "=" * 70)
    print("Download Summary")
    print("=" * 70)
    total_pcaps = sum(1 for f in RAW_DIR.rglob("*.pcap"))
    total_binetflow = sum(1 for f in RAW_DIR.rglob("*.binetflow*"))
    total_size_mb = sum(f.stat().st_size for f in RAW_DIR.rglob("*") if f.is_file()) / 1e6
    print(f"  PCAP files: {total_pcaps}")
    print(f"  Binetflow files: {total_binetflow}")
    print(f"  Total size: {total_size_mb:.1f} MB")
    print(f"\nNext step: python src/feature_extraction.py")


if __name__ == "__main__":
    main()
