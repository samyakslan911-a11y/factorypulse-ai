from fastapi import APIRouter, BackgroundTasks
from backend.db import analyses as db_analyses

router = APIRouter(prefix="/analyses", tags=["analyses"])

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

@router.post("/{supplier_id}/run", status_code=202)
def trigger_analysis(supplier_id: str, background_tasks: BackgroundTasks):
    from backend.agent.supplier_agent import run_supplier_agent
    from backend.api.stream import ensure_queue
    analysis = db_analyses.create_analysis(supplier_id, DEMO_USER_ID, "manual")
    analysis_id = analysis["id"]
    ensure_queue(analysis_id)
    background_tasks.add_task(run_supplier_agent, supplier_id, DEMO_USER_ID, "manual", analysis)
    return {"message": "Análisis iniciado", "supplier_id": supplier_id, "analysis_id": analysis_id}
