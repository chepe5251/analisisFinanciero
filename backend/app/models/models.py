"""
Modelos SQLAlchemy.
Todos importan Base desde core.database para garantizar un único metadata.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


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
    error_message = Column(Text, nullable=True)          # Mensaje de error si status=failed

    # Relaciones
    employee_templates = relationship("EmployeeTemplate", back_populates="upload", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="upload", cascade="all, delete-orphan")


class EmployeeTemplate(Base):
    """
    Registro de cada empleado de la plantilla principal.
    Supuesto: un empleado puede tener asignación en un solo banco/cuenta por plantilla.
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
    Supuesto: cada fila del reporte bancario es una transacción de pago.
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


class ReconciliationResult(Base):
    """
    Resultado de cruzar un empleado de la plantilla contra una transacción bancaria.

    Estados posibles:
    - matched:    match exacto (cuenta/nombre + monto dentro de tolerancia)
    - difference: match de persona pero diferencia de monto
    - missing:    empleado en plantilla sin transacción bancaria correspondiente
    - extra:      transacción en banco sin empleado en plantilla
    - duplicate:  más de una transacción que parece corresponder al mismo pago
    - pending:    requiere revisión manual

    matched_by documenta qué campo(s) se usaron para el match.
    """
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    employee_template_id = Column(Integer, ForeignKey("employee_templates.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    reconciliation_status = Column(String(50), nullable=False, index=True)
    expected_amount = Column(Float, nullable=True)
    reported_amount = Column(Float, nullable=True)
    difference_amount = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    matched_by = Column(String(100), nullable=True)      # 'account', 'employee_id', 'name_bank', 'name_amount'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Campos desnormalizados para facilitar consultas sin joins pesados
    employee_name = Column(String(200), nullable=True)
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(50), nullable=True)

    employee_template = relationship("EmployeeTemplate", back_populates="reconciliation_results")
    bank_transaction = relationship("BankTransaction", back_populates="reconciliation_results")


class ReconciliationBatch(Base):
    """
    Agrupa una ejecución de conciliación.
    Permite tener historial de múltiples corridas contra distintas combinaciones de archivos.
    """
    __tablename__ = "reconciliation_batches"

    id = Column(Integer, primary_key=True, index=True)
    template_upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="completed")
    total_results = Column(Integer, default=0)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Autenticación y autorización
# ---------------------------------------------------------------------------

class User(Base):
    """
    Usuario del sistema.
    Roles: admin | operator | viewer
    """
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
    """
    Registro de auditoría de acciones relevantes del sistema.
    username se desnormaliza para preservar el log si el usuario se elimina.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)        # desnormalizado
    action = Column(String(100), nullable=False, index=True)   # user.login, upload.template, etc.
    resource_type = Column(String(50), nullable=True)   # upload | reconciliation | user
    resource_id = Column(String(50), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
