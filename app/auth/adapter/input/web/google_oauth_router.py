import json
import uuid

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth.infrastructure.oauth.google_oauth_service import GoogleOAuthService
from app.auth.infrastructure.repository.redis_session_repository import (
    RedisSessionRepository,
)
from app.auth.domain.session import Session
from config.redis import get_redis_client
from config.settings import get_settings

google_oauth_router = APIRouter()

# 서비스 인스턴스
service = GoogleOAuthService()
redis_client = get_redis_client()
session_repo = RedisSessionRepository(redis_client)


@google_oauth_router.get("/google")
async def redirect_to_google():
    """Google 로그인 페이지로 리다이렉트"""
    url = service.get_authorization_url()
    return RedirectResponse(url)


@google_oauth_router.get("/google/callback")
async def google_callback(code: str, state: str | None = None):
    """
    Google OAuth 콜백 처리.

    1. code로 access token 획득
    2. access token으로 프로필 조회
    3. Redis에 세션 저장
    4. 쿠키에 session_id 설정 후 프론트엔드로 리다이렉트
    """
    # Access token 획득 및 프로필 조회
    access_token = service.get_access_token(code)
    profile = service.get_user_profile(access_token)

    email = profile.get("email")
    google_id = profile.get("sub")
    name = profile.get("name")

    # Session 생성
    session_id = str(uuid.uuid4())

    # Redis에 세션 데이터 저장
    redis_client.setex(
        f"session:{session_id}",
        6 * 60 * 60,  # 6시간
        json.dumps({
            "user_id": google_id,
            "email": email,
            "name": name,
            "access_token": access_token.access_token,
        }),
    )

    # 프론트엔드로 리다이렉트 + 쿠키 설정
    settings = get_settings()
    frontend_url = "http://localhost:3000"  # TODO: settings에서 가져오기

    response = RedirectResponse(frontend_url)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # 개발환경에서는 False
        samesite="lax",
        max_age=6 * 60 * 60,
    )

    return response


@google_oauth_router.get("/status")
async def auth_status(request: Request, session_id: str | None = Cookie(None)):
    """현재 로그인 상태 확인"""
    if not session_id:
        return {"logged_in": False}

    session_data = redis_client.get(f"session:{session_id}")
    if not session_data:
        return {"logged_in": False}

    # JSON 파싱
    if isinstance(session_data, bytes):
        session_data = session_data.decode("utf-8")

    session_dict = json.loads(session_data)

    return {
        "logged_in": True,
        "user_id": session_dict.get("user_id"),
        "email": session_dict.get("email"),
        "name": session_dict.get("name"),
    }


async def logout(session_id: str | None = Cookie(None)):
    """로그아웃 - 세션 삭제"""
    if session_id:
        redis_client.delete(f"session:{session_id}")

    response = JSONResponse(status_code=204, content=None)  # pyright: ignore[reportUndefinedVariable]
    response.delete_cookie("session_id")
    return response
