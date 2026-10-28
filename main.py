import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import configure_mappers

from app.api.v1.customers import router as customers_router
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.services import router as services_router
from app.api.v1.mechanics import router as mechanics_router
from app.api.v1.parts import router as parts_router
from app.api.v1.billing import router as billing_router
from app.api.v1.dashboard import router as dashboard_router

from app.core.database import Base, engine


from app.models.customer import Customer  
from app.models.vehicle import Vehicle  
from app.models.mechanic import Mechanic  
from app.models.service import ServiceRequest, ServiceHistory  
from app.models.part import Part, ServicePartUsage  
from app.models.billing import Bill, Payment, ServiceCharge  


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Car & Bike Garage Management System",
    version="1.0.0",
)


@app.on_event("startup")
def create_tables() -> None:
    configure_mappers()
    Base.metadata.create_all(bind=engine)


@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request data",
            "errors": [{k: v for k, v in e.items() if k in ("loc", "msg", "type")} for e in exc.errors()],
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.exception(
        "Database error on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed"},
    )


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


app.include_router(customers_router, prefix="/api/v1")
app.include_router(vehicles_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(mechanics_router, prefix="/api/v1")
app.include_router(parts_router, prefix="/api/v1")

app.include_router(billing_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
