"""Fast tests that do not call the AI."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agent, db, main, tools

client = TestClient(main.app)


def fake_agent(ticket_id, message):
    db.update_ticket(ticket_id, status="resolved", final_reply="fake reply")


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setattr(main, "run_agent", fake_agent)
    return db.create_business("Shop A"), db.create_business("Shop B")


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_or_wrong_key_is_rejected(keys):
    assert client.post("/v1/messages", json={"message": "hi"}).status_code == 401
    assert client.post("/v1/messages", json={"message": "hi"}, headers={"X-API-Key": "nope"}).status_code == 401


def test_empty_message_is_rejected(keys):
    assert client.post("/v1/messages", json={"message": ""}, headers={"X-API-Key": keys[0]}).status_code == 422


def test_business_cannot_see_another_businesss_ticket(keys):
    key_a, key_b = keys
    ticket_id = client.post("/v1/messages", json={"message": "hi"}, headers={"X-API-Key": key_a}).json()["ticket_id"]
    assert client.get(f"/v1/tickets/{ticket_id}", headers={"X-API-Key": key_a}).status_code == 200
    assert client.get(f"/v1/tickets/{ticket_id}", headers={"X-API-Key": key_b}).status_code == 404
    assert all(t["id"] != ticket_id for t in client.get("/v1/tickets", headers={"X-API-Key": key_b}).json())


def test_refund_policy_tool():
    assert tools.check_refund_policy("ORD-1002")["eligible"] is True      # delivered 12 days ago
    assert tools.check_refund_policy("ORD-1004")["eligible"] is False     # 92 days ago
    assert tools.check_refund_policy("ORD-1006")["eligible"] is False     # digital
    assert tools.check_refund_policy("ORD-9999")["found"] is False


def test_unknown_tool_does_not_crash():
    assert "error" in tools.run_tool("delete_everything", {}, 1)


def test_step_limit_hands_off_to_human():
    """A model that never stops calling tools must be cut off at MAX_STEPS."""
    call = SimpleNamespace(id="c1", function=SimpleNamespace(name="lookup_order", arguments='{"order_id": "ORD-1001"}'))
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )
    looping = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: response)))

    business_key = db.create_business("Loop Shop")
    ticket_id = db.create_ticket_row(db.get_business_by_key(business_key)["id"], "hello")
    agent.run_agent(ticket_id, "hello", client=looping)

    ticket = db.get_ticket(ticket_id)
    assert ticket["status"] == "handed_off"
    assert ticket["steps_used"] == agent.MAX_STEPS
    assert "Step limit" in ticket["handoff_reason"]
