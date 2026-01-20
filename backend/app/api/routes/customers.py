from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.core.security import require_admin
from app.models import Customer
from app.schemas.customer import CustomerCreate, CustomerOut

router = APIRouter()


@router.get("/", response_model=List[CustomerOut], dependencies=[Depends(require_admin)])
def list_customers(db: Session = Depends(get_db)) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.id.desc())
    return list(db.scalars(stmt).all())


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerOut, dependencies=[Depends(require_admin)])
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
