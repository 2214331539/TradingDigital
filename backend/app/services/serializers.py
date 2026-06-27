from typing import List

from app.db.models import AiModel, AssistantPreset, Conversation, Message, Project, Role, User


def role_codes(user: User) -> List[str]:
    return [role.code for role in user.roles]


def permission_codes(user: User) -> List[str]:
    codes = set()
    for role in user.roles:
        for permission in role.permissions:
            codes.add(permission.code)
    return sorted(codes)


def user_summary(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "roles": role_codes(user),
        "permissions": permission_codes(user),
    }


def admin_user_out(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "roles": role_codes(user),
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


def conversation_out(conversation: Conversation):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "project_id": conversation.project_id,
        "model_id": conversation.model_id,
        "assistant_id": conversation.assistant_id,
        "status": conversation.status,
        "is_archived": conversation.is_archived,
        "is_favorited": conversation.is_favorited,
        "is_temporary": conversation.is_temporary,
        "message_count": conversation.message_count,
        "last_message_at": conversation.last_message_at,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def message_out(message: Message):
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "model_id": message.model_id,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def conversation_detail(conversation: Conversation):
    payload = conversation_out(conversation)
    payload["messages"] = [
        message_out(message) for message in conversation.messages if not message.deleted_at
    ]
    return payload


def model_out(model: AiModel):
    return {
        "id": model.id,
        "name": model.name,
        "provider": model.provider,
        "model_key": model.model_key,
        "context_length": model.context_length,
        "max_output_tokens": model.max_output_tokens,
        "enabled": model.enabled,
        "is_default": model.is_default,
    }


def assistant_out(assistant: AssistantPreset):
    return {
        "id": assistant.id,
        "name": assistant.name,
        "description": assistant.description,
        "icon": assistant.icon,
        "default_model_id": assistant.default_model_id,
    }


def project_out(project: Project):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "icon": project.icon,
        "color": project.color,
        "sort_order": project.sort_order,
        "is_archived": project.is_archived,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def role_out(role: Role):
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "is_system": role.is_system,
    }
