"""aiogram 3 routers: /start /add /list /remove /check."""
from __future__ import annotations

import html
import logging
from urllib.parse import urlparse

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .config import Config
from .database import add_subscription, list_subscriptions, remove_subscription
from .monitor import check_subscription

log = logging.getLogger(__name__)
router = Router()


def _is_olx_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "olx.pl" in host


HELP = (
    "👋 <b>OLX Monitor</b>\n\n"
    "I'll check your OLX search links every 5 minutes and send new ads.\n\n"
    "<b>Commands:</b>\n"
    "/add &lt;OLX search URL&gt; [label] — add search\n"
    "/list — your searches\n"
    "/remove &lt;id&gt; — delete search\n"
    "/check — check now\n"
    "/help — this help\n\n"
    "<b>Example:</b>\n"
    "<code>/add https://www.olx.pl/motoryzacja/samochody/warszawa/ bmw</code>"
)


@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject, config: Config) -> None:
    if not command.args:
        await message.answer("Usage: <code>/add &lt;OLX search URL&gt; [label]</code>")
        return
    parts = command.args.split(maxsplit=1)
    url = parts[0].strip()
    label = parts[1].strip()[:60] if len(parts) > 1 else ""
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("❌ URL must start with http(s)://")
        return
    if not _is_olx_url(url):
        await message.answer("❌ That doesn't look like an olx.pl link.")
        return
    assert message.chat is not None
    sub_id = await add_subscription(config.db_path, message.chat.id, url, label)
    await message.answer(
        f"✅ Added <b>#{sub_id}</b> {html.escape(label or url)}\n"
        f"First check will save current ads silently, then you'll get only new ones.\n"
        f"Use /check to run the first check now."
    )


@router.message(Command("list"))
async def cmd_list(message: Message, config: Config) -> None:
    assert message.chat is not None
    subs = await list_subscriptions(config.db_path, message.chat.id)
    if not subs:
        await message.answer("📭 No searches yet. Add one with /add")
        return
    lines = ["📋 <b>Your searches:</b>"]
    for sub_id, url, label in subs:
        title = html.escape(label) if label else html.escape(url[:80])
        lines.append(f"\n<b>#{sub_id}</b> {title}\n{html.escape(url[:200])}")
    lines.append("\n/remove &lt;id&gt; to delete • /check to check now")
    await message.answer("\n".join(lines), disable_web_page_preview=True)


@router.message(Command("remove", "delete", "del"))
async def cmd_remove(message: Message, command: CommandObject, config: Config) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: <code>/remove &lt;id&gt;</code> (see /list)")
        return
    assert message.chat is not None
    ok = await remove_subscription(config.db_path, message.chat.id, int(command.args.strip()))
    await message.answer("🗑 Removed." if ok else "❌ No search with that id.")


@router.message(Command("check"))
async def cmd_check(message: Message, bot: Bot, config: Config) -> None:
    assert message.chat is not None
    subs = await list_subscriptions(config.db_path, message.chat.id)
    if not subs:
        await message.answer("📭 Nothing to check — add a search with /add first.")
        return
    status = await message.answer(f"🔎 Checking {len(subs)} search(es)…")
    total = 0
    for sub_id, url, label in subs:
        total += await check_subscription(bot, config, sub_id, message.chat.id, url, label)
    try:
        await status.edit_text(f"✅ Done. {total} new ad(s).")
    except Exception:
        await message.answer(f"✅ Done. {total} new ad(s).")
