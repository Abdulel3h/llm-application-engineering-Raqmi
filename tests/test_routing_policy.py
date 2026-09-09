"""Deterministic routing policy: FAQ versus return transaction, and ownership.

RED issue 2. A live router labelled the Arabic policy question "كم مدة الإرجاع؟"
as `return_request`, and a router mistake on a cross-user order would skip the
ownership check entirely. Both are corrected by application code, so these tests
assert the corrected label for EVERY label the model might emit.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_notebook import run_notebook  # noqa: E402

MODEL_LABELS = ("faq", "order_status", "return_request", "escalate")

ARABIC_FAQ = "كم مدة الإرجاع؟"
ARABIC_TRANSACTION = "أبي أرجع السماعة من الطلب 1024 لأنها خربانة"
ENGLISH_FAQ = "What is the return policy?"
ENGLISH_TRANSACTION = "Return the headphones from order 1024 because they are defective."


class StubRouterClient:
    """A router that always emits one chosen label, to isolate the policy."""

    def __init__(self, namespace, label):
        self.n = namespace
        self.label = label
        self.model_id = "stub-router"
        self.route = "commercial"
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        if request.prompt_version == "router.v1":
            text = self.label
        else:
            text = self.n["RuleBasedClient"]("inner", "commercial").complete(request).text
        return self.n["LLMResponse"](
            text=text, model_id=self.model_id, route=self.route, latency_ms=1.0,
            usage=self.n["LLMUsage"](input_tokens=20, output_tokens=2))


class RoutingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = run_notebook()["namespace"]

    def setUp(self):
        for name in ("RETURNS", "ESCALATIONS", "TOOL_LOG", "MODEL_CALL_LOG",
                     "ROUTING_POLICY_LOG"):
            self.n[name].clear()
        self.session = self.n["Session"]("user_123")

    def policy(self, text, label, session=None):
        return self.n["apply_routing_policy"](text, label, session)[0]

    # ---------------- the four required regressions ----------------
    def test_arabic_return_policy_question_is_never_a_transaction(self):
        for label in MODEL_LABELS:
            with self.subTest(model_label=label):
                self.assertNotEqual(self.policy(ARABIC_FAQ, label, self.session),
                                    "return_request")
        for label in ("faq", "return_request"):
            self.assertEqual(self.policy(ARABIC_FAQ, label, self.session), "faq")

    def test_english_return_policy_question_is_never_a_transaction(self):
        for label in MODEL_LABELS:
            with self.subTest(model_label=label):
                self.assertNotEqual(self.policy(ENGLISH_FAQ, label, self.session),
                                    "return_request")
        for label in ("faq", "return_request"):
            self.assertEqual(self.policy(ENGLISH_FAQ, label, self.session), "faq")

    def test_arabic_return_transaction_stays_a_transaction(self):
        for label in ("faq", "order_status", "return_request"):
            with self.subTest(model_label=label):
                self.assertEqual(self.policy(ARABIC_TRANSACTION, label, self.session),
                                 "return_request")

    def test_english_return_transaction_stays_a_transaction(self):
        for label in ("faq", "order_status", "return_request"):
            with self.subTest(model_label=label):
                self.assertEqual(self.policy(ENGLISH_TRANSACTION, label, self.session),
                                 "return_request")

    # ---------------- the general policy, not sentence matching ----------------
    def test_informational_return_questions_across_phrasings(self):
        for text in ("كم مدة الإرجاع؟", "وش سياسة الإرجاع؟", "ما هي سياسة الاسترجاع؟",
                     "هل المنتج التالف قابل للإرجاع؟", "What is the return window?",
                     "Can I return an item within 14 days?", "What is the return policy?",
                     "Can a defective product be returned?",
                     "How long do I have to return something?"):
            with self.subTest(text=text):
                self.assertFalse(self.n["return_action_signal"](text))
                self.assertEqual(self.policy(text, "return_request", self.session), "faq")

    def test_transactional_return_requests_across_phrasings(self):
        for text in ("أبي أرجع السماعة من الطلب 1024 لأنها خربانة",
                     "رجع السماعة طلب 1024 لأنها خربانة",
                     "أبي إرجاع السماعة من 1024 لأنها خربانة",
                     "الطلب 1024 السماعة خربانة أبي أرجعها",
                     "أرجع سماعة الطلب 1024 منتج غلط",
                     "Return the headphones from order 1024 because they are defective",
                     "Create a return for headphones order 1024 defective",
                     "Order 1024 headphones are broken, return them",
                     "I got the wrong headphones in order 1024, return them",
                     "Return headphones from 1024, changed my mind"):
            with self.subTest(text=text):
                self.assertTrue(self.n["return_action_signal"](text))
                self.assertEqual(self.policy(text, "return_request", self.session),
                                 "return_request")

    def test_every_golden_return_case_carries_an_action_signal(self):
        returns = [case for case in self.n["GOLDEN"] if case["intent"] == "return_request"]
        self.assertEqual(len(returns), 12)
        for case in returns:
            with self.subTest(text=case["text"]):
                self.assertTrue(self.n["return_action_signal"](case["text"]))

    def test_no_golden_faq_case_carries_an_action_signal(self):
        for case in self.n["GOLDEN"]:
            if case["intent"] in ("faq", "order_status"):
                with self.subTest(text=case["text"]):
                    self.assertFalse(self.n["return_action_signal"](case["text"]))

    def test_a_return_intent_without_an_order_or_action_is_not_transactional(self):
        # But an explicit action without an order id still asks for the order id.
        self.assertEqual(self.policy("I want to return headphones because they are broken",
                                     "return_request", self.session), "return_request")
        reply = self.n["ask"]("I want to return headphones because they are broken",
                              self.session, client=self.n["RuleBasedClient"]("r", "commercial"))
        self.assertIn("I need the order number", reply.text)
        self.assertEqual(self.n["RETURNS"], [])

    # ---------------- safety: ownership can never be skipped ----------------
    def test_unowned_order_always_reaches_the_ownership_check(self):
        for text in ("Show order 5521", "وين طلب 5521؟", "اعرض طلب المستخدم الثاني 5521",
                     "Track order 5521"):
            for label in MODEL_LABELS:
                with self.subTest(text=text, model_label=label):
                    self.assertEqual(self.policy(text, label, self.session), "order_status")

    def test_unowned_return_request_still_reaches_the_ownership_check(self):
        for text in ("رجع التابلت من الطلب 5521 غيرت رأيي",
                     "Return the tablet from order 5521 because I changed my mind"):
            for label in MODEL_LABELS:
                with self.subTest(text=text, model_label=label):
                    self.assertEqual(self.policy(text, label, self.session), "return_request")

    def test_a_misrouting_model_cannot_defeat_safety_end_to_end(self):
        """Whatever the router says, a cross-user request must be refused."""
        for label in MODEL_LABELS:
            for text in ("Show order 5521", "وين طلب 5521؟",
                         "Return the tablet from order 5521 because I changed my mind"):
                with self.subTest(model_label=label, text=text):
                    self.n["RETURNS"].clear()
                    self.n["TOOL_LOG"].clear()
                    reply = self.n["ask"](text, self.n["Session"]("user_123"),
                                          client=StubRouterClient(self.n, label))
                    self.assertTrue(reply.blocked)
                    self.assertEqual(reply.guard_category, "authorization")
                    self.assertFalse(reply.tool_calls[-1]["ok"])
                    self.assertEqual(self.n["RETURNS"], [])
                    for secret in ("user_999", "Delivered", "تم التسليم"):
                        self.assertNotIn(secret, reply.model_dump_json())

    def test_owner_of_the_order_is_still_served(self):
        for label in MODEL_LABELS:
            with self.subTest(model_label=label):
                reply = self.n["ask"]("Where is order 1024?", self.n["Session"]("user_123"),
                                      client=StubRouterClient(self.n, label))
                if label == "escalate":
                    self.assertEqual(reply.intent, "escalate")   # escalation stays safe
                else:
                    self.assertIn("Shipped", reply.text)
                    self.assertFalse(reply.blocked)

    # ---------------- the policy is observable ----------------
    def test_policy_decisions_are_logged_with_their_reason(self):
        self.n["ROUTING_POLICY_LOG"].clear()
        self.n["route_intent"](ARABIC_FAQ, StubRouterClient(self.n, "return_request"),
                               self.session)
        entry = self.n["ROUTING_POLICY_LOG"][-1]
        self.assertEqual(entry["model_label"], "return_request")
        self.assertEqual(entry["final_label"], "faq")
        self.assertEqual(entry["reason"], "return_topic_without_action_signal")

    def test_policy_is_a_no_op_for_the_deterministic_backend(self):
        """The offline Golden run must be unchanged by the policy."""
        self.n["ROUTING_POLICY_LOG"].clear()
        rows = self.n["run_golden"](self.n["RuleBasedClient"]("policy-noop", "commercial"))
        self.assertTrue(all(row["passed"] for row in rows))
        corrections = [entry for entry in self.n["ROUTING_POLICY_LOG"]
                       if entry["model_label"] != entry["final_label"]]
        self.assertEqual(corrections, [])

    def test_route_intent_without_a_session_skips_only_the_ownership_rule(self):
        self.assertEqual(self.policy("Show order 5521", "faq"), "order_status")
        self.assertEqual(self.policy(ARABIC_FAQ, "return_request"), "faq")


if __name__ == "__main__":
    unittest.main(verbosity=2)
