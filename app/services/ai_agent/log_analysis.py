from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.core.loadenv import Settings
import json
import re

log_analyzer_llm = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=0,
    api_key=Settings.GROQ_API_KEY,
)

def safe_json_extract(text: str):
    """Extract and parse the first JSON object from model output safely."""
    if not text:
        return {"status": "ok", "summary": ""}
    
    # Remove ```json fences if present
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {"status": "ok", "summary": ""}


def analyze_log_line(state):
    log_line = state["log_line"]

    prompt = ChatPromptTemplate.from_template("""
    You are a Docker log analysis AI.
    Analyze the given log line and output ONLY JSON (no markdown or text).

    If the line shows any sign of error (error, fail, exception, timeout, crash, etc),
    set "status": "error". Otherwise, "status": "ok".

    Log:
    {log_line}

    Response JSON format:
    {{
      "status": "error" | "ok",
      "summary": "<short human-readable summary>"
    }}
    """)

    try:
        response = log_analyzer_llm.invoke(prompt.format(log_line=log_line))
        raw_output = (response.content or "").strip()
        data = safe_json_extract(raw_output)

        status = data.get("status", "ok")
        summary = data.get("summary", "")

        # 🚨 Simple fallback detection (if LLM failed but log clearly has "error")
        if "error" in log_line.lower() and status == "ok":
            status = "error"
            summary = summary or "Detected error keyword in log."

        if status == "error":
            print(f"🚨 Detected error: {summary}")

        return {"analysis": json.dumps({"status": status, "summary": summary}), "status": status}

    except Exception as e:
        print(f"⚠️ Error analyzing (analyzer) log: {e}")
        return {"analysis": json.dumps({"status": "ok", "summary": ""}), "status": "ok"}
