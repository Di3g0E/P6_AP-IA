"""
Carga de transacciones para el agente Analyst.

Origen: P4_AP-IA/src/data/loader.py — adaptado para P6:
  - `load_from_csv(path)`: usa el formato del CSV de P5 (Description, Date,
    Amount con '€' y coma decimal, Area, Type).
  - `load_from_db(user_id)`: lee la tabla `transactions` de Postgres y la
    transforma al mismo esquema con columnas derivadas (Year, Month, YearMonth,
    Amount_clean, Date_parsed) que esperan los analytics.

Las dos funciones devuelven un DataFrame compatible con `analytics.py`.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.schema import Transaction


# Path al CSV de demo (mismo que usa init_db.py)
_DEFAULT_CSV = Path(__file__).resolve().parents[3] / "data" / "raw" / "db_mod_descript.csv"

_EMPTY_DF_COLUMNS = [
    "Description", "Date", "Amount_clean", "Area", "Type",
    "Date_parsed", "Year", "Month", "YearMonth",
]


def _parse_amount_eur(series: pd.Series) -> pd.Series:
    """Convierte '10,00€' o '1.234,50€' a float (10.00, 1234.50)."""
    return (
        series.astype(str)
        .str.replace("€", "", regex=False)
        .str.replace(".", "", regex=False)   # separador de miles
        .str.replace(",", ".", regex=False)  # decimal
        .astype(float)
    )


def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Añade Year, Month, YearMonth y ordena por fecha descendente."""
    df["Year"] = df["Date_parsed"].dt.year
    df["Month"] = df["Date_parsed"].dt.month
    df["YearMonth"] = df["Date_parsed"].dt.to_period("M")
    return df.sort_values("Date_parsed", ascending=False).reset_index(drop=True)


def load_from_csv(path: str | Path) -> pd.DataFrame:
    """
    Carga el CSV con formato P5 (`Description, Date, Amount, Area, Type`).

    Útil para arranque sin BD (smoke tests, modo demo).
    """
    df = pd.read_csv(path)
    df["Amount_clean"] = _parse_amount_eur(df["Amount"])
    df["Date_parsed"] = pd.to_datetime(df["Date"], dayfirst=True)
    return _add_derived_columns(df)


def load_from_db(
    session: Session,
    user_id: str | uuid.UUID,
    *,
    only_accepted: bool = True,
) -> pd.DataFrame:
    """
    Carga las transacciones de un usuario desde la BD y las transforma al
    esquema esperado por `analytics.py`.

    Acepta `user_id` como string o UUID; convierte si hace falta porque la
    columna `transactions.user_id` es de tipo `Uuid`.

    El campo `area` en BD es JSON (lista) — lo unimos con coma para
    mantener compatibilidad con los analytics que esperan `Area: str`.

    Args:
        only_accepted: si True (default) solo lee transacciones con
            `status='accepted'`. Las pendientes y rechazadas NO se cuentan
            en analytics hasta que el usuario las confirme.
    """
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if only_accepted:
        stmt = stmt.where(Transaction.status == "accepted")
    rows = session.execute(stmt).scalars().all()

    if not rows:
        # DataFrame vacío con las columnas esperadas
        return pd.DataFrame(columns=[
            "Description", "Date", "Amount_clean", "Area", "Type",
            "Date_parsed", "Year", "Month", "YearMonth",
        ])

    records = [{
        "Description": r.description,
        "Date": r.date.strftime("%d/%m/%Y"),
        "Amount_clean": float(r.amount),
        "Area": ", ".join(r.area) if r.area else "",
        "Type": r.type,
        "Date_parsed": pd.Timestamp(r.date),
    } for r in rows]

    df = pd.DataFrame(records)
    return _add_derived_columns(df)


def _safe_csv_fallback() -> pd.DataFrame:
    """Carga el CSV demo si existe; si no, DataFrame vacío con el esquema esperado."""
    if not _DEFAULT_CSV.exists():
        logger.warning(f"CSV demo no existe en {_DEFAULT_CSV}; devolviendo DataFrame vacío")
        return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)
    return load_from_csv(_DEFAULT_CSV)


def load_user_history_db_only(user_id: str) -> pd.DataFrame:
    """
    Lee SOLO de la BD las transacciones del usuario. Sin fallback al CSV.

    Útil cuando consumir datos ajenos al usuario daría una respuesta
    incorrecta (p. ej. el detector de anomalías del Security: validar contra
    el histórico de otro usuario sería un sinsentido). Si no hay datos del
    usuario, devuelve un DataFrame vacío y el llamador decide qué hacer.
    """
    try:
        from src.data.database import get_session, is_database_configured
    except Exception as e:
        logger.debug(f"BD no importable: {e}")
        return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

    if not is_database_configured() or not user_id:
        return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

    try:
        uuid.UUID(user_id)
    except ValueError:
        return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

    try:
        with get_session() as session:
            return load_from_db(session, user_id)
    except Exception as e:
        logger.warning(f"Lectura DB-only falló: {e}")
        return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)


def load_user_transactions(user_id: str) -> pd.DataFrame:
    """
    Helper compartido entre agentes: carga las transacciones de un usuario.

      1. Si la BD está configurada y tiene datos para `user_id` → DB.
      2. Si no → CSV demo si existe.
      3. Si tampoco hay CSV → DataFrame vacío con el esquema correcto.

    Centraliza la lógica para que `nodes.py` (Analyst) y `security/agent.py`
    (validate_transaction) compartan exactamente el mismo origen de datos.
    """
    try:
        from src.data.database import get_session, is_database_configured
    except Exception as e:
        logger.debug(f"BD no importable, usando CSV: {e}")
        return _safe_csv_fallback()

    if not is_database_configured() or not user_id:
        return _safe_csv_fallback()

    try:
        uuid.UUID(user_id)
    except ValueError:
        return _safe_csv_fallback()

    try:
        with get_session() as session:
            df = load_from_db(session, user_id)
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"Lectura de BD falló, fallback a CSV: {e}")

    return _safe_csv_fallback()
