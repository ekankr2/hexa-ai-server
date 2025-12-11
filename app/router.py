"""
Centralized router configuration.
All application routers are registered here and imported into main.py.
"""

from fastapi import FastAPI

from app.auth.adapter.input.web.google_oauth_router import google_oauth_router
from app.data.adapter.input.web.data_router import data_router
from app.data.infrastructure.orm.data_orm import DataORM  # noqa: F401
from app.user.infrastructure.model.user_model import UserModel  # noqa: F401
from app.consult.infrastructure.model.consult_session_model import ConsultSessionModel  # noqa: F401
from app.consult.adapter.input.web.consult_router import consult_router
from app.consult.adapter.input.web import consult_router as consult_router_module
from app.converter.adapter.input.web.converter_router import converter_router
from app.auth.adapter.input.web import auth_dependency
from app.user.adapter.input.web.user_router import user_router
from app.user.adapter.input.web import user_router as user_router_module

from config.database import get_db_session
from config.settings import get_settings
from app.user.infrastructure.repository.mysql_user_repository import MySQLUserRepository
from app.consult.infrastructure.repository.mysql_consult_repository import MySQLConsultRepository
from app.consult.infrastructure.service.openai_counselor_adapter import OpenAICounselorAdapter


def setup_routers(app: FastAPI) -> None:
    # Auth router
    app.include_router(google_oauth_router, prefix="/auth")

    # User router
    app.include_router(user_router, prefix="/user")

    # Data router
    app.include_router(data_router, prefix="/data")

    # Converter router (HAIS-17, 18)
    app.include_router(converter_router, prefix="/converter")

    # Consult router with real implementations
    settings = get_settings()
    db_session = get_db_session()

    user_repository = MySQLUserRepository(db_session)
    consult_router_module._user_repository = user_repository
    consult_router_module._consult_repository = MySQLConsultRepository(db_session)
    consult_router_module._ai_counselor = OpenAICounselorAdapter(api_key=settings.OPENAI_API_KEY)
    user_router_module._user_repository = user_repository
    app.include_router(consult_router, prefix="/consult")