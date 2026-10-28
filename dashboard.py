from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.service import ServiceRequest
from app.models.part import Part
from app.models.billing import Bill, Payment

router = APIRouter(prefix='/dashboard', tags=['Dashboard'])


@router.get('')
def dashboard(db: Session = Depends(get_db)):
    def count(model, *conditions):
        return db.scalar(select(func.count()).select_from(model).where(*conditions))
    active = ['Received', 'Inspection', 'In Service', 'Waiting for Parts']
    return {
        'total_customers': count(Customer),
        'total_cars': count(Vehicle, Vehicle.type == 'CAR'),
        'total_bikes': count(Vehicle, Vehicle.type == 'BIKE'),
        'vehicles_under_service': db.scalar(select(func.count(func.distinct(ServiceRequest.vehicle_id))).where(ServiceRequest.status.in_(active))),
        'completed_services': count(ServiceRequest, ServiceRequest.status.in_(['Completed', 'Delivered'])),
        'pending_services': count(ServiceRequest, ServiceRequest.status.in_(active)),
        'total_revenue': str(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)))),
        'total_billed_amount': str(db.scalar(select(func.coalesce(func.sum(Bill.final_amount), 0)))),
        'low_stock_parts': count(Part, Part.available_quantity <= Part.minimum_stock_level),
    }
