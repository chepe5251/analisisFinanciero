"""
Configuración de pytest.
"""
import pytest


@pytest.fixture(autouse=True)
def no_db_calls(monkeypatch):
    """
    Fixture global: los tests unitarios no necesitan BD real.
    Si algún test necesita BD, debe usar su propio fixture.
    """
    pass
