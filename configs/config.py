"""
Configuration for LLM-Powered Malicious Traffic Detection Experiments.
Maps directly to the ESORICS 2018 feature set and extends with LLM parameters.
"""

import os
from pathlib import Path

# ============================================================================
# PROJECT PATHS
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "traffic.db"
RESULTS_DIR = PROJECT_ROOT / "results"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

for d in [RAW_DIR, PROCESSED_DIR, RESULTS_DIR, PROMPTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# ESORICS 2018 SIDE-CHANNEL FEATURES (Section 4.2 of the paper)
# ============================================================================
# These are the ONLY 5 features we use — the core thesis.
SIDE_CHANNEL_FEATURES = [
    "packet_size",       # Ps: total packet size in bytes
    "payload_size",      # PAs: TCP data segment size
    "payload_ratio",     # Pr = PAs / Ps
    "ratio_to_prev",     # Rpp = Pp / PPs (0 for first packet)
    "time_diff",         # Td = Pt - PPt (0 for first packet)
]

# ============================================================================
# CTU MALWARE CAPTURE FACILITY — DATASET REGISTRY
# ============================================================================
# We select datasets that:
#   (a) have labeled binetflow files (CTU-13 scenarios: 42-54)
#   (b) cover diverse malware families for Leave-One-Family-Out
#   (c) include ransomware/newer threats with botnet-only pcaps

CTU_BASE_URL = "https://mcfp.felk.cvut.cz/publicDatasets"

# --- CTU-13 extended scenarios (have binetflow labels) ---
# These provide: binetflow.labeled files with flow-level labels
# AND botnet-specific pcap files for packet-level extraction
CTU13_SCENARIOS = {
    "CTU-Malware-Capture-Botnet-42": {
        "family": "Neris",
        "type": "botnet_spam_clickfraud",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110810.binetflow",
        "botnet_pcap": "botnet-capture-20110810-neris.pcap",
        "has_labels": True,
        "duration_hours": 6.15,
    },
    "CTU-Malware-Capture-Botnet-43": {
        "family": "Neris",
        "type": "botnet_spam_clickfraud",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110811.binetflow",
        "botnet_pcap": "botnet-capture-20110811-neris.pcap",
        "has_labels": True,
        "duration_hours": 0.26,
    },
    "CTU-Malware-Capture-Botnet-44": {
        "family": "Rbot",
        "type": "irc_botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110812.binetflow",
        "botnet_pcap": "botnet-capture-20110812-rbot.pcap",
        "has_labels": True,
        "duration_hours": 4.21,
    },
    "CTU-Malware-Capture-Botnet-45": {
        "family": "Virut",
        "type": "p2p_botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110815.binetflow",
        "botnet_pcap": "botnet-capture-20110815-fast-flux.pcap",
        "has_labels": True,
        "duration_hours": 11.63,
    },
    "CTU-Malware-Capture-Botnet-46": {
        "family": "Virut",
        "type": "p2p_botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110815-2.binetflow",
        "botnet_pcap": "botnet-capture-20110815-2-fast-flux.pcap",
        "has_labels": True,
        "duration_hours": 2.18,
    },
    "CTU-Malware-Capture-Botnet-47": {
        "family": "Sogou",
        "type": "http_botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110816.binetflow",
        "botnet_pcap": "botnet-capture-20110816-sogou.pcap",
        "has_labels": True,
        "duration_hours": 0.38,
    },
    "CTU-Malware-Capture-Botnet-48": {
        "family": "Murlo",
        "type": "botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110816-2.binetflow",
        "botnet_pcap": "botnet-capture-20110816-2-murlo.pcap",
        "has_labels": True,
        "duration_hours": 5.18,
    },
    "CTU-Malware-Capture-Botnet-49": {
        "family": "Neris",
        "type": "botnet_spam_clickfraud",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110817.binetflow",
        "botnet_pcap": "botnet-capture-20110817-bot.pcap",
        "has_labels": True,
        "duration_hours": 5.34,
    },
    "CTU-Malware-Capture-Botnet-50": {
        "family": "Neris",
        "type": "botnet_spam_clickfraud",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110818.binetflow",
        "botnet_pcap": "botnet-capture-20110818-bot.pcap",
        "has_labels": True,
        "duration_hours": 4.75,
    },
    "CTU-Malware-Capture-Botnet-51": {
        "family": "NSIS.ay",
        "type": "botnet_ddos",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110818-2.binetflow",
        "botnet_pcap": "botnet-capture-20110818-2-bot.pcap",
        "has_labels": True,
        "duration_hours": 0.07,
    },
    "CTU-Malware-Capture-Botnet-52": {
        "family": "NSIS.ay",
        "type": "botnet_ddos",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110819.binetflow",
        "botnet_pcap": "botnet-capture-20110819-bot.pcap",
        "has_labels": True,
        "duration_hours": 3.48,
    },
    "CTU-Malware-Capture-Botnet-53": {
        "family": "Menti",
        "type": "botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110810-2.binetflow",
        "botnet_pcap": "botnet-capture-20110810-2-menti.pcap",
        "has_labels": True,
        "duration_hours": 6.15,
    },
    "CTU-Malware-Capture-Botnet-54": {
        "family": "Virut",
        "type": "p2p_botnet",
        "infected_ip": "147.32.84.165",
        "binetflow": "capture20110811-2.binetflow",
        "botnet_pcap": "botnet-capture-20110811-2-bot.pcap",
        "has_labels": True,
        "duration_hours": 4.88,
    },
}

# --- Extended CTU scenarios (botnet pcap only, no binetflow labels) ---
# These we parse directly from pcap using Scapy
CTU_EXTENDED_SCENARIOS = {
    "CTU-Malware-Capture-Botnet-134-1": {
        "family": "CryptoWall",
        "type": "ransomware",
        "has_labels": False,
        "is_malicious": True,  # entire pcap is malicious
    },
    "CTU-Malware-Capture-Botnet-183-1": {
        "family": "Locky",
        "type": "ransomware",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-238-1": {
        "family": "TrickBot",
        "type": "banking_trojan",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-264-1": {
        "family": "Emotet",
        "type": "dropper_loader",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-252-1": {
        "family": "WannaCry",
        "type": "ransomware_worm",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-113-1": {
        "family": "Dridex",
        "type": "banking_trojan",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-114-1": {
        "family": "Emotet",
        "type": "dropper_loader",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-120-1": {
        "family": "njRAT",
        "type": "rat",
        "has_labels": False,
        "is_malicious": True,
    },
    "CTU-Malware-Capture-Botnet-90": {
        "family": "Conficker",
        "type": "worm_botnet",
        "has_labels": False,
        "is_malicious": True,
    },
}

# Normal traffic sources (for balancing dataset)
CTU_NORMAL_URL = "https://mcfp.felk.cvut.cz/publicDatasets"
# Normal captures are at: https://www.stratosphereips.org/datasets-normal

# ============================================================================
# ML EXPERIMENT PARAMETERS (mirror ESORICS 2018 Section 5)
# ============================================================================
ML_CONFIG = {
    "test_size": 0.3,                # outer grouped test fraction
    "validation_size": 0.2,          # inner grouped validation fraction within train+val
    "random_state": 42,
    "n_folds": 5,                    # retained for compatibility
    "repeated_holdout_repeats": 10,
    "max_split_attempts_per_repeat": 256,
    "early_stopping_rounds": 30,
    "manifest_protocol_version": "repeated_grouped_holdout_v2",
    "split_manifest_dir": "split_manifests",
    "experiment_1_sample_size": 200_000,   # full mixed dataset
    "experiment_2_sample_size": 20_000,    # limited sample (Sect 5.2)
    "experiment_3_sample_size": 100_000,   # encrypted-only cohort
    "holdout_modes": ["session", "capture"],
    "phase_2_algorithms": [
        "RandomForestClassifier",
        "XGBClassifier",
        "LGBMClassifier",
    ],
    "algorithms": [
        "LogisticRegression",
        "LinearDiscriminantAnalysis",
        "KNeighborsClassifier",
        "DecisionTreeClassifier",       # CART
        "GaussianNB",
        "SVC",
        "MLPClassifier",
    ],
}

# ============================================================================
# LLM EXPERIMENT PARAMETERS (THE NOVEL CONTRIBUTION)
# ============================================================================
LLM_CONFIG = {
    # API configuration - user must set env vars
    "anthropic_model": "claude-sonnet-5",
    "openai_model": "gpt-5.4",
    "default_provider": "openai",

    # GPT-5 family Responses API controls.
    "openai_reasoning_effort": "medium",
    "openai_text_verbosity": "low",
    "openai_min_completion_tokens": 2048,

    # Sampling parameters
    "max_tokens": 512,
    "temperature": 0.0,        # deterministic where the selected model supports it
    
    # Experiment 4A: Zero-shot
    "zero_shot_sample_size": 500,      # API budget: ~500 calls
    
    # Experiment 4B: Few-shot
    "few_shot_k_values": [1, 3, 5, 10],
    "few_shot_sample_size": 300,
    
    # Experiment 4C: Chain-of-thought
    "cot_sample_size": 200,
    
    # Experiment 4D: Leave-one-family-out
    "lofo_sample_per_family": 100,
    
    # Experiment 4E: Session-level windowed
    "window_sizes": [5, 10, 20, 50],
    "session_sample_size": 200,
    
    # Rate limiting
    "requests_per_minute": 50,
    "retry_max": 3,
    "retry_delay_seconds": 5,
}

# ============================================================================
# SESSION EXPERIMENT CONFIGURATION
# ============================================================================
NDSS_CONFIG = {
    # Feature configurations
    "feature_sets": ["minimal", "mercury", "combined"],
    "default_feature_set": "combined",
    "evaluation_modes": ["balanced", "deployment"],
    "default_evaluation_mode": "balanced",

    # Sample units
    "sample_units": ["session_sequence", "behavior_window"],
    "include_packet_ablation": True,

    # Deterministic cohort sizes
    "session_sample_size": 6000,
    "packet_ablation_sample_size": 3000,
    "llm_balanced_eval_samples_per_repeat": 80,
    "llm_deployment_validation_samples_per_repeat": 80,
    "llm_deployment_test_samples_per_repeat": 160,
    "llm_large_run_call_threshold": 1000,
    "llm_progress_every_calls": 20,
    "expected_malware_families": [
        "BitCoinMiner",
        "Dridex",
        "Hancitor",
        "TrojanDownloader",
        "Website_5.8.88.175",
    ],
    "llm_budget_profiles": {
        "full": {},
        # Designed for paired balanced+deployment runs at roughly 5,100 API
        # calls across whole sessions, ordered behavior windows, and packet ablation:
        # balanced: 15 variants * 5 folds * 26 test samples = 1,950 calls
        # deployment: 15 variants * 5 folds * (15 validation + 27 test) = 3,150 calls
        "paper_5k": {
            "feature_sets": ["minimal", "mercury", "combined"],
            "sample_units": ["session_sequence", "behavior_window", "packet_ablation"],
            "behavior_window_seconds": [5.0],
            "repeat_indices": [0, 1, 2, 3, 4],
            "balanced_eval_samples_per_repeat": 26,
            "deployment_validation_samples_per_repeat": 15,
            "deployment_test_samples_per_repeat": 27,
            "max_calls_per_run": 6000,
            "family_stratified_balanced": True,
        },
        # Higher-depth deployment profile for lower-cost GPT-5.4 runs. Use this
        # after the balanced paper_5k run when the goal is stronger deployment
        # threshold/prevalence evidence without launching the exhaustive sweep.
        # deployment: 15 variants * 5 folds * (25 validation + 55 test) = 6,000 calls
        "paper_6k": {
            "feature_sets": ["minimal", "mercury", "combined"],
            "sample_units": ["session_sequence", "behavior_window", "packet_ablation"],
            "behavior_window_seconds": [5.0],
            "repeat_indices": [0, 1, 2, 3, 4],
            "balanced_eval_samples_per_repeat": 26,
            "deployment_validation_samples_per_repeat": 25,
            "deployment_test_samples_per_repeat": 55,
            "max_calls_per_run": 6000,
            "family_stratified_balanced": True,
        },
    },
    "llm_context_mode": "both",  # blind, memory, or both
    "llm_memory_examples_per_class": 4,
    "llm_memory_chars_per_example": 900,

    # Session / window constraints
    "session_min_packets": 6,
    "behavior_window_seconds": [1.0, 5.0, 30.0],
    "behavior_window_min_packets": 6,
    "sequence_segment_size": 16,
    "max_sequence_segments": 32,

    # Session local baselines
    "local_algorithms": [
        "RandomForestClassifier",
        "XGBClassifier",
        "LGBMClassifier",
        "DecisionTreeClassifier",
        "KNeighborsClassifier",
    ],

    # Fine-tuned LLM baseline
    "finetune_base_model": "gpt-4.1-nano-2025-04-14",
    "finetune_job_suffix": "session-capture-disjoint",
    "finetune_export_dir": "finetune/session_protocol_v1",
    # Six-packet eligibility keeps all five malware captures feasible for the
    # capture-disjoint whole-session supervised baseline.
    "finetune_sample_unit": "session_sequence",
    "finetune_window_seconds": 5.0,

    # Deployment-mode threshold selection. The threshold is chosen on validation
    # only by maximizing recall subject to this false-positive constraint.
    "deployment_threshold_strategy": "max_recall_at_fpr",
    "deployment_max_validation_fpr": 0.05,
    "deployment_threshold_metric": "f1",  # retained for legacy result readers
    "deployment_threshold_grid_size": 101,

    # Fine-tuned evaluation is leakage-free only on the held-out fold used
    # when exporting the supervised corpus.
    "finetune_eval_repeat_index": 0,
}


# Separation protocol is independent of balanced/deployment prevalence mode.
SESSION_SPLIT_CONFIG = {
    "default_mode": "capture_disjoint_5fold",
    "modes": [
        "capture_disjoint_5fold",
        "within_capture_temporal",
    ],
    "within_capture_train_fraction": 0.60,
    "within_capture_validation_fraction": 0.20,
    "within_capture_test_fraction": 0.20,
    "within_capture_minimum_sessions_per_capture": 5,
    "balanced_family_stratified": True,
    # Feasibility-audited floor. Configurations below this floor fail closed and
    # emit an explicit unsupported row instead of a pathological metric.
    "minimum_test_support_per_class": 100,
    "minimum_validation_support_per_class": 100,
    "manifest_schema_version": 1,
    "manifest_lock_timeout_seconds": 60,
}

# ============================================================================
# MALWARE FAMILY GROUPINGS (for Leave-One-Family-Out experiments)
# ============================================================================
FAMILY_GROUPS = {
    "botnet_spam": ["Neris"],
    "irc_botnet": ["Rbot"],
    "p2p_botnet": ["Virut"],
    "http_botnet": ["Sogou", "Murlo", "Menti"],
    "ddos_botnet": ["NSIS.ay"],
    "ransomware": ["CryptoWall", "Locky", "WannaCry"],
    "banking_trojan": ["TrickBot", "Dridex"],
    "dropper": ["Emotet"],
    "rat": ["njRAT"],
    "worm": ["Conficker"],
    "downloader": ["TrojanDownloader", "Hancitor"],
    "web_attack": ["Website_5.8.88.175"],
    "cryptominer": ["BitCoinMiner"],
}

# Reverse mapping: family -> group
FAMILY_TO_GROUP = {}
for group, families in FAMILY_GROUPS.items():
    for fam in families:
        FAMILY_TO_GROUP[fam] = group

# ============================================================================
# LOCALLY MOUNTED PCAP DATA (ground-truth captures)
# ============================================================================
MNT_DIR        = PROJECT_ROOT / "mnt"
MNT_BENIGN_DIR = MNT_DIR / "benign"       # normal traffic pcaps (is_malicious=0)
MNT_ATTACK_DIR = MNT_DIR / "attack_pcap"  # malware captures    (is_malicious=1)

# Explicit family mapping for attack pcaps whose filenames do not encode
# the malware family name.  Key = pcap stem (filename without .pcap),
# Value = malware family string that matches an entry in FAMILY_GROUPS above.
#
# Filename-based inference works automatically for CTU-13 botnet pcaps whose
# names contain the family (e.g. "botnet-capture-20110810-neris.pcap" → "Neris").
# For opaque date-machine names (e.g. "2018-04-03_win12.pcap"), add an entry
# here.  Leave the value as "" to keep the label as "Unknown".
#
# Example:
#   "2018-04-03_win12": "Neris",
#   "2021-11-29_win5":  "TrickBot",
MNT_ATTACK_FAMILIES: dict = {
    "2018-04-03_win10": "TrojanDownloader",
    "2018-04-03_win12": "Website_5.8.88.175",
    "2018-04-04_win16": "Dridex",
    "2018-03-27_win23": "BitCoinMiner",
    "2021-11-29_win5":  "Hancitor",
}

# Create local-capture directories eagerly so audits and first-time runs do not
# fail on missing parents.
for d in [MNT_DIR, MNT_BENIGN_DIR, MNT_ATTACK_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Protocol-aware sessionisation parameters used during PCAP extraction.
FLOW_TIMEOUTS = {
    "tcp": 120.0,
    "udp": 60.0,
}
TCP_CLOSED_GRACE_SECONDS = 2.0
ENCRYPTED_PORTS = {22, 443, 465, 636, 853, 993, 995, 8443}
MAX_PCAP_PACKETS = 500_000

# ============================================================================
# ADVERSARIAL EXPERIMENT PARAMETERS (Gap 5)
# ============================================================================
ADV_CONFIG = {
    # Perturbation budget sweep — ε is the L∞ fraction of each feature's IQR
    "epsilon_values": [0.05, 0.10, 0.20, 0.30, 0.50],

    # Sample counts
    "n_adversarial_samples": 200,    # per ε, per attack method (CART / KNN)
    "n_session_samples": 100,        # sessions for Exp 5D
    "min_session_length": 10,        # minimum packets per session
    "max_session_length": 50,        # maximum packets used per session

    # Black-box attack query budgets (LLM API calls per sample)
    "query_budget_random":    20,    # Exp 5C — random search
    "query_budget_hillclimb": 30,    # Exp 5C — coordinate hill climbing
    "query_budget_adaptive":  50,    # Exp 5E — adaptive adversary

    # LLM evaluation parameters
    "llm_eval_sample_size": 100,     # adversarial samples evaluated on LLM per ε
    "llm_few_shot_k": 5,             # examples for few-shot LLM evaluation

    # Cost tracking (for paper budget estimates)
    "estimated_cost_per_query_usd": 0.003,
}
