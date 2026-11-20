import json
import os
import tempfile

# Use a throwaway database for tests. This must happen before the app is imported.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from dotenv import load_dotenv  # noqa: E402

load_dotenv()  # gets OPENAI_API_KEY from .env (DB_PATH is already set, so it is kept)

import pytest  # noqa: E402


def pytest_configure(config):
    config.case_log = []


@pytest.fixture
def case_log(request):
    return request.config.case_log


def pytest_terminal_summary(terminalreporter, config):
    log = config.case_log
    if not log:
        return
    ok = sum(c["passed"] for c in log)
    cost = sum(c["cost_usd"] for c in log)
    avg_ms = sum(c["duration_ms"] for c in log) // len(log)
    terminalreporter.write_sep("=", f"Handled {ok} of {len(log)} correctly")
    terminalreporter.write_line(f"Total cost: ${cost:.4f} | Average time: {avg_ms} ms | Model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({"handled_correctly": ok, "total": len(log), "total_cost_usd": round(cost, 4),
                   "avg_duration_ms": avg_ms, "cases": log}, f, indent=2)
    terminalreporter.write_line("Details saved to results.json")
