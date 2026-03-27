"""
Procesamiento y normalización de archivos CSV/Excel.

Estrategia de normalización:
  1. Se leen las columnas del archivo tal como vienen.
  2. Se normalizan a minúsculas y sin espacios extra.
  3. Se aplica el mapeo del banco específico (si existe) para renombrar columnas.
  4. Como fallback se intenta un mapeo genérico por alias comunes.
  5. El resultado es siempre un DataFrame con columnas internas estándar.

Supuesto: si un banco no está en BANK_COLUMN_MAPPINGS, el sistema intenta
detectar automáticamente las columnas con el mapeo genérico GENERIC_ALIASES.
Esto permite onboardear nuevos bancos sin cambiar código.
"""
import pandas as pd
import re
from typing import Dict, List, Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Mapeos por banco
# Formato: { columna_original_en_minúsculas: columna_interna }
# ---------------------------------------------------------------------------

BANK_COLUMN_MAPPINGS: Dict[str, Dict[str, str]] = {
    "banco_a": {
        "fecha": "transaction_date",
        "beneficiario": "beneficiary_name",
        "cuenta": "beneficiary_account",
        "importe": "amount",
        "referencia": "reference",
    },
    "banco b": {  # también acepta nombre con espacio
        "date": "transaction_date",
        "name": "beneficiary_name",
        "account": "beneficiary_account",
        "amount": "amount",
        "detail": "reference",
    },
    "banco_b": {
        "date": "transaction_date",
        "name": "beneficiary_name",
        "account": "beneficiary_account",
        "amount": "amount",
        "detail": "reference",
    },
    "banco_c": {
        "fecha_transaccion": "transaction_date",
        "nombre": "beneficiary_name",
        "cuenta_destino": "beneficiary_account",
        "monto": "amount",
        "descripcion": "reference",
    },
    "banco c": {
        "fecha_transaccion": "transaction_date",
        "nombre": "beneficiary_name",
        "cuenta_destino": "beneficiary_account",
        "monto": "amount",
        "descripcion": "reference",
    },
}

# Aliases genéricos usados cuando el banco no tiene mapeo explícito.
# Clave: posibles nombres de columna; Valor: nombre interno.
GENERIC_ALIASES: Dict[str, str] = {
    # Fecha
    "fecha": "transaction_date",
    "date": "transaction_date",
    "fecha_transaccion": "transaction_date",
    "fecha_pago": "transaction_date",
    "payment_date": "transaction_date",
    # Beneficiario
    "beneficiario": "beneficiary_name",
    "nombre": "beneficiary_name",
    "name": "beneficiary_name",
    "empleado": "beneficiary_name",
    "employee": "beneficiary_name",
    "beneficiary": "beneficiary_name",
    "beneficiary_name": "beneficiary_name",
    # Cuenta
    "cuenta": "beneficiary_account",
    "account": "beneficiary_account",
    "cuenta_destino": "beneficiary_account",
    "account_number": "beneficiary_account",
    "numero_cuenta": "beneficiary_account",
    # Monto
    "importe": "amount",
    "monto": "amount",
    "amount": "amount",
    "valor": "amount",
    "total": "amount",
    # Referencia
    "referencia": "reference",
    "reference": "reference",
    "detalle": "reference",
    "detail": "reference",
    "descripcion": "reference",
    "description": "reference",
    "concepto": "reference",
    # Moneda
    "moneda": "currency",
    "currency": "currency",
    "divisa": "currency",
    # Estado
    "estado": "status",
    "status": "status",
    "resultado": "status",
}

# Columnas internas de la plantilla de personal
TEMPLATE_COLUMN_MAPPINGS: Dict[str, str] = {
    "employee_id": "employee_id",
    "id_empleado": "employee_id",
    "codigo": "employee_id",
    "full_name": "full_name",
    "nombre": "full_name",
    "nombre_completo": "full_name",
    "name": "full_name",
    "identificacion": "identification",
    "identification": "identification",
    "cedula": "identification",
    "dni": "identification",
    "banco": "bank_name",
    "bank": "bank_name",
    "bank_name": "bank_name",
    "banco_nombre": "bank_name",
    "cuenta": "account_number",
    "account": "account_number",
    "account_number": "account_number",
    "numero_cuenta": "account_number",
    "monto_esperado": "expected_amount",
    "expected_amount": "expected_amount",
    "salario": "expected_amount",
    "sueldo": "expected_amount",
    "amount": "expected_amount",
    "moneda": "currency",
    "currency": "currency",
}


class FileProcessor:
    """Utilidades estáticas de lectura y normalización de archivos."""

    @staticmethod
    def read_csv(file_path: str) -> pd.DataFrame:
        """Lee CSV intentando UTF-8 y luego latin-1 como fallback."""
        try:
            return pd.read_csv(file_path, encoding="utf-8", dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="latin-1", dtype=str)

    @staticmethod
    def read_excel(file_path: str) -> pd.DataFrame:
        return pd.read_excel(file_path, dtype=str)

    @staticmethod
    def normalize_columns(
        df: pd.DataFrame,
        mappings: Dict[str, str],
        use_generic_fallback: bool = True,
    ) -> pd.DataFrame:
        """
        Normaliza nombres de columnas:
        1. Convierte a minúsculas y elimina espacios.
        2. Aplica el mapeo específico provisto.
        3. Si use_generic_fallback=True, aplica GENERIC_ALIASES para las que no mapearon.
        """
        result = df.copy()
        # Normalizar nombres actuales
        result.columns = [col.lower().strip().replace(" ", "_") for col in result.columns]

        # Aplicar mapeo específico
        result = result.rename(columns={k.lower(): v for k, v in mappings.items()})

        # Fallback genérico para columnas aún no mapeadas
        if use_generic_fallback:
            remaining = {
                col: GENERIC_ALIASES[col]
                for col in result.columns
                if col in GENERIC_ALIASES and col not in result.columns
            }
            if remaining:
                result = result.rename(columns=remaining)

        return result

    @staticmethod
    def get_bank_mapping(bank_name: str) -> Dict[str, str]:
        """Devuelve el mapeo de columnas para un banco dado."""
        key = bank_name.lower().strip()
        return BANK_COLUMN_MAPPINGS.get(key, {})

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        Intenta parsear una cadena de fecha con múltiples formatos.
        Retorna None si no puede parsearse (en lugar de lanzar excepción).
        """
        if not date_str or pd.isna(date_str):
            return None

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def clean_amount(value) -> float:
        """
        Limpia y convierte un valor a float.
        Maneja: '1,500.00', '1.500,00', '$1500', '1500', etc.
        """
        if isinstance(value, (int, float)):
            return float(value)

        cleaned = re.sub(r"[^\d.,-]", "", str(value).strip())

        # Formato europeo: '1.500,00'
        if re.match(r"^\d{1,3}(\.\d{3})*(,\d+)?$", cleaned):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Formato americano con coma como separador de miles: '1,500.00'
        elif "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        # Solo coma como decimal: '1500,50'
        elif "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except ValueError:
            raise ValueError(f"No se puede convertir a monto: '{value}'")

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normaliza un nombre para comparación aproximada:
        minúsculas, sin acentos, sin caracteres especiales.
        """
        if not name:
            return ""
        name = name.lower().strip()
        # Reemplazar caracteres acentuados comunes
        replacements = {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "ä": "a", "ë": "e", "ï": "i", "ö": "o", "ü": "u",
            "ñ": "n",
        }
        for accented, plain in replacements.items():
            name = name.replace(accented, plain)
        # Colapsar espacios múltiples
        return re.sub(r"\s+", " ", name).strip()

    @staticmethod
    def name_similarity(name_a: str, name_b: str) -> float:
        """
        Calcula similitud simple entre dos nombres normalizados.
        Usa intersección de tokens (palabras) sobre la unión.
        Supuesto: orden de palabras no importa ('Juan Pérez' ≈ 'Pérez Juan').
        """
        tokens_a = set(FileProcessor.normalize_name(name_a).split())
        tokens_b = set(FileProcessor.normalize_name(name_b).split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    @staticmethod
    def validate_required_columns(df: pd.DataFrame, required: List[str]) -> List[str]:
        """Retorna lista de columnas requeridas que faltan en el DataFrame."""
        return [col for col in required if col not in df.columns]
