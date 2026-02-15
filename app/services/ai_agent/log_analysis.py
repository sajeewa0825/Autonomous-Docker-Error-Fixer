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
    if not text:
        return {"status": "ok", "summary": "", "confidence": 0.5}

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
    return {"status": "ok", "summary": "", "confidence": 0.5}


def analyze_log_line(state):
    log_line = state["log_line"]
    container_name = state["container_name"]

    prompt = ChatPromptTemplate.from_template("""
You are a Docker log analysis AI.
Output ONLY JSON.

Rules:
- If log indicates error/failure/exception/timeout/crash -> status="error"
- else status="ok"
- Provide confidence in [0,1]

Log:
{log_line}

JSON:
{{
  "status": "error" | "ok",
  "summary": "<short summary>",
  "confidence": 0.0
}}
""")

    try:
        response = log_analyzer_llm.invoke(prompt.format(log_line=log_line))
        raw_output = (response.content or "").strip()
        data = safe_json_extract(raw_output)

        status = data.get("status", "ok")
        summary = data.get("summary", "")
        conf = float(data.get("confidence", 0.5))

        # fallback keyword
        if "error" in log_line.lower() and status == "ok":
            status = "error"
            summary = summary or "Detected error keyword in log."
            conf = max(conf, 0.65)

        if status == "error":
            print(f"[{container_name}] :🚨 Detected error: {summary} (conf={conf:.2f})")
        else:
            print(f"[{container_name}] :✅ Log OK")

        return {
            "analysis": json.dumps({"status": status, "summary": summary, "confidence": conf}),
            "status": status,
        }

    except Exception as e:
        print(f"[{container_name}] :⚠️ Analyzer error: {e}")
        return {"analysis": json.dumps({"status": "ok", "summary": "", "confidence": 0.5}), "status": "ok"}
