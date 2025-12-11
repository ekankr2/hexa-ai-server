from fastapi import Header, Cookie, HTTPException, status

from app.auth.infrastructure.repository.mysql_session_repository import MySqlSessionRepository
from config.database import get_db_session

from app.auth.application.port.session_repository_port import SessionRepositoryPort

# Session repository - will be set via dependency injection
_session_repository: SessionRepositoryPort | None = None


def set_session_repository(repo: SessionRepositoryPort) -> None:
    """세션 저장소 설정"""
    global _session_repository
    _session_repository = repo


def get_current_user_id(
    authorization: str | None = Header(default=None),
    session_id_cookie: str | None = Cookie(default=None, alias="session_id"),
) -> str:
    """
    현재 요청의 user_id를 반환하는 의존성.

    Authorization 헤더에서 Bearer 토큰(세션 ID)을 추출하고,
    세션 저장소에서 검증하여 user_id를 반환한다.
    """
    session_id = None

    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            session_id = parts[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="올바른 인증 형식이 아닙니다",
            )

    # Authorization이 없으면 쿠키로 대체
    if session_id is None and session_id_cookie:
        session_id = session_id_cookie

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
        )

    # 세션 저장소 검증
    # 세션 저장소 준비 (주입된 fake/테스트 우선)
    repo = _session_repository
    created_db = None
    if repo is None:
        created_db = get_db_session()
        repo = MySqlSessionRepository(created_db)

    try:
        session = repo.find_by_session_id(session_id)
    finally:
        if created_db:
            created_db.close()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 세션입니다",
        )

    return session.user_id
