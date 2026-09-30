"""Background asyncio checker: every N seconds scrape all subscriptions."""
from __future__ import annotations

import asyncio
import html
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound

from .config import Config
from .database import get_seen_ids, list_all_subscriptions, mark_seen
from .scraper import Listing, scrape_search

log = logging.getLogger(__name__)

MAX_ALERTS_PER_CHECK = 10


def format_listing(l: Listing, label: str = "") -> str:
    lines = []
    if label:
        lines.append(f"🔔 <b>{html.escape(label)}</b>")
    lines.append(f"🏷 <b>{html.escape(l.title)}</b>")
    if l.price:
        lines.append(f"💰 {html.escape(l.price)}")
    if l.location:
        lines.append(f"📍 {html.escape(l.location)}")
    lines.append(f"🔗 {l.url}")
    return "\n".join(lines)


async def check_subscription(bot: Bot, config: Config, sub_id: int, chat_id: int, url: str, label: str) -> int:
    """Check one subscription. Returns number of new listings sent."""
    try:
        listings = await scrape_search(url, timeout_ms=config.scrape_timeout_ms, headless=config.headless)
    except Exception:
        log.exception("Scrape failed for sub=%d url=%s", sub_id, url)
        return 0

    seen = await get_seen_ids(config.db_path, sub_id)
    if not seen:
        # First run: silent baseline, don't spam user with all current ads.
        await mark_seen(config.db_path, sub_id, [l.id for l in listings])
        try:
            await bot.send_message(
                chat_id,
                f"✅ Monitoring started for <b>{html.escape(label or url)}</b>\n"
                f"Saved {len(listings)} current ads as seen — you'll get only <b>new</b> ones.",
            )
        except (TelegramForbiddenError, TelegramNotFound):
            log.warning("Cannot message chat %d (blocked/deleted)", chat_id)
        except Exception:
            log.exception("Failed to send baseline message to %d", chat_id)
        return 0

    fresh = [l for l in listings if l.id not in seen]
    if listings:
        await mark_seen(config.db_path, sub_id, [l.id for l in listings])

    for l in fresh[:MAX_ALERTS_PER_CHECK]:
        try:
            await bot.send_message(chat_id, format_listing(l, label))
            await asyncio.sleep(0.4)  # gentle anti-flood
        except (TelegramForbiddenError, TelegramNotFound):
            log.warning("Cannot message chat %d (blocked/deleted)", chat_id)
            break
        except Exception:
            log.exception("Failed to send listing to %d", chat_id)
    if len(fresh) > MAX_ALERTS_PER_CHECK:
        try:
            await bot.send_message(chat_id, f"…and {len(fresh) - MAX_ALERTS_PER_CHECK} more new ads. Open the search link to see all.")
        except Exception:
            pass
    return len(fresh)


async def check_all_once(bot: Bot, config: Config) -> int:
    subs = await list_all_subscriptions(config.db_path)
    total = 0
    for sub_id, chat_id, url, label in subs:
        total += await check_subscription(bot, config, sub_id, chat_id, url, label)
    return total


async def monitor_loop(bot: Bot, config: Config) -> None:
    log.info("Monitor loop started, interval=%ds", config.check_interval_sec)
    await asyncio.sleep(10)  # let polling start first
    while True:
        try:
            total = await check_all_once(bot, config)
            if total:
                log.info("Sent %d new listing(s)", total)
        except Exception:
            log.exception("Monitor iteration failed")
        await asyncio.sleep(config.check_interval_sec)
