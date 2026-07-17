from datetime import datetime, timezone
from uuid import UUID
from backend.db.client import get_db

def create_analysis(supplier_id: str, user_id: str, triggered_by: str) -> dict:
    db = get_db()
    res = db.table("analyses").insert({
        "supplier_id": supplier_id,
        "user_id": user_id,
        "triggered_by": triggered_by,
        "status": "running",
    }).execute()
    return res.data[0]

def update_analysis(analysis_id: str, updates: dict) -> dict:
    db = get_db()
    updates["finished_at"] = datetime.now(timezone.utc).isoformat()
    res = db.table("analyses").update(updates).eq("id", analysis_id).execute()
    return res.data[0]

def get_analysis_history(supplier_id: str, limit: int = 20) -> list[dict]:
    db = get_db()
    res = (db.table("analyses")
             .select("*")
             .eq("supplier_id", supplier_id)
             .eq("status", "done")
             .order("started_at", desc=True)
             .limit(limit)
             .execute())
    return res.data

def save_step(analysis_id: str, step_number: int, tool_used: str, tool_input: dict, tool_output_summary: str, duration_ms: int = 0) -> None:
    db = get_db()
    db.table("analysis_steps").insert({
        "analysis_id": analysis_id,
        "step_number": step_number,
        "tool_used": tool_used,
        "tool_input": tool_input,
        "tool_output_summary": tool_output_summary[:500],
        "duration_ms": duration_ms,
    }).execute()

def get_steps(analysis_id: str) -> list[dict]:
    db = get_db()
    res = (db.table("analysis_steps")
             .select("*")
             .eq("analysis_id", analysis_id)
             .order("step_number")
             .execute())
    return res.data
