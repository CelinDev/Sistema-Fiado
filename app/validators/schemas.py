from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.database.models import DebtStatus, PaymentMethod
from app.utils.formatters import clean_digits, parse_currency_to_cents


class CustomerCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Nome completo do cliente")
    phone: Optional[str] = Field(None, max_length=25)
    cpf: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    credit_limit_cents: Optional[int] = Field(None, ge=0, description="Limite máximo em centavos")
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("O nome deve ter pelo menos 2 caracteres.")
        return cleaned

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        digits = clean_digits(v)
        if len(digits) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return digits


class CustomerUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=25)
    cpf: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    credit_limit_cents: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if len(cleaned) < 2:
                raise ValueError("O nome deve ter pelo menos 2 caracteres.")
            return cleaned
        return v

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        digits = clean_digits(v)
        if len(digits) != 11:
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return digits


class DebtCreateSchema(BaseModel):
    customer_id: int = Field(..., gt=0, description="ID do cliente")
    description: str = Field(..., min_length=2, max_length=255, description="Descrição da compra fiada")
    original_amount_cents: int = Field(..., gt=0, description="Valor original em centavos inteiros")
    due_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("A descrição da compra não pode ficar vazia.")
        return cleaned


class PaymentCreateSchema(BaseModel):
    customer_id: int = Field(..., gt=0)
    debt_id: Optional[int] = Field(None, gt=0, description="Dívida específica ou None para rateio automático")
    amount_cents: int = Field(..., gt=0, description="Valor do pagamento em centavos inteiros")
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class PaymentCancellationSchema(BaseModel):
    payment_id: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3, max_length=255, description="Motivo do cancelamento / estorno")
