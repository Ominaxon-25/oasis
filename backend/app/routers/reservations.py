from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import (
    ReservationCreate,
    ReservationOut,
    ReservationStatusUpdate
)
from app.services.reservation import reservation_service
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/reservations", tags=["Reservations & Concurrency"])


@router.post(
    "",
    response_model=ReservationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Reservation with Row-Level Concurrency Locking",
    responses={
        201: {"description": "Reservation created and confirmed."},
        400: {"description": "Bad Request (e.g. invalid party size or capacity mismatch)."},
        404: {"description": "Restaurant or table not found."},
        409: {"description": "Conflict: Selected table is no longer available for this time slot."}
    }
)
async def create_reservation(
    payload: ReservationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new table reservation protected by database row-level locking (SELECT ... FOR UPDATE).
    If an overlapping reservation exists for the requested slot, the transaction is rolled back
    and HTTP 409 Conflict is returned immediately.
    """
    return await reservation_service.create_reservation(
        db=db,
        payload=payload,
        background_tasks=background_tasks
    )


@router.get(
    "/{id}",
    response_model=ReservationOut,
    summary="Get Reservation Details by ID"
)
async def get_reservation(
    id: int = Path(..., description="Reservation ID", example=1),
    db: AsyncSession = Depends(get_db)
):
    reservation = await db.get(Reservation, id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {id} not found."
        )
    return reservation


@router.patch(
    "/{id}/status",
    response_model=ReservationOut,
    summary="Update Reservation Status (Vendor/Staff)"
)
async def update_reservation_status(
    payload: ReservationStatusUpdate,
    id: int = Path(..., description="Reservation ID", example=1),
    db: AsyncSession = Depends(get_db)
):
    reservation = await db.get(Reservation, id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {id} not found."
        )

    old_status = reservation.status
    reservation.status = payload.status
    await db.commit()
    await db.refresh(reservation)

    res_out = ReservationOut.model_validate(reservation)

    # Broadcast status change to vendor floor plan
    await ws_manager.broadcast(
        restaurant_id=reservation.restaurant_id,
        event_type="RESERVATION_STATUS_UPDATED",
        data={
            "reservation": res_out.model_dump(mode="json"),
            "old_status": old_status.value if hasattr(old_status, "value") else str(old_status),
            "new_status": payload.status.value
        }
    )

    return res_out
