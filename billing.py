from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ChargeCreate(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(None, max_length=1000)


class ChargeResponse(ChargeCreate):
    id: int
    service_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BillCreate(BaseModel):
    service_id: int = Field(gt=0)
    discount: Decimal = Field(default=Decimal('0'), ge=0, max_digits=14, decimal_places=2)
    tax_percent: Decimal = Field(default=Decimal('0'), ge=0, le=100, decimal_places=2)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: Literal['Cash', 'UPI', 'Card', 'Bank Transfer']
    reference: str | None = Field(None, max_length=100)


class PaymentResponse(PaymentCreate):
    id: int
    bill_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BillResponse(BaseModel):
    id: int
    bill_number: str
    service_id: int
    labour_total: Decimal
    parts_total: Decimal
    discount: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    final_amount: Decimal
    amount_paid: Decimal
    balance: Decimal
    payment_status: Literal['Pending', 'Paid', 'Partially Paid']
    details: dict
    created_at: datetime
