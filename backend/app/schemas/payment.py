from __future__ import annotations

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str = Field(default="card", min_length=2, max_length=50)
    provider_ref: str = ""


class PaymentUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=50)


class PaymentOut(BaseModel):
    id: int
    order_id: int
    payment_method: str
    status: str
    provider_ref: str

    class Config:
        from_attributes = True
