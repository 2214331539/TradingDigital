from tradedigital.apps.knowledge.models import KnowledgeBase, Tool


def knowledge_base_out(row: KnowledgeBase) -> dict:
    return {
        "id": row.id,
        "enterprise_id": row.enterprise_id,
        "name": row.name,
        "description": row.description,
        "type": row.type,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def tool_out(row: Tool) -> dict:
    return {
        "id": row.id,
        "enterprise_id": row.enterprise_id,
        "knowledge_base_id": row.knowledge_base_id,
        "name": row.name,
        "code": row.code,
        "description": row.description,
        "schema_json": row.schema_json,
        "endpoint_url": row.endpoint_url,
        "enabled": row.enabled,
    }

