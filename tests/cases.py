"""30 test messages. 'status' lists the accepted outcomes. 'must_call' tools have to be used.
'must_not_call' tools must not be used."""

R, T, H = "resolved", "ticket_created", "handed_off"

CASES = [
    # --- Order status (10) ---
    {"message": "Where is my order ORD-1001?", "status": [R], "must_call": ["lookup_order"]},
    {"message": "Can you track order ORD-1007? It is very late.", "status": [R, T], "must_call": ["lookup_order"]},
    {"message": "status of ord-1003 please", "status": [R], "must_call": ["lookup_order"]},
    {"message": "Has ORD-1002 been delivered yet?", "status": [R], "must_call": ["lookup_order"]},
    {"message": "What is in my order ORD-1008?", "status": [R], "must_call": ["lookup_order"]},
    {"message": "Where is my order?", "status": [R],
     "must_not_call": ["lookup_order", "create_ticket", "handoff_to_human"]},
    {"message": "Hi, I need help with my order.", "status": [R],
     "must_not_call": ["create_ticket", "handoff_to_human"]},
    {"message": "Can you check order ORD-9999 for me?", "status": [R], "must_call": ["lookup_order"]},
    {"message": "Is ORD-1005 still coming?", "status": [R], "must_call": ["lookup_order"]},
    {"message": "When will ORD-1001 arrive?", "status": [R], "must_call": ["lookup_order"]},
    # --- Refund allowed: ticket expected (5) ---
    {"message": "I want a refund for ORD-1002, the keyboard is not what I expected.", "status": [T],
     "must_call": ["check_refund_policy", "create_ticket"]},
    {"message": "Please refund order ORD-1008.", "status": [T],
     "must_call": ["check_refund_policy", "create_ticket"]},
    {"message": "Refund ORD-1003, I changed my mind.", "status": [T],
     "must_call": ["check_refund_policy", "create_ticket"]},
    {"message": "I would like my money back for ORD-1002.", "status": [T],
     "must_call": ["check_refund_policy", "create_ticket"]},
    {"message": "I want to return ORD-1008 and get a refund.", "status": [T],
     "must_call": ["check_refund_policy", "create_ticket"]},
    # --- Refund not allowed: no ticket (4) ---
    {"message": "I want a refund for ORD-1004.", "status": [R],
     "must_call": ["check_refund_policy"], "must_not_call": ["create_ticket"]},
    {"message": "Refund my software license, order ORD-1006.", "status": [R],
     "must_call": ["check_refund_policy"], "must_not_call": ["create_ticket"]},
    {"message": "Can I get a refund on ORD-1005?", "status": [R],
     "must_call": ["check_refund_policy"], "must_not_call": ["create_ticket"]},
    {"message": "I want a refund for ORD-1001.", "status": [R],
     "must_call": ["check_refund_policy"], "must_not_call": ["create_ticket"]},
    # --- Policy questions (2) ---
    {"message": "What is your refund policy?", "status": [R], "must_call": ["check_refund_policy"]},
    {"message": "How many days do I have to return something?", "status": [R],
     "must_call": ["check_refund_policy"]},
    # --- Needs a ticket (4) ---
    {"message": "My headphones from ORD-1008 arrived with a cracked ear cup. I need a replacement.",
     "status": [T], "must_call": ["create_ticket"]},
    {"message": "The website crashes every time I try to pay. Please report this.", "status": [T],
     "must_call": ["create_ticket"]},
    {"message": "ORD-1007 is two weeks late. Please open a ticket for this.", "status": [T],
     "must_call": ["create_ticket"]},
    {"message": "Please change the delivery address on ORD-1003 to 12 Baker Street.", "status": [T, H]},
    # --- Hand off to a human (5) ---
    {"message": "I am going to sue your company if this is not fixed today.", "status": [H],
     "must_call": ["handoff_to_human"]},
    {"message": "Let me talk to a real person right now.", "status": [H], "must_call": ["handoff_to_human"]},
    {"message": "Someone hacked my account and used my card to order things.", "status": [H],
     "must_call": ["handoff_to_human"]},
    {"message": "This is the third time you have ignored me. I want a manager.", "status": [H],
     "must_call": ["handoff_to_human"]},
    {"message": "The heater I bought caught fire and burned my table.", "status": [H],
     "must_call": ["handoff_to_human"]},
]

assert len(CASES) == 30
