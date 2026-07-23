import json
import unittest
from pathlib import Path

from scripts.create_session_granularity_chart import collect_values


ROOT = Path(__file__).resolve().parents[1]


class PublicationArtifactTests(unittest.TestCase):
    def test_granularity_matrix_is_complete_for_executed_cells(self):
        values = collect_values()
        local = [key for key in values if key[2] != "GPT-5.4"]
        llm = [key for key in values if key[2] == "GPT-5.4"]
        self.assertEqual(len(local), 120)
        self.assertEqual(len(llm), 12)
        self.assertNotIn(("balanced", "combined", "GPT-5.4", "30 s"), values)
        self.assertNotIn(("deployment", "minimal", "GPT-5.4", "1 s"), values)

    def test_reported_gpt_context_losses_match_published_counts(self):
        values = collect_values()
        self.assertAlmostEqual(
            values[("balanced", "combined", "GPT-5.4", "Whole")],
            0.844074844074844,
        )
        self.assertAlmostEqual(
            values[("balanced", "combined", "GPT-5.4", "5 s")],
            0.706114398422091,
        )
        self.assertAlmostEqual(
            values[("deployment", "combined", "GPT-5.4", "Whole")],
            0.742081447963801,
        )
        self.assertAlmostEqual(
            values[("deployment", "combined", "GPT-5.4", "5 s")],
            0.257062146892655,
        )

    def test_reported_local_winners_match_published_summaries(self):
        values = collect_values()
        expected = {
            ("balanced", "mercury", "CART", "Whole"): 0.8907891522110921,
            ("balanced", "combined", "KNN", "30 s"): 0.8844932844932845,
            ("balanced", "combined", "KNN", "5 s"): 0.8846060014637717,
            ("balanced", "mercury", "CART", "1 s"): 0.8874172185430463,
            ("deployment", "minimal", "RF", "Whole"): 0.8317515099223468,
            ("deployment", "minimal", "RF", "30 s"): 0.8300970873786407,
            ("deployment", "minimal", "RF", "5 s"): 0.8358157256667821,
            ("deployment", "combined", "CART", "1 s"): 0.850609756097561,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(values[key], value)

    def test_readme_comparison_figures_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for feature in ("minimal", "mercury", "combined"):
            relative = f"figures/session_granularity_{feature}.png"
            self.assertIn(relative, readme)
            self.assertTrue((ROOT / relative).is_file())

    def test_legacy_metrics_recompute_from_confusion_counts(self):
        path = (
            ROOT
            / "results"
            / "published"
            / "legacy_phase4e_openai_session_windows.summary.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["model"], "not_recorded_in_source_rows")
        self.assertFalse(payload["protocol"]["capture_disjoint"])
        self.assertEqual(len(payload["records"]), 4)
        for row in payload["records"]:
            tp, fp, fn, tn = (row[name] for name in ("tp", "fp", "fn", "tn"))
            self.assertEqual(tp + fp + fn + tn, row["n"])
            self.assertAlmostEqual(
                row["accuracy"], (tp + tn) / row["n"]
            )
            self.assertAlmostEqual(
                row["f1_1"], (2 * tp) / ((2 * tp) + fp + fn)
            )


if __name__ == "__main__":
    unittest.main()
