import json
import time


# region agent log
DEBUG_LOG_PATH = "/Users/nitinkanna/Documents/CreatorCampaignAnalyticsTool/.cursor/debug-bfc2c2.log"


def agent_debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    """
    Lightweight debug logger for the AI assistant.

    Writes a single NDJSON line to the shared debug log file. Never raises.
    Avoid logging PII or secrets in `data`.
    """
    payload = {
        "sessionId": "bfc2c2",
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data or {},
        "runId": run_id,
        "hypothesisId": hypothesis_id,
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # Never let debug logging break the app
        pass
# endregion

