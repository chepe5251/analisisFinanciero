"""
Modelos SQLAlchemy.
Todos importan Base desde core.database para garantizar un único metadata.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text,
    ForeignKey, JSON, Boolean, Numeric, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


# ===========================================================================
# Conciliación (módulo original)
# ===========================================================================

class Upload(Base):
    """
    Registro de cada archivo subido al sistema.
    file_type: 'template' para plantilla de personal, 'bank_report' para reporte bancario.
    status: pending → processing → completed | failed
    """
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)       # 'template' | 'bank_report'
    source_bank = Column(String(100), nullable=True)     # Solo para bank_report
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")       # pending | processing | completed | failed
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relaciones
    employee_templates = relationship("EmployeeTemplate", back_populates="upload", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="upload", cascade="all, delete-orphan")


class EmployeeTemplate(Base):
    """
    Registro de cada empleado de la plantilla principal.
    expected_amount es el monto que DEBE recibir el empleado.
    """
    __tablename__ = "employee_templates"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    employee_id = Column(String(50), nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    identification = Column(String(50), nullable=True)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(50), nullable=False, index=True)
    expected_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")

    upload = relationship("Upload", back_populates="employee_templates")
    reconciliation_results = relationship("ReconciliationResult", back_populates="employee_template")


class BankTransaction(Base):
    """
    Registro de cada transacción en los reportes bancarios.
    raw_data_json almacena la fila original antes de normalización (auditoría).
    """
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    bank_name = Column(String(100), nullable=False, index=True)
    transaction_date = Column(DateTime, nullable=True)
    beneficiary_name = Column(String(200), nullable=False)
    beneficiary_account = Column(String(50), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    reference = Column(String(255), nullable=True)
    status = Column(String(50), default="raw")           # raw | processed
    raw_data_json = Column(JSON, nullable=True)

    upload = relationship("Upload", back_populates="bank_transactions")
    reconciliation_results = relationship("ReconciliationResult", back_populates="bank_transaction")


class ReconciliationBatch(Base):
    """
    Agrupa una ejecución de conciliación.
    Permite tener historial de múltiples corridas.
    """
    __tablename__ = "reconciliation_batches"

    id = Column(Integer, primary_key=True, index=True)
    template_upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="completed")
    total_results = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    results = relationship("ReconciliationResult", back_populates="batch")


class ReconciliationResult(Base):
    """
    Resultado de cruzar un empleado de la plantilla contra una transacción bancaria.

    BUG FIX: se agrega batch_id para que cada corrida tenga su propio historial
    y no se borre el historial global en cada corrida (delete_all eliminado).
    """
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    # BUG FIX: campo batch_id para filtrar resultados por corrida
    batch_id = Column(Integer, ForeignKey("reconciliation_batches.id"), nullable=True, index=True)
    employee_template_id = Column(Integer, ForeignKey("employee_templates.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    reconciliation_status = Column(String(50), nullable=False, index=True)
    expected_amount = Column(Float, nullable=True)
    reported_amount = Column(Float, nullable=True)
    difference_amount = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    matched_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Campos desnormalizados para facilitar consultas sin joins pesados
    employee_name = Column(String(200), nullable=True)
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(50), nullable=True)

    batch = relationship("ReconciliationBatch", back_populates="results")
    employee_template = relationship("EmployeeTemplate", back_populates="reconciliation_results")
    bank_transaction = relationship("BankTransaction", back_populates="reconciliation_results")


# ===========================================================================
# Autenticación y autorización
# ===========================================================================

class User(Base):
    """Usuario del sistema. Roles: admin | operator | viewer"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(20), nullable=False)            # admin | operator | viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")


class AuditLog(Base):
    """Registro de auditoría de acciones relevantes del sistema."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])


# ===========================================================================
# Multi-tenant: Empresas
# ===========================================================================

class Company(Base):
    """Empresa raíz del árbol multi-tenant."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    tax_id = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    fiscal_periods = relationship("FiscalPeriod", back_populates="company")
    cost_centers = relationship("CostCenter", back_populates="company")
    chart_of_accounts = relationship("ChartOfAccount", back_populates="company")
    budgets = relationship("Budget", back_populates="company")
    invoices = relationship("Invoice", back_populates="company")


# ===========================================================================
# Contabilidad general
# ===========================================================================

class FiscalPeriod(Base):
    """Período contable (mes/año). Acepta nuevos asientos solo si está abierto."""
    __tablename__ = "fiscal_periods"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)             # 1-12
    name = Column(String(100), nullable=False)          # "Enero 2024"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="open")         # open | closed
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="fiscal_periods")
    journal_entries = relationship("JournalEntry", back_populates="fiscal_period")
    budgets = relationship("Budget", back_populates="fiscal_period")


class CostCenter(Base):
    """Centro de costo para clasificar ingresos y gastos."""
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    code = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="cost_centers")


class ChartOfAccount(Base):
    """
    Plan de cuentas jerárquico.
    account_type: asset | liability | equity | income | expense
    """
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    account_type = Column(String(20), nullable=False)   # asset|liability|equity|income|expense
    level = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="chart_of_accounts")
    # Self-referential: parent y children
    parent = relationship(
        "ChartOfAccount",
        back_populates="children",
        foreign_keys=[parent_id],
        remote_side=[id],
    )
    children = relationship(
        "ChartOfAccount",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    journal_lines = relationship("JournalEntryLine", back_populates="account")
    budget_lines = relationship("BudgetLine", back_populates="account")
    invoice_lines = relationship("InvoiceLine", back_populates="account")


class JournalEntry(Base):
    """
    Asiento contable.
    status: draft → posted | voided
    Regla: solo se puede editar en draft; para anular un posted se crea asiento inverso.
    """
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    fiscal_period_id = Column(Integer, ForeignKey("fiscal_periods.id"), nullable=False)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True)
    entry_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    reference = Column(String(100), nullable=True)
    status = Column(String(20), default="draft")        # draft | posted | voided
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    voided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    void_reason = Column(Text, nullable=True)
    # Referencia al origen (conciliación, factura, manual)
    source_type = Column(String(50), nullable=True)
    source_id = Column(Integer, nullable=True)

    fiscal_period = relationship("FiscalPeriod", back_populates="journal_entries")
    lines = relationship("JournalEntryLine", back_populates="entry", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])
    voided_by = relationship("User", foreign_keys=[voided_by_id])


class JournalEntryLine(Base):
    """Línea de un asiento contable (débito o crédito sobre una cuenta)."""
    __tablename__ = "journal_entry_lines"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    description = Column(Text, nullable=True)
    debit = Column(Float, default=0.0, nullable=False)
    credit = Column(Float, default=0.0, nullable=False)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("ChartOfAccount", back_populates="journal_lines")


# ===========================================================================
# Presupuestos
# ===========================================================================

class Budget(Base):
    """
    Presupuesto por período y centro de costo.
    status: draft → approved | closed
    Un presupuesto aprobado no se modifica; se crea una revisión referenciando al anterior.
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    fiscal_period_id = Column(Integer, ForeignKey("fiscal_periods.id"), nullable=False)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="draft")        # draft | approved | closed
    previous_budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="budgets")
    fiscal_period = relationship("FiscalPeriod", back_populates="budgets")
    lines = relationship("BudgetLine", back_populates="budget", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    previous_budget = relationship("Budget", remote_side=[id], foreign_keys=[previous_budget_id])


class BudgetLine(Base):
    """Línea de presupuesto: cuenta contable + monto planificado."""
    __tablename__ = "budget_lines"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)
    planned_amount = Column(Float, nullable=False, default=0.0)

    budget = relationship("Budget", back_populates="lines")
    account = relationship("ChartOfAccount", back_populates="budget_lines")


# ===========================================================================
# Facturación y cuentas por cobrar/pagar
# ===========================================================================

class Invoice(Base):
    """
    Factura emitida o recibida.
    invoice_type: issued (emitida → CxC) | received (recibida → CxP)
    status: draft | issued | paid | overdue | voided
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    invoice_type = Column(String(20), nullable=False)   # issued | received
    invoice_number = Column(String(50), nullable=True, index=True)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    counterparty_name = Column(String(200), nullable=False)
    counterparty_tax_id = Column(String(50), nullable=True)
    status = Column(String(20), default="draft")        # draft|issued|paid|overdue|voided
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")
    created_by = relationship("User", foreign_keys=[created_by_id])


class InvoiceLine(Base):
    """Línea de factura."""
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    tax_rate = Column(Float, default=0.0)               # Porcentaje (ej: 12.0 = 12%)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)

    invoice = relationship("Invoice", back_populates="lines")
    account = relationship("ChartOfAccount", back_populates="invoice_lines")


class Payment(Base):
    """Pago asociado a una factura."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=True)  # bank_transfer|check|cash|card
    bank_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")
