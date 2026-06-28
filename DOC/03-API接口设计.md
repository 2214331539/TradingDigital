# TradeDigital API 接口设计

## 1. 通用规则

API 前缀：

```text
/api/v1
```

响应格式：

```json
{
  "code": "OK",
  "message": "success",
  "data": {}
}
```

登录态：

```text
Cookie: td_session
HttpOnly: true
SameSite: Lax
```

前端所有请求必须设置：

```ts
credentials: "include"
```

## 2. Auth API

```text
GET  /api/v1/auth/sso/login
GET  /api/v1/auth/sso/callback
GET  /api/v1/auth/me
POST /api/v1/auth/logout
```

登录流程：

```text
前端 /login
→ /api/v1/auth/sso/login?enterprise_code=default
→ Keycloak
→ /api/v1/auth/sso/callback
→ 后端换 token、校验 id_token、upsert iam_users
→ 创建 iam_sessions
→ 写入 td_session
→ 重定向 /app
```

## 3. Platform API

```text
GET   /api/v1/platform/enterprises/current

GET   /api/v1/platform/users
GET   /api/v1/platform/users/{user_id}
PATCH /api/v1/platform/users/{user_id}/status
PATCH /api/v1/platform/users/{user_id}/roles

GET   /api/v1/platform/roles
POST  /api/v1/platform/roles
PATCH /api/v1/platform/roles/{role_id}
PATCH /api/v1/platform/roles/{role_id}/permissions

GET   /api/v1/platform/permissions
```

## 4. llm API

```text
GET    /api/v1/llm/models
GET    /api/v1/llm/assistant-presets

GET    /api/v1/llm/conversations
POST   /api/v1/llm/conversations
GET    /api/v1/llm/conversations/{conversation_id}
PATCH  /api/v1/llm/conversations/{conversation_id}
DELETE /api/v1/llm/conversations/{conversation_id}

POST   /api/v1/llm/chat/stream
POST   /api/v1/llm/chat/regenerate
POST   /api/v1/llm/chat/edit-and-rerun
```

权限要求：

|接口|权限|
|---|---|
|GET /llm/models|`llm.model.read`|
|GET /llm/assistant-presets|`llm.preset.read`|
|GET /llm/conversations|`llm.conversation.read_own`|
|POST/PATCH/DELETE /llm/conversations|`llm.conversation.manage_own`|
|POST /llm/chat/stream|`llm.chat.use`|

所有会话查询必须同时带：

```text
enterprise_id = ctx.enterprise_id
user_id = ctx.user_id
```

## 5. KnowledgeBase API

```text
GET   /api/v1/kb/knowledge-bases
POST  /api/v1/kb/knowledge-bases
GET   /api/v1/kb/knowledge-bases/{kb_id}
PATCH /api/v1/kb/knowledge-bases/{kb_id}
PATCH /api/v1/kb/knowledge-bases/{kb_id}/roles

POST  /api/v1/kb/query
POST  /api/v1/kb/tools/execute
```

## 6. Audit API

```text
GET /api/v1/audit/logs
```

需要权限：

```text
audit.log.read
```

## 7. SSE 事件

`POST /api/v1/llm/chat/stream` 返回：

```text
event: message_start
event: delta
event: message_end
event: error
```

AI 模型调用完成或失败后必须写入：

- `llm_messages`
- `llm_model_call_logs`
- `audit_operation_logs`
