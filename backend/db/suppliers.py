from uuid import UUID
from backend.db.client import get_db
from backend.models.supplier import SupplierCreate

def list_suppliers(user_id: str) -> list[dict]:
    db = get_db()
    res = db.table("suppliers_view").select("*").eq("user_id", user_id).execute()
    return res.data

def get_supplier(supplier_id: str, user_id: str) -> dict | None:
    db = get_db()
    res = (db.table("suppliers_view")
             .select("*")
             .eq("id", supplier_id)
             .eq("user_id", user_id)
             .single()
             .execute())
    return res.data

def create_supplier(user_id: str, data: SupplierCreate) -> dict:
    db = get_db()
    row = data.model_dump(exclude={"analyze_on_create"})
    row["user_id"] = user_id
    res = db.table("suppliers").insert(row).execute()
    return res.data[0]

def soft_delete_supplier(supplier_id: str, user_id: str) -> None:
    db = get_db()
    from datetime import datetime, timezone
    db.table("suppliers").update({"deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", supplier_id).eq("user_id", user_id).execute()
