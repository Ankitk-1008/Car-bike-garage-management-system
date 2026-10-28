from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServiceStatus(str, Enum):
    RECEIVED = 'Received'
    INSPECTION = 'Inspection'
    IN_SERVICE = 'In Service'
    WAITING_FOR_PARTS = 'Waiting for Parts'
    COMPLETED = 'Completed'
    DELIVERED = 'Delivered'


class ServiceBase(BaseModel):
    customer_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    service_type: str = Field(min_length=2, max_length=100)
    complaint: str = Field(min_length=3, max_length=2000)
    arrival_date: date
    expected_delivery_date: date

    @model_validator(mode='after')
    def check_dates(self):
        if self.expected_delivery_date < self.arrival_date:
            raise ValueError('Expected delivery date must be on or after arrival date')
        if not self.service_type.strip() or not self.complaint.strip():
            raise ValueError('Service type and complaint cannot be blank')
        self.service_type = self.service_type.strip()
        self.complaint = self.complaint.strip()
        return self


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_type: str = Field(min_length=2, max_length=100)
    complaint: str = Field(min_length=3, max_length=2000)
    arrival_date: date
    expected_delivery_date: date

    @model_validator(mode='after')
    def check_dates(self):
        if self.expected_delivery_date < self.arrival_date:
            raise ValueError('Expected delivery date must be on or after arrival date')
        if not self.service_type.strip() or not self.complaint.strip():
            raise ValueError('Service type and complaint cannot be blank')
        self.service_type = self.service_type.strip()
        self.complaint = self.complaint.strip()
        return self


class StatusUpdate(BaseModel):
    status: ServiceStatus
    note: str | None = Field(None, max_length=500)


class ServiceResponse(ServiceBase):
    id: int
    status: ServiceStatus
    mechanic_ids: list[int]
    created_at: datetime
    updated_at: datetime


class HistoryResponse(BaseModel):
    id: int
    service_id: int
    event: str
    old_status: str | None
    new_status: str | None
    note: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AssignmentResponse(BaseModel):
    service_id: int
    mechanic_ids: list[int]
