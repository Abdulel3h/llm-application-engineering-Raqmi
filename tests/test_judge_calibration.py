"""Live judge calibration: label hygiene, kappa arithmetic, and the revision loop."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_notebook import run_notebook  # noqa: E402


class ScriptedJudgeClient:
    """Provider double: verdicts are queued per rubric version."""

    model_id = "scripted-judge"
    route = "commercial"

    def __init__(self, namespace, verdicts_by_version):
        self.n = namespace
        self.verdicts = {k: list(v) for k, v in verdicts_by_version.items()}
        self.seen = []

    def complete(self, request):
        self.seen.append((request.prompt_version, request.user_text))
        verdict = self.verdicts[request.prompt_version].pop(0)
        return self.n["LLMResponse"](
            text=verdict, model_id=self.model_id, route=self.route, latency_ms=1.0,
            usage=self.n["LLMUsage"](input_tokens=20, output_tokens=1))


class JudgeCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = run_notebook()["namespace"]

    def setUp(self):
        self.n["MODEL_CALL_LOG"].clear()
        self.labels = self.n["JUDGE_LABELS"]

    # ---------------- corpus ----------------
    def test_reference_corpus_is_balanced_and_bilingual(self):
        cases = self.n["JUDGE_CASES"]
        self.assertEqual(len(cases), 36)
        self.assertGreaterEqual(len(cases), 30)
        self.assertLessEqual(len(cases), 40)
        self.assertEqual(sum(c["human_label"] == "PASS" for c in cases), 12)
        self.assertEqual(sum(c["human_label"] == "PARTIAL" for c in cases), 12)
        self.assertEqual(sum(c["human_label"] == "FAIL" for c in cases), 12)
        self.assertEqual(sum(c["language"] == "ar" for c in cases), 18)
        self.assertEqual(len({c["id"] for c in cases}), 36)
        for case in cases:
            self.assertTrue(case["question"] and case["answer"] and case["evidence"])

    def test_reference_labels_are_frozen(self):
        import hashlib
        import json
        digest = hashlib.sha256(json.dumps(
            [(c["id"], c["human_label"]) for c in self.n["JUDGE_CASES"]],
            ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(digest, self.n["JUDGE_LABEL_FINGERPRINT"])

    # ---------------- what the judge is allowed to see ----------------
    def test_payload_carries_question_evidence_and_answer_only(self):
        for case in self.n["JUDGE_CASES"]:
            with self.subTest(case=case["id"]):
                payload = self.n["judge_payload"](case)
                self.assertIn(case["question"], payload)
                self.assertIn(case["evidence"], payload)
                self.assertIn(case["answer"], payload)
                self.assertNotIn(case["id"], payload)
                relabelled = {**case, "human_label": "TOTALLY_DIFFERENT", "id": "zz-99"}
                self.assertEqual(self.n["judge_payload"](relabelled), payload)

    def test_a_changed_label_cannot_change_the_request(self):
        case = dict(self.n["JUDGE_CASES"][0])
        client = ScriptedJudgeClient(self.n, {"judge.v3": ["PASS"] * 36})
        original = list(self.n["JUDGE_CASES"])
        try:
            self.n["JUDGE_CASES"][0] = {**case, "human_label": "FAIL"}
            self.n["run_judge"](client, "judge.v3")
            flipped = [payload for _, payload in client.seen]
        finally:
            self.n["JUDGE_CASES"][:] = original
        client = ScriptedJudgeClient(self.n, {"judge.v3": ["PASS"] * 36})
        self.n["run_judge"](client, "judge.v3")
        self.assertEqual(flipped, [payload for _, payload in client.seen])

    def test_judge_rubrics_are_versioned_prompt_artefacts(self):
        for version in ("judge.v3", "judge.v3r"):
            with self.subTest(version=version):
                self.assertIn(version, self.n["PROMPTS"])
                self.assertIn(self.n["CANARY"], self.n["PROMPTS"][version])
                for label in ("PASS", "PARTIAL", "FAIL"):
                    self.assertIn(label, self.n["PROMPTS"][version])

    # ---------------- verdict parsing ----------------
    def test_verdict_parsing_is_tolerant_but_never_guesses(self):
        parse = self.n["parse_judge_label"]
        self.assertEqual(parse("PASS"), "PASS")
        self.assertEqual(parse(" partial \n"), "PARTIAL")
        self.assertEqual(parse("Verdict: FAIL."), "FAIL")
        self.assertEqual(parse("PARTIAL — the answer omits the number"), "PARTIAL")
        for junk in ("", None, "I am not sure", "42"):
            with self.subTest(junk=junk):
                self.assertEqual(parse(junk), "UNPARSED")

    # ---------------- arithmetic ----------------
    def test_kappa_matches_a_hand_computed_value(self):
        kappa = self.n["cohen_kappa"]
        self.assertEqual(kappa(["A", "B", "A"], ["A", "B", "A"]), 1.0)
        # 2x2, n=4: observed 0.5, expected 0.5 -> kappa 0
        self.assertAlmostEqual(kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"]), 0.0)
        # observed 0.75, expected 0.5 -> kappa 0.5
        self.assertAlmostEqual(kappa(["A", "A", "B", "B"], ["A", "A", "A", "B"]), 0.5)

    def test_calibration_result_reports_agreement_and_unparsed(self):
        verdicts = list(self.labels)
        verdicts[0] = "UNPARSED"
        result = self.n["calibration_result"]("judge.v3", verdicts)
        self.assertEqual(result["n"], 36)
        self.assertAlmostEqual(result["agreement"], 35 / 36)
        self.assertEqual(result["unparsed"], 1)
        self.assertLess(result["kappa"], 1.0)

    # ---------------- the revision loop ----------------
    def test_no_revision_when_the_first_pass_meets_the_target(self):
        client = ScriptedJudgeClient(self.n, {"judge.v3": list(self.labels)})
        first, final = self.n["calibrate_judge"](client)
        self.assertIs(final, first)
        self.assertEqual(final["kappa"], 1.0)
        self.assertEqual({version for version, _ in client.seen}, {"judge.v3"})

    def test_a_weak_first_pass_triggers_exactly_one_revised_run(self):
        weak = ["PASS"] * 24 + list(self.labels[24:])
        client = ScriptedJudgeClient(self.n, {"judge.v3": weak, "judge.v3r": list(self.labels)})
        first, final = self.n["calibrate_judge"](client)
        self.assertLess(first["kappa"], 0.60)
        self.assertEqual(final["kappa"], 1.0)
        self.assertEqual(final["prompt_version"], "judge.v3r")
        self.assertEqual([version for version, _ in client.seen].count("judge.v3r"), 36)

    def test_an_honest_failure_is_reported_rather_than_hidden(self):
        weak = ["PASS"] * 36
        client = ScriptedJudgeClient(self.n, {"judge.v3": weak, "judge.v3r": list(weak)})
        first, final = self.n["calibrate_judge"](client)
        self.assertLess(final["kappa"], 0.60)
        self.assertIsNot(final, first)
        self.assertEqual(final["verdicts"], weak)      # nothing is rewritten to pass

    def test_disagreement_table_lists_every_mismatch(self):
        import contextlib
        import io
        verdicts = list(self.labels)
        verdicts[0] = "FAIL" if verdicts[0] != "FAIL" else "PASS"
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.n["print_disagreements"](verdicts)
        printed = stream.getvalue()
        self.assertIn("disagreements: 1/36", printed)
        self.assertIn(self.n["JUDGE_CASES"][0]["id"], printed)

    # ---------------- the offline run that Run all produces ----------------
    def test_offline_calibration_is_labelled_and_not_a_gate(self):
        calibration = self.n["JUDGE_CALIBRATION"]
        self.assertEqual(calibration["mode"], "DEMO_PREVIEW")
        self.assertFalse(calibration["used_as_regression_gate"])
        self.assertFalse(self.n["JUDGE_IS_REGRESSION_GATE"])
        self.assertEqual(calibration["final"]["n"], 36)
        self.assertEqual(calibration["final"]["unparsed"], 0)
        self.assertEqual(calibration["label_fingerprint"], self.n["JUDGE_LABEL_FINGERPRINT"])
        self.assertEqual(calibration["target_kappa"], 0.60)

    def test_the_deterministic_stand_in_cannot_read_the_labels(self):
        judge = self.n["DeterministicJudgeClient"]()
        verdicts = self.n["run_judge"](judge, "judge.v3")
        self.assertNotEqual(verdicts, self.labels)          # not a copy of the answer key
        self.assertGreater(sum(a == b for a, b in zip(verdicts, self.labels)), 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
