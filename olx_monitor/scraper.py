"""OLX search-page scraper based on Playwright (Chromium, headless).

OLX markup changes often, so we use several selector fallbacks:
  - cards: a[data-cy="l-card"] / div[data-cy="l-card"] / a[href*="/d/oferta/"]
  - title: [data-cy="ad-card-title"] / h6 / h4
  - price: p[data-testid="ad-price"] / [data-testid="ad-price"]
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

CARD_SELECTORS = [
    'div[data-cy="l-card"]',
    'div[data-testid="l-card"]',
]

TITLE_SELECTORS = [
    '[data-testid="ad-card-title"] h4',
    '[data-testid="ad-card-title"]',
    '[data-cy="ad-card-title"]',
    'h4',
    'h6',
]

PRICE_SELECTORS = [
    'p[data-testid="ad-price"]',
    '[data-testid="ad-price"]',
    '[data-cy="ad-card-price"]',
]

LOCATION_SELECTORS = [
    'p[data-testid="location-date"]',
    '[data-testid="location-date"]',
]


@dataclass
class Listing:
    id: str
    title: str
    price: str
    url: str
    location: str = ""


def extract_listing_id(url: str) -> str:
    """Stable ID: OLX offer pages end with ...-ID<digits>.html -> take trailing digits."""
    m = re.search(r"ID([A-Za-z0-9]+)\.html", url)
    if m:
        return m.group(1)
    m = re.search(r"(\d+)(?:\.html)?/?$", url.rstrip("/"))
    if m:
        return m.group(1)
    return url  # fallback: full URL as ID


_playwright_lock = asyncio.Lock()


async def scrape_search(url: str, timeout_ms: int = 45_000, headless: bool = True) -> list[Listing]:
    """Open OLX search URL and return found listings (deduplicated by id)."""
    async with _playwright_lock:  # one browser at a time -> less RAM, fewer bans
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                context = await browser.new_context(
                    locale="pl-PL",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                # Let lazy cards render; tolerate cookie wall.
                try:
                    await page.wait_for_selector(
                        ", ".join(CARD_SELECTORS), timeout=15_000
                    )
                except Exception:
                    log.warning("No card selector matched for %s", url)
                await page.wait_for_timeout(1500)

                raw: list[dict] = await page.evaluate(
                    """(selectors) => {
                        const [cardSels, titleSels, priceSels, locSels] = selectors;
                        const cards = new Map();
                        for (const cs of cardSels) {
                            document.querySelectorAll(cs).forEach(card => {
                                // card is a div: find the offer link inside it
                                const link = card.querySelector('a[href*="/d/oferta/"]');
                                const href = link ? (link.getAttribute('href') || '') : '';
                                if (!href || cards.has(href)) return;
                                const pick = (sels) => {
                                    for (const s of sels) {
                                        const el = card.querySelector(s);
                                        if (el && el.innerText.trim()) return el.innerText.trim();
                                    }
                                    return '';
                                };
                                let title = pick(titleSels);
                                if (!title && link) {
                                    title = (link.getAttribute('aria-label') || link.getAttribute('title') || '').trim();
                                }
                                cards.set(href, {
                                    href,
                                    title: (title || '').slice(0, 200),
                                    price: pick(priceSels),
                                    location: pick(locSels),
                                });
                            });
                        }
                        return [...cards.values()];
                    }""",
                    [CARD_SELECTORS, TITLE_SELECTORS, PRICE_SELECTORS, LOCATION_SELECTORS],
                )
                await context.close()
            finally:
                await browser.close()

    listings: list[Listing] = []
    seen: set[str] = set()
    for item in raw:
        href: str = item.get("href", "")
        if not href or "/d/oferta/" not in href:
            continue
        full_url = urljoin("https://www.olx.pl/", href)
        lid = extract_listing_id(full_url)
        if lid in seen:
            continue
        seen.add(lid)
        listings.append(
            Listing(
                id=lid,
                title=item.get("title", "") or "(no title)",
                price=item.get("price", ""),
                url=full_url.split("?")[0],
                location=item.get("location", ""),
            )
        )
    log.info("Scraped %d listings from %s", len(listings), url)
    return listings
