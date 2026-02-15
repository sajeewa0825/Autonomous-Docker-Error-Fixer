from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.core.loadenv import Settings

import json
import re

from app.services.ai_agent.tools.Rag_retriever import retrieve_context_tool
from app.services.ai_agent.tools.web_search import web_search

tools = [retrieve_context_tool, web_search]

llm = ChatGroq(
    model=Settings.MODEL_NAME,
    temperature=Settings.TEMPERATURE,
    api_key=Settings.GROQ_API_KEY,
)

def safe_json_extract(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}

def _tool_call_safely(tool, **kwargs):
    if hasattr(tool, "invoke"):
        return tool.invoke(kwargs)
    if hasattr(tool, "run"):
        return tool.run(**kwargs)
    raise RuntimeError("Tool interface not supported")

def _fallback_command(log_line: str, container_name: str) -> tuple[str, str]:
    """
    Always returns a safe single command + reason.
    """
    s = (log_line or "").lower()

    # Disk full
    if "no space left on device" in s or "disk full" in s:
        return ("docker system prune -f --volumes", "Disk full pattern; prune is standard recovery.")
    # Port conflict
    if "port is already allocated" in s or "bind: address already in use" in s:
        return (f'client.containers.get("{container_name}").restart()', "Port conflict likely resolved by restarting container.")
    # OOM / killed
    if "oomkilled" in s or "exited (137)" in s:
        return (f'client.containers.get("{container_name}").restart()', "OOM pattern; restart is standard first action.")
    # Default safest fallback
    return (f'client.containers.get("{container_name}").restart()', "Fallback safe action: restart container.")

def llm_call(state):
    log_line = state["log_line"]
    container_name = state["container_name"]

    # analyzer summary/conf
    try:
        analysis_data = json.loads(state.get("analysis", "{}"))
    except Exception:
        analysis_data = {}
    log_summary = analysis_data.get("summary", "")
    analyzer_conf = float(analysis_data.get("confidence", 0.6))

    # env threshold
    approval_threshold = float(getattr(Settings, "APPROVAL_THRESHOLD", 0.75))

    # 1) RAG FIRST
    rag_context = ""
    try:
        rag_out = _tool_call_safely(retrieve_context_tool, query=log_line)
        rag_context = rag_out if isinstance(rag_out, str) else json.dumps(rag_out)
    except Exception:
        rag_context = ""

    # 2) Web only if rag empty
    web_context = ""
    if not rag_context.strip():
        try:
            web_out = _tool_call_safely(web_search, query=log_line)
            web_context = web_out if isinstance(web_out, str) else json.dumps(web_out)
        except Exception:
            web_context = ""

    prompt = ChatPromptTemplate.from_template("""
You are a Docker auto-repair AI agent in production.

Your job: for every error, ALWAYS recommend exactly ONE executable fix command.
Never output NO_ACTION_RECOMMENDED.

Decision order (strict):
1) RAG FIRST: If RAG context contains a matching error signature AND a fix command,
   output ONLY that exact fix (do not invent variations).
2) If RAG is missing/uncertain: use Web context to confirm the pattern and propose a widely accepted Docker fix.
3) If still uncertain: choose the safest reversible fallback from this ladder (pick the first applicable):
   A) Restart the specific container:
      client.containers.get("{container_name}").restart()
   B) If log indicates stuck/hanging and restart may fail:
      client.containers.get("{container_name}").kill(signal="SIGKILL")
   C) If log indicates disk space full:
      "docker system prune -f --volumes"
   If none apply, still pick A (restart) as the final fallback.

Output JSON ONLY (no markdown, no extra text):
{{
  "command": "<single executable command>",
  "confidence": <0.0 to 1.0>,
  "source": "rag" | "web" | "fallback",
  "reason": "<short reason>",
  "requires_approval": true | false
}}

Confidence rules (must follow):
- If command comes from RAG exact match: confidence >= 0.85
- If command comes from Web validation: confidence 0.70–0.84
- If command is fallback ladder: confidence 0.40–0.69

Approval rule:
- If confidence < {approval_threshold}, set requires_approval=true
- Else requires_approval=false

Safety constraints:
- Only one command. Never multiple commands.
- Prefer container-scoped actions over system-wide actions.
- Do NOT restart Docker daemon unless log explicitly indicates docker daemon failure.
- Use container_name exactly as provided.

Inputs:
- Log line: {log_line}
- Error summary: {log_summary}
- Analyzer confidence: {analyzer_conf}
- Container: {container_name}

RAG context:
{rag_context}

Web context:
{web_context}
""")

    resp = llm.invoke(prompt.format(
        log_line=log_line,
        log_summary=log_summary,
        analyzer_conf=analyzer_conf,
        container_name=container_name,
        rag_context=rag_context[:4000],
        web_context=web_context[:2000],
        approval_threshold=approval_threshold,
    ))

    data = safe_json_extract(getattr(resp, "content", ""))

    # If model fails, apply deterministic fallback
    cmd = (data.get("command") or "").strip()
    reason = (data.get("reason") or "").strip()
    source = (data.get("source") or "").strip().lower()
    conf = float(data.get("confidence", 0.0))

    if not cmd:
        cmd, reason = _fallback_command(log_line, container_name)
        source = "fallback"
        conf = 0.55

    # Normalize source
    if source not in {"rag", "web", "fallback"}:
        source = "rag" if rag_context.strip() else ("web" if web_context.strip() else "fallback")

    # Calibrate confidence to prevent random 0.99 on weak evidence
    source_floor_ceiling = {
        "rag": (0.85, 0.98),
        "web": (0.70, 0.84),
        "fallback": (0.40, 0.69),
    }
    lo, hi = source_floor_ceiling[source]
    conf = max(lo, min(hi, conf if conf else (lo + hi) / 2))

    # Blend with analyzer confidence slightly (keeps it consistent)
    conf = max(0.0, min(1.0, (conf * 0.80) + (analyzer_conf * 0.20)))

    requires_approval = conf < approval_threshold

    payload = {
        "command": cmd,
        "confidence": round(conf, 2),
        "source": source,
        "reason": reason or "Auto-repair recommendation generated.",
        "requires_approval": requires_approval,
    }

    print(f"[{container_name}] Suggested: {payload['command']} | conf={payload['confidence']} | approval={requires_approval} | source={source}")

    return {"response": json.dumps(payload)}
