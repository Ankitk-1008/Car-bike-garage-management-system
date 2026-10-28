from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleType(str, Enum):
    CAR = 'CAR'
    BIKE = 'BIKE'


class FuelType(str, Enum):
    PETROL = 'PETROL'
    DIESEL = 'DIESEL'
    CNG = 'CNG'
    ELECTRIC = 'ELECTRIC'
    HYBRID = 'HYBRID'


class VehicleBase(BaseModel):
    customer_id: int = Field(gt=0)
    registration_number: str = Field(min_length=5, max_length=20, pattern=r'^[A-Z0-9]+$')
    type: VehicleType
    brand: str = Field(min_length=2, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    manufacturing_year: int = Field(ge=1886)
    fuel_type: FuelType
    mileage: Decimal = Field(ge=0, max_digits=12, decimal_places=2)

    @field_validator('registration_number', mode='before')
    @classmethod
    def normalize_registration(cls, value):
        return value.strip().upper().replace(' ', '').replace('-', '') if isinstance(value, str) else value

    @field_validator('brand', 'model')
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Cannot be blank')
        return value

    @field_validator('manufacturing_year')
    @classmethod
    def valid_year(cls, value: int) -> int:
        if value > date.today().year + 1:
            raise ValueError('Manufacturing year is too far in the future')
        return value


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
