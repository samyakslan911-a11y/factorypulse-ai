from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

class Finding(BaseModel):
    id: str
    category: str          # "financial" | "operational" | "reputational"
    severity: str          # "low" | "medium" | "high"
    title: str
    description: str
    source_url: Optional[str]
    source_date: Optional[str]
    confidence: float

class AnalysisResult(BaseModel):
    id: UUID
    supplier_id: UUID
    status: str
    model_used: Optional[str]
    score_total: Optional[int]
    score_financial: Optional[int]
    score_operational: Optional[int]
    score_reputational: Optional[int]
    score_delta: Optional[int]
    summary: Optional[str]
    findings: list[Finding] = []
    sources_used: list[dict] = []
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    started_at: datetime
    finished_at: Optional[datetime]

class AnalysisStep(BaseModel):
    step_number: int
    tool_used: str
    tool_input: Optional[dict]
    tool_output_summary: Optional[str]
    tokens_used: Optional[int]
    duration_ms: Optional[int]
