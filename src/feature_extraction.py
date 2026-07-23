#!/usr/bin/env python3
"""
Phase 1: Feature Extraction Pipeline.

Two extraction paths:
  Path A: From botnet pcap files (Scapy) → packet-level side-channel features
  Path B: From binetflow labeled files → flow-level features with ground truth labels
  Path C: From mnt/ pre-existing pcaps → benign (mnt/benign/) and malware (mnt/attack_pcap/)

Both paths compute the 5 ESORICS side-channel features:
  1. Packet Size (Ps)
  2. Payload Size (PAs)
  3. Payload Ratio (Pr = PAs / Ps)
  4. Ratio to Previous Packet (Rpp = Pp / PPs)
  5. Time Difference (Td = Pt - PPt)
"""

import sys
import csv
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import (
    CTU13_SCENARIOS, CTU_EXTENDED_SCENARIOS, RAW_DIR, DB_PATH, CTU_BASE_URL,
    FAMILY_GROUPS, FAMILY_TO_GROUP, MNT_BENIGN_DIR, MNT_ATTACK_DIR,
    MNT_ATTACK_FAMILIES, FLOW_TIMEOUTS, TCP_CLOSED_GRACE_SECONDS,
    ENCRYPTED_PORTS, MAX_PCAP_PACKETS
)
from src.database import (
    init_db, register_dataset, insert_session, insert_packets_batch,
    get_dataset_stats
)

try:
    from scapy.all import PcapReader, TCP, UDP, IP, IPv6, Raw, conf
    conf.verb = 0  # suppress scapy warnings
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False
    print("[WARN] Scapy not installed. PCAP extraction disabled.")
    print("       Install with: pip install scapy")


def compute_side_channel_features(packet_size: int, payload_size: int,
                                   prev_packet_size: int | None,
                                   prev_time: float | None,
                                   current_time: float) -> tuple:
    """
    Compute the 5 ESORICS side-channel features for a single packet.

    Returns: (packet_size, payload_size, payload_ratio, ratio_to_prev, time_diff)
    """
    # Pr = PAs / Ps (avoid div by zero)
    payload_ratio = payload_size / packet_size if packet_size > 0 else 0.0

    # Rpp = Pp / PPs (0 for first packet in session)
    if prev_packet_size is not None and prev_packet_size > 0:
        ratio_to_prev = packet_size / prev_packet_size
    else:
        ratio_to_prev = 0.0

    # Td = Pt - PPt (0 for first packet in session)
    if prev_time is not None:
        time_diff = current_time - prev_time
    else:
        time_diff = 0.0

    return (packet_size, payload_size, payload_ratio, ratio_to_prev, time_diff)


# ============================================================================
# PATH A: Extract from PCAP files using Scapy
# ============================================================================

TCP_SYN = 0x02
TCP_ACK = 0x10
TCP_FIN = 0x01
TCP_RST = 0x04


def _normalize_session_key(src_ip: str, dst_ip: str,
                            src_port: int, dst_port: int,
                            proto: str) -> tuple:
    """Return a canonical bidirectional 5-tuple key."""
    if (src_ip, src_port) <= (dst_ip, dst_port):
        return (src_ip, dst_ip, src_port, dst_port, proto.lower())
    return (dst_ip, src_ip, dst_port, src_port, proto.lower())


def _extract_packet_record(pkt) -> dict | None:
    """
    Convert a Scapy packet to a lightweight record used by the sessioniser.

    The returned dict contains only the metadata needed to build flows, which
    makes the flow-boundary logic independently testable.
    """
    if not pkt.haslayer(IP) and not pkt.haslayer(IPv6):
        return None

    ip = pkt[IP] if pkt.haslayer(IP) else pkt[IPv6]

    if pkt.haslayer(TCP):
        proto = "tcp"
        transport = pkt[TCP]
        tcp_flags = int(getattr(transport, "flags", 0))
    elif pkt.haslayer(UDP):
        proto = "udp"
        transport = pkt[UDP]
        tcp_flags = 0
    else:
        return None

    src_ip = ip.src
    dst_ip = ip.dst
    src_port = int(transport.sport)
    dst_port = int(transport.dport)
    pkt_size = int(len(pkt))
    payload_size = int(len(pkt[Raw].load)) if pkt.haslayer(Raw) else 0
    timestamp = float(pkt.time)

    return {
        "base_key": _normalize_session_key(src_ip, dst_ip, src_port, dst_port, proto),
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "proto": proto,
        "packet_size": pkt_size,
        "payload_size": payload_size,
        "timestamp": timestamp,
        "is_encrypted": int(src_port in ENCRYPTED_PORTS or dst_port in ENCRYPTED_PORTS),
        "tcp_flags": tcp_flags,
    }


def _start_flow_state(packet: dict, flow_index: int) -> dict:
    return {
        "flow_index": flow_index,
        "initiator_ip": packet["src_ip"],
        "initiator_port": packet["src_port"],
        "responder_ip": packet["dst_ip"],
        "responder_port": packet["dst_port"],
        "proto": packet["proto"],
        "last_ts": packet["timestamp"],
        "packet_count": 0,
        "closed": False,
        "close_ts": None,
    }


def _flow_timeout(proto: str) -> float:
    return float(FLOW_TIMEOUTS.get(str(proto).lower(), FLOW_TIMEOUTS.get("tcp", 120.0)))


def _should_rotate_flow(state: dict | None, packet: dict) -> tuple[bool, str | None]:
    if state is None:
        return True, "new_flow"

    idle_for = float(packet["timestamp"] - state["last_ts"])
    if idle_for > _flow_timeout(packet["proto"]):
        return True, "timeout"

    if packet["proto"] == "tcp":
        flags = int(packet.get("tcp_flags", 0) or 0)
        syn_no_ack = bool(flags & TCP_SYN) and not bool(flags & TCP_ACK)
        # A lone SYN can be retransmitted during the same handshake.  Treat it as
        # a new connection only after prior bidirectional/continued activity.
        if syn_no_ack and state["packet_count"] > 1:
            return True, "syn_reuse"
        if state.get("closed") and state.get("close_ts") is not None:
            if packet["timestamp"] - state["close_ts"] > TCP_CLOSED_GRACE_SECONDS:
                return True, "post_close"

    return False, None


def _update_flow_state(state: dict, packet: dict) -> None:
    state["last_ts"] = packet["timestamp"]
    state["packet_count"] += 1
    if packet["proto"] == "tcp":
        flags = int(packet.get("tcp_flags", 0) or 0)
        if flags & (TCP_FIN | TCP_RST):
            state["closed"] = True
            state["close_ts"] = packet["timestamp"]


def sessionize_packet_records(records) -> list[dict]:
    """
    Split packet records into connection instances using inactivity timeouts and
    TCP connection-boundary signals.

    Returns a list of session dicts:
      {"state": state_dict, "packets": [packet_record, ...]}
    """
    active: dict[tuple, dict] = {}
    flow_counters: dict[tuple, int] = defaultdict(int)
    sessions: dict[tuple, dict] = {}

    for packet in records:
        base_key = packet["base_key"]
        state = active.get(base_key)
        rotate, _reason = _should_rotate_flow(state, packet)
        if rotate:
            flow_counters[base_key] += 1
            state = _start_flow_state(packet, flow_counters[base_key])
            active[base_key] = state
            flow_id = (base_key, state["flow_index"])
            sessions[flow_id] = {"state": state, "packets": []}
        else:
            flow_id = (base_key, state["flow_index"])

        sessions[flow_id]["packets"].append(packet)
        _update_flow_state(state, packet)

    return list(sessions.values())


def extract_from_pcap(pcap_path: Path, conn, dataset_id: int,
                      is_malicious: int, malware_family: str,
                      max_packets: int = MAX_PCAP_PACKETS) -> dict:
    """Extract side-channel features from a PCAP file with improved sessionisation."""
    if not HAS_SCAPY:
        raise RuntimeError("Scapy required for PCAP extraction")

    print(f"    Parsing PCAP: {pcap_path.name} ...")

    packet_records: list[dict] = []
    packet_count = 0

    try:
        with PcapReader(str(pcap_path)) as reader:
            for pkt in reader:
                if packet_count >= max_packets:
                    break
                record = _extract_packet_record(pkt)
                if record is None:
                    continue
                packet_records.append(record)
                packet_count += 1
                if packet_count % 50_000 == 0:
                    print(f"      Processed {packet_count} packets...")
    except Exception as e:
        print(f"    [ERROR] Failed to parse {pcap_path.name}: {e}")
        return {"packets": 0, "sessions": 0}

    sessions = sessionize_packet_records(packet_records)

    total_inserted_packets = 0
    total_sessions = 0
    for session in sessions:
        pkt_list = session["packets"]
        state = session["state"]
        if len(pkt_list) < 2:
            continue

        session_encrypted = any(int(p["is_encrypted"]) == 1 for p in pkt_list)
        session_id = insert_session(
            conn,
            dataset_id,
            state["initiator_ip"],
            state["responder_ip"],
            state["initiator_port"],
            state["responder_port"],
            state["proto"],
            is_malicious=is_malicious,
            label=f"{'Malicious' if is_malicious else 'Normal'}-{malware_family}",
            malware_family=malware_family if is_malicious else "",
            is_encrypted=int(session_encrypted),
        )

        prev_size = None
        prev_time = None
        packet_rows = []
        for idx, packet in enumerate(sorted(pkt_list, key=lambda p: p["timestamp"])):
            ps, pas, pr, rpp, td = compute_side_channel_features(
                packet["packet_size"],
                packet["payload_size"],
                prev_size,
                prev_time,
                packet["timestamp"],
            )
            direction = (
                "outgoing"
                if packet["src_ip"] == state["initiator_ip"] and packet["src_port"] == state["initiator_port"]
                else "incoming"
            )
            packet_rows.append((
                session_id,
                idx,
                ps,
                pas,
                pr,
                rpp,
                td,
                packet["timestamp"],
                direction,
                is_malicious,
            ))
            prev_size = packet["packet_size"]
            prev_time = packet["timestamp"]

        insert_packets_batch(conn, packet_rows)
        total_inserted_packets += len(packet_rows)
        total_sessions += 1
        if total_sessions % 500 == 0:
            conn.commit()

    conn.commit()
    return {"packets": total_inserted_packets, "sessions": total_sessions}


# ============================================================================
# PATH B: Extract from binetflow labeled files
# ============================================================================

def parse_binetflow_line(line: str) -> dict | None:
    """
    Parse a single line from a CTU binetflow labeled file.

    Format varies but typical columns:
    StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,
    sTos,dTos,TotPkts,TotBytes,SrcBytes,Label

    Returns dict with parsed fields or None if unparseable.
    """
    parts = line.strip().split(",")
    if len(parts) < 14:
        return None

    try:
        record = {
            "start_time": parts[0].strip(),
            "duration":   float(parts[1].strip()) if parts[1].strip() else 0.0,
            "proto":      parts[2].strip().lower(),
            "src_addr":   parts[3].strip(),
            "src_port":   parts[4].strip(),
            "direction":  parts[5].strip(),
            "dst_addr":   parts[6].strip(),
            "dst_port":   parts[7].strip(),
            "state":      parts[8].strip(),
            "s_tos":      parts[9].strip(),
            "d_tos":      parts[10].strip(),
            "tot_pkts":   int(parts[11].strip()) if parts[11].strip() else 0,
            "tot_bytes":  int(parts[12].strip()) if parts[12].strip() else 0,
            "src_bytes":  int(parts[13].strip()) if parts[13].strip() else 0,
            "label":      parts[14].strip() if len(parts) > 14 else "",
        }
        return record
    except (ValueError, IndexError):
        return None


def classify_binetflow_label(label: str) -> tuple:
    """
    Classify a binetflow label into (is_malicious: int, label_type: str).

    CTU-13 binetflow files prefix every label with "flow=" (e.g.
    "flow=From-Botnet-V42-Label42").  Some older files omit this prefix.
    Both formats are handled by stripping the prefix before matching.

    CTU-13 label semantics:
      - "From-Botnet*" → malicious (1)
      - "From-Normal*" → normal   (0)
      - "To-Botnet*"   → skip (-1): responses to the infected host, not
                         botnet-initiated traffic. Labelling them malicious
                         would contaminate the class with reply-traffic
                         characteristics that differ from initiating flows.
      - "Background"   → skip (-1): ambiguous mixed traffic
      - anything else  → skip (-1): unknown, do not assume a label
    """
    label_lower = label.lower().strip()

    # Strip CTU-13 "flow=" prefix (present in all official CTU binetflow files)
    if label_lower.startswith("flow="):
        label_lower = label_lower[5:]
    elif label_lower.startswith("label="):
        label_lower = label_lower[6:]

    if label_lower.startswith("from-botnet"):
        return (1, "botnet")
    elif label_lower.startswith("from-normal"):
        return (0, "normal")
    elif label_lower.startswith("background"):
        return (-1, "background")
    else:
        # Covers "To-Botnet", "To-Normal", and any unknown variants.
        return (-1, "unknown")


def extract_from_binetflow(binetflow_path: Path, conn, dataset_id: int,
                            malware_family: str, infected_ip: str = "",
                            max_flows: int = 100_000) -> dict:
    """
    Extract features from a CTU binetflow labeled file.

    Since binetflow provides FLOW-level data (not packet-level), we create
    synthetic packet-level features from the flow aggregates:

      - packet_size   = tot_bytes / tot_pkts  (avg packet size in flow)
      - payload_size  = avg_pkt_size - header_overhead
      - payload_ratio = payload_size / packet_size
      - ratio_to_prev = 0.0 — each binetflow entry is a separate session;
                        there is no prior packet to compare against
      - time_diff     = flow_duration / (tot_pkts - 1)  (avg inter-packet gap)
    """
    print(f"    Parsing binetflow: {binetflow_path.name} ...")

    stats = {"malicious": 0, "normal": 0, "skipped": 0, "sessions": 0}

    with open(binetflow_path, "r", errors="replace") as f:
        lines = f.readlines()

    # Skip header if present
    start_idx = 0
    if lines and ("StartTime" in lines[0] or "start" in lines[0].lower()):
        start_idx = 1

    flow_count = 0
    for line in lines[start_idx:]:
        if flow_count >= max_flows:
            break

        record = parse_binetflow_line(line)
        if not record:
            continue

        is_malicious, label_type = classify_binetflow_label(record["label"])
        if is_malicious == -1:
            stats["skipped"] += 1
            continue

        if record["tot_pkts"] <= 0 or record["tot_bytes"] <= 0:
            continue

        try:
            src_port = int(record["src_port"]) if record["src_port"].isdigit() else 0
            dst_port = int(record["dst_port"]) if record["dst_port"].isdigit() else 0
        except ValueError:
            src_port = 0
            dst_port = 0

        is_encrypted = 1 if dst_port in (443, 993, 995, 465, 8443) or \
                           src_port in (443, 993, 995, 465, 8443) else 0

        family = malware_family if is_malicious else ""
        session_id = insert_session(
            conn, dataset_id,
            record["src_addr"], record["dst_addr"],
            src_port, dst_port, record["proto"],
            is_malicious=is_malicious,
            label=record["label"],
            malware_family=family,
            is_encrypted=is_encrypted
        )
        stats["sessions"] += 1

        # Synthetic packet-level features from flow aggregates
        avg_pkt_size = record["tot_bytes"] / record["tot_pkts"]
        # Subtract per-packet header overhead to estimate payload
        header_overhead = 40 if record["proto"] == "tcp" else 28
        avg_payload_size = max(0.0, avg_pkt_size - header_overhead)

        # Average inter-packet gap within the flow
        if record["tot_pkts"] > 1 and record["duration"] > 0:
            avg_time_diff = record["duration"] / (record["tot_pkts"] - 1)
        else:
            avg_time_diff = 0.0

        # Each binetflow entry is an independent session.
        # Pass prev_packet_size=None so ratio_to_prev=0.0 (no cross-flow
        # contamination from adjacent, unrelated flow records).
        ps, pas, pr, rpp, td = compute_side_channel_features(
            int(avg_pkt_size), int(avg_payload_size),
            None,  # prev_packet_size: no prior packet in this session
            None,  # prev_time: not applicable at flow level
            0.0
        )
        # Replace td with the proper average inter-packet time for this flow
        td = avg_time_diff

        packet_records = [(
            session_id, 0, int(avg_pkt_size), int(avg_payload_size),
            pr, rpp, td, 0.0, "bidirectional", is_malicious
        )]
        insert_packets_batch(conn, packet_records)

        if is_malicious:
            stats["malicious"] += 1
        else:
            stats["normal"] += 1

        flow_count += 1
        if flow_count % 10_000 == 0:
            conn.commit()
            print(f"      Processed {flow_count} flows: "
                  f"{stats['malicious']} malicious, {stats['normal']} normal")

    conn.commit()
    return stats


# ============================================================================
# PATH C: Extract from mnt/ pre-existing pcap captures
# ============================================================================

def extract_mnt_pcaps(conn) -> dict:
    """
    Extract side-channel features from the ground-truth pcap files under mnt/:

      mnt/benign/      — normal (benign) traffic  → is_malicious=0
      mnt/attack_pcap/ — malware captures          → is_malicious=1

    Returns aggregate stats {"sessions": int, "packets": int}.
    """
    if not HAS_SCAPY:
        print("[SKIP] Scapy not available - cannot process mnt/ pcaps.")
        return {"sessions": 0, "packets": 0}

    total = {"sessions": 0, "packets": 0}

    # ---- Benign pcaps ----
    benign_pcaps = sorted(MNT_BENIGN_DIR.glob("*.pcap"))
    if not benign_pcaps:
        print(f"  [WARN] No pcap files found in {MNT_BENIGN_DIR}")
    else:
        print(f"\n--- Processing {len(benign_pcaps)} benign pcap(s) from mnt/benign/ ---")
        for pcap_path in benign_pcaps:
            dataset_name = f"mnt-benign-{pcap_path.stem}"
            dataset_id = register_dataset(
                conn, dataset_name, "", "normal_traffic", str(MNT_BENIGN_DIR)
            )
            if _already_processed(conn, dataset_id):
                print(f"    [CACHED] {pcap_path.name} already in DB - skipping")
                continue
            stats = extract_from_pcap(
                pcap_path, conn, dataset_id,
                is_malicious=0, malware_family=""
            )
            print(f"    -> {stats['sessions']} sessions, {stats['packets']} packets")
            total["sessions"] += stats["sessions"]
            total["packets"]  += stats["packets"]

    # ---- Attack pcaps ----
    attack_pcaps = sorted(MNT_ATTACK_DIR.glob("*.pcap"))
    if not attack_pcaps:
        print(f"  [WARN] No pcap files found in {MNT_ATTACK_DIR}")
    else:
        print(f"\n--- Processing {len(attack_pcaps)} attack pcap(s) from mnt/attack_pcap/ ---")
        for pcap_path in attack_pcaps:
            # Try to determine family: explicit config mapping first, then
            # filename inference, then fall back to "Unknown".
            family = MNT_ATTACK_FAMILIES.get(pcap_path.stem, "") or _infer_family_from_filename(pcap_path.stem)
            dataset_name = f"mnt-attack-{pcap_path.stem}"
            dataset_id = register_dataset(
                conn, dataset_name, family, "malware", str(MNT_ATTACK_DIR)
            )
            if _already_processed(conn, dataset_id):
                print(f"    [CACHED] {pcap_path.name} already in DB - skipping")
                continue
            stats = extract_from_pcap(
                pcap_path, conn, dataset_id,
                is_malicious=1, malware_family=family
            )
            if family != "Unknown":
                print(f"    -> {stats['sessions']} sessions, {stats['packets']} packets "
                      f"[family={family}]")
            else:
                print(f"    -> {stats['sessions']} sessions, {stats['packets']} packets "
                      f"[family=Unknown - add to MNT_ATTACK_FAMILIES in config.py]")
            total["sessions"] += stats["sessions"]
            total["packets"]  += stats["packets"]

    return total


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def _already_processed(conn, dataset_id: int) -> bool:
    """Return True if this dataset already has sessions in the DB."""
    cur = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE dataset_id = ?", (dataset_id,)
    )
    return cur.fetchone()[0] > 0


def _infer_family_from_filename(stem: str) -> str:
    """
    Try to infer malware family from a pcap filename stem by case-insensitive
    substring match against all families declared in FAMILY_GROUPS.

    Matches longest family name first to avoid short names shadowing longer ones
    (e.g. "NSIS.ay" before any hypothetical 4-char family).

    Returns the matched family string (preserving original casing from config),
    or "Unknown" if no match is found.

    Works well for CTU-13 botnet pcap names like
    "botnet-capture-20110810-neris.pcap" → "Neris".
    Does NOT work for opaque date-machine names like "2018-04-03_win12.pcap";
    those should be mapped explicitly in MNT_ATTACK_FAMILIES in config.py.
    """
    stem_norm = stem.lower().replace(".", "").replace("-", "").replace("_", "")
    all_families = [f for families in FAMILY_GROUPS.values() for f in families]
    for family in sorted(all_families, key=len, reverse=True):
        probe = family.lower().replace(".", "").replace("-", "").replace("_", "")
        if probe in stem_norm:
            return family
    return "Unknown"


def fix_existing_labels(conn) -> int:
    """
    Migration: for datasets already in the DB with malware_family='Unknown',
    try to re-infer the family from the dataset name and update both the
    datasets and sessions tables.

    Two strategies in priority order:
      1. Explicit mapping from MNT_ATTACK_FAMILIES config dict (user-supplied).
      2. Filename-based inference via _infer_family_from_filename.

    Returns the number of datasets whose family was updated.
    """
    rows = conn.execute(
        "SELECT id, name FROM datasets WHERE malware_family IN ('', 'Unknown')"
    ).fetchall()
    updated = 0
    for row in rows:
        dataset_id = row[0] if isinstance(row, tuple) else row["id"]
        name       = row[1] if isinstance(row, tuple) else row["name"]

        # Strip known prefixes to get the bare stem
        stem = name
        for prefix in ("mnt-attack-", "mnt-"):
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break

        # Strategy 1: explicit user mapping
        family = MNT_ATTACK_FAMILIES.get(stem, "")
        # Strategy 2: filename-based inference
        if not family or family == "Unknown":
            family = _infer_family_from_filename(stem)

        if family and family != "Unknown":
            conn.execute(
                "UPDATE datasets SET malware_family = ? WHERE id = ?",
                (family, dataset_id)
            )
            conn.execute(
                "UPDATE sessions SET malware_family = ? "
                "WHERE dataset_id = ? AND is_malicious = 1",
                (family, dataset_id)
            )
            updated += 1
            print(f"  [LABEL-FIX] {name} -> malware_family={family}")

    if updated:
        conn.commit()
    return updated


def _delete_existing_db_files() -> None:
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(DB_PATH) + suffix) if suffix else DB_PATH
        if p.exists():
            p.unlink()


def run_extraction(rebuild_db: bool = False):
    """Run the full feature extraction pipeline."""
    print("\n" + "=" * 70)
    print("PHASE 1: Feature Extraction Pipeline")
    print("=" * 70)

    if rebuild_db and DB_PATH.exists():
        print(f"[REBUILD] Removing existing database: {DB_PATH}")
        _delete_existing_db_files()

    conn = init_db()
    total_stats = {"sessions": 0, "packets": 0}

    # --- Extract from CTU-13 scenarios (binetflow labeled files) ---
    print("\n--- Processing CTU-13 scenarios (binetflow labels) ---")
    for scenario_name, meta in CTU13_SCENARIOS.items():
        scenario_dir = RAW_DIR / scenario_name

        binetflow_files = list(scenario_dir.glob("*.binetflow*"))
        if not binetflow_files:
            print(f"  [SKIP] No binetflow found for {scenario_name}")
            # Fall back to pcap if available
            pcap_files = list(scenario_dir.glob("*.pcap"))
            if pcap_files and HAS_SCAPY:
                dataset_id = register_dataset(
                    conn, scenario_name, meta["family"],
                    meta["type"], f"{CTU_BASE_URL}/{scenario_name}/"
                )
                if _already_processed(conn, dataset_id):
                    print(f"  [CACHED] {scenario_name} already in DB - skipping")
                    continue
                stats = extract_from_pcap(
                    pcap_files[0], conn, dataset_id,
                    is_malicious=1, malware_family=meta["family"]
                )
                total_stats["sessions"] += stats["sessions"]
                total_stats["packets"]  += stats["packets"]
            continue

        dataset_id = register_dataset(
            conn, scenario_name, meta["family"],
            meta["type"], f"{CTU_BASE_URL}/{scenario_name}/"
        )
        if _already_processed(conn, dataset_id):
            print(f"  [CACHED] {scenario_name} already in DB - skipping")
            continue

        print(f"\n  Processing: {scenario_name} ({meta['family']})")
        stats = extract_from_binetflow(
            binetflow_files[0], conn, dataset_id,
            malware_family=meta["family"],
            infected_ip=meta.get("infected_ip", "")
        )
        print(f"    -> {stats['malicious']} malicious, {stats['normal']} normal, "
              f"{stats['skipped']} skipped")
        total_stats["sessions"] += stats["sessions"]

    # --- Extract from extended scenarios (pcap only) ---
    if HAS_SCAPY:
        print("\n--- Processing extended scenarios (pcap only) ---")
        for scenario_name, meta in CTU_EXTENDED_SCENARIOS.items():
            scenario_dir = RAW_DIR / scenario_name
            pcap_files = list(scenario_dir.glob("*.pcap"))

            if not pcap_files:
                print(f"  [SKIP] No pcap found for {scenario_name}")
                continue

            dataset_id = register_dataset(
                conn, scenario_name, meta["family"],
                meta["type"], f"{CTU_BASE_URL}/{scenario_name}/"
            )
            if _already_processed(conn, dataset_id):
                print(f"  [CACHED] {scenario_name} already in DB - skipping")
                continue

            print(f"\n  Processing: {scenario_name} ({meta['family']})")
            stats = extract_from_pcap(
                pcap_files[0], conn, dataset_id,
                is_malicious=1 if meta.get("is_malicious") else 0,
                malware_family=meta["family"]
            )
            print(f"    -> {stats['sessions']} sessions, {stats['packets']} packets")
            total_stats["sessions"] += stats["sessions"]
            total_stats["packets"]  += stats["packets"]

    # --- Extract from mnt/ pcaps (ground-truth benign + attack captures) ---
    print("\n--- Processing mnt/ pcaps (ground-truth benign + attack captures) ---")
    mnt_stats = extract_mnt_pcaps(conn)
    total_stats["sessions"] += mnt_stats["sessions"]
    total_stats["packets"]  += mnt_stats["packets"]

    # --- Fix any pre-existing "Unknown" family labels ---
    n_fixed = fix_existing_labels(conn)
    if n_fixed:
        print(f"\n  [LABEL-FIX] Updated family labels for {n_fixed} dataset(s).")

    # --- Print summary ---
    print("\n" + "=" * 70)
    print("Feature Extraction Summary")
    print("=" * 70)

    db_stats = get_dataset_stats(conn)
    print(f"  Datasets:           {db_stats['num_datasets']}")
    print(f"  Total sessions:     {db_stats['num_sessions']}")
    print(f"  Malicious sessions: {db_stats['num_malicious_sessions']}")
    print(f"  Normal sessions:    {db_stats['num_normal_sessions']}")
    print(f"  Total packets:      {db_stats['num_packets']}")
    print(f"  Malicious packets:  {db_stats['num_malicious_packets']}")
    print(f"  Normal packets:     {db_stats['num_normal_packets']}")

    if db_stats["family_distribution"]:
        print(f"\n  Malware family distribution:")
        for fam, count in sorted(db_stats["family_distribution"].items(),
                                  key=lambda x: -x[1]):
            group = FAMILY_TO_GROUP.get(fam, "unknown")
            print(f"    {fam:20s} ({group:15s}): {count:>8d} sessions")

    conn.close()
    print(f"\nDatabase: {DB_PATH}")
    print("Next step: python run_all.py --phase 2 3")


if __name__ == "__main__":
    run_extraction()
