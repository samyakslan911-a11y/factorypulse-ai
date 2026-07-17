from fastapi import APIRouter, BackgroundTasks
from backend.scheduler.scheduler import get_status

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/status")
def scheduler_status():
    return get_status()


@router.post("/run-now", status_code=202)
def run_now(background_tasks: BackgroundTasks):
    from backend.db.suppliers import list_suppliers
    from backend.db.analyses import create_analysis
    from backend.agent.supplier_agent import run_supplier_agent

    suppliers = list_suppliers(DEMO_USER_ID)

    def _run_all():
        for supplier in suppliers:
            analysis = create_analysis(supplier["id"], supplier["user_id"], "manual_batch")
            run_supplier_agent(supplier["id"], supplier["user_id"], "manual_batch", analysis)

    background_tasks.add_task(_run_all)
    return {"message": f"Análisis iniciado para {len(suppliers)} proveedores"}
