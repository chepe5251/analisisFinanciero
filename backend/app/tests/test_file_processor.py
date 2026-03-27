"""
Tests de la capa de procesamiento y normalización de archivos.
"""
import pytest
import pandas as pd
import tempfile
import os

from app.utils.file_processor import FileProcessor, BANK_COLUMN_MAPPINGS, TEMPLATE_COLUMN_MAPPINGS


class TestCleanAmount:
    def test_float_passthrough(self):
        assert FileProcessor.clean_amount(1500.0) == 1500.0

    def test_int_passthrough(self):
        assert FileProcessor.clean_amount(1500) == 1500.0

    def test_string_plain(self):
        assert FileProcessor.clean_amount("1500") == 1500.0

    def test_string_with_comma_decimal(self):
        assert FileProcessor.clean_amount("1500,50") == 1500.50

    def test_string_american_format(self):
        assert FileProcessor.clean_amount("1,500.00") == 1500.0

    def test_string_european_format(self):
        assert FileProcessor.clean_amount("1.500,00") == 1500.0

    def test_string_with_currency_symbol(self):
        assert FileProcessor.clean_amount("$1500.00") == 1500.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            FileProcessor.clean_amount("no_es_numero")


class TestParseDate:
    def test_iso_format(self):
        d = FileProcessor.parse_date("2024-01-15")
        assert d is not None
        assert d.year == 2024
        assert d.month == 1
        assert d.day == 15

    def test_latam_format(self):
        d = FileProcessor.parse_date("15/01/2024")
        assert d is not None
        assert d.day == 15

    def test_us_format(self):
        d = FileProcessor.parse_date("01/15/2024")
        assert d is not None

    def test_invalid_returns_none(self):
        assert FileProcessor.parse_date("not-a-date") is None

    def test_none_returns_none(self):
        assert FileProcessor.parse_date(None) is None


class TestNormalizeName:
    def test_lowercase(self):
        assert FileProcessor.normalize_name("JUAN PÉREZ") == "juan perez"

    def test_accent_removal(self):
        assert FileProcessor.normalize_name("María García") == "maria garcia"

    def test_extra_spaces(self):
        assert FileProcessor.normalize_name("  Juan   Pérez  ") == "juan perez"


class TestNameSimilarity:
    def test_exact_match(self):
        score = FileProcessor.name_similarity("Juan Pérez", "Juan Pérez")
        assert score == 1.0

    def test_accent_difference(self):
        # Carmen Jiménez vs Carmen Jimenez
        score = FileProcessor.name_similarity("Carmen Jiménez", "Carmen Jimenez")
        assert score >= 0.8

    def test_word_order_independent(self):
        score = FileProcessor.name_similarity("Juan Pérez", "Pérez Juan")
        assert score == 1.0

    def test_partial_match(self):
        score = FileProcessor.name_similarity("Juan Carlos Pérez", "Juan Pérez")
        assert 0.5 < score < 1.0

    def test_no_match(self):
        score = FileProcessor.name_similarity("Juan Pérez", "Pedro Alvarado")
        assert score == 0.0

    def test_empty_string(self):
        score = FileProcessor.name_similarity("", "Juan Pérez")
        assert score == 0.0


class TestNormalizeColumns:
    def test_banco_a_mapping(self):
        df = pd.DataFrame({
            "fecha": ["2024-01-15"],
            "beneficiario": ["Juan"],
            "cuenta": ["123"],
            "importe": ["1500"],
            "referencia": ["REF001"],
        })
        mapping = BANK_COLUMN_MAPPINGS["banco_a"]
        result = FileProcessor.normalize_columns(df, mapping)
        assert "transaction_date" in result.columns
        assert "beneficiary_name" in result.columns
        assert "beneficiary_account" in result.columns
        assert "amount" in result.columns
        assert "reference" in result.columns

    def test_banco_b_mapping(self):
        df = pd.DataFrame({
            "date": ["15/01/2024"],
            "name": ["María García"],
            "account": ["0987654321"],
            "amount": ["1200.00"],
            "detail": ["Salary"],
        })
        mapping = BANK_COLUMN_MAPPINGS["banco_b"]
        result = FileProcessor.normalize_columns(df, mapping)
        assert "beneficiary_name" in result.columns
        assert "amount" in result.columns

    def test_template_mapping(self):
        df = pd.DataFrame({
            "employee_id": ["EMP001"],
            "nombre": ["Juan Pérez"],
            "banco": ["Banco_A"],
            "cuenta": ["1234567890"],
            "monto_esperado": ["1500.00"],
        })
        result = FileProcessor.normalize_columns(df, TEMPLATE_COLUMN_MAPPINGS)
        assert "full_name" in result.columns
        assert "bank_name" in result.columns
        assert "account_number" in result.columns
        assert "expected_amount" in result.columns

    def test_case_insensitive(self):
        df = pd.DataFrame({"FECHA": ["2024-01-15"], "IMPORTE": ["1500"]})
        mapping = BANK_COLUMN_MAPPINGS["banco_a"]
        result = FileProcessor.normalize_columns(df, mapping)
        assert "transaction_date" in result.columns

    def test_generic_fallback(self):
        df = pd.DataFrame({"monto": ["1500"], "nombre": ["Juan"]})
        result = FileProcessor.normalize_columns(df, {}, use_generic_fallback=True)
        assert "amount" in result.columns
        assert "beneficiary_name" in result.columns


class TestValidateRequiredColumns:
    def test_all_present(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        missing = FileProcessor.validate_required_columns(df, ["a", "b"])
        assert missing == []

    def test_missing_column(self):
        df = pd.DataFrame({"a": [1]})
        missing = FileProcessor.validate_required_columns(df, ["a", "b"])
        assert "b" in missing

    def test_csv_read_and_map(self):
        """Prueba end-to-end: leer CSV de banco_a y normalizar."""
        csv_content = "fecha,beneficiario,cuenta,importe,referencia\n2024-01-15,Juan,123,1500,REF"
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            path = f.name
        try:
            df = FileProcessor.read_csv(path)
            df = FileProcessor.normalize_columns(df, BANK_COLUMN_MAPPINGS["banco_a"])
            assert "beneficiary_name" in df.columns
            assert df["beneficiary_name"].iloc[0] == "Juan"
        finally:
            os.unlink(path)
