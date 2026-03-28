"""
Repositorios: única capa que habla directamente con SQLAlchemy.
Los servicios usan repositorios; los endpoints no acceden al ORM directamente.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.models.models import (
    Upload, EmployeeTemplate, BankTransaction,
    ReconciliationResult, ReconciliationBatch,
    User, AuditLog,
    Company, FiscalPeriod, CostCenter,
    ChartOfAccount, JournalEntry, JournalEntryLine,
    Budget, BudgetLine, Invoice, InvoiceLine, Payment,
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

    def get_all(self) -> List[ReconciliationResult]:
        return self.db.query(ReconciliationResult).order_by(ReconciliationResult.id).all()

    def get_filtered(
        self,
        status: Optional[str] = None,
        bank_name: Optional[str] = None,
        employee_name: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        batch_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ReconciliationResult], int]:
        """Retorna (registros, total) con filtros aplicados, opcionalmente por batch."""
        q = self.db.query(ReconciliationResult)

        if batch_id is not None:
            q = q.filter(ReconciliationResult.batch_id == batch_id)
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

    def get_inconsistencies(self, batch_id: Optional[int] = None) -> List[ReconciliationResult]:
        q = (
            self.db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.reconciliation_status.in_(
                    ["difference", "missing", "extra", "duplicate", "pending"]
                )
            )
        )
        if batch_id is not None:
            q = q.filter(ReconciliationResult.batch_id == batch_id)
        return q.order_by(ReconciliationResult.reconciliation_status, ReconciliationResult.id).all()

    def get_summary(self, batch_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Agrega los KPIs del dashboard.
        BUG FIX: acepta batch_id para filtrar por corrida específica.
        """
        q = self.db.query(
            ReconciliationResult.reconciliation_status,
            func.count(ReconciliationResult.id).label("count"),
            func.coalesce(func.sum(ReconciliationResult.expected_amount), 0).label("expected"),
            func.coalesce(func.sum(ReconciliationResult.reported_amount), 0).label("reported"),
            func.coalesce(func.sum(ReconciliationResult.difference_amount), 0).label("diff"),
        )
        if batch_id is not None:
            q = q.filter(ReconciliationResult.batch_id == batch_id)
        rows = q.group_by(ReconciliationResult.reconciliation_status).all()

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

    def get_bank_summary(self, batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        q = (
            self.db.query(
                ReconciliationResult.bank_name,
                ReconciliationResult.reconciliation_status,
                func.count(ReconciliationResult.id).label("count"),
                func.coalesce(func.sum(ReconciliationResult.reported_amount), 0).label("amount"),
            )
            .filter(ReconciliationResult.bank_name.isnot(None))
        )
        if batch_id is not None:
            q = q.filter(ReconciliationResult.batch_id == batch_id)
        rows = q.group_by(
            ReconciliationResult.bank_name, ReconciliationResult.reconciliation_status
        ).all()

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

    def create(self, template_upload_id: int, total_results: int = 0) -> ReconciliationBatch:
        batch = ReconciliationBatch(
            template_upload_id=template_upload_id,
            total_results=total_results,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def update_total(self, batch_id: int, total_results: int) -> None:
        batch = self.db.query(ReconciliationBatch).filter(ReconciliationBatch.id == batch_id).first()
        if batch:
            batch.total_results = total_results
            self.db.commit()

    def get_latest(self) -> Optional[ReconciliationBatch]:
        return (
            self.db.query(ReconciliationBatch)
            .order_by(ReconciliationBatch.created_at.desc())
            .first()
        )

    def get_all(self) -> List[ReconciliationBatch]:
        return (
            self.db.query(ReconciliationBatch)
            .order_by(ReconciliationBatch.created_at.desc())
            .all()
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


# ---------------------------------------------------------------------------
# Company Repository
# ---------------------------------------------------------------------------

class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, tax_id: Optional[str] = None, address: Optional[str] = None) -> Company:
        company = Company(name=name, tax_id=tax_id, address=address)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def get_by_id(self, company_id: int) -> Optional[Company]:
        return self.db.query(Company).filter(Company.id == company_id).first()

    def get_all(self) -> List[Company]:
        return self.db.query(Company).filter(Company.is_active == True).all()


# ---------------------------------------------------------------------------
# FiscalPeriod Repository
# ---------------------------------------------------------------------------

class FiscalPeriodRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> FiscalPeriod:
        period = FiscalPeriod(**data)
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def get_by_id(self, period_id: int) -> Optional[FiscalPeriod]:
        return self.db.query(FiscalPeriod).filter(FiscalPeriod.id == period_id).first()

    def get_all(self, company_id: Optional[int] = None) -> List[FiscalPeriod]:
        q = self.db.query(FiscalPeriod)
        if company_id:
            q = q.filter(FiscalPeriod.company_id == company_id)
        return q.order_by(FiscalPeriod.year.desc(), FiscalPeriod.month.desc()).all()

    def get_open(self, company_id: Optional[int] = None) -> List[FiscalPeriod]:
        q = self.db.query(FiscalPeriod).filter(FiscalPeriod.status == "open")
        if company_id:
            q = q.filter(FiscalPeriod.company_id == company_id)
        return q.all()

    def close_period(self, period_id: int) -> Optional[FiscalPeriod]:
        period = self.get_by_id(period_id)
        if period:
            period.status = "closed"
            self.db.commit()
        return period


# ---------------------------------------------------------------------------
# CostCenter Repository
# ---------------------------------------------------------------------------

class CostCenterRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> CostCenter:
        cc = CostCenter(**data)
        self.db.add(cc)
        self.db.commit()
        self.db.refresh(cc)
        return cc

    def get_by_id(self, cc_id: int) -> Optional[CostCenter]:
        return self.db.query(CostCenter).filter(CostCenter.id == cc_id).first()

    def get_all(self, company_id: Optional[int] = None) -> List[CostCenter]:
        q = self.db.query(CostCenter).filter(CostCenter.is_active == True)
        if company_id:
            q = q.filter(CostCenter.company_id == company_id)
        return q.order_by(CostCenter.code).all()


# ---------------------------------------------------------------------------
# ChartOfAccount Repository
# ---------------------------------------------------------------------------

class ChartOfAccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> ChartOfAccount:
        account = ChartOfAccount(**data)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_by_id(self, account_id: int) -> Optional[ChartOfAccount]:
        return self.db.query(ChartOfAccount).filter(ChartOfAccount.id == account_id).first()

    def get_by_code(self, code: str, company_id: Optional[int] = None) -> Optional[ChartOfAccount]:
        q = self.db.query(ChartOfAccount).filter(ChartOfAccount.code == code)
        if company_id:
            q = q.filter(ChartOfAccount.company_id == company_id)
        return q.first()

    def get_all(self, company_id: Optional[int] = None) -> List[ChartOfAccount]:
        q = self.db.query(ChartOfAccount).filter(ChartOfAccount.is_active == True)
        if company_id:
            q = q.filter(ChartOfAccount.company_id == company_id)
        return q.order_by(ChartOfAccount.code).all()

    def get_roots(self, company_id: Optional[int] = None) -> List[ChartOfAccount]:
        """Cuentas sin padre (nivel raíz)."""
        q = self.db.query(ChartOfAccount).filter(
            ChartOfAccount.parent_id.is_(None),
            ChartOfAccount.is_active == True,
        )
        if company_id:
            q = q.filter(ChartOfAccount.company_id == company_id)
        return q.order_by(ChartOfAccount.code).all()


# ---------------------------------------------------------------------------
# JournalEntry Repository
# ---------------------------------------------------------------------------

class JournalEntryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, entry_data: dict, lines_data: List[dict]) -> JournalEntry:
        entry = JournalEntry(**entry_data)
        self.db.add(entry)
        self.db.flush()  # get entry.id before commit
        for line_data in lines_data:
            line = JournalEntryLine(entry_id=entry.id, **line_data)
            self.db.add(line)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_by_id(self, entry_id: int) -> Optional[JournalEntry]:
        return self.db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()

    def get_all(
        self,
        company_id: Optional[int] = None,
        fiscal_period_id: Optional[int] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[JournalEntry], int]:
        q = self.db.query(JournalEntry)
        if company_id:
            q = q.filter(JournalEntry.company_id == company_id)
        if fiscal_period_id:
            q = q.filter(JournalEntry.fiscal_period_id == fiscal_period_id)
        if status:
            q = q.filter(JournalEntry.status == status)
        total = q.count()
        items = q.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc()).offset(offset).limit(limit).all()
        return items, total

    def get_lines_for_account(
        self,
        account_id: int,
        fiscal_period_id: Optional[int] = None,
        status: str = "posted",
    ) -> List[JournalEntryLine]:
        q = (
            self.db.query(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .filter(
                JournalEntryLine.account_id == account_id,
                JournalEntry.status == status,
            )
        )
        if fiscal_period_id:
            q = q.filter(JournalEntry.fiscal_period_id == fiscal_period_id)
        return q.order_by(JournalEntry.entry_date, JournalEntry.id).all()

    def get_trial_balance(
        self,
        company_id: Optional[int] = None,
        fiscal_period_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Suma débitos y créditos por cuenta para el balance de comprobación."""
        q = (
            self.db.query(
                ChartOfAccount.id.label("account_id"),
                ChartOfAccount.code.label("account_code"),
                ChartOfAccount.name.label("account_name"),
                ChartOfAccount.account_type.label("account_type"),
                func.coalesce(func.sum(JournalEntryLine.debit), 0).label("total_debit"),
                func.coalesce(func.sum(JournalEntryLine.credit), 0).label("total_credit"),
            )
            .join(JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
            .filter(JournalEntry.status == "posted")
        )
        if company_id:
            q = q.filter(JournalEntry.company_id == company_id)
        if fiscal_period_id:
            q = q.filter(JournalEntry.fiscal_period_id == fiscal_period_id)
        rows = q.group_by(
            ChartOfAccount.id, ChartOfAccount.code, ChartOfAccount.name, ChartOfAccount.account_type
        ).order_by(ChartOfAccount.code).all()

        result = []
        for row in rows:
            net = float(row.total_debit) - float(row.total_credit)
            result.append({
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "account_type": row.account_type,
                "total_debit": float(row.total_debit),
                "total_credit": float(row.total_credit),
                "net_balance": net,
            })
        return result


# ---------------------------------------------------------------------------
# Budget Repository
# ---------------------------------------------------------------------------

class BudgetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, budget_data: dict, lines_data: List[dict]) -> Budget:
        budget = Budget(**budget_data)
        self.db.add(budget)
        self.db.flush()
        for line_data in lines_data:
            line = BudgetLine(budget_id=budget.id, **line_data)
            self.db.add(line)
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def get_by_id(self, budget_id: int) -> Optional[Budget]:
        return self.db.query(Budget).filter(Budget.id == budget_id).first()

    def get_all(self, company_id: Optional[int] = None) -> List[Budget]:
        q = self.db.query(Budget)
        if company_id:
            q = q.filter(Budget.company_id == company_id)
        return q.order_by(Budget.created_at.desc()).all()

    def approve(self, budget_id: int, approved_by_id: int) -> Optional[Budget]:
        budget = self.get_by_id(budget_id)
        if budget:
            budget.status = "approved"
            budget.approved_by_id = approved_by_id
            budget.approved_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(budget)
        return budget

    def get_executed_amount(self, budget_id: int, account_id: int) -> float:
        """Calcula el monto ejecutado para una línea presupuestaria."""
        budget = self.get_by_id(budget_id)
        if not budget:
            return 0.0
        row = (
            self.db.query(func.coalesce(func.sum(JournalEntryLine.debit), 0))
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .filter(
                JournalEntryLine.account_id == account_id,
                JournalEntry.fiscal_period_id == budget.fiscal_period_id,
                JournalEntry.status == "posted",
            )
            .scalar()
        )
        return float(row or 0)


# ---------------------------------------------------------------------------
# Invoice Repository
# ---------------------------------------------------------------------------

class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, invoice_data: dict, lines_data: List[dict]) -> Invoice:
        invoice = Invoice(**invoice_data)
        self.db.add(invoice)
        self.db.flush()
        for line_data in lines_data:
            line = InvoiceLine(invoice_id=invoice.id, **line_data)
            self.db.add(line)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_all(
        self,
        company_id: Optional[int] = None,
        invoice_type: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Invoice], int]:
        q = self.db.query(Invoice)
        if company_id:
            q = q.filter(Invoice.company_id == company_id)
        if invoice_type:
            q = q.filter(Invoice.invoice_type == invoice_type)
        if status:
            q = q.filter(Invoice.status == status)
        total = q.count()
        items = q.order_by(Invoice.invoice_date.desc()).offset(offset).limit(limit).all()
        return items, total

    def update_status(self, invoice_id: int, status: str) -> Optional[Invoice]:
        invoice = self.get_by_id(invoice_id)
        if invoice:
            invoice.status = status
            self.db.commit()
            self.db.refresh(invoice)
        return invoice

    def add_payment(self, invoice_id: int, payment_data: dict) -> Payment:
        payment = Payment(invoice_id=invoice_id, **payment_data)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_total_paid(self, invoice_id: int) -> float:
        result = (
            self.db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.invoice_id == invoice_id)
            .scalar()
        )
        return float(result or 0)

    def get_overdue(self, as_of: datetime, company_id: Optional[int] = None) -> List[Invoice]:
        q = self.db.query(Invoice).filter(
            Invoice.due_date < as_of,
            Invoice.status.in_(["issued", "overdue"]),
        )
        if company_id:
            q = q.filter(Invoice.company_id == company_id)
        return q.all()
