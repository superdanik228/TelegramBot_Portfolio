"""Bot configuration loaded from environment (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load /Users/danielshumskyi/Desktop/Telegram_bots/.env (project root)
# and olx_monitor/.env if present.
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str
    check_interval_sec: int = 300
    scrape_timeout_ms: int = 45_000
    headless: bool = True


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token.startswith("twoj_token"):
        raise RuntimeError(
            "BOT_TOKEN is missing. Put your BotFather token into "
            f"{ROOT_DIR / '.env'} as BOT_TOKEN=..."
        )

    db_path = os.getenv("OLX_DB_PATH", "").strip() or str(
        Path(__file__).resolve().parent / "olx_seen.db"
    )
    interval = int(os.getenv("OLX_CHECK_INTERVAL_SEC", "300") or 300)
    headless_raw = os.getenv("OLX_HEADLESS", "1").strip().lower()
    headless = headless_raw not in ("0", "false", "no")

    return Config(
        bot_token=token,
        db_path=db_path,
        check_interval_sec=max(60, interval),
        headless=headless,
    )
