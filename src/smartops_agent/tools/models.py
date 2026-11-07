"""Modèles Pydantic partagés entre tous les outils."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator


class ToolErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    FORBIDDEN = "FORBIDDEN"
    CLIENT_NOT_PAID = "CLIENT_NOT_PAID"
    OPTED_OUT = "OPTED_OUT"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    TIMEOUT = "TIMEOUT"


class ToolError(Exception):
    def __init__(self, code: ToolErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"error": self.code.value, "message": self.message}


# --- search_crm ---


class EntityType(StrEnum):
    lead = "lead"
    client = "client"
    project = "project"
    team_member = "team_member"


class SearchCrmInput(BaseModel):
    query: str = ""
    entity: EntityType
    status: str | None = None

    @field_validator("query")
    @classmethod
    def query_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("query must be at most 100 characters")
        return v


class CrmRecord(BaseModel):
    id: str
    name: str
    status: str


class SearchCrmOutput(BaseModel):
    results: list[CrmRecord]


# --- get_invoice_status ---


class GetInvoiceStatusInput(BaseModel):
    invoice_id: str | None = None
    project_id: str | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> GetInvoiceStatusInput:
        if self.invoice_id is None and self.project_id is None:
            raise ValueError("invoice_id or project_id is required")
        return self


class InvoiceRecord(BaseModel):
    id: str
    amount: float
    currency: str
    status: str
    due_date: str


class GetInvoiceStatusOutput(BaseModel):
    invoices: list[InvoiceRecord]


# --- calculate_commission ---


class CalculateCommissionInput(BaseModel):
    project_id: str
    person_id: str


class CommissionDetail(BaseModel):
    base: float
    apporteur_share: float
    realisation_share: float
    total: float
    currency: str
    rule_applied: str
    breakdown: str


class CalculateCommissionOutput(BaseModel):
    commission: CommissionDetail


# --- draft_followup ---


class ToneType(StrEnum):
    neutral = "neutral"
    friendly = "friendly"
    formal = "formal"


class DraftFollowupInput(BaseModel):
    lead_id: str
    tone: ToneType


class DraftFollowupOutput(BaseModel):
    subject: str
    body: str
    disclaimer: str = "Brouillon — non envoyé"


# --- request_human_action ---


class RequestHumanActionInput(BaseModel):
    action: str
    reason: str
    payload: dict[str, Any]


class RequestHumanActionOutput(BaseModel):
    request_id: str
    status: str = "pending"
