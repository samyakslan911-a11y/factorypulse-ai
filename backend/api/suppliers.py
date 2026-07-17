from fastapi import APIRouter, BackgroundTasks, HTTPException
from backend.models.supplier import SupplierCreate, SupplierView
from backend.db import suppliers as db_suppliers
from backend.db import analyses as db_analyses

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

# Usuario demo fijo hasta implementar auth
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

@router.get("/", response_model=list[dict])
def list_suppliers():
    return db_suppliers.list_suppliers(DEMO_USER_ID)

@router.get("/{supplier_id}")
def get_supplier(supplier_id: str):
    s = db_suppliers.get_supplier(supplier_id, DEMO_USER_ID)
    if not s:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return s

@router.post("/", status_code=201)
def create_supplier(data: SupplierCreate, background_tasks: BackgroundTasks):
    try:
        supplier = db_suppliers.create_supplier(DEMO_USER_ID, data)
        if data.analyze_on_create:
            background_tasks.add_task(_run_analysis, supplier["id"])
        return supplier
    except Exception as exc:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")

@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: str):
    db_suppliers.soft_delete_supplier(supplier_id, DEMO_USER_ID)

@router.get("/{supplier_id}/history")
def get_history(supplier_id: str):
    return db_analyses.get_analysis_history(supplier_id)

@router.get("/{supplier_id}/analyses/{analysis_id}/steps")
def get_steps(supplier_id: str, analysis_id: str):
    return db_analyses.get_steps(analysis_id)

def _run_analysis(supplier_id: str):
    # Importación local para evitar ciclo de imports
    from backend.agent.supplier_agent import run_supplier_agent
    run_supplier_agent(supplier_id, DEMO_USER_ID, triggered_by="manual")
