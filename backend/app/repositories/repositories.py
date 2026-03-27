"""
Repositorios: única capa que habla directamente con SQLAlchemy.
Los servicios usan repositorios; los endpoints no acceden al ORM directamente.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any, Tuple

from app.models.models import (
    Upload, EmployeeTemplate, BankTransaction,
    ReconciliationResult, ReconciliationBatch,
    User, AuditLog,
)
from app.schemas.schemas import (
    UploadCreate, EmployeeTemplateCreate,
    BankTransactionCreate, ReconciliationResultCreate,
)


# ---------------------------------------------------------------------------
# Upload Repository
# ---------------------------------------------------------------------------

class UploadRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: UploadCreate) -> Upload:
        record = Upload(**data.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_id(self, upload_id: int) -> Optional[Upload]:
        return self.db.query(Upload).filter(Upload.id == upload_id).first()

    def get_all(self, file_type: Optional[str] = None) -> List[Upload]:
        q = self.db.query(Upload)
        if file_type:
            q = q.filter(Upload.file_type == file_type)
        return q.order_by(Upload.uploaded_at.desc()).all()

    def update_status(
        self,
        upload_id: int,
        status: str,
        total_rows: int = 0,
        processed_rows: int = 0,
        error_rows: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        record = self.get_by_id(upload_id)
        if not record:
            return
        record.status = status
        record.total_rows = total_rows
        record.processed_rows = processed_rows
        record.error_rows = error_rows
        record.error_message = error_message
        self.db.commit()


# ---------------------------------------------------------------------------
# Employee Template Repository
# ---------------------------------------------------------------------------

class EmployeeTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, templates: List[EmployeeTemplateCreate]) -> List[EmployeeTemplate]:
        records = [EmployeeTemplate(**t.model_dump()) for t in templates]
        self.db.add_all(records)
        self.db.commit()
        for r in records:
            self.db.refresh(r)
        return records

    def get_by_upload_id(self, upload_id: int) -> List[EmployeeTemplate]:
        return (
            self.db.query(EmployeeTemplate)
            .filter(EmployeeTemplate.upload_id == upload_id)
            .all()
        )

    def get_by_account(self, account_number: str) -> Optional[EmployeeTemplate]:
        return (
            self.db.query(EmployeeTemplate)
            .filter(EmployeeTemplate.account_number == account_number)
            .first()
        )


# ---------------------------------------------------------------------------
# Bank Transaction Repository
# ---------------------------------------------------------------------------

class BankTransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, transactions: List[BankTransactionCreate]) -> List[BankTransaction]:
        records = [BankTransaction(**t.model_dump()) for t in transactions]
        self.db.add_all(records)
        self.db.commit()
        for r in records:
            self.db.refresh(r)
        return records

    def get_by_upload_id(self, upload_id: int) -> List[BankTransaction]:
        return (
            self.db.query(BankTransaction)
            .filter(BankTransaction.upload_id == upload_id)
            .all()
        )


# ---------------------------------------------------------------------------
# Reconciliation Result Repository
# ---------------------------------------------------------------------------

class ReconciliationResultRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, results: List[ReconciliationResultCreate]) -> List[ReconciliationResult]:
        records = [ReconciliationResult(**r.model_dump()) for r in results]
        self.db.add_all(records)
        self.db.commit()
        for r in records:
            self.db.refresh(r)
        return records

    def delete_all(self) -> None:
        """Limpia resultados anteriores antes de una nueva corrida."""
        self.db.query(ReconciliationResult).delete()
        self.db.commit()

    def get_all(self) -> List[ReconciliationResult]:
        return self.db.query(ReconciliationResult).order_by(ReconciliationResult.id).all()

    def get_filtered(
        self,
        status: Optional[str] = None,
        bank_name: Optional[str] = None,
        employee_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ReconciliationResult], int]:
        """Retorna (registros, total) con filtros aplicados."""
        q = self.db.query(ReconciliationResult)

        if status:
            q = q.filter(ReconciliationResult.reconciliation_status == status)
        if bank_name:
            q = q.filter(ReconciliationResult.bank_name.ilike(f"%{bank_name}%"))
        if employee_name:
            q = q.filter(ReconciliationResult.employee_name.ilike(f"%{employee_name}%"))
        if min_amount is not None:
            q = q.filter(
                or_(
                    ReconciliationResult.expected_amount >= min_amount,
                    ReconciliationResult.reported_amount >= min_amount,
                )
            )
        if max_amount is not None:
            q = q.filter(
                or_(
                    ReconciliationResult.expected_amount <= max_amount,
                    ReconciliationResult.reported_amount <= max_amount,
                )
            )

        total = q.count()
        items = q.order_by(ReconciliationResult.id).offset(offset).limit(limit).all()
        return items, total

    def get_inconsistencies(self) -> List[ReconciliationResult]:
        """Registros que requieren atención del operador."""
        return (
            self.db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.reconciliation_status.in_(
                    ["difference", "missing", "extra", "duplicate", "pending"]
                )
            )
            .order_by(ReconciliationResult.reconciliation_status, ReconciliationResult.id)
            .all()
        )

    def get_summary(self) -> Dict[str, Any]:
        """Agrega los KPIs del dashboard en una sola consulta."""
        rows = (
            self.db.query(
                ReconciliationResult.reconciliation_status,
                func.count(ReconciliationResult.id).label("count"),
                func.coalesce(func.sum(ReconciliationResult.expected_amount), 0).label("expected"),
                func.coalesce(func.sum(ReconciliationResult.reported_amount), 0).label("reported"),
                func.coalesce(func.sum(ReconciliationResult.difference_amount), 0).label("diff"),
            )
            .group_by(ReconciliationResult.reconciliation_status)
            .all()
        )

        summary: Dict[str, Any] = {
            "total_processed": 0,
            "total_matched": 0,
            "total_difference": 0,
            "total_missing": 0,
            "total_extra": 0,
            "total_duplicate": 0,
            "total_pending": 0,
            "total_expected_amount": 0.0,
            "total_reported_amount": 0.0,
            "total_matched_amount": 0.0,
            "total_difference_amount": 0.0,
        }

        for row in rows:
            s = row.reconciliation_status
            summary["total_processed"] += row.count
            summary[f"total_{s}"] = row.count
            summary["total_expected_amount"] += float(row.expected or 0)
            summary["total_reported_amount"] += float(row.reported or 0)
            if s == "matched":
                summary["total_matched_amount"] += float(row.expected or 0)
            if s == "difference":
                summary["total_difference_amount"] += abs(float(row.diff or 0))

        return summary

    def get_bank_summary(self) -> List[Dict[str, Any]]:
        """Resumen por banco para el dashboard."""
        rows = (
            self.db.query(
                ReconciliationResult.bank_name,
                ReconciliationResult.reconciliation_status,
                func.count(ReconciliationResult.id).label("count"),
                func.coalesce(func.sum(ReconciliationResult.reported_amount), 0).label("amount"),
            )
            .filter(ReconciliationResult.bank_name.isnot(None))
            .group_by(ReconciliationResult.bank_name, ReconciliationResult.reconciliation_status)
            .all()
        )

        # Agrupar por banco
        by_bank: Dict[str, Dict] = {}
        for row in rows:
            bank = row.bank_name or "Desconocido"
            if bank not in by_bank:
                by_bank[bank] = {
                    "bank_name": bank,
                    "total_transactions": 0,
                    "total_amount": 0.0,
                    "matched": 0,
                    "difference": 0,
                    "extra": 0,
                    "missing": 0,
                    "duplicate": 0,
                }
            by_bank[bank]["total_transactions"] += row.count
            by_bank[bank]["total_amount"] += float(row.amount or 0)
            by_bank[bank][row.reconciliation_status] = (
                by_bank[bank].get(row.reconciliation_status, 0) + row.count
            )

        return list(by_bank.values())


# ---------------------------------------------------------------------------
# Reconciliation Batch Repository
# ---------------------------------------------------------------------------

class ReconciliationBatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, template_upload_id: int, total_results: int) -> ReconciliationBatch:
        batch = ReconciliationBatch(
            template_upload_id=template_upload_id,
            total_results=total_results,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_latest(self) -> Optional[ReconciliationBatch]:
        return (
            self.db.query(ReconciliationBatch)
            .order_by(ReconciliationBatch.created_at.desc())
            .first()
        )


# ---------------------------------------------------------------------------
# User Repository
# ---------------------------------------------------------------------------

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def count(self) -> int:
        return self.db.query(User).count()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_credential(self, credential: str) -> Optional[User]:
        """Busca por username o email."""
        return (
            self.db.query(User)
            .filter((User.username == credential) | (User.email == credential))
            .first()
        )

    def get_all(self) -> List[User]:
        return self.db.query(User).order_by(User.created_at.desc()).all()

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, **kwargs) -> User:
        for field, value in kwargs.items():
            if value is not None:
                setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_last_login(self, user: User) -> None:
        from datetime import datetime
        user.last_login_at = datetime.utcnow()
        self.db.commit()


# ---------------------------------------------------------------------------
# Audit Log Repository
# ---------------------------------------------------------------------------

class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_all(self, limit: int = 200) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
