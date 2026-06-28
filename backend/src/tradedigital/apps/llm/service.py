from tradedigital.apps.llm.models import AssistantPreset, Conversation, LlmModel, LlmProject, Message


def model_out(model: LlmModel) -> dict:
    return {
        "id": model.id,
        "provider_code": model.provider_code,
        "provider": model.provider_code,
        "model_key": model.model_key,
        "display_name": model.display_name,
        "name": model.display_name,
        "type": model.type,
        "context_length": model.context_length,
        "max_output_tokens": model.max_output_tokens,
        "support_streaming": model.support_streaming,
        "enabled": model.enabled,
        "is_default": model.is_default,
    }


def assistant_out(preset: AssistantPreset) -> dict:
    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "system_prompt": preset.system_prompt,
        "visibility": preset.visibility,
        "icon": preset.icon,
        "default_model_id": preset.default_model_id,
    }


def conversation_out(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "enterprise_id": conversation.enterprise_id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "assistant_preset_id": conversation.assistant_preset_id,
        "assistant_id": conversation.assistant_preset_id,
        "model_id": conversation.model_id,
        "project_id": conversation.project_id,
        "status": conversation.status,
        "archived": conversation.archived,
        "is_archived": conversation.archived,
        "pinned": conversation.pinned,
        "is_favorited": conversation.pinned,
        "temporary": conversation.temporary,
        "is_temporary": conversation.temporary,
        "message_count": conversation.message_count,
        "last_message_at": conversation.last_message_at,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def project_out(project: LlmProject) -> dict:
    return {
        "id": project.id,
        "enterprise_id": project.enterprise_id,
        "user_id": project.user_id,
        "name": project.name,
        "description": project.description,
        "color": project.color,
        "archived": project.archived,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def message_out(message: Message) -> dict:
    return {
        "id": message.id,
        "enterprise_id": message.enterprise_id,
        "conversation_id": message.conversation_id,
        "user_id": message.user_id,
        "role": message.role,
        "content": message.content,
        "metadata_json": message.metadata_json,
        "status": message.status,
        "model_id": message.model_id,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def conversation_detail(conversation: Conversation) -> dict:
    payload = conversation_out(conversation)
    payload["messages"] = [
        message_out(message) for message in conversation.messages if not message.deleted_at
    ]
    return payload
