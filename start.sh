#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="${FRONTEND_PORT:-5273}"
POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-55433}"
KEYCLOAK_HOST_PORT="${KEYCLOAK_HOST_PORT:-8080}"

BACKEND_PID=""
FRONTEND_PID=""
CLEANED_UP=0

mkdir -p "$LOG_DIR"

info() {
  printf '[TradeDigital] %s\n' "$1"
}

fail() {
  printf '[TradeDigital] ERROR: %s\n' "$1" >&2
  exit 1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

port_in_use() {
  local port="$1"
  if has_command lsof; then
    lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  else
    curl -fsS "http://127.0.0.1:$port" >/dev/null 2>&1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local retries=90

  for _ in $(seq 1 "$retries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      info "$name is ready: $url"
      return 0
    fi
    sleep 1
  done

  fail "$name did not become ready. Check logs in $LOG_DIR"
}

wait_for_postgres() {
  local retries=90
  for _ in $(seq 1 "$retries"); do
    if (cd "$INFRA_DIR" && docker compose exec -T postgres pg_isready -U tradedigital -d tradedigital) >/dev/null 2>&1; then
      info "PostgreSQL is ready."
      return 0
    fi
    sleep 1
  done
  fail "PostgreSQL did not become ready."
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp_file

  tmp_file="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { updated = 0 }
    $0 ~ "^" key "=" {
      print key "=" value
      updated = 1
      next
    }
    { print }
    END {
      if (!updated) {
        print key "=" value
      }
    }
  ' "$file" > "$tmp_file"
  mv "$tmp_file" "$file"
}

ensure_backend_env() {
  local env_file="$BACKEND_DIR/.env"

  if [[ ! -f "$env_file" ]]; then
    info "Creating backend/.env from .env.example"
    cp "$BACKEND_DIR/.env.example" "$env_file"
  fi

  set_env_value "$env_file" "APP_NAME" "TradeDigital"
  set_env_value "$env_file" "APP_ENV" "development"
  set_env_value "$env_file" "DEBUG" "true"
  set_env_value "$env_file" "FRONTEND_URL" "http://$FRONTEND_HOST:$FRONTEND_PORT"
  set_env_value "$env_file" "BACKEND_URL" "http://$BACKEND_HOST:$BACKEND_PORT"
  set_env_value "$env_file" "DATABASE_URL" "postgresql+asyncpg://tradedigital:tradedigital@127.0.0.1:$POSTGRES_HOST_PORT/tradedigital"
  set_env_value "$env_file" "SESSION_COOKIE_NAME" "td_session"
  set_env_value "$env_file" "SESSION_SECRET" "change-this-in-development"
  set_env_value "$env_file" "SESSION_EXPIRE_HOURS" "24"
  set_env_value "$env_file" "OIDC_PROVIDER" "keycloak"
  set_env_value "$env_file" "OIDC_ISSUER_URL" "http://127.0.0.1:$KEYCLOAK_HOST_PORT/realms/tradedigital"
  set_env_value "$env_file" "OIDC_CLIENT_ID" "tradedigital-web"
  set_env_value "$env_file" "OIDC_CLIENT_SECRET" "change-this-client-secret"
  set_env_value "$env_file" "OIDC_REDIRECT_URI" "http://$BACKEND_HOST:$BACKEND_PORT/api/v1/auth/sso/callback"
  set_env_value "$env_file" "DEFAULT_ENTERPRISE_CODE" "default"
  set_env_value "$env_file" "DEFAULT_LOGIN_REDIRECT" "/app"
  set_env_value "$env_file" "DEFAULT_MODEL_DISPLAY_NAME" "Gemini 3.5 Flash"
  set_env_value "$env_file" "DEFAULT_MODEL_PROVIDER_CODE" "openai_compatible"
  set_env_value "$env_file" "DEFAULT_MODEL_KEY" "gemini-3.5-flash"
  set_env_value "$env_file" "DEFAULT_MODEL_BASE_URL" "https://aicenter.thyseed.com/v1"
  set_env_value "$env_file" "DEFAULT_MODEL_API_KEY_REF" "AICENTER_API_KEY"
  set_env_value "$env_file" "DEFAULT_MODEL_SUPPORT_STREAMING" "false"
  if ! grep -q '^AICENTER_API_KEY=' "$env_file"; then
    printf 'AICENTER_API_KEY=\n' >> "$env_file"
  fi
}

cleanup() {
  if [[ "$CLEANED_UP" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  info "Stopping app services started by this script..."
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup INT TERM EXIT

has_command uv || fail "uv is required. Install it first: https://docs.astral.sh/uv/"
has_command npm || fail "npm is required. Install Node.js first."
has_command curl || fail "curl is required."
has_command docker || fail "Docker is required for local PostgreSQL and Keycloak."

[[ -d "$INFRA_DIR" ]] || fail "infra directory not found."
[[ -d "$BACKEND_DIR" ]] || fail "backend directory not found."
[[ -d "$FRONTEND_DIR" ]] || fail "frontend directory not found."

info "Starting local infrastructure..."
info "Using PostgreSQL host port $POSTGRES_HOST_PORT and Keycloak host port $KEYCLOAK_HOST_PORT."
(cd "$INFRA_DIR" && POSTGRES_HOST_PORT="$POSTGRES_HOST_PORT" KEYCLOAK_HOST_PORT="$KEYCLOAK_HOST_PORT" docker compose up -d)
wait_for_postgres
wait_for_url "http://127.0.0.1:$KEYCLOAK_HOST_PORT/realms/tradedigital/.well-known/openid-configuration" "Keycloak"

ensure_backend_env

info "Preparing backend dependencies..."
(cd "$BACKEND_DIR" && uv sync)

info "Applying database migrations..."
(cd "$BACKEND_DIR" && uv run alembic upgrade head)

info "Seeding database..."
(cd "$BACKEND_DIR" && uv run python -m tradedigital.scripts.seed)

info "Preparing frontend dependencies..."
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  (cd "$FRONTEND_DIR" && npm install)
else
  info "Frontend node_modules already exists."
fi

if port_in_use "$BACKEND_PORT"; then
  info "Backend port $BACKEND_PORT is already in use. Reusing existing service."
else
  info "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
  (
    cd "$BACKEND_DIR"
    exec uv run uvicorn tradedigital.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) >>"$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID="$!"
fi

if port_in_use "$FRONTEND_PORT"; then
  info "Frontend port $FRONTEND_PORT is already in use. Reusing existing service."
else
  info "Starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
  (
    cd "$FRONTEND_DIR"
    exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) >>"$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID="$!"
fi

wait_for_url "http://$BACKEND_HOST:$BACKEND_PORT/health" "Backend"
wait_for_url "http://$FRONTEND_HOST:$FRONTEND_PORT/" "Frontend"

cat <<EOF

TradeDigital is running.

Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT/
Backend:  http://$BACKEND_HOST:$BACKEND_PORT
API Docs: http://$BACKEND_HOST:$BACKEND_PORT/docs
Keycloak: http://127.0.0.1:$KEYCLOAK_HOST_PORT
Postgres: 127.0.0.1:$POSTGRES_HOST_PORT

Development SSO accounts:
  admin@tradedigital.local    / Admin@123456
  employee@tradedigital.local / Employee@123456

Logs:
  $LOG_DIR/backend.log
  $LOG_DIR/frontend.log

Press Ctrl+C to stop app services started by this script.
Docker infrastructure remains running; stop it with: cd infra && docker compose down

EOF

if [[ -n "$BACKEND_PID" || -n "$FRONTEND_PID" ]]; then
  wait
else
  trap - INT TERM EXIT
fi
