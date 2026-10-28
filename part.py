from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PartBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    part_number: str = Field(min_length=2, max_length=60, pattern=r'^[A-Z0-9_-]+$')
    category: str = Field(min_length=2, max_length=100)
    available_quantity: int = Field(ge=0)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    minimum_stock_level: int = Field(ge=0)

    @field_validator('part_number', mode='before')
    @classmethod
    def normalize_number(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator('name', 'category')
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError('At least 2 non-space characters required')
        return value


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    part_number: str = Field(min_length=2, max_length=60, pattern=r'^[A-Z0-9_-]+$')
    category: str = Field(min_length=2, max_length=100)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    minimum_stock_level: int = Field(ge=0)

    @field_validator('part_number', mode='before')
    @classmethod
    def normalize_number(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator('name', 'category')
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError('At least 2 non-space characters required')
        return value


class PartResponse(PartBase):
    id: int
    low_stock: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StockAdd(BaseModel):
    quantity: int = Field(gt=0)


class PartUsageCreate(BaseModel):
    part_id: int = Field(gt=0)
    quantity_used: int = Field(gt=0)


class PartUsageResponse(BaseModel):
    id: int
    service_id: int
    part_id: int
    quantity_used: int
    unit_price: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UsageResult(BaseModel):
    usage: PartUsageResponse
    part: PartResponse
    alert: str | None
