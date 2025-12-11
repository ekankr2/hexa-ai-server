from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.adapter.input.web.auth_dependency import get_current_user_id
from app.user.application.port.user_repository_port import UserRepositoryPort
from app.user.domain.user import User
from app.shared.vo.mbti import MBTI
from app.shared.vo.gender import Gender

user_router = APIRouter()

# Global repository instance (set in app.router or tests)
_user_repository: UserRepositoryPort | None = None


class UpdateProfileRequest(BaseModel):
    mbti: str
    gender: str


@user_router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    """현재 로그인한 사용자의 프로필 조회"""
    if not _user_repository:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User repository가 설정되지 않았습니다",
        )

    user = _user_repository.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    return {
        "id": user.id,
        "email": user.email,
        "mbti": user.mbti.value if user.mbti else None,
        "gender": user.gender.value if user.gender else None,
    }


@user_router.put("/profile")
def update_profile(
    request: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
):
    """MBTI/성별 프로필 저장 (upsert)"""
    if not _user_repository:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User repository가 설정되지 않았습니다",
        )

    user = _user_repository.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    try:
        mbti = MBTI(request.mbti)
        gender = Gender(request.gender.upper())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    updated_user = User(
        id=user.id,
        email=user.email,
        mbti=mbti,
        gender=gender,
    )
    _user_repository.save(updated_user)

    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "mbti": updated_user.mbti.value,
        "gender": updated_user.gender.value,
    }