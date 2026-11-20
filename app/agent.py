"""The agent loop: ask the model, run the tools it picks, repeat, with a step limit."""
import json
import os
import time

from openai import OpenAI

from . import db, tools

MAX_STEPS = 6  # max number of model calls per customer message

# USD per 1 million tokens (input, output). Check OpenAI's pricing page for current numbers.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60), "gpt-4o": (2.50, 10.00)}

SYSTEM_PROMPT = """You are a customer support agent for an online shop. Today's date is 2025-06-01.
Tools: lookup_order, check_refund_policy, create_ticket, handoff_to_human.

Rules:
- Never invent order details. Only state facts that tools returned.
- If the customer asks about an order but gives no order number (like ORD-1234), ask for it. Do not use tools yet.
- Order status or tracking questions: call lookup_order, then answer.
- Refund requests: call check_refund_policy with the order number.
  If eligible, call create_ticket (priority normal, summary with the order number and reason) so the billing team processes it, then tell the customer.
  If not eligible, explain why politely and do not create a ticket.
- General policy questions (no order): call check_refund_policy without an order_id and explain.
- Problems you cannot fix yourself (damaged item, website bugs, address changes, late orders the customer wants investigated): call create_ticket.
- Call handoff_to_human for legal threats, safety issues, fraud or hacked accounts, requests for a human or manager, or a very upset customer.
- Keep replies short, friendly, plain text. Call create_ticket or handoff_to_human at most once."""


def _cost(model, usage):
    price_in, price_out = PRICES.get(model, PRICES["gpt-4o-mini"])
    return (usage.prompt_tokens * price_in + usage.completion_tokens * price_out) / 1_000_000


def run_agent(ticket_id, message, client=None):
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}]
    started = time.perf_counter()
    total_cost, model_calls, seq, reply = 0.0, 0, 0, None

    for _ in range(MAX_STEPS):
        t0 = time.perf_counter()
        try:
            client = client or OpenAI()
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=tools.TOOL_SCHEMAS, temperature=0
            )
        except Exception as e:  # network error, bad key, rate limit...
            seq += 1
            db.add_step(ticket_id, seq, "error", model, None, f"{type(e).__name__}: {e}",
                        int((time.perf_counter() - t0) * 1000))
            tools.run_tool("handoff_to_human", {"reason": f"AI model error: {type(e).__name__}"}, ticket_id)
            reply = "Sorry, something went wrong on our side. A human agent will follow up."
            break

        model_calls += 1
        step_cost = _cost(model, resp.usage)
        total_cost += step_cost
        msg = resp.choices[0].message
        seq += 1
        db.add_step(
            ticket_id, seq, "model", model,
            json.dumps({"messages_in_context": len(messages)}),
            msg.content if not msg.tool_calls else "Wants to call: " + ", ".join(c.function.name for c in msg.tool_calls),
            int((time.perf_counter() - t0) * 1000), step_cost,
        )

        if not msg.tool_calls:
            reply = msg.content
            break

        messages.append({
            "role": "assistant", "content": msg.content,
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in msg.tool_calls],
        })
        for call in msg.tool_calls:
            t1 = time.perf_counter()
            try:
                args = json.loads(call.function.arguments or "{}")
                result = tools.run_tool(call.function.name, args, ticket_id)
            except json.JSONDecodeError:
                args, result = call.function.arguments, {"error": "Arguments were not valid JSON"}
            seq += 1
            db.add_step(ticket_id, seq, "tool", call.function.name, json.dumps(args), json.dumps(result),
                        int((time.perf_counter() - t1) * 1000))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    else:
        # Loop ended without a final answer: the step limit was hit.
        seq += 1
        db.add_step(ticket_id, seq, "error", "step_limit", None, f"Stopped after {MAX_STEPS} model calls", 0)
        tools.run_tool("handoff_to_human", {"reason": f"Step limit reached ({MAX_STEPS})"}, ticket_id)
        reply = "I couldn't finish this on my own, so I'm passing it to a human agent."

    ticket = db.get_ticket(ticket_id)
    status = ticket["status"] if ticket["status"] != "open" else "resolved"
    db.update_ticket(
        ticket_id, status=status, final_reply=reply, steps_used=model_calls,
        cost_usd=round(total_cost, 6), duration_ms=int((time.perf_counter() - started) * 1000),
    )
    return {"status": status, "reply": reply}
