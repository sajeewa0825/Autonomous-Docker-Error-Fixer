import json

def is_error_log(state):
    # print("🧩 is_error_log() received state keys:", list(state.keys()))
    data = state.get("analysis", {})
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return "ok"

    if isinstance(data, dict) and data.get("status") == "error":
        # print("🚨 Detected error in is_error_log()")
        return "error"
    return "ok"
