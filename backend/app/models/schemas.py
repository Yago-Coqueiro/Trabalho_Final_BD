from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    created_at: datetime


# ── Accounts ──────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    type: Literal["corrente", "poupanca", "cartao", "outro"] = "corrente"
    balance: Decimal = Decimal("0")


class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    type: str
    balance: Decimal
    created_at: datetime
    updated_at: datetime


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    icon: str = "tag"
    color: str = "#42a5f5"


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None


class CategoryResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    name: str
    icon: str
    color: str
    is_default: bool
    created_at: datetime


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: Decimal
    description: str | None = None
    type: Literal["income", "expense"]
    status: Literal["confirmed", "pending"] = "confirmed"
    date: date
    category_id: UUID | None = None
    account_id: UUID | None = None


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_id: UUID | None
    category_id: UUID | None
    amount: Decimal
    description: str | None
    type: str
    status: str
    date: date
    created_at: datetime
    updated_at: datetime
    category_name: str | None = None
    category_color: str | None = None
    category_icon: str | None = None


# ── Budget Goals ──────────────────────────────────────────────────────────────

class BudgetGoalCreate(BaseModel):
    category_id: UUID | None = None
    amount: Decimal
    month: int
    year: int

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("month deve estar entre 1 e 12")
        return v


class BudgetGoalResponse(BaseModel):
    id: UUID
    user_id: UUID
    category_id: UUID | None
    amount: Decimal
    month: int
    year: int
    created_at: datetime
    category_name: str | None = None
    category_color: str | None = None


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    content: str
    created_at: datetime


class ChatSendResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


# ── Dashboard ─────────────────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    category_id: UUID | None
    category_name: str
    category_color: str
    total: float


class DailyPoint(BaseModel):
    date: date
    income: float
    expense: float


class DashboardSummary(BaseModel):
    balance: float
    total_income: float
    total_expense: float
    transaction_count: int
    category_breakdown: list[CategoryBreakdown]
    daily_evolution: list[DailyPoint]
    latest_insight: str | None


# ── Settings ──────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    display_name: str


class PasswordChange(BaseModel):
    new_password: str
