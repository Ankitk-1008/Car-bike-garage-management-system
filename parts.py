from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import part as crud
from app.models.part import Part, ServicePartUsage
from app.models.service import ServiceHistory, ServiceRequest
from app.schemas.part import PartCreate, PartResponse, PartUpdate, PartUsageCreate, PartUsageResponse, StockAdd, UsageResult

router = APIRouter(tags=['Inventory'])


def required_part(db: Session, part_id: int) -> Part:
    item = db.get(Part, part_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Part not found')
    return item


def part_response(item: Part) -> PartResponse:
    return PartResponse.model_validate({
        'id': item.id, 'name': item.name, 'part_number': item.part_number,
        'category': item.category, 'available_quantity': item.available_quantity,
        'price': item.price, 'minimum_stock_level': item.minimum_stock_level,
        'low_stock': item.available_quantity <= item.minimum_stock_level,
        'created_at': item.created_at, 'updated_at': item.updated_at,
    })


@router.post('/parts', response_model=PartResponse, status_code=status.HTTP_201_CREATED)
def create_part(data: PartCreate, db: Session = Depends(get_db)):
    item = Part(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Part number already exists')
    db.refresh(item)
    return part_response(item)


@router.get('/parts', response_model=list[PartResponse])
def list_parts(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    return [part_response(p) for p in crud.list_parts(db, skip, limit)]


@router.get('/parts/low-stock', response_model=list[PartResponse])
def low_stock_alerts(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    return [part_response(p) for p in crud.list_parts(db, skip, limit, True)]


@router.get('/parts/{part_id}', response_model=PartResponse)
def get_part(part_id: int, db: Session = Depends(get_db)):
    return part_response(required_part(db, part_id))


@router.put('/parts/{part_id}', response_model=PartResponse)
def update_part(part_id: int, data: PartUpdate, db: Session = Depends(get_db)):
    item = required_part(db, part_id)
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Part number already exists')
    db.refresh(item)
    return part_response(item)


@router.delete('/parts/{part_id}')
def delete_part(part_id: int, db: Session = Depends(get_db)):
    item = required_part(db, part_id)
    if item.usages:
        raise HTTPException(status_code=409, detail='Part has service usage history and cannot be deleted')
    db.delete(item)
    db.commit()
    return {'message': 'Part deleted successfully'}


@router.post('/parts/{part_id}/restock', response_model=PartResponse)
def restock_part(part_id: int, data: StockAdd, db: Session = Depends(get_db)):
    required_part(db, part_id)
    db.execute(update(Part).where(Part.id == part_id).values(available_quantity=Part.available_quantity + data.quantity))
    db.commit()
    db.expire_all()
    return part_response(required_part(db, part_id))


@router.post('/services/{service_id}/parts', response_model=UsageResult, status_code=status.HTTP_201_CREATED)
def use_part(service_id: int, data: PartUsageCreate, db: Session = Depends(get_db)):
    service = db.get(ServiceRequest, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail='Service request not found')
    if service.status in ('Completed', 'Delivered'):
        raise HTTPException(status_code=409, detail='Service is already completed or delivered')
    part = required_part(db, data.part_id)
    unit_price = part.price
    # Conditional SQL update prevents two concurrent requests from overselling stock.
    result = db.execute(
        update(Part).where(Part.id == data.part_id, Part.available_quantity >= data.quantity_used)
        .values(available_quantity=Part.available_quantity - data.quantity_used)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail='Insufficient stock')
    usage = ServicePartUsage(service_id=service_id, part_id=data.part_id, quantity_used=data.quantity_used, unit_price=unit_price)
    db.add(usage)
    db.add(ServiceHistory(service_id=service_id, event='PART_USED', note=f'Part ID {data.part_id}, quantity {data.quantity_used}'))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Part usage could not be saved')
    db.refresh(usage)
    db.expire_all()
    current = required_part(db, data.part_id)
    low = current.available_quantity <= current.minimum_stock_level
    return UsageResult(usage=PartUsageResponse.model_validate(usage), part=part_response(current), alert='Low stock: reorder this part' if low else None)


@router.get('/services/{service_id}/parts', response_model=list[PartUsageResponse])
def service_parts(service_id: int, db: Session = Depends(get_db)):
    if db.get(ServiceRequest, service_id) is None:
        raise HTTPException(status_code=404, detail='Service request not found')
    return crud.list_usages(db, service_id)
