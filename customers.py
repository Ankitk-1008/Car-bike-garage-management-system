from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import customer as crud
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix='/customers', tags=['Customers'])


def customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = crud.get(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer


def ensure_unique(db: Session, phone: str, email: str | None, exclude_id: int | None = None) -> None:
    phone_match = crud.get_by_phone(db, phone)
    if phone_match and phone_match.id != exclude_id:
        raise HTTPException(status_code=409, detail='Phone already exists')
    if email:
        email_match = crud.get_by_email(db, email)
        if email_match and email_match.id != exclude_id:
            raise HTTPException(status_code=409, detail='Email already exists')


@router.post('', response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    ensure_unique(db, data.phone, str(data.email) if data.email else None)
    try:
        return crud.create(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Phone or email already exists')


@router.get('', response_model=list[CustomerResponse])
def list_customers(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    return crud.list_all(db, skip, limit)


@router.get('/{customer_id}', response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_or_404(db, customer_id)


@router.put('/{customer_id}', response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    customer = customer_or_404(db, customer_id)
    ensure_unique(db, data.phone, str(data.email) if data.email else None, exclude_id=customer_id)
    try:
        return crud.update(db, customer, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Phone or email already exists')


@router.delete('/{customer_id}')
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = customer_or_404(db, customer_id)
    try:
        crud.delete(db, customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Delete customer vehicles first')
    return {'message': 'Customer deleted successfully'}


@router.get('/{customer_id}/vehicles')
def customer_vehicles(customer_id: int, db: Session = Depends(get_db)):
    from app.crud.vehicle import list_all
    from app.schemas.vehicle import VehicleResponse
    customer_or_404(db, customer_id)
    return [VehicleResponse.model_validate(v) for v in list_all(db, 0, 100, customer_id)]


@router.get('/{customer_id}/services')
def customer_services(customer_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    from app.crud.service import list_all
    from app.api.v1.services import output
    customer_or_404(db, customer_id)
    return [output(s) for s in list_all(db, skip, limit, customer_id, None, None)]
