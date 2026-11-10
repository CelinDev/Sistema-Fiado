import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DebtStatus(str, enum.Enum):
    PENDING = "PENDENTE"
    PARTIALLY_PAID = "PARCIALMENTE_PAGO"
    PAID = "PAGO"
    OVERDUE = "VENCIDO"
    CANCELLED = "CANCELADO"


class PaymentMethod(str, enum.Enum):
    CASH = "DINHEIRO"
    PIX = "PIX"
    CARD = "CARTAO"
    TRANSFER = "TRANSFERENCIA"
    OTHER = "OUTROS"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    cpf: Mapped[Optional[str]] = mapped_column(String(14), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credit_limit_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relacionamentos
    debts: Mapped[List["Debt"]] = relationship("Debt", back_populates="customer", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

    @property
    def current_debt_cents(self) -> int:
        """Soma do saldo devedor de todas as dívidas não canceladas."""
        return sum(
            d.remaining_cents
            for d in self.debts
            if d.status != DebtStatus.CANCELLED.value
        )

    @property
    def total_purchases_cents(self) -> int:
        """Total histórico de compras (não canceladas)."""
        return sum(
            d.original_amount_cents
            for d in self.debts
            if d.status != DebtStatus.CANCELLED.value
        )

    @property
    def total_paid_cents(self) -> int:
        """Total já pago (desconsiderando pagamentos cancelados/estornados)."""
        return sum(
            p.amount_cents
            for p in self.payments
            if not p.is_cancelled
        )


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    original_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_cents: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default=DebtStatus.PENDING.value, nullable=False, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relacionamentos
    customer: Mapped["Customer"] = relationship("Customer", back_populates="debts")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="debt")

    @property
    def is_overdue(self) -> bool:
        if self.status in [DebtStatus.PAID.value, DebtStatus.CANCELLED.value]:
            return False
        if self.due_date and self.due_date < date.today() and self.remaining_cents > 0:
            return True
        return False


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    debt_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("debts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(30), default=PaymentMethod.CASH.value, nullable=False
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    # Relacionamentos
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")
    debt: Mapped[Optional["Debt"]] = relationship("Debt", back_populates="payments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
