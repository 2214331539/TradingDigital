import asyncio
import uuid

from sqlalchemy import delete, insert, select

from tradedigital.apps.llm.domain.models import AssistantPreset, LlmModel, llm_model_role_grants
from tradedigital.core.config import get_settings
from tradedigital.core.crypto import encrypt_secret
from tradedigital.core.database import AsyncSessionLocal, engine
from tradedigital.core.time import utc_now
from tradedigital.platform.iam.models import (
    Permission,
    Role,
    SSOConnection,
    User,
    iam_role_permissions,
    iam_user_roles,
)
from tradedigital.platform.org.models import Enterprise

PERMISSIONS = [
    ("platform.admin.access", "平台管理入口", "platform", "admin", "access"),
    ("iam.user.read", "查看用户", "iam", "user", "read"),
    ("iam.user.manage", "管理用户", "iam", "user", "manage"),
    ("iam.role.read", "查看角色", "iam", "role", "read"),
    ("iam.role.manage", "管理角色", "iam", "role", "manage"),
    ("iam.permission.read", "查看权限", "iam", "permission", "read"),
    ("llm.chat.use", "使用 llm 对话", "llm", "chat", "use"),
    ("llm.conversation.read_own", "查看自己的 llm 会话", "llm", "conversation", "read_own"),
    ("llm.conversation.manage_own", "管理自己的 llm 会话", "llm", "conversation", "manage_own"),
    ("llm.model.read", "查看可用模型", "llm", "model", "read"),
    ("llm.model.manage", "管理模型", "llm", "model", "manage"),
    ("llm.preset.read", "查看助手预设", "llm", "preset", "read"),
    ("llm.preset.manage", "管理助手预设", "llm", "preset", "manage"),
    ("kb.knowledge_base.read", "查看知识库", "kb", "knowledge_base", "read"),
    ("kb.knowledge_base.manage", "管理知识库", "kb", "knowledge_base", "manage"),
    ("kb.query.use", "使用知识库查询", "kb", "query", "use"),
    ("kb.tool.execute", "调用知识库工具", "kb", "tool", "execute"),
    ("audit.log.read", "查看审计日志", "audit", "log", "read"),
]

ENTERPRISE_ADMIN_PERMISSIONS = [code for code, *_ in PERMISSIONS]
EMPLOYEE_PERMISSIONS = [
    "llm.chat.use",
    "llm.conversation.read_own",
    "llm.conversation.manage_own",
    "llm.model.read",
    "llm.preset.read",
    "kb.query.use",
]


async def ensure_enterprise(session) -> Enterprise:
    enterprise = await session.scalar(select(Enterprise).where(Enterprise.code == "default"))
    if enterprise:
        enterprise.name = "电商数字化演示企业"
        enterprise.status = "active"
        return enterprise
    enterprise = Enterprise(id=str(uuid.uuid4()), name="电商数字化演示企业", code="default", status="active")
    session.add(enterprise)
    await session.flush()
    return enterprise


async def ensure_permissions(session) -> dict[str, Permission]:
    permission_map: dict[str, Permission] = {}
    for code, name, module, resource, action in PERMISSIONS:
        permission = await session.scalar(select(Permission).where(Permission.code == code))
        if not permission:
            permission = Permission(
                id=str(uuid.uuid4()),
                code=code,
                name=name,
                module=module,
                resource=resource,
                action=action,
                created_at=utc_now(),
            )
            session.add(permission)
            await session.flush()
        permission_map[code] = permission
    return permission_map


async def ensure_roles(session, enterprise: Enterprise) -> dict[str, Role]:
    roles = {
        "enterprise_admin": ("企业管理员", "拥有 TradeDigital 企业管理与业务模块权限"),
        "employee": ("员工", "普通企业员工，仅可使用 llm 和被授权知识库"),
    }
    role_map: dict[str, Role] = {}
    for code, (name, description) in roles.items():
        role = await session.scalar(
            select(Role).where(Role.enterprise_id == enterprise.id, Role.code == code)
        )
        if not role:
            role = Role(
                id=code,
                enterprise_id=enterprise.id,
                code=code,
                name=name,
                description=description,
                is_system=True,
            )
            session.add(role)
            await session.flush()
        else:
            role.id = code
            role.name = name
            role.description = description
            role.is_system = True
        role_map[code] = role
    return role_map


async def sync_role_permissions(session, role_map: dict[str, Role], permission_map: dict[str, Permission]) -> None:
    grants = {
        "enterprise_admin": ENTERPRISE_ADMIN_PERMISSIONS,
        "employee": EMPLOYEE_PERMISSIONS,
    }
    for role_code, permission_codes in grants.items():
        await session.execute(
            delete(iam_role_permissions).where(iam_role_permissions.c.role_id == role_map[role_code].id)
        )
        await session.execute(
            insert(iam_role_permissions),
            [
                {
                    "role_id": role_map[role_code].id,
                    "permission_id": permission_map[permission_code].id,
                    "created_at": utc_now(),
                }
                for permission_code in permission_codes
            ],
        )


async def ensure_users(session, enterprise: Enterprise, role_map: dict[str, Role]) -> None:
    users = [
        ("admin@tradedigital.local", "TradeDigital Admin", "enterprise_admin"),
        ("employee@tradedigital.local", "TradeDigital Employee", "employee"),
    ]
    for email, name, role_code in users:
        user = await session.scalar(
            select(User).where(User.enterprise_id == enterprise.id, User.email == email)
        )
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                enterprise_id=enterprise.id,
                sso_provider="keycloak",
                sso_subject=f"seed:{email}",
                email=email,
                name=name,
                status="active",
            )
            session.add(user)
            await session.flush()
        await session.execute(delete(iam_user_roles).where(iam_user_roles.c.user_id == user.id))
        await session.execute(
            insert(iam_user_roles),
            [{"user_id": user.id, "role_id": role_map[role_code].id, "created_at": utc_now()}],
        )


async def ensure_sso_connection(session, enterprise: Enterprise) -> None:
    settings = get_settings()
    connection = await session.scalar(
        select(SSOConnection).where(
            SSOConnection.enterprise_id == enterprise.id,
            SSOConnection.provider == settings.oidc_provider,
        )
    )
    if not connection:
        connection = SSOConnection(
            id=str(uuid.uuid4()),
            enterprise_id=enterprise.id,
            provider=settings.oidc_provider,
            issuer_url=settings.oidc_issuer_url,
            client_id=settings.oidc_client_id,
            client_secret_encrypted=encrypt_secret(settings.oidc_client_secret),
            redirect_uri=settings.oidc_redirect_uri,
            enabled=True,
        )
        session.add(connection)
    else:
        connection.issuer_url = settings.oidc_issuer_url
        connection.client_id = settings.oidc_client_id
        connection.client_secret_encrypted = encrypt_secret(settings.oidc_client_secret)
        connection.redirect_uri = settings.oidc_redirect_uri
        connection.enabled = True


async def ensure_llm_defaults(session, enterprise: Enterprise, role_map: dict[str, Role]) -> None:
    settings = get_settings()
    model = await session.scalar(select(LlmModel).where(LlmModel.is_default.is_(True)))
    if not model:
        model = LlmModel(
            id=str(uuid.uuid4()),
            provider_code=settings.default_model_provider_code,
            model_key=settings.default_model_key,
            display_name=settings.default_model_display_name,
            type="chat",
            base_url=settings.default_model_base_url,
            api_key_ref=settings.default_model_api_key_ref,
            context_length=settings.default_model_context_length,
            max_output_tokens=settings.default_model_max_output_tokens,
            default_temperature=settings.default_model_temperature,
            support_streaming=settings.default_model_support_streaming,
            enabled=True,
            is_default=True,
        )
        session.add(model)
        await session.flush()
    else:
        model.provider_code = settings.default_model_provider_code
        model.model_key = settings.default_model_key
        model.display_name = settings.default_model_display_name
        model.base_url = settings.default_model_base_url
        model.api_key_ref = settings.default_model_api_key_ref
        model.support_streaming = settings.default_model_support_streaming
        model.enabled = True

    await session.execute(delete(llm_model_role_grants).where(llm_model_role_grants.c.model_id == model.id))
    await session.execute(
        insert(llm_model_role_grants),
        [
            {"model_id": model.id, "role_id": role.id, "created_at": utc_now()}
            for role in role_map.values()
        ],
    )

    preset = await session.scalar(
        select(AssistantPreset).where(
            AssistantPreset.enterprise_id == enterprise.id,
            AssistantPreset.name == "通用助手",
        )
    )
    if not preset:
        session.add(
            AssistantPreset(
                id=str(uuid.uuid4()),
                enterprise_id=enterprise.id,
                name="通用助手",
                description="适合日常问答、写作、代码解释和方案设计。",
                system_prompt="你是 TradeDigital 平台中的 llm 助手，回答要清晰、可靠、实用。",
                visibility="enterprise",
                default_model_id=model.id,
                icon="sparkles",
                enabled=True,
            )
        )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        enterprise = await ensure_enterprise(session)
        permission_map = await ensure_permissions(session)
        role_map = await ensure_roles(session, enterprise)
        await sync_role_permissions(session, role_map, permission_map)
        await ensure_users(session, enterprise, role_map)
        await ensure_sso_connection(session, enterprise)
        await ensure_llm_defaults(session, enterprise, role_map)
        await session.commit()
    await engine.dispose()
    print("TradeDigital seed completed.")


if __name__ == "__main__":
    asyncio.run(main())
