"""The 4 tools the agent can use. All data is fake."""
from datetime import date

from . import db

FAKE_TODAY = date(2025, 6, 1)
REFUND_WINDOW_DAYS = 30

POLICY_TEXT = (
    "Physical items can be refunded within 30 days of delivery. "
    "Digital products are not refundable. "
    "Orders that have not shipped can be cancelled for a full refund. "
    "Damaged or faulty items are handled by the support team through a ticket."
)

ORDERS = {
    "ORD-1001": {"status": "shipped", "items": [{"name": "Wireless Mouse", "price": 25}], "total": 25,
                 "placed": "2025-05-27", "tracking": "TRK881122", "eta": "2025-06-03", "digital": False},
    "ORD-1002": {"status": "delivered", "items": [{"name": "Mechanical Keyboard", "price": 80}], "total": 80,
                 "placed": "2025-05-15", "delivered": "2025-05-20", "digital": False},
    "ORD-1003": {"status": "processing", "items": [{"name": "Desk Lamp", "price": 40}], "total": 40,
                 "placed": "2025-05-31", "digital": False},
    "ORD-1004": {"status": "delivered", "items": [{"name": "USB Hub", "price": 30}], "total": 30,
                 "placed": "2025-02-24", "delivered": "2025-03-01", "digital": False},
    "ORD-1005": {"status": "cancelled", "items": [{"name": "Phone Case", "price": 15}], "total": 15,
                 "placed": "2025-05-10", "digital": False},
    "ORD-1006": {"status": "delivered", "items": [{"name": "Photo Editor License", "price": 60}], "total": 60,
                 "placed": "2025-05-25", "delivered": "2025-05-25", "digital": True},
    "ORD-1007": {"status": "shipped", "items": [{"name": "Standing Desk", "price": 300}], "total": 300,
                 "placed": "2025-05-10", "tracking": "TRK553300", "eta": "2025-05-25", "digital": False,
                 "note": "Delayed. Stuck at regional hub since 2025-05-22."},
    "ORD-1008": {"status": "delivered", "items": [{"name": "Headphones", "price": 120}], "total": 120,
                 "placed": "2025-05-27", "delivered": "2025-05-30", "digital": False},
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up an order by its order number (like ORD-1001). Returns status, items, tracking and dates.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "Order number, like ORD-1001"}},
            "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "check_refund_policy",
        "description": "Check the refund policy. With an order_id, also says if that order can be refunded. Without one, returns the general policy.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "Optional order number"}}}}},
    {"type": "function", "function": {
        "name": "create_ticket",
        "description": "Create a support ticket for the human team (refund requests, damaged items, bugs, late orders). Use once.",
        "parameters": {"type": "object", "properties": {
            "subject": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            "summary": {"type": "string", "description": "What the customer needs, with the order number if any"}},
            "required": ["subject", "priority", "summary"]}}},
    {"type": "function", "function": {
        "name": "handoff_to_human",
        "description": "Hand the conversation to a human agent. Use for legal threats, safety issues, fraud, angry customers, or when the customer asks for a person.",
        "parameters": {"type": "object", "properties": {
            "reason": {"type": "string"}}, "required": ["reason"]}}},
]


def _find_order(order_id):
    return ORDERS.get(str(order_id or "").strip().upper())


def lookup_order(order_id):
    order = _find_order(order_id)
    if not order:
        return {"found": False, "message": f"No order found with number {order_id}."}
    return {"found": True, "order_id": str(order_id).strip().upper(), **order}


def check_refund_policy(order_id=None):
    result = {"policy": POLICY_TEXT}
    if not order_id:
        return result
    order = _find_order(order_id)
    if not order:
        return {**result, "found": False, "message": f"No order found with number {order_id}."}
    status = order["status"]
    if status == "processing":
        eligible, reason = True, "Not shipped yet. It can be cancelled for a full refund."
    elif status == "cancelled":
        eligible, reason = False, "This order is already cancelled."
    elif status == "shipped":
        eligible, reason = False, "Not delivered yet. The 30-day refund window starts after delivery."
    elif order["digital"]:
        eligible, reason = False, "Digital products are not refundable."
    else:
        days = (FAKE_TODAY - date.fromisoformat(order["delivered"])).days
        if days <= REFUND_WINDOW_DAYS:
            eligible, reason = True, f"Delivered {days} days ago, inside the 30-day window."
        else:
            eligible, reason = False, f"Delivered {days} days ago, outside the 30-day window."
    return {**result, "found": True, "order_id": str(order_id).strip().upper(),
            "eligible": eligible, "reason": reason}


def create_ticket(ticket_id, subject, priority, summary):
    if priority not in ("low", "normal", "high"):
        priority = "normal"
    db.update_ticket(ticket_id, status="ticket_created", subject=subject, priority=priority, summary=summary)
    return {"created": True, "ticket_id": ticket_id, "message": "Ticket created. The team will follow up."}


def handoff_to_human(ticket_id, reason):
    db.update_ticket(ticket_id, status="handed_off", handoff_reason=reason)
    return {"handed_off": True, "message": "A human agent will take over this conversation."}


def run_tool(name, args, ticket_id):
    """Run one tool by name. Bad tool names or bad arguments return an error dict, never crash."""
    try:
        if name == "lookup_order":
            return lookup_order(**args)
        if name == "check_refund_policy":
            return check_refund_policy(**args)
        if name == "create_ticket":
            return create_ticket(ticket_id, **args)
        if name == "handoff_to_human":
            return handoff_to_human(ticket_id, **args)
        return {"error": f"Unknown tool: {name}"}
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
