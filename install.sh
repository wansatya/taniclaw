#!/usr/bin/env bash
# ============================================================
#  TaniClaw v1 — One-Command Installer
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/wansatya/taniclaw/main/install.sh | bash
#
#  Options (env vars):
#    INSTALL_MODE=uv       (default) — uv install + local sqlite
#    INSTALL_DIR=<path>    — where to clone (default: ~/taniclaw)
#    GROQ_API_KEY=<key>    — optional, enables LLM
#    TELEGRAM_BOT_TOKEN=<token>  — optional notifications
#    TELEGRAM_CHAT_ID=<id>       — optional notifications
# ============================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Config ────────────────────────────────────────────────────────────────────
export TANICLAW_VERSION="1.0.0"
export UV_NO_WORKSPACE=1
INSTALL_DIR="${INSTALL_DIR:-$HOME/.taniclaw}"
REPO_URL="https://github.com/wansatya/taniclaw"
INSTALL_MODE="uv"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${GREEN}[TaniClaw]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}     $*"; }
error()   { echo -e "${RED}[ERROR]${NC}    $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}${BLUE}==> $*${NC}"; }
success() { echo -e "${GREEN}${BOLD}✓ $*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "
${GREEN}${BOLD}
  ████████╗ █████╗ ███╗   ██╗██╗ ██████╗██╗      █████╗ ██╗    ██╗
     ██╔══╝██╔══██╗████╗  ██║██║██╔════╝██║     ██╔══██╗██║    ██║
     ██║   ███████║██╔██╗ ██║██║██║     ██║     ███████║██║ █╗ ██║
     ██║   ██╔══██║██║╚██╗██║██║██║     ██║     ██╔══██║██║███╗██║
     ██║   ██║  ██║██║ ╚████║██║╚██████╗███████╗██║  ██║╚███╔███╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝${NC}
${BLUE}  v${TANICLAW_VERSION:-1.0.0} — Lightweight Autonomous Agriculture Skill${NC}
  🌱 Food Security Agent for Everyone
"

# ── OS detection ──────────────────────────────────────────────────────────────
detect_os() {
  OS="unknown"
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS="${ID:-unknown}"
  elif [[ "$(uname)" == "Darwin" ]]; then
    OS="macos"
  fi
  ARCH=$(uname -m)
  info "Detected OS: ${OS}, arch: ${ARCH}"
}

# ── Check prerequisites ───────────────────────────────────────────────────────
check_cmd() {
  command -v "$1" &>/dev/null
}

require_cmd() {
  if ! check_cmd "$1"; then
    error "$1 is required but not installed. Install it and re-run."
  fi
}

install_uv() {
  # Install uv if not already present
  if check_cmd uv; then
    success "uv found: $(uv --version)"
    return
  fi
  info "Installing uv (fast Python package manager)..."
  curl -fsSL https://astral.sh/uv/install.sh | sh
  # Add to PATH for this session
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if ! check_cmd uv; then
    error "uv installation failed. Install manually: https://docs.astral.sh/uv/"
  fi
  success "uv installed: $(uv --version)"
}

install_dependencies() {
  header "Checking dependencies..."
  install_uv
  # uv manages Python itself — no system python3 needed
  info "uv will manage Python 3.13 automatically"
}

# ── Clone / download repo ─────────────────────────────────────────────────────
get_repo() {
  header "Setting up TaniClaw in ${INSTALL_DIR}..."

  # Fresh start: remove old directory if it exists
  if [[ -d "$INSTALL_DIR" ]]; then
    warn "Removing existing directory at ${INSTALL_DIR} for a fresh installation..."
    rm -rf "$INSTALL_DIR"
  fi

  if check_cmd git; then
    info "Cloning from ${REPO_URL}..."
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
  else
    # Fallback: download tarball
    info "git not found — downloading archive..."
    require_cmd curl
    mkdir -p "$INSTALL_DIR"
    curl -fsSL "${REPO_URL}/archive/refs/heads/main.tar.gz" \
      | tar -xz -C "$INSTALL_DIR" --strip-components=1
  fi

  success "Source code ready at ${INSTALL_DIR}"
}

# ── Generate .env ─────────────────────────────────────────────────────────────
generate_env() {
  header "Configuring environment..."
  ENV_FILE="${INSTALL_DIR}/.env"

  if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — skipping generation (edit manually if needed)"
    return
  fi

  cat > "$ENV_FILE" <<EOF
# TaniClaw v1 — generated by install.sh on $(date)

TANICLAW_DATABASE_URL=sqlite:///${INSTALL_DIR}/taniclaw.db
TANICLAW_HOST=0.0.0.0
TANICLAW_PORT=8000
TANICLAW_LOG_LEVEL=INFO
TANICLAW_SCHEDULER_INTERVAL_MINUTES=60
TANICLAW_TIMEZONE=Asia/Jakarta
TANICLAW_WEATHER_API_BASE=https://api.open-meteo.com/v1

# LLM (Groq) — set GROQ_API_KEY to enable
TANICLAW_LLM_ENABLED=${GROQ_API_KEY:+true}${GROQ_API_KEY:-false}
TANICLAW_GROQ_API_KEY=${GROQ_API_KEY:-}
TANICLAW_LLM_MODEL=llama-3.1-8b-instant
TANICLAW_LLM_FALLBACK_MODEL=llama-3.3-70b-versatile

# Security
TANICLAW_MAX_WATERING_AMOUNT_ML=500
TANICLAW_MAX_DAILY_ACTIONS=50
TANICLAW_MAX_FERTILIZER_GRAMS=20

# Notifications
TANICLAW_NOTIFICATION_ENABLED=${TELEGRAM_BOT_TOKEN:+true}${TELEGRAM_BOT_TOKEN:-false}
TANICLAW_TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TANICLAW_TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
EOF

  success ".env generated (using SQLite)"
  if [[ -n "${GROQ_API_KEY:-}" ]]; then
    info "✓ Groq LLM enabled (${GROQ_API_KEY:0:8}...)"
  fi
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    info "✓ Telegram notifications enabled"
  fi
}

# ── uv install ────────────────────────────────────────────────────────────────
install_uv_app() {
  header "Installing TaniClaw via uv..."
  cd "$INSTALL_DIR"

  VENV_DIR="${INSTALL_DIR}/.venv"

  # Create / recreate venv with uv (pins Python 3.13)
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment with uv (Python 3.13)..."
    uv venv "$VENV_DIR" --python 3.13
  else
    info "Using existing virtual environment at ${VENV_DIR}"
  fi

  # Install project — uv resolves & installs all deps in one shot, much faster than pip
  # UV_NO_WORKSPACE=1 prevents it from looking at parent directories for workspaces
  info "Installing TaniClaw and dependencies (uv)..."
  UV_NO_WORKSPACE=1 uv pip install --python "${VENV_DIR}/bin/python" -e "."

  success "TaniClaw installed via uv"

  # Expose the taniclaw binary from the venv
  TANICLAW_BIN="${VENV_DIR}/bin/taniclaw"

  # Create systemd service (optional, Linux only)
  if check_cmd systemctl && [[ "$(uname)" == "Linux" ]]; then
    install_systemd_service
  fi

  # Start directly
  info "Starting TaniClaw..."
  nohup "$TANICLAW_BIN" start &>"${INSTALL_DIR}/taniclaw.log" &
  PID=$!
  echo $PID > "${INSTALL_DIR}/taniclaw.pid"
  success "TaniClaw started (PID: ${PID})"
  info "Logs: ${INSTALL_DIR}/taniclaw.log"
}

# ── Systemd service (optional) ────────────────────────────────────────────────
install_systemd_service() {
  SERVICE_FILE="/etc/systemd/system/taniclaw.service"
  VENV="${INSTALL_DIR}/.venv"

  if [[ -w "/etc/systemd/system" ]] || [[ "$(id -u)" -eq 0 ]]; then
    info "Installing systemd service..."
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=TaniClaw — Autonomous Agriculture Agent
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${VENV}/bin/taniclaw start
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable taniclaw
    success "Systemd service installed (taniclaw.service)"
    info "To start on boot: sudo systemctl start taniclaw"
  else
    warn "Skipping systemd service (no write access). Re-run as root to install."
  fi
}

# ── Wait and verify ───────────────────────────────────────────────────────────
verify_installation() {
  header "Verifying installation..."
  PORT="${TANICLAW_PORT:-8000}"
  MAX_WAIT=60
  WAITED=0

  info "Waiting for TaniClaw to be ready on port ${PORT}..."
  while ! curl -sf "http://localhost:${PORT}/health" &>/dev/null; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [[ $WAITED -ge $MAX_WAIT ]]; then
      warn "TaniClaw did not respond within ${MAX_WAIT}s."
      warn "Check logs for errors."
      warn "Run: tail -f ${INSTALL_DIR}/taniclaw.log"
      return 1
    fi
    echo -n "."
  done
  echo ""
  success "TaniClaw is running!"
}

# ── Print final instructions ──────────────────────────────────────────────────
print_summary() {
  PORT="${TANICLAW_PORT:-8000}"
  echo -e "
${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗
║          🌱 TaniClaw v${TANICLAW_VERSION} — Ready!                  ║
╚══════════════════════════════════════════════════════╝${NC}

  ${BOLD}Dashboard:${NC}  http://localhost:${PORT}/
  ${BOLD}Chat AI:${NC}    http://localhost:${PORT}/chat
  ${BOLD}API Docs:${NC}   http://localhost:${PORT}/docs
  ${BOLD}Health:${NC}     http://localhost:${PORT}/health

  ${BOLD}Tambah tanaman pertama Anda di Dashboard!${NC}

${YELLOW}Useful commands:${NC}
  Stop:     kill \$(cat ${INSTALL_DIR}/taniclaw.pid)
  Logs:     tail -f ${INSTALL_DIR}/taniclaw.log
  Restart:  ${INSTALL_DIR}/.venv/bin/taniclaw start
  Update:   cd ${INSTALL_DIR} && git pull && UV_NO_WORKSPACE=1 uv pip install --python ${INSTALL_DIR}/.venv/bin/python -e .

"
  info "Questions? See: ${REPO_URL}"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  detect_os
  install_dependencies
  get_repo
  generate_env

  install_uv_app

  verify_installation || true
  print_summary
}

main "$@"
