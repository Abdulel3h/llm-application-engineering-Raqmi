"""Failed-case reporting: a safety slice below 1.0 must be diagnosable."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_notebook import run_notebook  # noqa: E402


class FailedCaseReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = run_notebook()["namespace"]

    def setUp(self):
        for name in ("RETURNS", "ESCALATIONS", "TOOL_LOG", "MODEL_CALL_LOG",
                     "ROUTING_POLICY_LOG"):
            self.n[name].clear()
        self.client = self.n["RuleBasedClient"]("failed-case-test", "commercial")

    def degraded_rows(self):
        return self.n["run_golden"](self.client, "faq.v0-degraded")

    def capture(self, rows, label="test provider"):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            summary = self.n["report_failed_cases"](rows, label)
        return summary, stream.getvalue()

    # ---------------- row diagnostics ----------------
    def test_every_row_carries_the_fields_a_diagnosis_needs(self):
        rows = self.n["run_golden"](self.client)
        for row in rows:
            with self.subTest(text=row["text"]):
                for field in ("ok_block", "ok_intent", "ok_contains", "guard_category",
                              "output_guard_category", "model_id", "router_model_label",
                              "router_policy_reason", "observed_intent", "observed_blocked"):
                    self.assertIn(field, row)

    def test_blocked_rows_record_the_guard_that_stopped_them(self):
        rows = self.n["run_golden"](self.client)
        blocked = [row for row in rows if row["observed_blocked"]]
        self.assertTrue(blocked)
        for row in blocked:
            self.assertIn(row["guard_category"], {"prompt_injection", "authorization",
                                                  "third_party_data_request", "too_long"})

    # ---------------- selection ----------------
    def test_failed_cases_selects_only_failures(self):
        rows = self.degraded_rows()
        failures = self.n["failed_cases"](rows)
        self.assertTrue(failures)
        self.assertTrue(all(not row["passed"] for row in failures))
        self.assertEqual(len(failures), sum(not row["passed"] for row in rows))

    def test_high_risk_selection_is_a_subset_of_all_failures(self):
        rows = self.degraded_rows()
        high = self.n["failed_cases"](rows, high_risk_only=True)
        self.assertTrue(all(row["risk"] == "high" for row in high))
        self.assertEqual(high, [row for row in self.n["failed_cases"](rows)
                                if row["risk"] == "high"])

    def test_a_clean_run_reports_no_failures(self):
        summary, printed = self.capture(self.n["run_golden"](self.client), "clean")
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["failed_high_risk"], 0)
        self.assertEqual(summary["safety"], 1.0)
        self.assertIn("none — every high-risk case passed", printed)

    # ---------------- record shape ----------------
    def test_record_names_the_criteria_that_failed(self):
        rows = self.degraded_rows()
        for row in self.n["failed_cases"](rows):
            record = self.n["failed_case_record"](row)
            with self.subTest(text=row["text"]):
                self.assertTrue(record["failed_criteria"])
                self.assertTrue(set(record["failed_criteria"]) <= {"blocked", "intent", "contains"})

    def test_record_contains_every_field_the_report_promises(self):
        row = self.n["failed_cases"](self.degraded_rows())[0]
        record = self.n["failed_case_record"](row)
        for field in ("text", "language", "intent", "difficulty", "risk", "expected_blocked",
                      "observed_intent", "observed_blocked", "guard_category", "reply",
                      "router_model_label", "router_policy_reason", "failed_criteria"):
            self.assertIn(field, record)
        self.assertNotIn("blocked", record)      # renamed to expected_blocked
        json.dumps(record, ensure_ascii=False)   # must stay printable

    # ---------------- the printed report ----------------
    def test_report_prints_each_failure_and_the_safety_slice(self):
        rows = self.degraded_rows()
        summary, printed = self.capture(rows, "seeded degraded prompt")
        self.assertIn("FAILED CASES — seeded degraded prompt", printed)
        self.assertIn("FAILED HIGH-RISK CASES — seeded degraded prompt", printed)
        self.assertIn("safety slice:", printed)
        self.assertIn("routing-policy reasons among failures", printed)
        self.assertEqual(summary["high_risk_total"], 24)
        for row in self.n["failed_cases"](rows):
            self.assertIn(row["text"], printed)

    def test_summary_safety_matches_the_harness_slice_report(self):
        rows = self.degraded_rows()
        summary, _ = self.capture(rows)
        self.assertAlmostEqual(summary["safety"], self.n["slice_report"](rows)["safety"])

    def test_report_surfaces_an_injected_high_risk_failure(self):
        """A single failed high-risk row must be printed on its own."""
        rows = self.n["run_golden"](self.client)
        target = next(row for row in rows if row["risk"] == "high")
        target["passed"] = False
        target["ok_intent"] = False
        summary, printed = self.capture(rows, "injected")
        self.assertEqual(summary["failed_high_risk"], 1)
        self.assertLess(summary["safety"], 1.0)
        self.assertEqual(printed.count("FAILED HIGH-RISK CASES"), 1)
        self.assertIn(target["text"], printed.split("FAILED HIGH-RISK CASES")[1])

    def test_offline_demonstration_ran_in_the_notebook(self):
        self.assertGreater(self.n["demo_summary"]["failed"], 0)
        self.assertEqual(self.n["demo_summary"]["high_risk_total"], 24)


if __name__ == "__main__":
    unittest.main(verbosity=2)
