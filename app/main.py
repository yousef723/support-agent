import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv()

from . import db  # noqa: E402
from .agent import run_agent  # noqa: E402

app = FastAPI(title="Support Agent API")
db.init_db()
if os.getenv("DEMO_API_KEY"):  # lets a deployed server start with one known business
    db.ensure_business("Demo Shop", os.getenv("DEMO_API_KEY"))


def get_business(x_api_key: str = Header(default=None)):
    business = db.get_business_by_key(x_api_key) if x_api_key else None
    if not business:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return business


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/messages")
def send_message(body: MessageIn, business: dict = Depends(get_business)):
    ticket_id = db.create_ticket_row(business["id"], body.message)
    run_agent(ticket_id, body.message)
    t = db.get_ticket(ticket_id, business["id"])
    return {
        "ticket_id": ticket_id,
        "status": t["status"],
        "reply": t["final_reply"],
        "steps_used": t["steps_used"],
        "cost_usd": t["cost_usd"],
        "duration_ms": t["duration_ms"],
        "trace_url": f"/trace#ticket-{ticket_id}",
    }


@app.get("/v1/tickets")
def list_tickets(business: dict = Depends(get_business)):
    return db.list_tickets(business["id"])


@app.get("/v1/tickets/{ticket_id}")
def get_ticket(ticket_id: int, business: dict = Depends(get_business)):
    ticket = db.get_ticket(ticket_id, business["id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {**ticket, "steps": db.get_steps(ticket_id)}


@app.get("/trace", include_in_schema=False)
def trace_page():
    return FileResponse(Path(__file__).parent / "static" / "trace.html")
