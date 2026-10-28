from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import vehicle as crud
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(prefix='/vehicles', tags=['Vehicles'])


def existing_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    item = crud.get(db, vehicle_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Vehicle not found')
    return item


def check_references(db: Session, customer_id: int, registration: str, exclude_id: int | None = None) -> None:
    if db.get(Customer, customer_id) is None:
        raise HTTPException(status_code=404, detail='Customer not found')
    existing = crud.get_by_registration(db, registration)
    if existing and existing.id != exclude_id:
        raise HTTPException(status_code=409, detail='Registration number already exists')


@router.post('', response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: VehicleCreate, db: Session = Depends(get_db)):
    check_references(db, data.customer_id, data.registration_number)
    try:
        return crud.create(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Customer missing or registration number already exists')


@router.get('', response_model=list[VehicleResponse])
def list_vehicles(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), customer_id: int | None = Query(None, gt=0), db: Session = Depends(get_db)):
    return crud.list_all(db, skip, limit, customer_id)


@router.get("/search")
def search_vehicle(
    registration_number: str = Query(min_length=5, max_length=25),
    db: Session = Depends(get_db),
):
    registration = (
        registration_number.strip().upper().replace(" ", "").replace("-", "")
    )

    vehicle = crud.get_by_registration(db, registration)

    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    customer = db.get(Customer, vehicle.customer_id)
    customer_vehicles = crud.list_all(
        db, skip=0, limit=100, customer_id=customer.id
    )

    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
        },
        "vehicles": [
            {
                "type": item.type,
                "registration_number": item.registration_number,
            }
            for item in customer_vehicles
        ],
    }


@router.get('/{vehicle_id}', response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    return existing_vehicle(db, vehicle_id)


@router.put('/{vehicle_id}', response_model=VehicleResponse)
def update_vehicle(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db)):
    item = existing_vehicle(db, vehicle_id)
    check_references(db, data.customer_id, data.registration_number, exclude_id=vehicle_id)
    try:
        return crud.update(db, item, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Customer missing or registration number already exists')


@router.delete('/{vehicle_id}')
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    crud.delete(db, existing_vehicle(db, vehicle_id))
    return {'message': 'Vehicle deleted successfully'}
