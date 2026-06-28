# TradeDigital

TradeDigital（电商数字化）是一个企业数字化平台。当前版本包含平台底座、`llm` 模型对话模块、KnowledgeBase 知识库模块骨架。

## 技术栈

- 前端：React + TypeScript + Vite
- 后端：Python + FastAPI + SQLAlchemy Async
- 数据库：PostgreSQL
- 认证：Keycloak OIDC SSO + 服务端 Session
- 模型：OpenAI Compatible API

## 本地启动

```bash
./start.sh
```

启动后访问：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000
API 文档：http://127.0.0.1:8000/docs
Keycloak：http://127.0.0.1:8080
PostgreSQL：127.0.0.1:55433
```

本地 PostgreSQL 默认映射到宿主机 `55433`，避免和已有本机 PostgreSQL 的 `5432` 冲突。如需自定义：`POSTGRES_HOST_PORT=55434 ./start.sh`。

开发账号：

|角色|邮箱|密码|
|---|---|---|
|企业管理员|admin@tradedigital.local|Admin@123456|
|员工|employee@tradedigital.local|Employee@123456|

## 手动启动

```bash
cd infra
docker compose up -d

cd ../backend
cp .env.example .env
uv run alembic upgrade head
uv run python -m tradedigital.scripts.seed
uv run uvicorn tradedigital.main:app --reload --host 127.0.0.1 --port 8000

cd ../frontend
npm install
npm run dev
```

## 验证

```bash
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
npm run lint
npm run build
```

详细架构与开发文档见 [DOC/00-文档索引.md](./DOC/00-文档索引.md)。
