#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_PID=""
FRONTEND_PID=""

mkdir -p "$LOG_DIR"

info() {
  printf '[ChatAI] %s\n' "$1"
}

fail() {
  printf '[ChatAI] ERROR: %s\n' "$1" >&2
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
  local retries=60

  for _ in $(seq 1 "$retries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      info "$name is ready: $url"
      return 0
    fi
    sleep 1
  done

  fail "$name did not become ready. Check logs in $LOG_DIR"
}

cleanup() {
  info "Stopping services started by this script..."
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

[[ -d "$BACKEND_DIR" ]] || fail "backend directory not found."
[[ -d "$FRONTEND_DIR" ]] || fail "frontend directory not found."

info "Preparing backend dependencies..."
if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  (cd "$BACKEND_DIR" && uv sync)
else
  info "Backend virtual environment already exists."
fi

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
    exec uv run uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
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

ChatAI is running.

Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT/
Backend:  http://$BACKEND_HOST:$BACKEND_PORT
API Docs: http://$BACKEND_HOST:$BACKEND_PORT/docs

Default accounts:
  superadmin@chatai.local / ChatAI@123456
  admin@chatai.local      / Admin@123456
  user@chatai.local       / User@123456

Logs:
  $LOG_DIR/backend.log
  $LOG_DIR/frontend.log

Press Ctrl+C to stop services started by this script.

EOF

if [[ -n "$BACKEND_PID" || -n "$FRONTEND_PID" ]]; then
  wait
else
  trap - INT TERM EXIT
fi

