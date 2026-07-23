import json
import sqlite3
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src.session_dataset import (
    SessionDatasetSpec,
    _eligible_session_pool,
    _manifest_lock,
    eligibility_for_spec,
)
from src.session_experiments import (
    _load_existing_result_rows,
    _select_threshold_from_validation,
    _summarise_local_rows,
    _train_and_evaluate_repeat,
    _write_result_rows,
)
from src.session_splits import (
    CAPTURE_DISJOINT_5FOLD,
    WITHIN_CAPTURE_TEMPORAL,
    SessionSplitFeasibilityError,
    build_capture_disjoint_5fold_manifest,
    build_within_capture_temporal_manifest,
    cohort_hash,
    load_session_manifest,
    materialize_session_splits,
    save_session_manifest,
)


FAMILIES = [
    "BitCoinMiner",
    "Dridex",
    "Hancitor",
    "TrojanDownloader",
    "Website_5.8.88.175",
]


def synthetic_cohort(samples_per_capture=120, samples_per_session=1):
    rows = []
    sample_id = 1
    session_id = 1
    capture_specs = [(capture_id, 0, "") for capture_id in range(1, 8)]
    capture_specs.extend(
        (capture_id, 1, family)
        for capture_id, family in zip(range(8, 13), FAMILIES)
    )
    sessions_per_capture = samples_per_capture // samples_per_session
    for capture_id, label, family in capture_specs:
        for session_offset in range(sessions_per_capture):
            start = capture_id * 1_000_000 + session_offset * 10
            for packet_offset in range(samples_per_session):
                rows.append(
                    {
                        "packet_id": sample_id,
                        "session_id": session_id,
                        "dataset_id": capture_id,
                        "is_malicious": label,
                        "malware_family": family,
                        "session_start_time": float(start),
                    }
                )
                sample_id += 1
            session_id += 1
    return pd.DataFrame(rows)


def common_manifest_kwargs():
    return {
        "experiment_key": "test",
        "evaluation_mode": "balanced",
        "cohort_filters": {"sample_unit": "behavior_window"},
        "eligibility": {
            "sample_unit": "behavior_window",
            "minimum_packets_per_session": 6,
            "encrypted_only": False,
        },
        "expected_families": FAMILIES,
        "random_state": 42,
    }


class EligibilityTests(unittest.TestCase):
    def test_session_thresholds_are_six_and_packet_ablation_is_distinct(self):
        common = dict(feature_set="minimal", group_by="capture", sample_size=100)
        behavior = SessionDatasetSpec(sample_unit="behavior_window", **common)
        session = SessionDatasetSpec(sample_unit="session_sequence", **common)
        packet = SessionDatasetSpec(sample_unit="packet_ablation", **common)
        self.assertEqual(eligibility_for_spec(behavior)["minimum_packets_per_session"], 6)
        self.assertEqual(eligibility_for_spec(session)["minimum_packets_per_session"], 6)
        self.assertEqual(eligibility_for_spec(packet)["minimum_packets_per_session"], 2)

    def test_six_and_seven_packet_sessions_are_session_and_window_eligible(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY, dataset_id INTEGER, is_malicious INTEGER,
                malware_family TEXT, is_encrypted INTEGER
            );
            CREATE TABLE packets (id INTEGER PRIMARY KEY, session_id INTEGER);
            """
        )
        packet_id = 1
        for session_id, count in enumerate((5, 6, 7, 8), start=1):
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                (session_id, session_id, session_id % 2, "family", 0),
            )
            for _ in range(count):
                conn.execute("INSERT INTO packets VALUES (?, ?)", (packet_id, session_id))
                packet_id += 1
        behavior = _eligible_session_pool(conn, min_packets=6)
        whole = _eligible_session_pool(conn, min_packets=6)
        self.assertEqual(behavior["session_id"].astype(int).tolist(), [2, 3, 4])
        self.assertEqual(whole["session_id"].astype(int).tolist(), [2, 3, 4])
        conn.close()

    def test_eligibility_changes_cohort_hash(self):
        ids = [1, 2, 3]
        six = {"minimum_packets_per_session": 6}
        seven = {"minimum_packets_per_session": 7}
        self.assertNotEqual(cohort_hash(ids, six), cohort_hash(ids, seven))


class CaptureDisjointTests(unittest.TestCase):
    def setUp(self):
        self.df = synthetic_cohort()
        self.manifest = build_capture_disjoint_5fold_manifest(
            self.df,
            minimum_test_support_per_class=20,
            minimum_validation_support_per_class=20,
            **common_manifest_kwargs(),
        )

    def test_all_families_and_captures_are_held_out(self):
        folds = materialize_session_splits(self.df, self.manifest)
        self.assertEqual(len(folds), 5)
        self.assertEqual(
            [fold[0]["held_out_malware_family"] for fold in folds], FAMILIES
        )
        tested_benign = set()
        for metadata, train, validation, test in folds:
            train_captures = set(train["dataset_id"].astype(int))
            validation_captures = set(validation["dataset_id"].astype(int))
            test_captures = set(test["dataset_id"].astype(int))
            self.assertFalse(train_captures & validation_captures)
            self.assertFalse(train_captures & test_captures)
            self.assertFalse(validation_captures & test_captures)
            self.assertEqual(metadata["test"]["support_0"], metadata["test"]["support_1"])
            tested_benign.update(test_captures & set(range(1, 8)))
        self.assertEqual(tested_benign, set(range(1, 8)))

    def test_manifest_tamper_is_rejected(self):
        tampered = json.loads(json.dumps(self.manifest))
        overlapping = tampered["folds"][0]["train_sample_ids"][0]
        tampered["folds"][0]["test_sample_ids"][0] = overlapping
        with self.assertRaises(RuntimeError):
            materialize_session_splits(self.df, tampered)

    def test_fold_construction_ignores_features_models_and_predictions(self):
        augmented = self.df.copy()
        augmented["feature"] = np.linspace(-100, 100, len(augmented))
        augmented["model_prediction"] = np.arange(len(augmented)) % 2
        rebuilt = build_capture_disjoint_5fold_manifest(
            augmented,
            minimum_test_support_per_class=20,
            minimum_validation_support_per_class=20,
            **common_manifest_kwargs(),
        )
        self.assertEqual(rebuilt["manifest_hash"], self.manifest["manifest_hash"])

    def test_missing_family_fails_closed(self):
        missing_hancitor = self.df[self.df["malware_family"] != "Hancitor"].copy()
        with self.assertRaises(SessionSplitFeasibilityError):
            build_capture_disjoint_5fold_manifest(
                missing_hancitor,
                minimum_test_support_per_class=20,
                minimum_validation_support_per_class=20,
                **common_manifest_kwargs(),
            )

    def test_manifest_hash_and_schema_are_fail_closed(self):
        path = Path("results") / f"_test_manifest_{uuid.uuid4().hex}.json"
        try:
            save_session_manifest(path, self.manifest)
            loaded = load_session_manifest(
                path,
                expected_split_mode=CAPTURE_DISJOINT_5FOLD,
                expected_eligibility=common_manifest_kwargs()["eligibility"],
            )
            self.assertEqual(loaded["manifest_hash"], self.manifest["manifest_hash"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["schema_version"] = 0
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_session_manifest(
                    path,
                    expected_split_mode=CAPTURE_DISJOINT_5FOLD,
                    expected_eligibility=common_manifest_kwargs()["eligibility"],
                )
        finally:
            path.unlink(missing_ok=True)


class TemporalTests(unittest.TestCase):
    def test_temporal_split_never_splits_a_session(self):
        df = synthetic_cohort(samples_per_capture=24, samples_per_session=2)
        manifest = build_within_capture_temporal_manifest(
            df,
            train_fraction=0.6,
            validation_fraction=0.2,
            test_fraction=0.2,
            minimum_sessions_per_capture=5,
            **common_manifest_kwargs(),
        )
        metadata, train, validation, test = materialize_session_splits(df, manifest)[0]
        session_sets = [
            set(frame["session_id"].astype(int)) for frame in (train, validation, test)
        ]
        self.assertFalse(session_sets[0] & session_sets[1])
        self.assertFalse(session_sets[0] & session_sets[2])
        self.assertFalse(session_sets[1] & session_sets[2])
        self.assertEqual(manifest["split_mode"], WITHIN_CAPTURE_TEMPORAL)
        for boundary in metadata["temporal_boundaries"].values():
            self.assertLessEqual(boundary["train_max_time"], boundary["validation_min_time"])
            self.assertLessEqual(boundary["validation_max_time"], boundary["test_min_time"])


class MetricsAndSafetyTests(unittest.TestCase):
    def test_validation_threshold_obeys_fpr_constraint(self):
        y_true = np.asarray([0] * 20 + [1] * 10)
        scores = np.asarray([0.01] * 19 + [0.9] + [0.2] * 2 + [0.8] * 8)
        threshold, metrics = _select_threshold_from_validation(y_true, scores)
        self.assertGreaterEqual(threshold, 0.2)
        self.assertLessEqual(metrics["validation_fpr"], 0.05 + 1e-12)
        self.assertEqual(metrics["threshold_strategy"], "max_recall_at_fpr")

    def test_summary_reports_dispersion_and_pooled_metrics(self):
        rows = []
        for fold, (tp, fp, fn, tn) in enumerate(((8, 2, 2, 8), (5, 1, 5, 9))):
            rows.append(
                {
                    "experiment": "e",
                    "algorithm": "RF",
                    "record_type": "repeat",
                    "repeat_index": fold,
                    "fold_index": fold,
                    "held_out_malware_family": FAMILIES[fold],
                    "test_support": {"support_0": 10, "support_1": 10},
                    "accuracy": (tp + tn) / 20,
                    "f1_1": 2 * tp / (2 * tp + fp + fn),
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tn": tn,
                }
            )
        summary = _summarise_local_rows(rows, 2)
        self.assertIsNotNone(summary)
        self.assertIn("accuracy_median", summary)
        self.assertIn("accuracy_q1", summary)
        self.assertEqual(summary["accuracy_min"], min(row["accuracy"] for row in rows))
        self.assertAlmostEqual(summary["pooled_accuracy"], 30 / 40)

    def test_test_labels_cannot_change_selected_threshold(self):
        train = pd.DataFrame(
            {"x": np.r_[np.linspace(0.0, 0.4, 20), np.linspace(0.6, 1.0, 20)],
             "is_malicious": [0] * 20 + [1] * 20}
        )
        validation = pd.DataFrame(
            {"x": np.r_[np.linspace(0.05, 0.35, 10), np.linspace(0.65, 0.95, 10)],
             "is_malicious": [0] * 10 + [1] * 10}
        )
        test = pd.DataFrame(
            {"x": np.linspace(0.0, 1.0, 20), "is_malicious": [0] * 10 + [1] * 10}
        )
        inverted_test = test.copy()
        inverted_test["is_malicious"] = 1 - inverted_test["is_malicious"]
        first = _train_and_evaluate_repeat(
            "DecisionTreeClassifier",
            train,
            validation,
            test,
            ["x"],
            evaluation_mode="deployment",
        )
        second = _train_and_evaluate_repeat(
            "DecisionTreeClassifier",
            train,
            validation,
            inverted_test,
            ["x"],
            evaluation_mode="deployment",
        )
        self.assertEqual(first["selected_threshold"], second["selected_threshold"])
        self.assertEqual(first["validation_fpr"], second["validation_fpr"])

    def test_manifest_lock_serializes_parallel_writers(self):
        path = Path("results") / f"_test_lock_{uuid.uuid4().hex}.json"
        try:
            active = 0
            maximum_active = 0
            guard = threading.Lock()

            def worker():
                nonlocal active, maximum_active
                with _manifest_lock(path):
                    with guard:
                        active += 1
                        maximum_active = max(maximum_active, active)
                    time.sleep(0.03)
                    with guard:
                        active -= 1

            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(lambda _: worker(), range(4)))
            self.assertEqual(maximum_active, 1)
            self.assertFalse(path.with_suffix(".json.lock").exists())
        finally:
            path.with_suffix(".json.lock").unlink(missing_ok=True)

    def test_result_loader_rejects_mixed_split_modes(self):
        path = Path("results") / f"_test_results_{uuid.uuid4().hex}.json"
        try:
            _write_result_rows(
                path,
                [
                    {"split_mode": CAPTURE_DISJOINT_5FOLD},
                    {"split_mode": WITHIN_CAPTURE_TEMPORAL},
                ],
            )
            with self.assertRaises(RuntimeError):
                _load_existing_result_rows(
                    path,
                    expected_split_mode=CAPTURE_DISJOINT_5FOLD,
                )
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
