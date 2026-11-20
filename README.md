# AI Customer Support Agent API

Python, FastAPI, PostgreSQL, Docker, OpenAI API, pytest, GitHub Actions

A FastAPI service where a business sends a customer message and an AI agent (OpenAI) answers it.
The agent can use 4 tools: look up an order, check the refund policy, create a ticket, or hand off to a human.
Every model call and tool call is saved, so a person can open a trace page and see why the agent acted.
Each business has its own API key and can only see its own tickets.
All data is fake.

## Results

- Handled **39 of 40** test messages correctly (30 standard cases and 10 harder ones)
- Model: gpt-4o-mini
- Total cost for the 40 messages: **$0.0092**
- Average time per message: **4.2 s**
- First run on all 40 gave 38 of 40. The two failures showed real weaknesses (strict order-number matching and a missed safety rule). I fixed both and ran again.
- One known miss: for "Is ORD-1005 still coming?" the agent asked for an order number that was already in the message.
- Results vary slightly between runs because the model is not fully deterministic. The fixes were made after seeing the failures, so the final score is closer to a regression check than a fresh test.
- I wrote the test messages together with the agent's rules, so a high score does not mean it would handle every real customer message.
## How it works

1. `POST /v1/messages` with an `X-API-Key` header. The key identifies the business.
2. A ticket row is created. The agent loop starts.
3. The agent asks the model what to do. If the model picks a tool, the tool runs and the result goes back to the model.
4. This repeats until the model gives a final answer or the **step limit (6 model calls)** is reached. If the limit is hit, the ticket is handed to a human.
5. Every step, its time and its cost are saved in PostgreSQL. Open `/trace` to see them.

Tools (`app/tools.py`): `lookup_order`, `check_refund_policy`, `create_ticket`, `handoff_to_human`.

Ticket outcomes: `resolved`, `ticket_created`, `handed_off`.

## Run it with Docker (API + PostgreSQL)

```
copy .env.example .env        (then set OPENAI_API_KEY and DEMO_API_KEY in .env)
docker compose up --build
```

Open http://127.0.0.1:8000/docs. The demo business's API key is the `DEMO_API_KEY` from your `.env`.

```
curl -X POST http://127.0.0.1:8000/v1/messages -H "X-API-Key: YOUR_DEMO_API_KEY" -H "Content-Type: application/json" -d "{\"message\": \"Where is my order ORD-1001?\"}"
```

Then open http://127.0.0.1:8000/trace, paste your key, and click a ticket.

## Run it without Docker

Without `DATABASE_URL`, the app uses a local SQLite file, so no database server is needed.

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        (then put your OpenAI key in .env)
python -m app.create_business "Acme Shop"
uvicorn app.main:app --reload
```

To use PostgreSQL here too, set `DATABASE_URL=postgresql://user:password@localhost:5432/dbname` in `.env`.

## Tests

```
pytest -v
```

- `tests/test_api.py`: fast tests with no AI (API keys, business isolation, refund rules, step limit).
- `tests/test_agent_cases.py`: 40 customer messages sent to the real model. Each one checks the final outcome and which tools were used or not used.

GitHub Actions runs the fast tests on every push against a real PostgreSQL database. The 40 real-model messages cost a little money, so they run by hand: Actions, then CI, then Run workflow (needs an `OPENAI_API_KEY` repository secret).

## Live demo

URL: 

## Limits (on purpose)

- Fake orders only, in code. No real payments or refunds: the agent creates a ticket for a human.
- A new database connection is opened for each query. That is fine for a demo; a busy deployment would use a connection pool.
- The test messages were written by me together with the agent's rules, so a high score does not mean it would handle every real customer message.
