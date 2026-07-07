from __future__ import annotations

from scraper.platforms.altenar import AltenarScraper
from scraper.platforms.betano import BetanoScraper
from scraper.platforms.bet365 import Bet365Scraper
from scraper.platforms.efbet import EfbetScraper
from scraper.platforms.egt_digital import EgtScraper
from scraper.platforms.sportinno import SportInnoScraper
from scraper.platforms.base import PlatformScraper

_SCRAPERS: dict[str, PlatformScraper] = {
    "winbet": EgtScraper("winbet", "winbet-api.egt-digital.com"),
    "inbet": EgtScraper("inbet", "inbet-api.egt-digital.com"),
    "palmsbet": AltenarScraper("palmsbet", "palmsbet.com"),
    "8888": SportInnoScraper(),
    "efbet": EfbetScraper(),
    "betano": BetanoScraper(),
    "bet365": Bet365Scraper(),
}


def get_scraper(bookmaker_slug: str) -> PlatformScraper:
    scraper = _SCRAPERS.get(bookmaker_slug)
    if not scraper:
        raise KeyError(f"No scraper for bookmaker: {bookmaker_slug}")
    return scraper
