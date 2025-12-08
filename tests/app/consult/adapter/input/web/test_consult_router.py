import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Optional

from app.consult.adapter.input.web.consult_router import (
    consult_router,
    get_analysis_use_case,
)
from app.consult.application.use_case.get_analysis_use_case import GetAnalysisUseCase
from app.consult.application.port.consult_repository_port import ConsultRepositoryPort
from app.consult.application.port.ai_counselor_port import AICounselorPort
from app.consult.domain.consult_session import ConsultSession
from app.consult.domain.message import Message
from app.consult.domain.analysis import Analysis
from app.shared.domain.user_profile import UserProfile
from app.shared.domain.gender import Gender
from app.shared.domain.mbti import MBTI


class FakeConsultRepository(ConsultRepositoryPort):
    """테스트용 Fake Repository"""

    def __init__(self):
        self.sessions = {}

    def save(self, session: ConsultSession) -> ConsultSession:
        self.sessions[session.session_id] = session
        return session

    def find_by_id(self, session_id: str) -> Optional[ConsultSession]:
        return self.sessions.get(session_id)


class FakeAICounselor(AICounselorPort):
    """테스트용 Fake AI Counselor"""

    def generate_analysis(
        self, profile: UserProfile, conversation_history: list[dict]
    ) -> Analysis:
        return Analysis(
            situation="직장 상사와의 소통에 어려움을 겪고 있습니다.",
            traits="INTJ는 논리적이고 독립적인 성향입니다.",
            solutions="감정을 먼저 공감하는 연습을 해보세요.",
            cautions="논리적인 태도가 냉정하게 느껴질 수 있습니다.",
        )


@pytest.fixture
def test_app():
    """테스트용 FastAPI 앱"""
    app = FastAPI()

    # Fake 의존성 생성
    repository = FakeConsultRepository()
    counselor = FakeAICounselor()
    use_case = GetAnalysisUseCase(repository=repository, counselor=counselor)

    # 의존성 오버라이드
    app.dependency_overrides[get_analysis_use_case] = lambda: use_case

    app.include_router(consult_router, prefix="/convert")

    return app, repository


def test_get_analysis_returns_200_for_completed_session(test_app):
    """3턴 완료된 세션은 200 OK와 분석 결과를 반환한다"""
    app, repository = test_app
    client = TestClient(app)

    # Given: 3턴 완료된 세션 생성
    profile = UserProfile(gender=Gender("FEMALE"), mbti=MBTI("INTJ"))
    session = ConsultSession(user_id="user-123", profile=profile)
    session.add_message(Message(role="user", content="질문1"))
    session.add_message(Message(role="assistant", content="답변1"))
    session.add_message(Message(role="user", content="질문2"))
    session.add_message(Message(role="assistant", content="답변2"))
    session.add_message(Message(role="user", content="질문3"))
    session.add_message(Message(role="assistant", content="답변3"))
    repository.save(session)

    # When: GET /convert/{session_id}/analysis 호출
    response = client.get(f"/convert/{session.session_id}/analysis")

    # Then: 200 OK와 분석 결과 반환
    assert response.status_code == 200
    data = response.json()
    assert data["situation"] == "직장 상사와의 소통에 어려움을 겪고 있습니다."
    assert data["traits"] == "INTJ는 논리적이고 독립적인 성향입니다."
    assert data["solutions"] == "감정을 먼저 공감하는 연습을 해보세요."
    assert data["cautions"] == "논리적인 태도가 냉정하게 느껴질 수 있습니다."


def test_get_analysis_returns_404_for_non_existent_session(test_app):
    """존재하지 않는 세션은 404 Not Found를 반환한다"""
    app, _ = test_app
    client = TestClient(app)

    # When: 존재하지 않는 session_id로 호출
    response = client.get("/convert/non-existent-id/analysis")

    # Then: 404 Not Found
    assert response.status_code == 404
    assert "세션을 찾을 수 없습니다" in response.json()["detail"]


def test_get_analysis_returns_400_for_incomplete_session(test_app):
    """3턴 미완료 세션은 400 Bad Request를 반환한다"""
    app, repository = test_app
    client = TestClient(app)

    # Given: 2턴만 완료된 세션
    profile = UserProfile(gender=Gender("MALE"), mbti=MBTI("ENFP"))
    session = ConsultSession(user_id="user-123", profile=profile)
    session.add_message(Message(role="user", content="질문1"))
    session.add_message(Message(role="assistant", content="답변1"))
    session.add_message(Message(role="user", content="질문2"))
    repository.save(session)

    # When: GET /convert/{session_id}/analysis 호출
    response = client.get(f"/convert/{session.session_id}/analysis")

    # Then: 400 Bad Request
    assert response.status_code == 400
    assert "상담이 아직 완료되지 않았습니다" in response.json()["detail"]
