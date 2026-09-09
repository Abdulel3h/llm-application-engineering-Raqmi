"""Catalog-controlled product identity checks at the native tool boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from raqmi_tool_calling import (  # noqa: E402
    ask_with_native_tools,
    bind_tool_client,
    canonicalize_product,
)
from tests.notebook_runtime import build_namespace  # noqa: E402


def completion(*calls, text=None):
    return {"model": "product-test", "choices": [{"message": {
        "role": "assistant", "content": text, "tool_calls": list(calls),
    }}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def tool_call(name, arguments, call_id="call-product"):
    return {"id": call_id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(arguments, ensure_ascii=False),
    }}


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, url, payload, headers):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class ProductCanonicalizationTests(unittest.TestCase):
    def setUp(self):
        self.module_name = "_raqmi_product_identity_runtime"
        self.ns = build_namespace(module_name=self.module_name)
        for name in ("RETURNS", "ESCALATIONS", "TOOL_LOG", "MODEL_CALL_LOG"):
            self.ns[name].clear()
        self.session = self.ns["Session"]("user_123")

    def tearDown(self):
        sys.modules.pop(self.module_name, None)

    def canonical(self, value):
        return canonicalize_product(value, catalog=self.ns["CATALOG"],
                                     aliases=self.ns["ALIASES"])

    def run_return(self, product, *, order_id="1024", user="user_123"):
        transport = ScriptedTransport([
            completion(tool_call("create_return", {
                "order_id": order_id, "product": product,
                "reason": "defective", "language": "en", "needs_human": False,
            })),
            completion(text="done"),
        ])
        client = bind_tool_client(
            self.ns, route="commercial", base_url="https://example.test/v1",
            model_id="product-test", transport=transport,
        )
        reply = ask_with_native_tools(
            "Return the item from my order because it is defective",
            self.ns["Session"](user), namespace=self.ns, client=client,
            allow_return=True,
        )
        return reply

    def test_presentation_variants_resolve_to_one_catalog_sku(self):
        self.assertEqual(self.canonical(" headphones "), "headphones")
        self.assertEqual(self.canonical("HEADPHONES"), "headphones")
        self.assertEqual(self.canonical("\uff28\uff45\uff41\uff44\uff50\uff48\uff4f\uff4e\uff45\uff53"),
                         "headphones")
        self.assertEqual(self.canonical("  سماعة   رأس "), "headphones")

    def test_unknown_ambiguous_and_malformed_values_fail_closed(self):
        for value in ("mystery product", "\x00headphones", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.canonical(value)
        ambiguous = {
            "one": {"ar": "مشترك", "en": "Shared"},
            "two": {"ar": "مشترك", "en": "Other"},
        }
        with self.assertRaisesRegex(ValueError, "ambiguous_catalog_product"):
            canonicalize_product("shared", catalog=ambiguous)

    def test_authorized_native_return_accepts_model_capitalization_and_spacing(self):
        reply = self.run_return("  Headphones  ")
        self.assertFalse(reply.blocked)
        self.assertEqual(len(self.ns["RETURNS"]), 1)
        self.assertEqual(self.ns["RETURNS"][0]["product"], "headphones")
        self.assertEqual(reply.tool_calls[-1]["product_input"], "  Headphones  ")
        self.assertEqual(reply.tool_calls[-1]["product_canonical"], "headphones")

    def test_unknown_product_is_rejected_before_authorization_or_mutation(self):
        reply = self.run_return("mystery product")
        self.assertTrue(reply.blocked)
        self.assertEqual(reply.guard_category, "invalid_product")
        self.assertEqual(self.ns["RETURNS"], [])

    def test_wrong_item_and_cross_user_order_remain_denied(self):
        wrong_item = self.run_return("TABLET")
        self.assertTrue(wrong_item.blocked)
        self.assertEqual(wrong_item.guard_category, "authorization")
        self.assertEqual(self.ns["RETURNS"], [])

        cross_user = self.run_return(" tablet ", order_id="5521", user="user_123")
        self.assertTrue(cross_user.blocked)
        self.assertEqual(cross_user.guard_category, "authorization")
        self.assertEqual(self.ns["RETURNS"], [])

    def test_normalized_retries_reuse_one_return_id_across_runs(self):
        first = self.run_return("Headphones")
        return_id = self.ns["RETURNS"][0]["return_id"]
        second = self.run_return("  headphones  ")
        self.assertFalse(first.blocked)
        self.assertFalse(second.blocked)
        self.assertEqual(len(self.ns["RETURNS"]), 1)
        self.assertEqual(self.ns["RETURNS"][0]["return_id"], return_id)
        self.assertEqual(second.tool_calls[-1]["detail"], "reused_result")

    def test_unrelated_products_keep_distinct_identities_and_records(self):
        self.assertNotEqual(self.canonical("keyboard"), self.canonical("mouse"))
        first = self.run_return("keyboard", order_id="1025")
        second = self.run_return("mouse", order_id="1025")
        self.assertFalse(first.blocked)
        self.assertFalse(second.blocked)
        self.assertEqual([record["product"] for record in self.ns["RETURNS"]],
                         ["keyboard", "mouse"])
        self.assertEqual([record["return_id"] for record in self.ns["RETURNS"]],
                         ["R-1001", "R-1002"])


if __name__ == "__main__":
    unittest.main()
