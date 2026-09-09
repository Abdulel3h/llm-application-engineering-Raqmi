# Optional native tool-calling protocol

The uploaded live notebook proves provider HTTP routing and application-dispatched tools. It does not prove native function calling: the adapter sends system/user messages without a `tools` field, and `ask()` invokes Python functions after parsing the router result. Return extraction similarly validates a Python candidate before calling the model and ignores the model response.

`raqmi_tool_calling.py` is a post-capture, opt-in implementation of the missing protocol. It is designed to bind to the notebook namespace rather than duplicate the domain data or bypass the existing `LLMClient` boundary.

For each request it:

1. Sends three OpenAI-compatible function definitions: `lookup_order`, `create_return`, and `escalate_to_human`.
2. Accepts at most one model-emitted tool call per response and validates its JSON arguments with strict Pydantic schemas (`extra="forbid"`).
3. Supplies the authenticated `Session` from application state; the model cannot provide or override the user ID.
4. Executes ownership and product checks before reads or side effects, logs risk class and loop iteration, and passes a sanitized result as a `role: tool` message.
5. Requires an application-supplied `allow_return=True` consent boolean for a side-effecting return; model arguments cannot provide that consent.
6. Stops terminal escalation immediately, reuses a completed return result on duplicate replay, and bounds iterations, tool calls, batch size, and transaction side effects.
7. Sanitizes provider and transport failures into application categories without echoing private exception text.

The protocol can be exercised with a namespace created from the notebook definitions:

```python
from raqmi_tool_calling import bind_tool_client, ask_with_native_tools

client = bind_tool_client(namespace, route="commercial")
reply = ask_with_native_tools(
    "Return the headphones from order 1024 because they are defective",
    Session("user_123"), namespace=namespace, client=client, allow_return=True,
)
```

The test suite scripts provider responses and never sends a real request. It checks tool schemas, tool-result messages, ownership denials, wrong-item denials, malformed/unknown arguments, terminal escalation, duplicate calls, bounded loops, one-return-per-run behavior, sanitized failures, application consent for side effects, trusted FAQ templates, and all three risk classes. It also checks that an untrusted `user_id` or model-supplied consent argument cannot execute.

This module was added after the captured DeepSeek/ALLaM comparison. Its offline tests are evidence for the protocol implementation only; they do not change or retroactively validate the notebook's LIVE scores. A final submission claiming full native function-calling coverage still needs a fresh provider-backed transcript and a language-split extraction/repair evaluation.
