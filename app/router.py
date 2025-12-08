"""
Centralized router configuration.
All application routers are registered here and imported into main.py.
"""

from fastapi import FastAPI

from app.data.adapter.input.web.data_router import data_router
from app.data.infrastructure.orm.data_orm import DataORM  # noqa: F401
from app.consult.infrastructure.orm.consult_orm import ConsultORM  # noqa: F401
from app.consult.adapter.input.web.consult_router import consult_router


def setup_routers(app: FastAPI) -> None:
    app.include_router(data_router, prefix="/data")
    app.include_router(consult_router, prefix="/convert")
