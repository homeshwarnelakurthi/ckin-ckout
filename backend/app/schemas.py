"""Pydantic request/response models."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# --- Users ---
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    hourly_rate: Decimal
    is_active: bool


# --- Time entries ---
class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    clock_in_at: datetime
    clock_out_at: datetime | None
    total_minutes: int | None
    total_pay: Decimal | None
    status: str
    edited_by: uuid.UUID | None
    notes: str | None


class ClockResponse(BaseModel):
    entry: TimeEntryOut
    message: str


class SummaryPeriod(BaseModel):
    total_minutes: int
    total_hours: float
    total_pay: Decimal


class SummaryResponse(BaseModel):
    today: SummaryPeriod
    week: SummaryPeriod
    month: SummaryPeriod
    open_entry: TimeEntryOut | None


class EntryPatchRequest(BaseModel):
    clock_in_at: datetime | None = None
    clock_out_at: datetime | None = None
    status: str | None = Field(default=None, pattern="^(open|closed|flagged)$")
    notes: str | None = None
    reason: str | None = None  # recorded in the audit log


class MetaResponse(BaseModel):
    business_name: str
    manager_name: str
    display_timezone: str
    default_hourly_rate: float


TokenResponse.model_rebuild()
