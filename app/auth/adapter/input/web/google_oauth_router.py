import uuid

from fastapi import APIRouter, Cookie, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session as DbSession

from app.auth.infrastructure.oauth.google_oauth_service import GoogleOAuthService
from app.auth.infrastructure.repository.mysql_session_repository import (
    MySqlSessionRepository,
)
from app.auth.domain.session import Session
from app.user.infrastructure.model.user_model import UserModel
from config.database import get_db
from config.settings import get_settings
from config.database import get_db_session
from app.user.infrastructure.repository.mysql_user_repository import MySQLUserRepository
from app.user.domain.user import User

google_oauth_router = APIRouter()

# 서비스 인스턴스
service = GoogleOAuthService()


def get_session_repo(db: DbSession = Depends(get_db)) -> MySqlSessionRepository:
    return MySqlSessionRepository(db)


@google_oauth_router.get("/google")
async def redirect_to_google():
    """Google 로그인 페이지로 리다이렉트"""
    url = service.get_authorization_url()
    return RedirectResponse(url)


@google_oauth_router.get("/google/callback")
async def google_callback(code: str, state: str | None = None, db: DbSession = Depends(get_db)):
    """
    Google OAuth 콜백 처리.

    1. code로 access token 획득
    2. access token으로 프로필 조회
    3. DB에 유저 저장/업데이트 및 세션 저장
    4. 쿠키에 session_id 설정 후 프론트엔드로 리다이렉트
    """
    # Access token 획득 및 프로필 조회
    access_token = service.get_access_token(code)
    profile = service.get_user_profile(access_token)

    email = profile.get("email")
    google_id = profile.get("sub")

    # 유저 조회 또는 생성
    user = db.query(UserModel).filter(UserModel.id == google_id).first()
    if not user:
        user = UserModel(id=google_id, email=email)
        db.add(user)
        db.commit()

    # Session 생성
    session_id = str(uuid.uuid4())
    session_repo = MySqlSessionRepository(db)
    session_repo.save(Session(session_id=session_id, user_id=google_id))

    # 프론트엔드로 리다이렉트 + 쿠키 설정
    settings = get_settings()

    response = RedirectResponse(settings.FRONTEND_URL)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=6 * 60 * 60,
    )

    return response


@google_oauth_router.get("/status")
async def auth_status(request: Request, session_id: str | None = Cookie(None), db: DbSession = Depends(get_db)):
    """현재 로그인 상태 확인"""
    if not session_id:
        return {"logged_in": False}

    session_repo = MySqlSessionRepository(db)
    session = session_repo.find_by_session_id(session_id)

    if not session:
        return {"logged_in": False}

    # 유저 정보 조회
    user = db.query(UserModel).filter(UserModel.id == session.user_id).first()
    if not user:
        return {"logged_in": False}

    return {
        "logged_in": True,
        "user_id": user.id,
        "email": user.email,
    }


@google_oauth_router.post("/logout")
async def logout(session_id: str | None = Cookie(None), db: DbSession = Depends(get_db)):
    """로그아웃 - 세션 삭제"""
    if session_id:
        session_repo = MySqlSessionRepository(db)
        session_repo.delete(session_id)

    response = JSONResponse(status_code=204, content=None)
    response.delete_cookie("session_id")
    return response