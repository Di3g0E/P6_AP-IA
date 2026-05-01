"""
Agente Analyst — operaciones expuestas al Orquestador.

Cada operación devuelve un `AnalysisReport` (dataclass del contrato), nunca
texto libre: el Orquestador es el único que narra al usuario.

Operaciones (ver doc/agent_contracts.md):
  - monthly_summary
  - category_breakdown
  - spending_trends
  - savings_rate
  - detect_anomalies
  - recurring_expenses
  - predict_next_month
  - check_goals  (dispara `notify_goal_threshold` si pct >= 0.80)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import pandas as pd
from loguru import logger

from src.agents.analyst import analytics, forecasters
from src.agents.contracts import (
    AnalysisReport, DataPoint, Goal, GoalAlert,
)
from src.utils.notifications import (
    UserNotificationConfig, notify_goal_threshold,
)


# Operaciones puramente analíticas (devuelven AnalysisReport)

def monthly_summary(df: pd.DataFrame, year: Optional[int] = None,
                    month: Optional[int] = None) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="summary", metrics={"empty": True})
    metrics = analytics.compute_monthly_summary(df, year=year, month=month)
    return AnalysisReport(type="summary", period=metrics.get("period"),
                          metrics=metrics)


def category_breakdown(df: pd.DataFrame, period: Optional[str] = None) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="category", metrics={"empty": True})
    metrics = analytics.compute_category_breakdown(df, period=period)
    return AnalysisReport(type="category", period=period, metrics=metrics)


def spending_trends(df: pd.DataFrame, n_months: int = 6) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="trend", metrics={"empty": True})
    metrics = analytics.compute_spending_trends(df, n_months=n_months)
    series = [DataPoint(label=k, value=v) for k, v in metrics["monthly_totals"].items()]
    return AnalysisReport(type="trend", metrics=metrics, series=series)


def savings_rate(df: pd.DataFrame, n_months: int = 6) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="savings_rate", metrics={"empty": True})
    metrics = analytics.compute_savings_rate(df, n_months=n_months)
    series = [DataPoint(label=k, value=v) for k, v in metrics["monthly_rates"].items()]
    return AnalysisReport(type="savings_rate", metrics=metrics, series=series)


def detect_anomalies(df: pd.DataFrame) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="anomaly", metrics={"empty": True, "anomalies": []})
    items = analytics.detect_anomalies(df)
    return AnalysisReport(type="anomaly", metrics={"anomalies": items, "count": len(items)})


def recurring_expenses(df: pd.DataFrame) -> AnalysisReport:
    if df.empty:
        return AnalysisReport(type="recurring", metrics={"empty": True, "items": []})
    items = analytics.compute_recurring_expenses(df)
    return AnalysisReport(type="recurring", metrics={"items": items, "count": len(items)})


def recent_transactions(df: pd.DataFrame, n: int = 10) -> AnalysisReport:
    """
    Devuelve las N transacciones más recientes (orden descendente por fecha).

    Útil para "muéstrame mi último gasto" / "qué he registrado hoy".
    """
    if df.empty:
        return AnalysisReport(type="summary", metrics={"empty": True, "items": []})

    # `df` viene ya ordenado descendente por Date_parsed desde el data_source.
    head = df.head(max(1, int(n)))
    items = [
        {
            "date": row["Date"],
            "description": row["Description"],
            "amount": round(float(row["Amount_clean"]), 2),
            "area": row["Area"],
            "type": row["Type"],
        }
        for _, row in head.iterrows()
    ]
    return AnalysisReport(
        type="summary",
        metrics={"items": items, "count": len(items), "kind": "recent_transactions"},
    )


def predict_next_month(df: pd.DataFrame, area: Optional[str] = None,
                       method: str = "rf") -> AnalysisReport:
    """Predice gasto del próximo mes. Si `area` se especifica, filtra por categoría."""
    if df.empty:
        return AnalysisReport(type="prediction", metrics={"empty": True})

    expenses = df[df["Type"] == "Expenses"]
    if area:
        expenses = expenses[expenses["Area"] == area]

    monthly = expenses.groupby("YearMonth")["Amount_clean"].sum().sort_index()
    if len(monthly) < 6:
        return AnalysisReport(type="prediction",
                              metrics={"error": f"Histórico insuficiente: {len(monthly)} meses (mínimo 6)"})

    try:
        result = forecasters.predict_next_month(monthly, method=method)
    except Exception as e:
        return AnalysisReport(type="prediction", metrics={"error": str(e)})

    series = [DataPoint(label=str(k), value=float(v)) for k, v in monthly.items()]
    metrics = {
        "area": area or "all",
        "history_months": len(monthly),
        **result,
    }
    return AnalysisReport(type="prediction", metrics=metrics, series=series)


# Operación con efectos: check_goals dispara notificaciones

def check_goals(
    df: pd.DataFrame,
    goals: list[Goal],
    notif_config: Optional[UserNotificationConfig] = None,
) -> AnalysisReport:
    """Evalúa cada objetivo activo y dispara notificación si pct >= 0.80.

    Args:
        df: transacciones del usuario.
        goals: lista de objetivos activos.
        notif_config: si se proporciona, se envía `notify_goal_threshold`
            por cada objetivo que supere el umbral.
    """
    alerts: list[GoalAlert] = []

    for g in goals:
        if not g.active:
            continue

        # Evaluamos en el mes en curso (último presente en df)
        if df.empty or "YearMonth" not in df.columns:
            continue

        latest_period = df["YearMonth"].max()
        period_df = df[(df["YearMonth"] == latest_period) & (df["Type"] == "Expenses")]
        spent = period_df[period_df["Area"] == g.area]["Amount_clean"].sum()

        limit = float(g.max_amount)
        pct = float(spent) / limit if limit > 0 else 0.0
        if pct < 0.80:
            continue

        severity: str = "critical" if pct >= 1.0 else "warning"
        alert = GoalAlert(
            goal_id=g.id or "",
            area=g.area,
            current=Decimal(str(round(float(spent), 2))),
            limit=g.max_amount,
            pct=round(pct, 3),
            severity=severity,  # type: ignore[arg-type]
        )
        alerts.append(alert)

        if notif_config is not None:
            try:
                notify_goal_threshold(
                    notif_config,
                    area=g.area, current=alert.current, limit=alert.limit, pct=alert.pct,
                )
            except Exception as e:
                logger.warning(f"Fallo al notificar goal_threshold: {e}")

    return AnalysisReport(
        type="goal_status",
        metrics={"alerts_count": len(alerts), "goals_evaluated": len(goals)},
        goal_alerts=alerts,
    )
