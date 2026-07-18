from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from backend.models.supplier import SupplierCreate, SupplierView
from backend.db import suppliers as db_suppliers
from backend.db import analyses as db_analyses
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

@router.get("/", response_model=list[dict])
def list_suppliers(user_id: str = Depends(get_current_user)):
    return db_suppliers.list_suppliers(user_id)

@router.get("/{supplier_id}")
def get_supplier(supplier_id: str, user_id: str = Depends(get_current_user)):
    s = db_suppliers.get_supplier(supplier_id, user_id)
    if not s:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return s

@router.post("/", status_code=201)
def create_supplier(data: SupplierCreate, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    try:
        supplier = db_suppliers.create_supplier(user_id, data)
        if data.analyze_on_create:
            background_tasks.add_task(_run_analysis, supplier["id"], user_id)
        return supplier
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")

@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: str, user_id: str = Depends(get_current_user)):
    db_suppliers.soft_delete_supplier(supplier_id, user_id)

@router.get("/{supplier_id}/history")
def get_history(supplier_id: str, user_id: str = Depends(get_current_user)):
    return db_analyses.get_analysis_history(supplier_id)

@router.get("/{supplier_id}/analyses/{analysis_id}/steps")
def get_steps(supplier_id: str, analysis_id: str, user_id: str = Depends(get_current_user)):
    return db_analyses.get_steps(analysis_id)

def _run_analysis(supplier_id: str, user_id: str):
    from backend.agent.supplier_agent import run_supplier_agent
    run_supplier_agent(supplier_id, user_id, triggered_by="manual")
