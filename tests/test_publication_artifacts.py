import json
import unittest
from pathlib import Path

from scripts.create_session_granularity_chart import _cell_label, collect_values


ROOT = Path(__file__).resolve().parents[1]


class PublicationArtifactTests(unittest.TestCase):
    def test_granularity_matrix_is_complete_for_executed_cells(self):
        values = collect_values()
        local = [key for key in values if key[2] != "GPT-5.4"]
        llm = [key for key in values if key[2] == "GPT-5.4"]
        self.assertEqual(len(local), 120)
        self.assertEqual(len(llm), 24)

    def test_author_supplied_gpt_window_values_are_loaded_exactly(self):
        values = collect_values()
        expected = {
            ("balanced", "minimal", "GPT-5.4", "30 s"): 0.604,
            ("balanced", "minimal", "GPT-5.4", "1 s"): 0.556,
            ("deployment", "minimal", "GPT-5.4", "30 s"): 0.795,
            ("deployment", "minimal", "GPT-5.4", "1 s"): 0.496,
            ("balanced", "mercury", "GPT-5.4", "30 s"): 0.689,
            ("balanced", "mercury", "GPT-5.4", "1 s"): 0.606,
            ("deployment", "mercury", "GPT-5.4", "30 s"): 0.381,
            ("deployment", "mercury", "GPT-5.4", "1 s"): 0.232,
            ("balanced", "combined", "GPT-5.4", "30 s"): 0.751,
            ("balanced", "combined", "GPT-5.4", "1 s"): 0.666,
            ("deployment", "combined", "GPT-5.4", "30 s"): 0.400,
            ("deployment", "combined", "GPT-5.4", "1 s"): 0.257,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(values[key], value)
        self.assertEqual(_cell_label("GPT-5.4", "30 s", 0.604), "60.4*")
        self.assertEqual(_cell_label("GPT-5.4", "1 s", 0.556), "55.6*")
        self.assertEqual(_cell_label("GPT-5.4", "5 s", 0.5995), "60.0")

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

    def test_completed_gpt_sweeps_have_reported_context_ordering(self):
        values = collect_values()
        granularities = ("Whole", "30 s", "5 s", "1 s")
        expected_losses = {
            ("balanced", "minimal"): 0.054,
            ("balanced", "mercury"): 0.16118403547671845,
            ("balanced", "combined"): 0.178074844074844,
            ("deployment", "minimal"): 0.40728467153284675,
            ("deployment", "mercury"): 0.462021101992966,
            ("deployment", "combined"): 0.485081447963801,
        }
        for (mode, feature), expected_loss in expected_losses.items():
            series = [
                values[(mode, feature, "GPT-5.4", granularity)]
                for granularity in granularities
            ]
            self.assertEqual(max(series), series[0])
            self.assertEqual(min(series), series[-1])
            self.assertAlmostEqual(series[0] - series[-1], expected_loss)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("completed four-horizon sweep", readme)
        self.assertNotIn("dedicated multi-window LLM sweep", readme)
        self.assertNotIn("points strengthen the observed degradation", readme)

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

    def test_reported_local_worst_cells_match_published_summaries(self):
        values = collect_values()
        expected = {
            ("balanced", "combined", "CART", "Whole"): 0.8767323121808899,
            ("balanced", "combined", "CART", "30 s"): 0.7598816886259747,
            ("balanced", "minimal", "KNN", "5 s"): 0.750814332247557,
            ("balanced", "combined", "CART", "1 s"): 0.7585464333781965,
            ("deployment", "mercury", "LGBM", "Whole"): 0.7999331439077386,
            ("deployment", "mercury", "XGB", "30 s"): 0.7990622906898861,
            ("deployment", "mercury", "XGB", "5 s"): 0.7987284590931906,
            ("deployment", "mercury", "XGB", "1 s"): 0.7993305439330544,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(values[key], value)

    def test_readme_comparison_figures_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for feature in ("minimal", "mercury", "combined"):
            relative = f"figures/session_granularity_{feature}.png"
            self.assertIn(relative, readme)
            self.assertTrue((ROOT / relative).is_file())

    def test_phase4e_metrics_recompute_from_confusion_counts(self):
        path = (
            ROOT
            / "results"
            / "published"
            / "phase4e_openai_session_windows.summary.json"
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

    def test_publication_docs_use_phase4e_label(self):
        text = "\n".join(
            [
                (ROOT / "README.md").read_text(encoding="utf-8"),
                (ROOT / "results" / "published" / "README.md").read_text(
                    encoding="utf-8"
                ),
            ]
        )
        self.assertIn("The Phase 4E archive", text)
        self.assertIn("phase4e_openai_session_windows", text)


if __name__ == "__main__":
    unittest.main()
