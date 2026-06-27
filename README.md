# ChatAI

ChatAI 是一个 React + TypeScript 前端、Python + FastAPI 后端的 ChatGPT 风格 Web 对话项目。

第一版已实现开发骨架和主流程：

- ChatGPT 风格用户端布局：侧边栏、会话列表、模型选择、底部输入框、消息流。
- 用户登录和 JWT 认证。
- 会话列表、会话详情、会话删除、归档、收藏。
- SSE 流式聊天接口。
- 默认 mock 模型，未配置真实模型 API 时也能本地演示。
- 管理后台：用户、角色、模型、统计、操作日志基础页面。
- RBAC 权限：超级管理员、管理员、普通用户。

## 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端地址：

```text
http://127.0.0.1:8000
```

OpenAPI：

```text
http://127.0.0.1:8000/docs
```

## 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

前端地址：

```text
http://127.0.0.1:5173
```

## 默认账号

|角色|邮箱|密码|
|---|---|---|
|超级管理员|`superadmin@chatai.local`|`ChatAI@123456`|
|管理员|`admin@chatai.local`|`Admin@123456`|
|普通用户|`user@chatai.local`|`User@123456`|

## 模型 API 配置

默认模型为 `mock`，无需 API Key。

后续接真实 OpenAI-compatible API 时，可在后台新增模型，配置：

- Provider：`openai_compatible`
- Base URL：例如 `https://api.example.com/v1`
- API Key Ref：例如 `OPENAI_API_KEY`

然后在后端环境变量中设置：

```bash
export OPENAI_API_KEY="your-key"
export CHATAI_MOCK_MODEL_ENABLED=false
```

## 主要目录

```text
DOC/                 产品与研发文档
frontend/            React + TypeScript 前端
backend/             FastAPI 后端
backend/app/api/     REST 与 SSE 接口
backend/app/db/      SQLAlchemy 数据模型
backend/app/seed/    初始化角色、权限、账号、模型
```

