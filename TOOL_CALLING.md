# Native model-issued tool calling

Raqmi accepts real function calls from the provider: the model emits `tool_calls`, the application validates and authorizes them, executes the tool itself, and returns the result as a `role: tool` message for the model to answer from.

**Authorization is not delegated to the LLM.** The model chooses *which tool to propose*. It never decides whether the call is allowed. Session identity comes from application state, ownership is checked by `Session.authorize_order()`, product membership is checked against the authorized order, and the return id is minted by the application. The argument schemas forbid unknown fields, so a model-supplied `user_id`, `customer_id` or consent flag is rejected outright rather than ignored.

## The proved pipeline

```text
user message
 ↓ guard stages 1-4 (normalize, injection guard, PII mask, safety classifier)
model issues a native tool_call                ← the model's only decision
 ↓
provider envelope normalization                ← copy id, type, function.name, function.arguments
 ↓
tool whitelist                                 ← lookup_order | create_return | escalate_to_human
 ↓
strict Pydantic argument validation            ← extra="forbid", strict=True
 ↓
catalogue-controlled product canonicalization  ← NFKC, casefold, collapsed whitespace, catalogue aliases
 ↓
Session.authorize_order(order_id)              ← deterministic application code
 ↓
canonical product ∈ authorized order's items
 ↓
side-effect execution
 ↓
idempotency on (customer, order, canonical product)
 ↓
role: tool result (identity fields stripped)
 ↓
model writes the final user-facing answer
```

`raqmi_tool_calling.py` is the reviewable copy of the code; the notebook embeds a byte-identical copy in cell `raqmi-tools-module` so a standalone Colab upload needs no second file. `scripts/sync_tool_module.py --check` and a test both fail if the two drift.

| Tool | Risk class | Application control |
|---|---|---|
| `lookup_order(order_id)` | `read_only` | session must own the order |
| `create_return(order_id, product, reason, language, needs_human)` | `side_effect` | ownership, item membership, application consent, idempotent replay |
| `escalate_to_human(reason)` | `terminal` | always allowed; ends the loop immediately |

## Envelope normalization — permissive envelope, strict arguments

OpenAI-compatible providers decorate each tool call with fields of their own; DeepSeek attaches an `index`. An envelope model declared `extra="forbid"` rejected the whole call because of it, before the tool name was ever read.

`normalize_tool_call()` therefore copies **only** the four fields the application consumes — `id`, `type`, `function.name`, `function.arguments` — out of whatever the provider sent. It accepts mappings and attribute-style SDK objects, re-serializes already-parsed argument objects, defaults a missing `type`, and synthesizes an id when one is absent. Genuinely malformed envelopes are still refused.

**This relaxes the envelope only.** Tool arguments still go through the strict per-tool schema afterwards, so unknown fields, wrong types and bad patterns remain rejected. Refusals are specific — `invalid_tool_envelope`, `unknown_tool`, `duplicate_call_id`, `invalid_tool_arguments` — and the audit log carries the real tool name and risk class even when a call is refused. `record_tool_diagnostic()` keeps a safe record of the envelope shape and the Pydantic errors; it never touches request headers, credentials or system prompts.

## Product canonicalization

A model may write a catalogue item in any presentation: `Headphones`, `HEADPHONES`, `  headphones  `, full-width characters, or the Arabic `سماعة رأس`. `canonicalize_product()` resolves these to one catalogue SKU using Unicode NFKC, `casefold()` and collapsed whitespace, matched against an identity map built **only** from catalogue SKUs, Arabic names, English names and the catalogue's own alias list.

It is catalogue-controlled, not fuzzy: an unknown value raises `unknown_product`, a malformed one `invalid_product`, and two catalogue entries that would collide raise `ambiguous_catalog_product`. A model cannot invent a product or widen the catalogue. Canonicalization runs **after** strict validation and **before** authorization, and the order's own items are canonicalized on the same path, so membership compares like with like. The idempotency key uses the canonical identity, so casing variants cannot create a second return.

## Bounds and idempotency

One tool call per provider response; `max_iterations` and `max_tool_calls` ceilings validated on entry; repeated `tool_call.id` rejected; **one open return per `(customer, order, canonical product)`**, so a retry replays the original return id instead of writing a second record, within a run and across runs. A second distinct return in one run is refused rather than executed. Provider and transport failures are sanitized into application categories, and a failure after a completed transaction still reports the transaction.

## Final LIVE evidence

From the official executed notebook, section *Native Tool Calling — Live Evidence* against `deepseek-v4-flash`:

| Scenario | Result |
|---|---|
| **Authorized lookup** — order 1024, owned | **PASS** — model issued `lookup_order`, application executed it, `role: tool` result returned, model wrote the final answer |
| **Cross-user lookup** — order 5521, another customer | **DENIED by authorization** — `authorization_denied`; nothing executed; no other customer's data in the reply |
| **Authorized return** — order 1024, headphones, defective | **PASS** — model issued `lookup_order` then `create_return` |
| `returns_created` | **1** |
| `return_id` | **R-1001** |
| canonical product | **`headphones`** |
| tool-call diagnostics | none recorded — every provider tool call validated |

In that run DeepSeek looked the order up first and then emitted the product already lowercased, so `product_input` and `product_canonical` were both `headphones`. The case-mismatch path that previously failed is proven deterministically by the offline scripted transcript, which sends the exact `Headphones` spelling DeepSeek used earlier and prints `product canonicalization: 'Headphones' -> 'headphones'` before executing.

System prompts are withheld from every printed transcript, and request headers — which carry the API key — are never recorded.

## Offline coverage

The notebook's scripted sections run on every Run all with no key: three full transcripts plus negative and bounds checks for unknown tools, malformed arguments, cross-user return, model-supplied identity, duplicate replay, iteration and tool-call limits, and the terminal tool.

`tests/test_tool_calling.py` (124 tests) covers the required A–H scenarios by name, the provider envelope including the exact `index`-carrying shape that once failed, and the guard-pipeline integration. `tests/test_product_canonicalization.py` covers presentation variants, unknown/ambiguous/malformed values, wrong item, cross-user order, normalized retry idempotency, and that unrelated products keep distinct identities.

## Not claimed

**ALLaM's native tool-call parsing was never exercised.** The live tool section targets DeepSeek only; ALLaM is evaluated through the router path in the backend comparison.
