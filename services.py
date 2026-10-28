from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import service as crud
from app.models.customer import Customer
from app.models.mechanic import Mechanic
from app.models.service import ServiceHistory, ServiceRequest
from app.models.vehicle import Vehicle
from app.schemas.service import AssignmentResponse, HistoryResponse, ServiceCreate, ServiceResponse, ServiceStatus, ServiceUpdate, StatusUpdate

router = APIRouter(prefix='/services', tags=['Services'])
ORDER = list(ServiceStatus)


def required_service(db: Session, service_id: int) -> ServiceRequest:
    item = crud.get(db, service_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Service request not found')
    return item


def output(item: ServiceRequest) -> ServiceResponse:
    return ServiceResponse.model_validate({
        'id': item.id, 'customer_id': item.customer_id, 'vehicle_id': item.vehicle_id,
        'service_type': item.service_type, 'complaint': item.complaint,
        'arrival_date': item.arrival_date, 'expected_delivery_date': item.expected_delivery_date,
        'status': item.status, 'mechanic_ids': [m.id for m in item.mechanics],
        'created_at': item.created_at, 'updated_at': item.updated_at,
    })


@router.post('', response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    if db.get(Customer, data.customer_id) is None:
        raise HTTPException(status_code=404, detail='Customer not found')
    vehicle = db.get(Vehicle, data.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail='Vehicle not found')
    if vehicle.customer_id != data.customer_id:
        raise HTTPException(status_code=422, detail='Vehicle does not belong to this customer')
    try:
        return output(crud.create(db, data))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Customer or vehicle changed; retry the request')


@router.get('', response_model=list[ServiceResponse])
def list_services(
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    customer_id: int | None = Query(None, gt=0), vehicle_id: int | None = Query(None, gt=0),
    mechanic_id: int | None = Query(None, gt=0), db: Session = Depends(get_db),
):
    return [output(item) for item in crud.list_all(db, skip, limit, customer_id, vehicle_id, mechanic_id)]


@router.get('/{service_id}', response_model=ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    return output(required_service(db, service_id))


@router.put('/{service_id}', response_model=ServiceResponse)
def update_service(service_id: int, data: ServiceUpdate, db: Session = Depends(get_db)):
    item = required_service(db, service_id)
    if item.status == ServiceStatus.DELIVERED.value:
        raise HTTPException(status_code=409, detail='Delivered service cannot be edited')
    return output(crud.update(db, item, data))


@router.patch('/{service_id}/status', response_model=ServiceResponse)
def change_status(service_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    item = required_service(db, service_id)
    current = ServiceStatus(item.status)
    next_status = data.status
    # Parts can be requested during inspection or active service; after parts arrive, work resumes.
    allowed = {
        ServiceStatus.RECEIVED: {ServiceStatus.INSPECTION},
        ServiceStatus.INSPECTION: {ServiceStatus.IN_SERVICE, ServiceStatus.WAITING_FOR_PARTS},
        ServiceStatus.IN_SERVICE: {ServiceStatus.WAITING_FOR_PARTS, ServiceStatus.COMPLETED},
        ServiceStatus.WAITING_FOR_PARTS: {ServiceStatus.IN_SERVICE},
        ServiceStatus.COMPLETED: {ServiceStatus.DELIVERED},
        ServiceStatus.DELIVERED: set(),
    }
    if next_status not in allowed[current]:
        raise HTTPException(status_code=409, detail=f'Cannot move from {current.value} to {next_status.value}')
    item.status = next_status.value
    db.add(ServiceHistory(service_id=item.id, event='STATUS_CHANGED', old_status=current.value, new_status=next_status.value, note=data.note))
    db.commit()
    db.refresh(item)
    return output(item)


@router.get('/{service_id}/history', response_model=list[HistoryResponse])
def get_history(service_id: int, db: Session = Depends(get_db)):
    required_service(db, service_id)
    return crud.history(db, service_id)


@router.post('/{service_id}/mechanics/{mechanic_id}', response_model=AssignmentResponse)
def assign_mechanic(service_id: int, mechanic_id: int, db: Session = Depends(get_db)):
    item = required_service(db, service_id)
    mechanic = db.get(Mechanic, mechanic_id)
    if mechanic is None:
        raise HTTPException(status_code=404, detail='Mechanic not found')
    if item.status == ServiceStatus.DELIVERED.value:
        raise HTTPException(status_code=409, detail='Delivered service cannot be assigned')
    if any(m.id == mechanic_id for m in item.mechanics):
        raise HTTPException(status_code=409, detail='Mechanic already assigned')
    item.mechanics.append(mechanic)
    db.add(ServiceHistory(service_id=item.id, event='MECHANIC_ASSIGNED', note=f'Mechanic ID {mechanic_id} assigned'))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Assignment could not be saved')
    return AssignmentResponse(service_id=item.id, mechanic_ids=[m.id for m in item.mechanics])


@router.delete('/{service_id}/mechanics/{mechanic_id}', response_model=AssignmentResponse)
def unassign_mechanic(service_id: int, mechanic_id: int, db: Session = Depends(get_db)):
    item = required_service(db, service_id)
    mechanic = next((m for m in item.mechanics if m.id == mechanic_id), None)
    if mechanic is None:
        raise HTTPException(status_code=404, detail='Mechanic is not assigned to this service')
    if item.status == ServiceStatus.DELIVERED.value:
        raise HTTPException(status_code=409, detail='Delivered service assignments cannot be changed')
    item.mechanics.remove(mechanic)
    db.add(ServiceHistory(service_id=item.id, event='MECHANIC_UNASSIGNED', note=f'Mechanic ID {mechanic_id} unassigned'))
    db.commit()
    return AssignmentResponse(service_id=item.id, mechanic_ids=[m.id for m in item.mechanics])
