"""
Autonomous Web Scraper & Data Extractor
Practice project using https://books.toscrape.com/ (a website intended for scraping practice).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://books.toscrape.com/"
DEFAULT_OUTPUT_DIR = Path("output")
CSV_FIELDS = ["title", "price", "price_numeric", "category", "url"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("book_scraper")


def build_session() -> requests.Session:
    """Create a reusable HTTP session with a small retry policy."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "EducationalBookScraper/1.0 (learning project)"
    })
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_soup(session: requests.Session, url: str, timeout: int = 15) -> BeautifulSoup:
    """Fetch a page and return a BeautifulSoup parser."""
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")



def price_to_number(price_text: str) -> float:
    """Convert a displayed price such as £36.94 or Â£36.94 into 36.94."""
    cleaned = price_text.replace("Â", "").replace("£", "").replace(",", "").strip()
    return float(cleaned)



def discover_categories(
    session: requests.Session, base_url: str = BASE_URL
) -> list[dict[str, str]]:
    """Read category names and absolute URLs from the homepage sidebar."""
    soup = fetch_soup(session, base_url)
    sidebar = soup.find("div", class_="side_categories")
    if sidebar is None:
        raise ValueError("Could not find the category sidebar on the homepage.")

    categories = []
    for link in sidebar.select("ul li ul li a"):
        href = link.get("href")
        name = link.get_text(" ", strip=True)
        if href and name:
            categories.append({
                "name": name,
                "url": urljoin(base_url, href),
            })
    return categories


def scrape_category(
    session: requests.Session,
    category: dict[str, str],
    delay: float = 0.2,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    """Scrape all paginated listing pages for one category."""
    books: list[dict[str, Any]] = []
    current_url: str | None = category["url"]
    page_number = 1
    visited_pages: set[str] = set()

    while current_url:
        # Protect against accidental pagination loops.
        if current_url in visited_pages:
            logger.warning("Repeated page URL detected; stopping category: %s", current_url)
            break
        visited_pages.add(current_url)

        logger.info("Category '%s' — page %d: %s", category["name"], page_number, current_url)
        soup = fetch_soup(session, current_url, timeout=timeout)
        cards = soup.select("article.product_pod")

        for card in cards:
            title_element = card.select_one("h3 a")
            price_element = card.select_one("p.price_color")
            if title_element is None:
                continue

            title = title_element.get("title") or title_element.get_text(" ", strip=True)
            href = title_element.get("href")
            book_url = urljoin(current_url, href) if href else ""

            price_text = price_element.get_text(strip=True) if price_element else ""           
            # Fix a common UTF-8 decoding display issue
            price_text = price_text.replace("Â", "")
            try:
                numeric_price: float | None = price_to_number(price_text)
            except (ValueError, AttributeError):
                numeric_price = None

                
            books.append({
                "title": title,
                "price": price_text or "Price unavailable",
                "price_numeric": numeric_price,
                "category": category["name"],
                "url": book_url,
            })

        logger.info("Found %d book cards on page %d.", len(cards), page_number)
        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            current_url = urljoin(current_url, next_link["href"])
            page_number += 1
            if delay > 0:
                time.sleep(delay)
        else:
            current_url = None

    return books


def deduplicate_books(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one record per book URL; use title as a fallback if URL is missing."""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()

    for book in books:
        key = book.get("url") or book.get("title", "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(book)

    return unique


def sort_books_by_price(books: list[dict[str, Any]], descending: bool = False) -> list[dict[str, Any]]:
    """Sort books by numeric price; records without valid prices go last."""
    valid = [book for book in books if isinstance(book.get("price_numeric"), (int, float))]
    invalid = [book for book in books if not isinstance(book.get("price_numeric"), (int, float))]
    valid.sort(key=lambda book: book["price_numeric"], reverse=descending)
    return valid + invalid


def save_csv(books: list[dict[str, Any]], output_path: Path) -> None:
    """Write scraped records to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(books)


def save_json(books: list[dict[str, Any]], output_path: Path) -> None:
    """Write scraped records to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(books, file, ensure_ascii=False, indent=4)


def run_scraper(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    delay: float = 0.2,
    limit_categories: int | None = None,
    descending: bool = False,
) -> list[dict[str, Any]]:
    """Run the full scrape, de-duplicate, sort, and export data."""
    session = build_session()
    try:
        categories = discover_categories(session)
        if limit_categories is not None:
            categories = categories[:limit_categories]
        if not categories:
            raise ValueError("No categories were discovered.")

        logger.info("Discovered %d categories.", len(categories))
        collected: list[dict[str, Any]] = []

        for index, category in enumerate(categories, start=1):
            logger.info("Starting category %d/%d: %s", index, len(categories), category["name"])
            try:
                collected.extend(scrape_category(session, category, delay=delay))
            except requests.RequestException as error:
                logger.error("Skipping category '%s' after request error: %s", category["name"], error)

        unique = deduplicate_books(collected)
        sorted_books = sort_books_by_price(unique, descending=descending)

        if not sorted_books:
            raise RuntimeError("No books were scraped. Check your internet connection or the website structure.")

        csv_path = output_dir / "books.csv"
        json_path = output_dir / "books.json"
        save_csv(sorted_books, csv_path)
        save_json(sorted_books, json_path)

        priced = [book for book in sorted_books if isinstance(book.get("price_numeric"), (int, float))]
        logger.info("=" * 45)
        logger.info("SCRAPING SUMMARY")
        logger.info("Raw records collected: %d", len(collected))
        logger.info("Unique books: %d", len(unique))
        logger.info("Books with valid prices: %d", len(priced))
        logger.info("CSV saved to: %s", csv_path.resolve())
        logger.info("JSON saved to: %s", json_path.resolve())
        logger.info("10 %s-priced books:", "highest" if descending else "cheapest")
        for book in priced[:10]:
            logger.info("  %s — %s", book["title"], book["price"])

        return sorted_books
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Books to Scrape categories and export books to CSV and JSON."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for output files (default: output).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Seconds to wait between pages in the same category (default: 0.2).",
    )
    parser.add_argument(
        "--limit-categories",
        type=int,
        default=None,
        help="Optional category limit for a quick test, e.g. --limit-categories 2.",
    )
    parser.add_argument(
        "--descending",
        action="store_true",
        help="Sort from highest to lowest price instead of lowest to highest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.delay < 0:
        raise SystemExit("--delay must be zero or greater.")
    if args.limit_categories is not None and args.limit_categories < 1:
        raise SystemExit("--limit-categories must be at least 1.")

    try:
        run_scraper(
            output_dir=args.output_dir,
            delay=args.delay,
            limit_categories=args.limit_categories,
            descending=args.descending,
        )
    except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
        logger.error("Scraper stopped: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
