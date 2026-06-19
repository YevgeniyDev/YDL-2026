"""Re-runnable crawler for yessenovfoundation.org.

Strategy: breadth-first over SAME-HOST links only, bounded by depth/page count, with a
polite delay. Each page's main content is stripped of nav/footer/scripts, converted to
clean markdown, and saved to data/raw/<lang>-<slug>.md with a small header carrying the
source URL and detected language (used later as a citation + language tag).

Run:  python scraper/scrape.py
"""
from __future__ import annotations

import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

# Allow running as a plain script (python scraper/scrape.py) without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import config  # noqa: E402

try:
    from langdetect import detect as _detect_lang
except Exception:  # langdetect is optional for the scraper
    _detect_lang = None

HEADERS = {
    "User-Agent": "YessenovFoundationBot/1.0 (+chatbot KB builder; contact admin)",
}

# Content containers we drop entirely before extracting text.
_DROP_TAGS = ["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"]

# URL paths/extensions we never want to fetch.
_SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|ico|css|js|pdf|docx?|xlsx?|zip|mp4|mp3)$", re.I)


def same_host(url: str, root_host: str) -> bool:
    return urlparse(url).netloc == root_host


def clean_url(base: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(base, href)
    absolute, _ = urldefrag(absolute)  # drop #fragments
    if _SKIP_EXT.search(urlparse(absolute).path):
        return None
    # Normalize a trailing slash so "/path" and "/path/" aren't crawled twice.
    if absolute.endswith("/") and urlparse(absolute).path != "/":
        absolute = absolute.rstrip("/")
    return absolute


def detect_lang(text: str, url: str) -> str:
    # Prefer an explicit language hint in the URL path, fall back to langdetect.
    path = urlparse(url).path.lower()
    for code in ("kk", "kz", "ru", "en"):
        if f"/{code}/" in path or path.endswith(f"/{code}"):
            return "kk" if code == "kz" else code
    if _detect_lang:
        try:
            code = _detect_lang(text[:1000])
            return "kk" if code == "kz" else code
        except Exception:
            pass
    return "unknown"


def html_to_markdown(soup: BeautifulSoup) -> str:
    """Very small HTML→markdown: headings, paragraphs and list items only."""
    parts: list[str] = []
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for el in main.find_all(["h1", "h2", "h3", "h4", "li", "p"]):
        text = " ".join(el.get_text(" ", strip=True).split())
        if not text:
            continue
        name = el.name
        if name == "h1":
            parts.append(f"# {text}")
        elif name == "h2":
            parts.append(f"## {text}")
        elif name == "h3":
            parts.append(f"### {text}")
        elif name == "h4":
            parts.append(f"#### {text}")
        elif name == "li":
            parts.append(f"- {text}")
        else:
            parts.append(text)
    # Collapse consecutive duplicate lines (common with nested templates).
    out: list[str] = []
    for line in parts:
        if not out or out[-1] != line:
            out.append(line)
    return "\n\n".join(out)


def slugify(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-") or "home"
    return slug[:80]


def crawl() -> None:
    root = config.SITE_ROOT.rstrip("/")
    root_host = urlparse(root).netloc
    out_dir = config.RAW_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    queue: deque[str] = deque([root])
    saved = 0

    session = requests.Session()
    session.headers.update(HEADERS)

    while queue and saved < config.SCRAPE_MAX_PAGES:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  ! fetch failed {url}: {e}")
            continue
        if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(resp.text, "lxml")

        # Enqueue same-host links BEFORE we strip tags.
        for a in soup.find_all("a", href=True):
            nxt = clean_url(url, a["href"])
            if nxt and same_host(nxt, root_host) and nxt not in seen:
                queue.append(nxt)

        # Strip chrome, then extract.
        for tag in soup(_DROP_TAGS):
            tag.decompose()
        markdown = html_to_markdown(soup)
        if len(markdown) < 200:  # skip near-empty pages (image galleries, redirects)
            continue

        title = (soup.title.get_text(strip=True) if soup.title else "") or slugify(url)
        lang = detect_lang(markdown, url)
        fname = f"{lang}-{slugify(url)}.md"
        header = f"---\nsource_url: {url}\nlang: {lang}\ntitle: {title}\n---\n\n"
        (out_dir / fname).write_text(header + markdown, encoding="utf-8")
        saved += 1
        print(f"  [{saved}] {lang}  {url}  ({len(markdown)} chars)")

        time.sleep(config.SCRAPE_DELAY_SECONDS)

    print(f"\nDone. Saved {saved} pages to {out_dir} (visited {len(seen)} URLs).")


if __name__ == "__main__":
    crawl()
