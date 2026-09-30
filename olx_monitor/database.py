"""SQLite storage: subscriptions (search URLs) + seen listing IDs."""
from __future__ import annotations

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, url)
);
CREATE TABLE IF NOT EXISTS seen_listings (
    subscription_id INTEGER NOT NULL,
    listing_id TEXT NOT NULL,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subscription_id, listing_id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
);
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def add_subscription(db_path: str, chat_id: int, url: str, label: str = "") -> int:
    """Insert subscription, return its id (existing one if duplicate)."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.execute(
            "INSERT OR IGNORE INTO subscriptions (chat_id, url, label) VALUES (?, ?, ?)",
            (chat_id, url, label),
        )
        await db.commit()
        async with db.execute(
            "SELECT id FROM subscriptions WHERE chat_id = ? AND url = ?",
            (chat_id, url),
        ) as cur:
            row = await cur.fetchone()
            assert row is not None
            return int(row[0])


async def remove_subscription(db_path: str, chat_id: int, sub_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        cur = await db.execute(
            "DELETE FROM subscriptions WHERE id = ? AND chat_id = ?",
            (sub_id, chat_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_subscriptions(db_path: str, chat_id: int) -> list[tuple[int, str, str]]:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        async with db.execute(
            "SELECT id, url, label FROM subscriptions WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ) as cur:
            return [(r[0], r[1], r[2]) for r in await cur.fetchall()]


async def list_all_subscriptions(db_path: str) -> list[tuple[int, int, str, str]]:
    """All subscriptions across chats: (id, chat_id, url, label)."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        async with db.execute(
            "SELECT id, chat_id, url, label FROM subscriptions ORDER BY id"
        ) as cur:
            return [(r[0], r[1], r[2], r[3]) for r in await cur.fetchall()]


async def get_seen_ids(db_path: str, subscription_id: int) -> set[str]:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        async with db.execute(
            "SELECT listing_id FROM seen_listings WHERE subscription_id = ?",
            (subscription_id,),
        ) as cur:
            return {r[0] for r in await cur.fetchall()}


async def mark_seen(db_path: str, subscription_id: int, listing_ids: list[str]) -> None:
    if not listing_ids:
        return
    async with aiosqlite.connect(db_path) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO seen_listings (subscription_id, listing_id) VALUES (?, ?)",
            [(subscription_id, lid) for lid in listing_ids],
        )
        await db.commit()
