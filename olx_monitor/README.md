# 🔔 OLX Monitor Bot

> Telegram bot that watches your OLX search links and instantly notifies you about **new listings**. Never miss a good deal again.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2ea6ff)](https://docs.aiogram.dev)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-green)](https://playwright.dev)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-lightgrey)](https://sqlite.org)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

## 🎬 Demo

https://github.com/user-attachments/assets/demo-placeholder

<video src="olx_monitor/assets/demo.mp4" width="360" controls></video>

![Demo preview](olx_monitor/assets/demo_preview.png)

## ✨ What it does

You send the bot an OLX search URL (e.g. cars in Warsaw, iPhone 13 in Kraków) — it checks that page **every 5 minutes** in the background and sends you only the ads it hasn't seen before:

```
🔔 bmw e46
🏷 BMW 320D f30 automat, mały przebieg
💰 39 900 zł
📍 Warszawa, Białołęka
🔗 https://www.olx.pl/d/oferta/...
```

- ➕ Unlimited search subscriptions per chat
- 🧠 Smart dedup via SQLite (`seen_listings`) — no repeats, no spam
- 🤫 First check is a silent baseline (saves current ads, notifies nothing)
- ⚡ Manual `/check` + automatic background loop (`asyncio.create_task`)
- 🛡 Resilient Playwright scraper with selector fallbacks for changing OLX markup

## 🚀 Quickstart

```bash
# 1. Install deps (one time)
pip install -r olx_monitor/requirements.txt
playwright install chromium

# 2. Set token from @BotFather
echo "BOT_TOKEN=123456:ABC..." > .env

# 3. Run
python -m olx_monitor.bot
```

Open your bot in Telegram and try:

```
/add https://www.olx.pl/motoryzacja/samochody/warszawa/?search%5Border%5D=created_at:desc bmw
/check
```

## 💬 Commands

| Command | Description |
|---|---|
| `/start`, `/help` | Show help |
| `/add <OLX search URL> [label]` | Subscribe, e.g. `/add https://www.olx.pl/.../ iphone` |
| `/list` | List your subscriptions |
| `/remove <id>` | Unsubscribe (`/list` to see ids) |
| `/check` | Check all your searches right now |

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — (required) | Token from [@BotFather](https://t.me/BotFather) |
| `OLX_CHECK_INTERVAL_SEC` | `300` | How often to re-check (min 60) |
| `OLX_DB_PATH` | `olx_monitor/olx_seen.db` | SQLite file |
| `OLX_HEADLESS` | `1` | `0` to watch the browser while debugging |

## 🏗 How it works

```
Telegram (/add URL) → SQLite: subscriptions
                            ↓
monitor_loop (asyncio, every N sec) → scrape_search() [Playwright/Chromium]
                            ↓
                   diff vs seen_listings → send only fresh ads
```

| File | Role |
|---|---|
| `bot.py` | Entry point: polling + background `monitor_loop` task |
| `handlers.py` | aiogram 3 routers: `/add /list /remove /check` |
| `monitor.py` | Periodic checker, formats & sends new ads |
| `scraper.py` | Headless Chromium scrape: `l-card` → title / price / location / id |
| `database.py` | `aiosqlite`: `subscriptions` + `seen_listings` |
| `config.py` | Env-based config |

## 🛠 Tech stack

**Python 3.10+ · aiogram 3 · Playwright (Chromium) · aiosqlite · asyncio · python-dotenv**

## 📌 Roadmap

- [ ] Price-drop alerts + filters (max price, keywords)
- [ ] Photo thumbnails in notifications
- [ ] Docker + 24/7 hosting guide
- [ ] Multi-marketplace support (OTOMOTO, Allegro)

---
Built for people who hunt OLX daily and hate pressing F5. 🎯

