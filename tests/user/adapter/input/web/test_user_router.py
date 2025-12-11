import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.user.adapter.input.web.user_router import user_router
from app.user.domain.user import User
from app.auth.domain.session import Session
from tests.user.fixtures.fake_user_repository import FakeUserRepository
from tests.auth.fixtures.fake_session_repository import FakeSessionRepository


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(user_router, prefix="/user")
    return app


@pytest.fixture
def user_repo():
    return FakeUserRepository()


@pytest.fixture
def session_repo():
    return FakeSessionRepository()


@pytest.fixture
def client(app, user_repo, session_repo):
    from app.user.adapter.input.web import user_router as router_module
    from app.auth.adapter.input.web import auth_dependency

    router_module._user_repository = user_repo
    auth_dependency._session_repository = session_repo

    return TestClient(app)


def test_update_profile_success_with_authorization_header(client, user_repo, session_repo):
    user = User(id="user-123", email="test@example.com")
    user_repo.save(user)
    session_repo.save(Session(session_id="valid-session", user_id="user-123"))

    response = client.put(
        "/user/profile",
        headers={"Authorization": "Bearer valid-session"},
        json={"mbti": "intj", "gender": "male"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mbti"] == "INTJ"
    assert data["gender"] == "MALE"


def test_update_profile_success_with_cookie(client, user_repo, session_repo):
    user = User(id="user-123", email="test@example.com")
    user_repo.save(user)
    session_repo.save(Session(session_id="valid-session", user_id="user-123"))

    response = client.put(
        "/user/profile",
        cookies={"session_id": "valid-session"},
        json={"mbti": "intj", "gender": "female"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mbti"] == "INTJ"
    assert data["gender"] == "FEMALE"


def test_update_profile_requires_auth(client):
    response = client.put(
        "/user/profile",
        json={"mbti": "INTJ", "gender": "MALE"},
    )
    assert response.status_code == 401


def test_update_profile_user_not_found_returns_404(client, session_repo):
    session_repo.save(Session(session_id="valid-session", user_id="missing-user"))

    response = client.put(
        "/user/profile",
        headers={"Authorization": "Bearer valid-session"},
        json={"mbti": "INTJ", "gender": "MALE"},
    )

    assert response.status_code == 404


def test_update_profile_invalid_mbti_returns_400(client, user_repo, session_repo):
    user = User(id="user-123", email="test@example.com")
    user_repo.save(user)
    session_repo.save(Session(session_id="valid-session", user_id="user-123"))

    response = client.put(
        "/user/profile",
        headers={"Authorization": "Bearer valid-session"},
        json={"mbti": "XXXX", "gender": "MALE"},
    )

    assert response.status_code == 400


def test_get_profile_success(client, user_repo, session_repo):
    user = User(id="user-123", email="test@example.com")
    user_repo.save(user)
    session_repo.save(Session(session_id="valid-session", user_id="user-123"))

    response = client.get(
        "/user/profile",
        headers={"Authorization": "Bearer valid-session"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-123"
    assert data["email"] == "test@example.com"
    assert data["mbti"] is None
    assert data["gender"] is None


def test_get_profile_requires_auth(client):
    response = client.get("/user/profile")
    assert response.status_code == 401


def test_get_profile_user_not_found_returns_404(client, session_repo):
    session_repo.save(Session(session_id="valid-session", user_id="missing-user"))

    response = client.get(
        "/user/profile",
        headers={"Authorization": "Bearer valid-session"},
    )

    assert response.status_code == 404

