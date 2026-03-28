"""
Configuración de pytest con base de datos SQLite en memoria para tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    from app.models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    from app.main import app
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db):
    from app.models.models import User
    user = User(
        username="testadmin",
        email="testadmin@test.com",
        hashed_password=hash_password("Admin1234!"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def operator_user(db):
    from app.models.models import User
    user = User(
        username="testoperator",
        email="testoperator@test.com",
        hashed_password=hash_password("Operator1234!"),
        full_name="Test Operator",
        role="operator",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def viewer_user(db):
    from app.models.models import User
    user = User(
        username="testviewer",
        email="testviewer@test.com",
        hashed_password=hash_password("Viewer1234!"),
        full_name="Test Viewer",
        role="viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_token(client, credential: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"credential": credential, "password": password})
    return resp.json().get("access_token", "")


@pytest.fixture()
def admin_token(client, admin_user):
    return _get_token(client, "testadmin", "Admin1234!")


@pytest.fixture()
def operator_token(client, operator_user):
    return _get_token(client, "testoperator", "Operator1234!")


@pytest.fixture()
def viewer_token(client, viewer_user):
    return _get_token(client, "testviewer", "Viewer1234!")


@pytest.fixture()
def fiscal_period(db):
    from app.models.models import FiscalPeriod
    from datetime import datetime
    period = FiscalPeriod(
        year=2024, month=1, name="Enero 2024",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        status="open",
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@pytest.fixture()
def income_account(db):
    from app.models.models import ChartOfAccount
    acc = ChartOfAccount(code="4001", name="Ventas", account_type="income", level=1)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@pytest.fixture()
def expense_account(db):
    from app.models.models import ChartOfAccount
    acc = ChartOfAccount(code="5001", name="Sueldos", account_type="expense", level=1)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc
