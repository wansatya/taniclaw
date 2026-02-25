# TaniClaw v1 — Lightweight Autonomous Agriculture Skill

> 🌱 **Food Security Agent for Everyone** — Rules-first, LLM-optional, multi-platform.

TaniClaw is a lightweight autonomous agriculture assistant that monitors plant growth stages, weather, and provides daily actionable instructions — in Bahasa Indonesia. Built for smallholder farmers and hobbyist gardeners.

## ✨ Features

- 🌿 **Track plant lifecycle** — Seed → Germination → Vegetative → Flowering → Harvest
- 🌤️ **Real-time weather** — Open-Meteo API (free, no API key needed)
- 📋 **Daily instructions** — Bilingual (ID/EN) actionable care tasks  
- 💧 **Smart watering** — Skip when it rains, increase when hot
- 🌿 **Fertilizer scheduling** — Stage-appropriate NPK recommendations
- 🐛 **Disease detection** — Knowledge-based symptom matching
- 💬 **Chat interface** — Ask questions in Bahasa Indonesia
- 🔔 **Notifications** — Telegram and WhatsApp support
- 🤖 **Optional LLM** — Groq SDK (llama-3.1-8b-instant) for complex queries

## 🚀 Quick Start

### ⚡ One-Command Install

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/wansatya/taniclaw/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/wansatya/taniclaw/main/install.ps1 | iex
```

That's it. Opens at http://localhost:8000 🌱

---

### Manual Installation (uv)

We recommend using [uv](https://github.com/astral-sh/uv) for the fastest experience.

```bash
# 1. Clone the repo
git clone https://github.com/wansatya/taniclaw && cd taniclaw

# 2. Run immediately (auto-installs deps)
# On Windows use: $env:UV_NO_WORKSPACE=1; uv run taniclaw start
UV_NO_WORKSPACE=1 uv run taniclaw start
```

Open: http://localhost:8000

## 🌱 Supported Plants

| Plant | Type | Duration |
|-------|------|----------|
| 🌶️ Cabai | chili | ~120 days |
| 🍅 Tomat | tomato | ~90 days |
| 🥬 Bayam | spinach | ~35 days |
| 🥗 Selada | lettuce | ~45 days |
| 💧 Hidroponik | hydroponic | varies |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/plants` | Add a new plant |
| GET | `/api/plants` | List all plants |
| GET | `/api/plants/{id}/instructions` | Daily instructions |
| POST | `/api/chat` | Chat with TaniClaw |
| GET | `/api/farm/summary` | Farm overview |
| GET | `/api/weather/{plant_id}` | Weather data |

Full docs: http://localhost:8000/docs

## ⚙️ Configuration

TaniClaw stores its data in `~/.taniclaw` (Linux/macOS) or `$HOME\.taniclaw` (Windows).

Copy `.env.example` to `.env`:

```env
TANICLAW_DATABASE_URL=sqlite:///~/.taniclaw/taniclaw.db

# Optional: Enable LLM (Groq)
TANICLAW_LLM_ENABLED=true
TANICLAW_GROQ_API_KEY=your_key

# Optional: Telegram notifications
TANICLAW_NOTIFICATION_ENABLED=true
TANICLAW_TELEGRAM_BOT_TOKEN=your_token
TANICLAW_TELEGRAM_CHAT_ID=your_chat_id
```

## 🏗️ Architecture

```
Rules Engine (YAML) → Security Guard → Tool Executor → Memory (DB)
         ↑                                                    ↑
Weather API ──────────── Agent Loop ──────────────────────────┘
         ↓                    ↓
   LLM Gateway           Scheduler
   (Groq SDK, optional)  (every 1 hour)
```

- **Rules-first**: All decisions from YAML rules. LLM is never used by default.
- **Security Guard**: Validates every action before execution.
- **≤50MB RAM**: Runs well on Raspberry Pi 3B+ and low-end laptops.
- **Zero tokens**: No LLM cost unless you enable it.

## 🧪 Testing

```bash
uv run pytest
```

## 📜 License

MIT — Built for food security. Free forever.
