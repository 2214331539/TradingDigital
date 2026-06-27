import os

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import AiModel, AssistantPreset, Organization, Permission, Role, User

PERMISSIONS = [
    ("chat", "创建会话", "chat:create"),
    ("chat", "查看自己的会话", "chat:read_own"),
    ("chat", "更新自己的会话", "chat:update_own"),
    ("chat", "删除自己的会话", "chat:delete_own"),
    ("chat", "分享自己的会话", "chat:share_own"),
    ("chat", "导出自己的会话", "chat:export_own"),
    ("chat", "审计所有会话", "chat:audit_all"),
    ("user", "查看用户", "user:read"),
    ("user", "创建用户", "user:create"),
    ("user", "编辑用户", "user:update"),
    ("user", "禁用用户", "user:disable"),
    ("user", "删除用户", "user:delete"),
    ("user", "重置密码", "user:reset_password"),
    ("user", "分配角色", "user:assign_role"),
    ("role", "查看角色", "role:read"),
    ("role", "创建角色", "role:create"),
    ("role", "编辑角色", "role:update"),
    ("role", "删除角色", "role:delete"),
    ("role", "分配角色", "role:assign"),
    ("permission", "查看权限", "permission:read"),
    ("permission", "维护权限", "permission:update"),
    ("model", "查看模型", "model:read"),
    ("model", "使用基础模型", "model:use_basic"),
    ("model", "使用高级模型", "model:use_advanced"),
    ("model", "新增模型", "model:create"),
    ("model", "编辑模型", "model:update"),
    ("model", "禁用模型", "model:disable"),
    ("model", "删除模型", "model:delete"),
    ("model", "测试模型", "model:test"),
    ("system", "查看系统", "system:read"),
    ("system", "更新系统", "system:update"),
    ("analytics", "查看统计", "analytics:read"),
    ("log", "查看日志", "log:read"),
    ("audit", "敏感审计", "audit:read_sensitive"),
]


def ensure_role(db: Session, code: str, name: str, description: str) -> Role:
    role = db.query(Role).filter(Role.code == code).first()
    if role:
        return role
    role = Role(code=code, name=name, description=description, is_system=True)
    db.add(role)
    db.flush()
    return role


def ensure_lightweight_schema(db: Session) -> None:
    inspector = inspect(db.bind)
    if "conversations" in inspector.get_table_names():
        conversation_columns = {column["name"] for column in inspector.get_columns("conversations")}
        if "project_id" not in conversation_columns:
            db.execute(text("ALTER TABLE conversations ADD COLUMN project_id VARCHAR(36)"))
            db.commit()


def seed_database(db: Session) -> None:
    ensure_lightweight_schema(db)

    organization = db.query(Organization).filter(Organization.code == "default").first()
    if not organization:
        organization = Organization(name="默认组织", code="default")
        db.add(organization)
        db.flush()

    permission_map = {}
    for module, name, code in PERMISSIONS:
        permission = db.query(Permission).filter(Permission.code == code).first()
        if not permission:
            permission = Permission(module=module, name=name, code=code)
            db.add(permission)
            db.flush()
        permission_map[code] = permission

    super_admin = ensure_role(db, "super_admin", "超级管理员", "系统最高权限角色")
    admin = ensure_role(db, "admin", "管理员", "企业内部管理角色")
    user = ensure_role(db, "user", "普通用户", "普通聊天用户")

    super_admin.permissions = list(permission_map.values())
    admin_codes = [
        code
        for code in permission_map
        if code
        not in {
            "chat:audit_all",
            "user:delete",
            "role:create",
            "role:update",
            "role:delete",
            "permission:update",
            "model:delete",
            "system:update",
            "audit:read_sensitive",
        }
    ]
    admin.permissions = [permission_map[code] for code in admin_codes]
    user_codes = [
        "chat:create",
        "chat:read_own",
        "chat:update_own",
        "chat:delete_own",
        "chat:share_own",
        "chat:export_own",
        "model:read",
        "model:use_basic",
    ]
    user.permissions = [permission_map[code] for code in user_codes]

    users = [
        ("superadmin", "superadmin@chatai.local", "ChatAI@123456", [super_admin]),
        ("admin", "admin@chatai.local", "Admin@123456", [admin]),
        ("demo", "user@chatai.local", "User@123456", [user]),
    ]
    for username, email, password, roles in users:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            db.add(
                User(
                    organization_id=organization.id,
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    roles=roles,
                )
            )

    default_model_name = os.getenv("CHATAI_DEFAULT_MODEL_NAME", "ChatAI Default")
    default_model_provider = os.getenv("CHATAI_DEFAULT_MODEL_PROVIDER", "openai_compatible")
    default_model_key = os.getenv("CHATAI_DEFAULT_MODEL_KEY", "gpt-4o-mini")
    default_model_base_url = os.getenv("CHATAI_DEFAULT_MODEL_BASE_URL", "https://api.openai.com/v1")
    default_model_api_key_ref = os.getenv("CHATAI_DEFAULT_MODEL_API_KEY_REF", "OPENAI_API_KEY")

    model = db.query(AiModel).filter(AiModel.is_default.is_(True)).first()
    if not model:
        model = AiModel(
            name=default_model_name,
            provider=default_model_provider,
            model_key=default_model_key,
            base_url=default_model_base_url,
            api_key_ref=default_model_api_key_ref,
            context_length=128000,
            max_output_tokens=4096,
            enabled=True,
            is_default=True,
            sort_order=1,
            roles=[super_admin, admin, user],
        )
        db.add(model)
        db.flush()
    elif model.provider == "mock" or model.model_key == "mock-chat-model":
        model.name = default_model_name
        model.provider = default_model_provider
        model.model_key = default_model_key
        model.base_url = default_model_base_url
        model.api_key_ref = default_model_api_key_ref
        model.enabled = True
        model.is_default = True
        model.roles = [super_admin, admin, user]

    if not db.query(AssistantPreset).filter(AssistantPreset.name == "通用助手").first():
        db.add(
            AssistantPreset(
                name="通用助手",
                description="适合日常问答、写作、代码解释和方案设计。",
                system_prompt="你是 ChatAI，一个清晰、可靠、实用的 AI 助手。",
                default_model_id=model.id,
                icon="sparkles",
                enabled=True,
                is_system=True,
            )
        )

    db.commit()
