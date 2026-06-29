import asyncio
import os
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

TEST_DIR = tempfile.mkdtemp(prefix="tradedigital-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{os.path.join(TEST_DIR, 'test.db')}"
os.environ["SESSION_COOKIE_NAME"] = "td_session"
os.environ["DEFAULT_MODEL_API_KEY_REF"] = "TEST_MODEL_API_KEY"
os.environ["TEST_MODEL_API_KEY"] = "test-key"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradedigital.apps.llm.models import LlmModel, llm_model_role_grants  # noqa: E402
from tradedigital.apps.knowledge import models as knowledge_models  # noqa: F401, E402
from tradedigital.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from tradedigital.core.time import utc_now  # noqa: E402
from tradedigital.main import app  # noqa: E402
from tradedigital.platform.iam import oidc  # noqa: E402
from tradedigital.platform.audit import models as audit_models  # noqa: F401, E402
from tradedigital.platform.iam.models import User  # noqa: E402
from tradedigital.platform.iam.service import create_session  # noqa: E402
from tradedigital.platform.org import models as org_models  # noqa: F401, E402
from tradedigital.scripts.seed import main as seed_main  # noqa: E402


async def prepare_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await seed_main()


asyncio.run(prepare_database())


async def create_cookie(email: str) -> str:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        user = await session.scalar(select(User).where(User.email == email))
        assert user
        token = await create_session(session, user, user_agent="pytest", ip_address="127.0.0.1")
        await session.commit()
        return token


@contextmanager
def authenticated_client(email: str = "employee@tradedigital.local") -> Iterator[TestClient]:
    client = TestClient(app)
    token = asyncio.run(create_cookie(email))
    client.cookies.set("td_session", token)
    with client:
        yield client


async def get_user_id(email: str) -> str:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        user = await session.scalar(select(User).where(User.email == email))
        assert user
        return user.id


async def create_test_user(email: str, name: str = "Test User") -> str:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        seed_user = await session.scalar(select(User).where(User.email == "employee@tradedigital.local"))
        assert seed_user
        user = User(
            id=str(uuid.uuid4()),
            enterprise_id=seed_user.enterprise_id,
            sso_provider="pytest",
            sso_subject=f"pytest:{email}",
            email=email,
            name=name,
            status="active",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(user)
        await session.commit()
        return user.id


def test_archived_conversation_is_hidden_from_default_list():
    with authenticated_client() as client:
        title = f"archive-check-{uuid.uuid4()}"

        created = client.post("/api/v1/llm/conversations", json={"title": title})
        assert created.status_code == 200
        conversation_id = created.json()["data"]["id"]

        archived = client.patch(
            f"/api/v1/llm/conversations/{conversation_id}",
            json={"archived": True},
        )
        assert archived.status_code == 200

        default_list = client.get("/api/v1/llm/conversations")
        assert default_list.status_code == 200
        default_ids = {item["id"] for item in default_list.json()["data"]["items"]}
        assert conversation_id not in default_ids

        archived_list = client.get("/api/v1/llm/conversations?archived=true")
        assert archived_list.status_code == 200
        archived_ids = {item["id"] for item in archived_list.json()["data"]["items"]}
        assert conversation_id in archived_ids


def test_employee_cannot_select_model_without_role_access():
    with authenticated_client() as client:
        model_id = str(uuid.uuid4())

        async def add_restricted_model() -> None:
            async with AsyncSessionLocal() as session:
                model = LlmModel(
                    id=model_id,
                    provider_code="openai_compatible",
                    model_key=f"admin-only-{uuid.uuid4()}",
                    display_name="Admin Only Model",
                    type="chat",
                    base_url="https://example.invalid/v1",
                    api_key_ref="TEST_MODEL_API_KEY",
                    support_streaming=False,
                    enabled=True,
                    is_default=False,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                session.add(model)
                await session.flush()
                await session.execute(
                    llm_model_role_grants.insert().values(
                        model_id=model_id,
                        role_id="enterprise_admin",
                        created_at=utc_now(),
                    )
                )
                await session.commit()

        asyncio.run(add_restricted_model())

        response = client.post(
            "/api/v1/llm/conversations",
            json={"title": "unauthorized-model-check", "model_id": model_id},
        )
        assert response.status_code == 403


def test_employee_cannot_read_platform_users():
    with authenticated_client() as client:
        response = client.get("/api/v1/platform/users")
        assert response.status_code == 403


def test_admin_can_read_user_detail_beyond_first_page():
    async def add_many_users() -> str:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            seed_user = await session.scalar(
                select(User).where(User.email == "employee@tradedigital.local")
            )
            assert seed_user
            old_timestamp = utc_now() - timedelta(days=1)
            target = User(
                id=str(uuid.uuid4()),
                enterprise_id=seed_user.enterprise_id,
                sso_provider="pytest",
                sso_subject=f"pytest:target:{uuid.uuid4()}",
                email=f"target-{uuid.uuid4()}@example.test",
                name="Pagination Target",
                status="active",
                created_at=old_timestamp,
                updated_at=old_timestamp,
            )
            session.add(target)
            for index in range(105):
                session.add(
                    User(
                        id=str(uuid.uuid4()),
                        enterprise_id=seed_user.enterprise_id,
                        sso_provider="pytest",
                        sso_subject=f"pytest:filler:{uuid.uuid4()}",
                        email=f"filler-{index}-{uuid.uuid4()}@example.test",
                        name=f"Filler {index}",
                        status="active",
                        created_at=utc_now() + timedelta(seconds=index),
                        updated_at=utc_now() + timedelta(seconds=index),
                    )
                )
            await session.commit()
            return target.id

    target_id = asyncio.run(add_many_users())
    with authenticated_client("admin@tradedigital.local") as client:
        response = client.get(f"/api/v1/platform/users/{target_id}")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == target_id


def test_admin_role_assignment_rejects_unknown_role():
    user_id = asyncio.run(create_test_user(f"role-missing-{uuid.uuid4()}@example.test"))
    with authenticated_client("admin@tradedigital.local") as client:
        response = client.patch(
            f"/api/v1/platform/users/{user_id}/roles",
            json={"role_ids": ["missing-role"]},
        )
        assert response.status_code == 404


def test_admin_role_assignment_serializes_permissions_after_update():
    user_id = asyncio.run(create_test_user(f"role-update-{uuid.uuid4()}@example.test"))
    with authenticated_client("admin@tradedigital.local") as client:
        response = client.patch(
            f"/api/v1/platform/users/{user_id}/roles",
            json={"role_ids": ["employee"]},
        )
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["roles"] == ["employee"]
        assert "llm.chat.use" in payload["permissions"]


def test_admin_role_permission_update_rejects_unknown_permission():
    with authenticated_client("admin@tradedigital.local") as client:
        response = client.patch(
            "/api/v1/platform/roles/employee/permissions",
            json={"permission_ids": ["missing-permission"]},
        )
        assert response.status_code == 404


def test_invalid_user_status_is_rejected():
    user_id = asyncio.run(get_user_id("employee@tradedigital.local"))
    with authenticated_client("admin@tradedigital.local") as client:
        response = client.patch(
            f"/api/v1/platform/users/{user_id}/status",
            json={"status": "paused"},
        )
        assert response.status_code == 422


def test_regenerate_endpoint_is_explicitly_not_implemented():
    with authenticated_client() as client:
        response = client.post(
            "/api/v1/llm/chat/regenerate",
            json={"conversation_id": str(uuid.uuid4()), "message_id": str(uuid.uuid4())},
        )
        assert response.status_code == 501


def test_llm_project_can_group_conversations():
    with authenticated_client() as client:
        project = client.post("/api/v1/llm/projects", json={"name": "Launch Research"})
        assert project.status_code == 200
        project_id = project.json()["data"]["id"]

        created = client.post(
            "/api/v1/llm/conversations",
            json={"title": "Project conversation", "project_id": project_id},
        )
        assert created.status_code == 200
        assert created.json()["data"]["project_id"] == project_id

        projects = client.get("/api/v1/llm/projects")
        assert projects.status_code == 200
        assert project_id in {item["id"] for item in projects.json()["data"]}


def test_llm_rejects_foreign_project():
    first_project_id: str
    with authenticated_client("admin@tradedigital.local") as client:
        project = client.post("/api/v1/llm/projects", json={"name": "Admin Private"})
        assert project.status_code == 200
        first_project_id = project.json()["data"]["id"]

    with authenticated_client("employee@tradedigital.local") as client:
        created = client.post(
            "/api/v1/llm/conversations",
            json={"title": "Should fail", "project_id": first_project_id},
        )
        assert created.status_code == 404


def test_message_feedback_updates_metadata():
    async def add_message() -> str:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            user = await session.scalar(select(User).where(User.email == "employee@tradedigital.local"))
            assert user
            from tradedigital.apps.llm.models import Conversation, Message

            conversation = Conversation(
                enterprise_id=user.enterprise_id,
                user_id=user.id,
                title="feedback-check",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(conversation)
            await session.flush()
            message = Message(
                enterprise_id=user.enterprise_id,
                conversation_id=conversation.id,
                role="assistant",
                content="hello",
                status="completed",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(message)
            await session.commit()
            return message.id

    message_id = asyncio.run(add_message())
    with authenticated_client() as client:
        response = client.patch(f"/api/v1/llm/messages/{message_id}", json={"feedback": "like"})
        assert response.status_code == 200
        assert response.json()["data"]["metadata_json"]["feedback"] == "like"


def test_oidc_discovery_ignores_proxy_environment(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, str]:
            return {"issuer": "http://127.0.0.1:8080/realms/tradedigital"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url: str):
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr(oidc.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(oidc.discover_oidc("http://127.0.0.1:8080/realms/tradedigital"))

    assert result["issuer"] == "http://127.0.0.1:8080/realms/tradedigital"
    assert captured["trust_env"] is False
    assert captured["url"].endswith("/.well-known/openid-configuration")


def test_create_role_generates_uuid_primary_key():
    with authenticated_client("admin@tradedigital.local") as client:
        code = f"analyst_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/platform/roles",
            json={"code": code, "name": "Data Analyst"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # The primary key must be a generated UUID, not the (per-enterprise) code,
        # otherwise two enterprises reusing a code would collide on the global PK.
        assert data["code"] == code
        assert data["id"] != code
        assert uuid.UUID(data["id"])


def test_client_secret_encryption_round_trip():
    from tradedigital.core.crypto import decrypt_secret, encrypt_secret

    secret = "super-secret-value"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert encrypted.startswith("enc:v1:")
    assert decrypt_secret(encrypted) == secret
    # Legacy plaintext (no prefix) must pass through unchanged for backward compat.
    assert decrypt_secret(secret) == secret


def teardown_module() -> None:
    asyncio.run(engine.dispose())
