from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MechanicBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r'^[0-9]{10,15}$')
    specialization: str = Field(min_length=2, max_length=100)
    experience_years: int = Field(ge=0, le=70)

    @field_validator('name', 'specialization')
    @classmethod
    def strip_nonblank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Must have at least 2 characters')
        return value


class MechanicCreate(MechanicBase):
    pass


class MechanicUpdate(MechanicBase):
    pass


class MechanicResponse(MechanicBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
