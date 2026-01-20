from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.core.security import require_admin
from app.models import Order
from app.models import Payment
from app.schemas.payment import PaymentCreate, PaymentOut, PaymentUpdate

router = APIRouter()


class PaymentVerifyRequest(BaseModel):
    """Request body for payment verification."""
    order_id: int
    success: bool
    provider_ref: str = ""


@router.get("/", response_model=List[PaymentOut], dependencies=[Depends(require_admin)])
def list_payments(db: Session = Depends(get_db)) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.id.desc())
    return list(db.scalars(stmt).all())


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)) -> Payment:
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = Payment(
        order_id=payload.order_id,
        payment_method=payload.payment_method,
        provider_ref=payload.provider_ref,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/verify", response_model=PaymentOut)
def verify_payment(payload: PaymentVerifyRequest, db: Session = Depends(get_db)) -> Payment:
    """
    Mock payment verification endpoint.
    In production, this would verify with actual payment gateway.
    """
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check if payment already exists for this order
    stmt = select(Payment).where(Payment.order_id == payload.order_id)
    existing_payment = db.scalars(stmt).first()

    if existing_payment:
        # Update existing payment
        existing_payment.status = "paid" if payload.success else "failed"
        existing_payment.provider_ref = payload.provider_ref or existing_payment.provider_ref
        db.add(existing_payment)
        payment = existing_payment
    else:
        # Create new payment record
        payment = Payment(
            order_id=payload.order_id,
            payment_method="card",
            provider_ref=payload.provider_ref,
            status="paid" if payload.success else "failed"
        )
        db.add(payment)

    # Update order status based on payment result
    if payload.success:
        order.payment_status = "paid"
        order.order_status = "confirmed"
    else:
        order.payment_status = "failed"

    db.add(order)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentOut, dependencies=[Depends(require_admin)])
def update_payment(payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = payload.status
    db.add(payment)

    # convenience: if payment marked as paid, also update order
    if payload.status.lower() in {"paid", "succeeded", "success"}:
        order = db.get(Order, payment.order_id)
        if order:
            order.payment_status = "paid"
            order.order_status = "confirmed"
            db.add(order)

    db.commit()
    db.refresh(payment)
    return payment