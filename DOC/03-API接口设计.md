# ChatAI API 接口设计

## 1. 接口约定

### 1.1 基础路径

```text
/api/v1
```

### 1.2 认证方式

业务接口默认使用 Bearer Token。

```http
Authorization: Bearer <access_token>
```

### 1.3 通用响应结构

成功：

```json
{
  "code": "OK",
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数错误",
  "details": [
    {
      "field": "email",
      "reason": "邮箱格式不正确"
    }
  ]
}
```

分页：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

### 1.4 通用错误码

|错误码|HTTP|说明|
|---|---:|---|
|`UNAUTHORIZED`|401|未登录或 Token 无效|
|`FORBIDDEN`|403|无权限|
|`NOT_FOUND`|404|资源不存在|
|`VALIDATION_ERROR`|422|参数校验失败|
|`CONFLICT`|409|资源冲突|
|`RATE_LIMITED`|429|请求过于频繁|
|`MODEL_UNAVAILABLE`|503|模型不可用|
|`MODEL_CALL_FAILED`|502|模型调用失败|
|`INTERNAL_ERROR`|500|服务器错误|

## 2. 认证接口

### 2.1 登录

```http
POST /api/v1/auth/login
```

请求：

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid",
      "username": "alice",
      "email": "user@example.com",
      "roles": ["user"],
      "permissions": ["chat:create", "chat:read_own"]
    }
  }
}
```

### 2.2 刷新 Token

```http
POST /api/v1/auth/refresh
```

请求：

```json
{
  "refresh_token": "jwt"
}
```

### 2.3 退出登录

```http
POST /api/v1/auth/logout
```

### 2.4 获取当前用户

```http
GET /api/v1/auth/me
```

### 2.5 修改密码

```http
POST /api/v1/auth/change-password
```

请求：

```json
{
  "old_password": "old",
  "new_password": "new"
}
```

## 3. 会话接口

### 3.1 创建会话

```http
POST /api/v1/conversations
```

请求：

```json
{
  "title": "新聊天",
  "model_id": "uuid",
  "assistant_id": "uuid",
  "is_temporary": false,
  "project_id": null
}
```

响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "id": "uuid",
    "title": "新聊天",
    "model_id": "uuid",
    "assistant_id": "uuid",
    "is_archived": false,
    "is_favorited": false,
    "created_at": "2026-06-27T12:00:00Z",
    "updated_at": "2026-06-27T12:00:00Z"
  }
}
```

### 3.2 会话列表

```http
GET /api/v1/conversations?page=1&page_size=30&keyword=&archived=false&favorited=
```

返回当前用户自己的会话。管理员不通过该接口查看他人会话。

### 3.3 会话详情

```http
GET /api/v1/conversations/{conversation_id}
```

响应包含会话信息和消息列表。

### 3.4 更新会话

```http
PATCH /api/v1/conversations/{conversation_id}
```

请求：

```json
{
  "title": "新的标题",
  "is_archived": false,
  "is_favorited": true,
  "model_id": "uuid",
  "assistant_id": "uuid"
}
```

### 3.5 删除会话

```http
DELETE /api/v1/conversations/{conversation_id}
```

软删除，普通用户只能删除自己的会话。

### 3.6 搜索会话

```http
GET /api/v1/conversations/search?keyword=产品文档&page=1&page_size=20
```

搜索范围：

- 会话标题。
- 用户消息。
- AI 消息。

### 3.7 清空当前用户会话

```http
DELETE /api/v1/conversations
```

请求：

```json
{
  "confirm_text": "DELETE"
}
```

## 4. 聊天与消息接口

### 4.1 获取消息列表

```http
GET /api/v1/conversations/{conversation_id}/messages
```

### 4.2 发送消息并流式生成

```http
POST /api/v1/chat/completions/stream
Accept: text/event-stream
```

请求：

```json
{
  "conversation_id": "uuid",
  "model_id": "uuid",
  "assistant_id": "uuid",
  "content": "请帮我写一份项目计划",
  "parent_message_id": "uuid",
  "temporary": false,
  "options": {
    "temperature": 0.7,
    "max_output_tokens": 2048
  }
}
```

SSE 事件：

```text
event: message_start
data: {"message_id":"uuid","conversation_id":"uuid"}

event: delta
data: {"message_id":"uuid","content":"第一段增量文本"}

event: usage
data: {"prompt_tokens":100,"completion_tokens":200,"total_tokens":300,"latency_ms":1200}

event: message_end
data: {"message_id":"uuid","status":"completed"}
```

错误：

```text
event: error
data: {"code":"MODEL_CALL_FAILED","message":"模型调用失败，请稍后重试"}
```

### 4.3 停止生成

```http
POST /api/v1/chat/generations/{generation_id}/stop
```

说明：

- 前端主动中断连接。
- 后端标记当前生成任务为 cancelled。
- 已生成内容保留。

### 4.4 重新生成

```http
POST /api/v1/messages/{message_id}/regenerate
Accept: text/event-stream
```

`message_id` 为需要重新生成的 AI 消息 ID，后端找到对应的上一条用户消息并重新调用模型。

### 4.5 编辑用户消息并重新生成

```http
POST /api/v1/messages/{message_id}/edit-and-regenerate
Accept: text/event-stream
```

请求：

```json
{
  "content": "修改后的问题",
  "strategy": "truncate_after"
}
```

第一版 `strategy` 固定为 `truncate_after`，表示该用户消息之后的消息软删除并重新生成。

### 4.6 更新消息反馈

```http
POST /api/v1/messages/{message_id}/feedback
```

请求：

```json
{
  "rating": "down",
  "reason": "回答不准确",
  "comment": "第三段内容有误"
}
```

### 4.7 删除单条消息

```http
DELETE /api/v1/messages/{message_id}
```

仅允许删除自己的会话消息。

## 5. 模型接口

### 5.1 当前用户可用模型

```http
GET /api/v1/models/available
```

返回当前用户有权限使用的模型。

### 5.2 模型详情

```http
GET /api/v1/models/{model_id}
```

## 6. 助手预设接口

### 6.1 可用助手列表

```http
GET /api/v1/assistants
```

### 6.2 助手详情

```http
GET /api/v1/assistants/{assistant_id}
```

## 7. 分享接口

### 7.1 创建分享链接

```http
POST /api/v1/conversations/{conversation_id}/share
```

请求：

```json
{
  "title": "分享标题",
  "visibility": "organization",
  "show_user_name": false,
  "expires_at": null
}
```

### 7.2 关闭分享

```http
DELETE /api/v1/share-links/{share_id}
```

### 7.3 访问分享

```http
GET /api/v1/share/{token}
```

## 8. 个人设置接口

### 8.1 获取个人设置

```http
GET /api/v1/user-settings/me
```

### 8.2 更新个人设置

```http
PATCH /api/v1/user-settings/me
```

请求：

```json
{
  "theme": "system",
  "language": "zh-CN",
  "default_model_id": "uuid",
  "default_assistant_id": "uuid"
}
```

### 8.3 导出个人会话

```http
POST /api/v1/exports/conversations
```

请求：

```json
{
  "format": "json",
  "conversation_ids": []
}
```

## 9. 管理端用户接口

### 9.1 用户列表

```http
GET /api/v1/admin/users?page=1&page_size=20&keyword=&status=&role=
```

权限：`user:read`

### 9.2 创建用户

```http
POST /api/v1/admin/users
```

权限：`user:create`

请求：

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "initial_password",
  "role_ids": ["uuid"],
  "status": "active"
}
```

### 9.3 更新用户

```http
PATCH /api/v1/admin/users/{user_id}
```

权限：`user:update`

### 9.4 禁用用户

```http
POST /api/v1/admin/users/{user_id}/disable
```

权限：`user:disable`

### 9.5 启用用户

```http
POST /api/v1/admin/users/{user_id}/enable
```

### 9.6 重置密码

```http
POST /api/v1/admin/users/{user_id}/reset-password
```

## 10. 管理端角色与权限接口

### 10.1 角色列表

```http
GET /api/v1/admin/roles
```

### 10.2 创建角色

```http
POST /api/v1/admin/roles
```

### 10.3 更新角色

```http
PATCH /api/v1/admin/roles/{role_id}
```

### 10.4 删除角色

```http
DELETE /api/v1/admin/roles/{role_id}
```

内置角色不可删除。

### 10.5 权限列表

```http
GET /api/v1/admin/permissions
```

### 10.6 给角色配置权限

```http
PUT /api/v1/admin/roles/{role_id}/permissions
```

请求：

```json
{
  "permission_ids": ["uuid"]
}
```

## 11. 管理端模型接口

### 11.1 模型列表

```http
GET /api/v1/admin/models?page=1&page_size=20&keyword=&enabled=
```

### 11.2 新增模型

```http
POST /api/v1/admin/models
```

请求：

```json
{
  "name": "Fast Chat",
  "provider": "openai_compatible",
  "model_key": "gpt-4.1-mini",
  "base_url": "https://api.example.com/v1",
  "api_key_ref": "OPENAI_API_KEY",
  "context_length": 128000,
  "max_output_tokens": 4096,
  "default_temperature": 0.7,
  "support_streaming": true,
  "enabled": true,
  "allowed_role_ids": ["uuid"]
}
```

### 11.3 更新模型

```http
PATCH /api/v1/admin/models/{model_id}
```

### 11.4 禁用模型

```http
POST /api/v1/admin/models/{model_id}/disable
```

### 11.5 测试模型

```http
POST /api/v1/admin/models/{model_id}/test
```

请求：

```json
{
  "prompt": "请回复 pong"
}
```

## 12. 管理端统计与日志接口

### 12.1 后台首页统计

```http
GET /api/v1/admin/dashboard
```

返回：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "total_users": 100,
    "active_users_today": 20,
    "messages_today": 300,
    "model_calls_today": 280,
    "avg_latency_ms": 1800,
    "failure_rate": 0.02
  }
}
```

### 12.2 操作日志

```http
GET /api/v1/admin/logs/operations?page=1&page_size=20&action=&user_id=&result=
```

### 12.3 登录日志

```http
GET /api/v1/admin/logs/logins?page=1&page_size=20&user_id=&result=
```

### 12.4 模型调用日志

```http
GET /api/v1/admin/logs/model-calls?page=1&page_size=20&model_id=&user_id=&status=
```

## 13. 系统设置接口

### 13.1 获取系统设置

```http
GET /api/v1/admin/system-settings
```

权限：`system:read`

### 13.2 更新系统设置

```http
PUT /api/v1/admin/system-settings
```

权限：`system:update`

请求：

```json
{
  "product_name": "ChatAI",
  "registration_enabled": false,
  "guest_enabled": false,
  "default_model_id": "uuid",
  "default_assistant_id": "uuid",
  "allow_share": true,
  "allow_export": true,
  "daily_message_limit": 200
}
```

## 14. 前后端对接注意事项

- 流式接口不要使用普通 JSON 响应。
- 前端需要支持请求取消，取消后调用停止生成接口。
- 所有管理端按钮需要同时做前端权限隐藏和后端权限校验。
- 普通用户查询会话时后端必须加 `user_id = current_user.id` 条件。
- 管理员默认不能通过管理接口读取用户会话正文。
- 模型 API Key 不返回前端。
- 所有删除第一版采用软删除。

