from fastapi import APIRouter, BackgroundTasks, Depends
from backend.scheduler.scheduler import get_status
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def scheduler_status(user_id: str = Depends(get_current_user)):
    return get_status()


@router.post("/run-now", status_code=202)
def run_now(background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    from backend.db.suppliers import list_suppliers
    from backend.db.analyses import create_analysis
    from backend.agent.supplier_agent import run_supplier_agent

    suppliers = list_suppliers(user_id)

    def _run_all():
        for supplier in suppliers:
            analysis = create_analysis(supplier["id"], supplier["user_id"], "manual")
            run_supplier_agent(supplier["id"], supplier["user_id"], "manual", analysis)

    background_tasks.add_task(_run_all)
    return {"message": f"Análisis iniciado para {len(suppliers)} proveedores"}
