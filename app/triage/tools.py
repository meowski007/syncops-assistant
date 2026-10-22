"""
Tool definitions and execution engine for LLM-powered incident triage.
Provides genuine callable tool interfaces for database inspection and runbook retrieval.
"""

import json
from pathlib import Path
from typing import Any
from app.config import RUNBOOKS_DIR
from app.database import get_db, get_db_path
from app.incidents import get_incident_by_id
from app.logging_config import logger

# Bounded output limit to prevent context blowup
MAX_RUNBOOK_CHARS = 4000

def tool_get_incident_details(incident_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """
    Callable Tool: Queries the synthetic database for full incident details,
    affected cohort telemetry, and associated customer support tickets.
    """
    target_path = Path(db_path) if db_path else get_db_path()
    try:
        with get_db(target_path) as conn:
            inc = get_incident_by_id(conn, incident_id)
            if not inc:
                return {
                    "error": f"Incident '{incident_id}' not found in database.",
                    "status": "NOT_FOUND"
                }
            return inc
    except Exception as e:
        logger.error(f"Error executing tool_get_incident_details: {e}")
        return {"error": str(e), "status": "QUERY_ERROR"}

def tool_search_and_read_runbook(query_or_filename: str) -> dict[str, Any]:
    """
    Callable Tool: Searches and reads operational Markdown runbooks located in runbooks/
    Returns matching filename and markdown content.
    """
    try:
        query_lower = query_or_filename.lower().replace(".md", "")
        available_files = list(RUNBOOKS_DIR.glob("*.md"))
        
        if not available_files:
            return {"error": "No runbooks found in runbooks directory.", "available": []}
            
        matched_file: Path | None = None
        
        # 1. Exact or partial filename match
        for f in available_files:
            if query_lower in f.stem.lower():
                matched_file = f
                break
                
        # 2. Keyword fallback match across categories
        if not matched_file:
            category_mapping = {
                "sync": "sync_failures.md",
                "schema": "sync_failures.md",
                "database": "sync_failures.md",
                "auth": "authentication_errors.md",
                "token": "authentication_errors.md",
                "cert": "authentication_errors.md",
                "firmware": "firmware_update_failures.md",
                "iot": "firmware_update_failures.md",
                "ble": "firmware_update_failures.md",
                "payload": "payload_timeout_guide.md",
                "timeout": "payload_timeout_guide.md",
                "rate": "payload_timeout_guide.md",
                "confirm": "recovery_confirmation.md",
                "recovery": "recovery_confirmation.md",
            }
            for keyword, target_name in category_mapping.items():
                if keyword in query_lower:
                    candidate = RUNBOOKS_DIR / target_name
                    if candidate.exists():
                        matched_file = candidate
                        break
                        
        if not matched_file:
            # Return catalog of available runbooks
            return {
                "message": f"No direct match for '{query_or_filename}'.",
                "available_runbooks": [f.name for f in available_files]
            }
            
        content = matched_file.read_text(encoding="utf-8")
        if len(content) > MAX_RUNBOOK_CHARS:
            content = content[:MAX_RUNBOOK_CHARS] + "\n\n...[TRUNCATED FOR BOUNDED CONTEXT]..."
            
        return {
            "filename": matched_file.name,
            "content": content,
            "status": "SUCCESS"
        }
    except Exception as e:
        logger.error(f"Error executing tool_search_and_read_runbook: {e}")
        return {"error": str(e), "status": "READ_ERROR"}

# OpenAI-Compatible Tool Specifications
OPENAI_TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "get_incident_details",
            "description": "Fetch detailed information, cohort telemetry, and customer tickets for a specific incident ID from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "The incident ID to investigate, e.g. INC-2026-1001"
                    }
                },
                "required": ["incident_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_read_runbook",
            "description": "Search and retrieve standard operating procedures and mitigation steps from operational markdown runbooks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_or_filename": {
                        "type": "string",
                        "description": "Runbook name or topic keyword (e.g., 'payload_timeout', 'sync_failures', 'auth', 'firmware', 'recovery')"
                    }
                },
                "required": ["query_or_filename"]
            }
        }
    }
]

def execute_tool(tool_name: str, arguments_json: str | dict, db_path: str | Path | None = None) -> str:
    """Executes the requested tool and returns serialized JSON result string."""
    try:
        args = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON arguments: {e}"})

    if tool_name == "get_incident_details":
        inc_id = args.get("incident_id", "")
        res = tool_get_incident_details(inc_id, db_path=db_path)
        return json.dumps(res)
    elif tool_name == "search_and_read_runbook":
        query = args.get("query_or_filename", "")
        res = tool_search_and_read_runbook(query)
        return json.dumps(res)
    else:
        return json.dumps({"error": f"Unknown tool name: {tool_name}"})
