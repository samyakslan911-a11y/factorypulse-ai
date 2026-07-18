from fastapi import APIRouter, BackgroundTasks, Depends
from backend.db import analyses as db_analyses
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/analyses", tags=["analyses"])

@router.post("/{supplier_id}/run", status_code=202)
def trigger_analysis(supplier_id: str, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    from backend.agent.supplier_agent import run_supplier_agent
    from backend.api.stream import ensure_queue
    analysis = db_analyses.create_analysis(supplier_id, user_id, "manual")
    analysis_id = analysis["id"]
    ensure_queue(analysis_id)
    background_tasks.add_task(run_supplier_agent, supplier_id, user_id, "manual", analysis)
    return {"message": "Análisis iniciado", "supplier_id": supplier_id, "analysis_id": analysis_id}
