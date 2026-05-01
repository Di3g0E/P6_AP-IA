"""
Endpoints REST de transacciones para clientes que prefieren acceso directo
en vez de pasar por el chat.

  - POST   /transactions               — alta manual.
  - GET    /transactions/pending       — lista las marcadas para revisión.
  - POST   /transactions/pending/{id}/confirm — aprueba una pendiente.
  - DELETE /transactions/pending/{id}  — rechaza una pendiente.

Todos requieren `Authorization: Bearer <token>`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.agents.contracts import ManualEntry
from src.agents.registrar import agent as registrar
from src.api.dependencies import get_current_user_id


router = APIRouter(prefix="/transactions", tags=["transactions"])


# Schemas de respuesta

class TransactionRecordOut(BaseModel):
    id: str
    description: str
    date: date
    amount: Decimal
    currency: str
    area: list[str]
    type: Literal["Income", "Expenses"]
    source: str
    status: Literal["accepted", "pending", "rejected"]


class PendingReviewOut(BaseModel):
    record: TransactionRecordOut
    anomaly_reasons: list[str]


class ManualTransactionRequest(BaseModel):
    description: str = Field(..., min_length=1)
    date: date
    amount: Decimal
    type: Literal["Income", "Expenses"]
    area: Optional[list[str]] = Field(
        None,
        description="Lista opcional de categorías. Si se omite, el clasificador la inferirá.",
    )


class ManualTransactionResponse(BaseModel):
    accepted: list[TransactionRecordOut] = []
    pending_review: list[PendingReviewOut] = []
    rejected: list[dict] = []


# Helpers para serializar TransactionRecord (Pydantic) → dict de salida

def _record_to_out(record) -> TransactionRecordOut:
    return TransactionRecordOut(
        id=record.id,
        description=record.description,
        date=record.date,
        amount=record.amount,
        currency=record.currency,
        area=record.area,
        type=record.type,
        source=record.source,
        status=record.status,
    )


# Endpoints

@router.post(
    "",
    response_model=ManualTransactionResponse,
    summary="Alta manual de transacción",
)
def add_manual(
    body: ManualTransactionRequest,
    user_id: str = Depends(get_current_user_id),
) -> ManualTransactionResponse:
    entry = ManualEntry(
        user_id=user_id,
        description=body.description,
        date=body.date,
        amount=body.amount,
        type=body.type,
        area=body.area,
    )
    result = registrar.add_manual_transaction(entry)
    return ManualTransactionResponse(
        accepted=[_record_to_out(r) for r in result.accepted],
        pending_review=[
            PendingReviewOut(record=_record_to_out(p.record),
                             anomaly_reasons=p.anomaly_reasons)
            for p in result.pending_review
        ],
        rejected=[{"reason": r.reason} for r in result.rejected],
    )


@router.get(
    "/pending",
    response_model=list[PendingReviewOut],
    summary="Listar transacciones pendientes de revisión",
)
def list_pending(
    user_id: str = Depends(get_current_user_id),
) -> list[PendingReviewOut]:
    result = registrar.list_pending_reviews(user_id)
    return [
        PendingReviewOut(
            record=_record_to_out(p.record),
            anomaly_reasons=p.anomaly_reasons,
        )
        for p in result.pending_review
    ]


@router.post(
    "/pending/{transaction_id}/confirm",
    response_model=TransactionRecordOut,
    summary="Aprobar una transacción pendiente",
)
def confirm_pending(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TransactionRecordOut:
    result = registrar.confirm_pending(user_id, transaction_id)
    if result.accepted:
        return _record_to_out(result.accepted[0])

    # Hubo un error; el motivo está en rejected[0].reason
    reason = (result.rejected[0].reason if result.rejected
              else "No se pudo confirmar la transacción.")
    if "no encontrada" in reason.lower():
        raise HTTPException(status.HTTP_404_NOT_FOUND, reason)
    if "uuid" in reason.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    raise HTTPException(status.HTTP_409_CONFLICT, reason)


@router.delete(
    "/pending/{transaction_id}",
    summary="Rechazar una transacción pendiente",
)
def reject_pending(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    result = registrar.reject_pending(user_id, transaction_id)
    if not result.rejected:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Resultado vacío inesperado")

    item = result.rejected[0]
    raw = item.raw_input or {}
    if raw.get("transaction_id") == transaction_id:
        # Camino feliz: el usuario rechazó la transacción.
        return {"id": transaction_id, "status": "rejected"}

    # Error real
    reason = item.reason
    if "no encontrada" in reason.lower():
        raise HTTPException(status.HTTP_404_NOT_FOUND, reason)
    if "uuid" in reason.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    raise HTTPException(status.HTTP_409_CONFLICT, reason)
