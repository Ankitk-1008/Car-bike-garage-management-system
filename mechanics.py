from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import mechanic as crud
from app.crud import service as service_crud
from app.models.mechanic import Mechanic
from app.schemas.mechanic import MechanicCreate, MechanicResponse, MechanicUpdate
from app.schemas.service import ServiceResponse
from app.api.v1.services import output

router = APIRouter(prefix='/mechanics', tags=['Mechanics'])


def required_mechanic(db: Session, mechanic_id: int) -> Mechanic:
    item = crud.get(db, mechanic_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Mechanic not found')
    return item


def check_phone(db: Session, phone: str, exclude_id: int | None = None):
    match = crud.get_by_phone(db, phone)
    if match and match.id != exclude_id:
        raise HTTPException(status_code=409, detail='Mechanic phone already exists')


@router.post('', response_model=MechanicResponse, status_code=status.HTTP_201_CREATED)
def create_mechanic(data: MechanicCreate, db: Session = Depends(get_db)):
    check_phone(db, data.phone)
    try:
        return crud.create(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Mechanic phone already exists')


@router.get('', response_model=list[MechanicResponse])
def list_mechanics(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    return crud.list_all(db, skip, limit)


@router.get('/{mechanic_id}', response_model=MechanicResponse)
def get_mechanic(mechanic_id: int, db: Session = Depends(get_db)):
    return required_mechanic(db, mechanic_id)


@router.put('/{mechanic_id}', response_model=MechanicResponse)
def update_mechanic(mechanic_id: int, data: MechanicUpdate, db: Session = Depends(get_db)):
    item = required_mechanic(db, mechanic_id)
    check_phone(db, data.phone, exclude_id=item.id)
    try:
        return crud.update(db, item, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Mechanic phone already exists')


@router.get('/{mechanic_id}/services', response_model=list[ServiceResponse])
def mechanic_services(mechanic_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    required_mechanic(db, mechanic_id)
    return [output(item) for item in service_crud.list_all(db, skip, limit, None, None, mechanic_id)]


@router.delete('/{mechanic_id}')
def delete_mechanic(mechanic_id: int, db: Session = Depends(get_db)):
    item = required_mechanic(db, mechanic_id)
    if item.services:
        raise HTTPException(status_code=409, detail='Unassign mechanic from all services before deleting')
    db.delete(item)
    db.commit()
    return {'message': 'Mechanic deleted successfully'}
