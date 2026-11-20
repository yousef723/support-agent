"""Sends the 30 messages through the real API and the real AI model, then checks the results."""
import os

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from tests.cases import CASES

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not set")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def headers():
    return {"X-API-Key": db.create_business("Test Shop")}


@pytest.mark.parametrize("case", CASES, ids=[f"{i + 1:02d}" for i in range(len(CASES))])
def test_agent_case(case, client, headers, case_log):
    r = client.post("/v1/messages", json={"message": case["message"]}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    detail = client.get(f"/v1/tickets/{data['ticket_id']}", headers=headers).json()
    used = [s["name"] for s in detail["steps"] if s["kind"] == "tool"]

    problems = []
    if data["status"] not in case["status"]:
        problems.append(f"status was {data['status']}, wanted one of {case['status']}")
    for tool in case.get("must_call", []):
        if tool not in used:
            problems.append(f"did not call {tool}")
    for tool in case.get("must_not_call", []):
        if tool in used:
            problems.append(f"should not have called {tool}")
    if not data["reply"]:
        problems.append("empty reply")

    case_log.append({"message": case["message"], "passed": not problems, "status": data["status"],
                     "tools_used": used, "problems": problems, "cost_usd": data["cost_usd"],
                     "duration_ms": data["duration_ms"]})
    assert not problems, "; ".join(problems) + f" | tools used: {used} | reply: {data['reply']}"
