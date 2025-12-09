import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.consult.adapter.input.web.consult_router import consult_router
from app.user.domain.user import User
from app.shared.vo.mbti import MBTI
from app.shared.vo.gender import Gender
from app.auth.domain.session import Session
from tests.user.fixtures.fake_user_repository import FakeUserRepository
from tests.auth.fixtures.fake_session_repository import FakeSessionRepository
from tests.consult.fixtures.fake_consult_repository import FakeConsultRepository
from tests.consult.fixtures.fake_ai_counselor import FakeAICounselor
from app.consult.domain.consult_session import ConsultSession


@pytest.fixture
def app():
    """FastAPI 앱"""
    app = FastAPI()
    app.include_router(consult_router, prefix="/consult")
    return app


@pytest.fixture
def user_repo():
    """테스트용 User 저장소"""
    return FakeUserRepository()


@pytest.fixture
def session_repo():
    """테스트용 Session 저장소"""
    return FakeSessionRepository()


@pytest.fixture
def consult_repo():
    """테스트용 Consult 저장소"""
    return FakeConsultRepository()


@pytest.fixture
def ai_counselor():
    """테스트용 AI 상담사"""
    return FakeAICounselor(response="AI 응답입니다")


@pytest.fixture
def client(app, user_repo, session_repo, consult_repo, ai_counselor):
    """테스트 클라이언트"""
    # 의존성 주입 (간단하게 global 변수 사용)
    from app.consult.adapter.input.web import consult_router as router_module
    from app.auth.adapter.input.web import auth_dependency

    router_module._user_repository = user_repo
    router_module._consult_repository = consult_repo
    router_module._ai_counselor = ai_counselor
    auth_dependency._session_repository = session_repo

    return TestClient(app)


def test_start_consult_returns_session_id(client, user_repo, session_repo):
    """인증된 사용자가 상담을 시작하면 세션 ID와 AI 인사말을 반환한다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 세션
    session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(session)

    # When: 상담 시작 API를 호출하면
    response = client.post(
        "/consult/start",
        headers={"Authorization": "Bearer valid-session-123"}
    )

    # Then: 200 OK와 세션 ID, 인사말을 반환한다
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["session_id"] is not None
    assert "greeting" in data
    assert data["greeting"] is not None
    assert len(data["greeting"]) > 0


def test_start_consult_without_auth_returns_401(client):
    """인증 없이 상담을 시작하면 401을 반환한다"""
    # When: Authorization 헤더 없이 API를 호출하면
    response = client.post("/consult/start")

    # Then: 401 Unauthorized를 반환한다
    assert response.status_code == 401


def test_start_consult_with_invalid_session_returns_401(client):
    """잘못된 세션으로 상담을 시작하면 401을 반환한다"""
    # When: 잘못된 세션으로 API를 호출하면
    response = client.post(
        "/consult/start",
        headers={"Authorization": "Bearer invalid-session"}
    )

    # Then: 401 Unauthorized를 반환한다
    assert response.status_code == 401


def test_start_consult_without_user_profile_returns_400(client, user_repo, session_repo):
    """MBTI/Gender가 없는 사용자는 400을 반환한다"""
    # Given: MBTI/Gender가 없는 사용자
    user = User(id="user-123", email="test@example.com")
    user_repo.save(user)

    # Given: 유효한 세션
    session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(session)

    # When: 상담 시작 API를 호출하면
    response = client.post(
        "/consult/start",
        headers={"Authorization": "Bearer valid-session-123"}
    )

    # Then: 400 Bad Request를 반환한다
    assert response.status_code == 400


def test_send_message_returns_ai_response(client, user_repo, session_repo, consult_repo):
    """메시지 전송 시 AI 응답을 반환한다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # Given: 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="user-123",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    consult_repo.save(consult_session)

    # When: 메시지 전송 API를 호출하면
    response = client.post(
        "/consult/consult-session-123/message",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "안녕하세요"}
    )

    # Then: 200 OK와 AI 응답을 반환한다
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] == "AI 응답입니다"


def test_send_message_without_auth_returns_401(client, consult_repo):
    """인증 없이 메시지를 보내면 401을 반환한다"""
    # Given: 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="user-123",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    consult_repo.save(consult_session)

    # When: Authorization 헤더 없이 API를 호출하면
    response = client.post(
        "/consult/consult-session-123/message",
        json={"content": "안녕하세요"}
    )

    # Then: 401 Unauthorized를 반환한다
    assert response.status_code == 401


def test_send_message_to_others_session_returns_403(client, user_repo, session_repo, consult_repo):
    """다른 사용자의 세션에 메시지를 보내면 403을 반환한다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # Given: 다른 사용자의 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="other-user",
        mbti=MBTI("ENFP"),
        gender=Gender("FEMALE")
    )
    consult_repo.save(consult_session)

    # When: 다른 사용자의 세션에 메시지를 보내면
    response = client.post(
        "/consult/consult-session-123/message",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "안녕하세요"}
    )

    # Then: 403 Forbidden을 반환한다
    assert response.status_code == 403


def test_send_message_to_nonexistent_session_returns_404(client, user_repo, session_repo):
    """존재하지 않는 세션에 메시지를 보내면 404를 반환한다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # When: 존재하지 않는 세션에 메시지를 보내면
    response = client.post(
        "/consult/nonexistent-session/message",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "안녕하세요"}
    )

    # Then: 404 Not Found를 반환한다
    assert response.status_code == 404


def test_send_message_returns_remaining_turns(client, user_repo, session_repo, consult_repo):
    """메시지 전송 시 남은 턴 수를 반환한다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # Given: 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="user-123",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    consult_repo.save(consult_session)

    # When: 첫 번째 메시지 전송
    response = client.post(
        "/consult/consult-session-123/message",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "첫 번째 질문"}
    )

    # Then: 남은 턴 수가 4이다
    assert response.status_code == 200
    data = response.json()
    assert "remaining_turns" in data
    assert data["remaining_turns"] == 4


def test_send_message_to_completed_session_returns_400(client, user_repo, session_repo, consult_repo):
    """5턴 완료된 세션에 메시지를 보내면 400을 반환한다"""
    from app.consult.domain.message import Message

    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # Given: 5턴 완료된 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="user-123",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    for i in range(5):
        consult_session.add_message(Message(role="user", content=f"질문 {i+1}"))
        consult_session.add_message(Message(role="assistant", content=f"답변 {i+1}"))
    consult_repo.save(consult_session)

    # When: 6번째 메시지를 보내면
    response = client.post(
        "/consult/consult-session-123/message",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "추가 질문"}
    )

    # Then: 400 Bad Request를 반환한다
    assert response.status_code == 400
    assert "상담이 완료되었습니다" in response.json()["detail"]


def test_send_message_stream_returns_sse_events(client, user_repo, session_repo, consult_repo):
    """메시지 전송 시 SSE 스트리밍으로 AI 응답을 받을 수 있다"""
    # Given: 로그인한 사용자
    user = User(
        id="user-123",
        email="test@example.com",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    user_repo.save(user)

    # Given: 유효한 인증 세션
    auth_session = Session(session_id="valid-session-123", user_id="user-123")
    session_repo.save(auth_session)

    # Given: 상담 세션
    consult_session = ConsultSession(
        id="consult-session-123",
        user_id="user-123",
        mbti=MBTI("INTJ"),
        gender=Gender("MALE")
    )
    consult_repo.save(consult_session)

    # When: 스트리밍 API를 호출하면
    response = client.post(
        "/consult/consult-session-123/message/stream",
        headers={"Authorization": "Bearer valid-session-123"},
        json={"content": "안녕하세요"}
    )

    # Then: SSE 응답을 반환한다
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # SSE 형식 검증
    content = response.text
    assert "data:" in content
