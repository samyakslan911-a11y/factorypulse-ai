from pydantic import BaseModel, HttpUrl
from typing import Optional
from uuid import UUID
from datetime import datetime

class SupplierCreate(BaseModel):
    name: str
    website: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = []
    analyze_on_create: bool = False

class SupplierView(BaseModel):
    id: UUID
    name: str
    website: Optional[str]
    country: Optional[str]
    industry: Optional[str]
    tags: list[str]
    current_score: Optional[int]
    score_financial: Optional[int]
    score_operational: Optional[int]
    score_reputational: Optional[int]
    score_delta: Optional[int]
    risk_status: str
    last_analyzed: Optional[datetime]
    last_analysis_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
