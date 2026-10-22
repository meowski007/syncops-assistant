"""
Autonomous LLM Triage Agent with Genuine Tool-Calling and Safe Fallback.
Integrates with OpenAI-compatible tool calling while providing 100% reliable
offline deterministic fallback when credentials are absent or network is unavailable.
"""

import json
import os
from pathlib import Path
from typing import Any
from app.config import settings
from app.logging_config import logger
from app.schemas import TriageResult
from app.triage.prompts import TRIAGE_SYSTEM_PROMPT
from app.triage.tools import OPENAI_TOOLS_SPEC, execute_tool
from app.triage.fallback import run_deterministic_triage
from app.metrics import TRIAGE_OPERATIONS_TOTAL

def triage_incident(
    incident_id: str,
    force_fallback: bool = False,
    db_path: str | Path | None = None
) -> TriageResult:
    """
    Investigates an incident using LLM tool-calling if configured,
    or deterministic rule-based analysis if keys are absent or fallback is requested.
    """
    api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    
    if force_fallback or not api_key or api_key.startswith("your-") or len(api_key.strip()) < 10:
        logger.info(f"Using deterministic fallback for incident '{incident_id}' (LLM not configured or forced).")
        res = run_deterministic_triage(incident_id, db_path=db_path)
        TRIAGE_OPERATIONS_TOTAL.labels(mode="deterministic_fallback", outcome="success").inc()
        return res

    # Attempt LLM Tool-Calling with OpenAI SDK
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=15.0)
        
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Please perform a complete SRE triage investigation for incident '{incident_id}'. "
                           f"Use your tools to query the incident details and read the relevant runbook before generating the final JSON assessment."
            }
        ]
        
        # Bounded tool-calling loop (max 5 iterations)
        max_turns = 5
        for turn in range(max_turns):
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=OPENAI_TOOLS_SPEC,
                tool_choice="auto",
                temperature=0.1,
            )
            choice = response.choices[0]
            message = choice.message
            
            # Check if model requested tool execution
            if message.tool_calls:
                # Add assistant message with tool calls to history
                messages.append(message)
                
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = tool_call.function.arguments
                    tool_id = tool_call.id
                    
                    logger.info(f"LLM invoking tool '{fn_name}'", extra={"args": fn_args})
                    tool_output = execute_tool(fn_name, fn_args, db_path=db_path)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tool_output
                    })
            else:
                # Model returned final answer
                content = message.content or ""
                # Attempt to extract JSON
                content_clean = content.strip()
                if "```json" in content_clean:
                    content_clean = content_clean.split("```json")[1].split("```")[0].strip()
                elif "```" in content_clean:
                    content_clean = content_clean.split("```")[1].split("```")[0].strip()
                    
                parsed = json.loads(content_clean)
                parsed["incident_id"] = incident_id
                parsed["analysis_mode"] = "llm_tool_calling"
                parsed["requires_human_review"] = True
                
                result = TriageResult(**parsed)
                logger.info(f"LLM tool-calling triage completed successfully for '{incident_id}'.")
                TRIAGE_OPERATIONS_TOTAL.labels(mode="llm_tool_calling", outcome="success").inc()
                return result
                
        # If loop exceeded max turns without producing final response, use fallback
        logger.warning(f"LLM tool-calling loop exceeded max turns for '{incident_id}'. Falling back to deterministic engine.")
        TRIAGE_OPERATIONS_TOTAL.labels(mode="llm_tool_calling", outcome="max_turns_exceeded").inc()
        return run_deterministic_triage(incident_id, db_path=db_path)

    except Exception as e:
        logger.error(f"LLM tool-calling failed ({e}). Gracefully falling back to deterministic engine.")
        TRIAGE_OPERATIONS_TOTAL.labels(mode="llm_tool_calling", outcome="error_fallback").inc()
        fallback_res = run_deterministic_triage(incident_id, db_path=db_path)
        fallback_res.evidence.append(f"Notice: LLM provider unavailable ({type(e).__name__}); completed via deterministic SRE engine.")
        return fallback_res
