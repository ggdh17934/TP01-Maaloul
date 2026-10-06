"""TP01: collect every quote on the first page of at least 1,050 authors."""

import hashlib
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from itertools import islice
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.quotationspage.com"
TARGET = 1050
AUTHOR_TARGET = 1050
DELAY = 3.0
USER_AGENT = "TP1QuotesBot/1.0 (University of Eloued educational TP)"
OUTPUT = Path(__file__).resolve().parent / "quotes.csv"
CACHE_DIR = OUTPUT.parent / "tmp" / "first-page-cache"
COLUMNS = ["quote", "author", "author_url", "quote_url"]


def progress(message):
    print(message, file=sys.stderr, flush=True)


def clean_text(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def comparison_key(text):
    """Compare wording while ignoring case, whitespace, and punctuation."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return clean_text("".join(character for character in normalized
                              if not unicodedata.category(character).startswith("P")))


def site_url(href, current=BASE_URL + "/"):
    """Resolve real website links without following unrelated external sites."""
    parts = urlsplit(urljoin(current, href))
    if parts.scheme not in {"http", "https"} or parts.netloc != urlsplit(BASE_URL).netloc:
        raise ValueError(f"Link leaves the selected website: {href}")
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))


@dataclass
class Author:
    name: str
    url: str
    advertised_count: int


def discover_authors(html, page_url):
    """Read authors in displayed order from a featured or letter index."""
    soup = BeautifulSoup(html, "html.parser")
    authors, seen = [], set()
    for link in soup.select("a[href]"):
        try:
            url = site_url(link["href"], page_url)
        except ValueError:
            continue
        path = urlsplit(url).path
        if not re.fullmatch(r"/quotes/[^/]+/?", path) or path.endswith(".html"):
            continue
        url = url.rstrip("/")
        name = clean_text(link.get_text(" ", strip=True))
        if not name or url in seen:
            continue
        # The website places the advertised count immediately after the name.
        suffix = str(link.next_sibling or "")
        match = re.search(r"\((\d+)\)", suffix)
        authors.append(Author(name, url, int(match.group(1)) if match else 0))
        seen.add(url)
    if not authors:
        raise ValueError(f"No author links found at {page_url}; inspect the HTML.")
    return authors


def iter_authors(client, letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    """Discover distinct authors in A-Z index order; fetch letters as needed."""
    seen = set()
    for letter in letters:
        url = BASE_URL + f"/quotes/{letter}.html"
        html = client.fetch_html(url)
        for author in discover_authors(html, url):
            if author.url not in seen:
                seen.add(author.url)
                yield author


class PageClient:
    """Sequential Requests downloads, robots checking, and a three-second pause."""

    def __init__(self, cache_dir=CACHE_DIR):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.robots = None
        self.delay = DELAY
        self.last_finished = None
        self.requests_made = 0
        self.html_pages = 0
        self.network_pages = 0
        self.cache_hits = 0
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None

    def check_robots(self):
        response = self.request(BASE_URL + "/robots.txt")
        self.robots = RobotFileParser()
        self.robots.parse(response.text.splitlines())
        self.delay = max(DELAY, self.robots.crawl_delay(USER_AGENT) or 0)
        progress(f"Robots checked. Sequential requests; pause: {self.delay:g} seconds.")

    def request(self, url):
        url = site_url(url)
        for redirect in range(6):
            for attempt in range(3):
                if self.robots and not self.robots.can_fetch(USER_AGENT, url):
                    raise ValueError(f"URL disallowed by robots.txt: {url}")
                if self.last_finished is not None:
                    time.sleep(max(0, self.delay - (time.monotonic() - self.last_finished)))
                self.requests_made += 1
                try:
                    response = self.session.get(url, timeout=(10, 30), allow_redirects=False)
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == 2:
                        raise
                    progress(f"Connection failed; retrying in {10 * (attempt + 1)} seconds.")
                    time.sleep(10 * (attempt + 1))
                    continue
                finally:
                    self.last_finished = time.monotonic()
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    wait = 30 * (attempt + 1)
                    retry_after = response.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        wait = max(wait, int(retry_after))
                    elif retry_after:
                        try:
                            when = parsedate_to_datetime(retry_after)
                            wait = max(wait, (when - datetime.now(timezone.utc)).total_seconds())
                        except (TypeError, ValueError):
                            pass
                    progress(f"HTTP {response.status_code}; waiting {wait:.0f}s before retry.")
                    time.sleep(wait)
                    continue
                break
            if response.status_code in {301, 302, 303, 307, 308}:
                url = site_url(response.headers["Location"], url)
                continue
            response.raise_for_status()
            if "text/" not in response.headers.get("Content-Type", ""):
                raise ValueError(f"Unexpected response type at {url}")
            if any(marker in response.text.lower() for marker in
                   ("cf-chl-", "challenges.cloudflare.com", "g-recaptcha", "h-captcha")):
                raise ValueError(f"Bot challenge encountered at {url}; stopping.")
            return response
        raise ValueError(f"Too many redirects at {url}")

    def fetch_html(self, url):
        url = site_url(url)
        if self.robots and not self.robots.can_fetch(USER_AGENT, url):
            raise ValueError(f"URL disallowed by robots.txt: {url}")
        cached = None
        cache_path = None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
            if cache_path.exists():
                try:
                    candidate = json.loads(cache_path.read_text(encoding="utf-8"))
                    if candidate["requested_url"] != url or not isinstance(candidate["html"], str):
                        raise ValueError("Invalid cached page")
                    final_url = site_url(candidate["url"])
                    if self.robots and not self.robots.can_fetch(USER_AGENT, final_url):
                        raise ValueError("Cached redirect is disallowed")
                    cached = candidate
                except (ValueError, KeyError, TypeError):
                    progress(f"Invalid cached page; fetching again: {url}")
        if cached is None:
            response = self.request(url)
            cached = {"requested_url": url, "url": response.url, "html": response.text}
            self.network_pages += 1
            if cache_path is not None:
                temporary = cache_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
                temporary.replace(cache_path)
            source = "downloaded"
        else:
            self.cache_hits += 1
            source = "cached"
        self.html_pages += 1
        progress(f"[HTML page {self.html_pages}; {source}] {cached['url']}")
        # Q1 explicitly asks to display the full source, not just a preview.
        print(f"\n--- HTML SOURCE: {cached['url']} ---\n", flush=True)
        print(cached["html"], flush=True)
        return cached["html"]


# Q1: fetch only the first page for each selected author and display full HTML.
def question_1(client, authors):
    pages = []
    seen = set()
    for author in authors:
        if author.url in seen:
            raise ValueError(f"Repeated author page: {author.url}")
        seen.add(author.url)
        html = client.fetch_html(author.url)
        pages.append((author.url, author.url, html))
        progress(f"Fetched first page for {author.name} ({len(pages)}/{len(authors)}).")
    return pages


# Q2: extract all quotations and their matching authors with BeautifulSoup.
def question_2(pages):
    records = []
    for author_url, page_url, html in pages:
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.select("dt.quote")
        if not blocks:
            raise ValueError(f"No quotations found at {page_url}; inspect the HTML.")
        for block in blocks:
            link = next((a for a in block.select("a[href]")
                         if re.fullmatch(r"/quote/\d+\.html", urlsplit(
                             urljoin(page_url, a["href"])).path)), None)
            if not link:
                raise ValueError(f"Quotation has no detail link at {page_url}")
            attribution = None
            for sibling in block.next_siblings:
                if getattr(sibling, "name", None) == "dt":
                    break
                if (getattr(sibling, "name", None) == "dd"
                        and "author" in sibling.get("class", [])):
                    attribution = sibling
                    break
            author = attribution.find("b") if attribution else None
            text = clean_text(link.get_text(" ", strip=True))
            name = clean_text(author.get_text(" ", strip=True)) if author else ""
            if not text or not name:
                raise ValueError(f"Empty quote or missing author at {page_url}")
            records.append({"quote": text, "author": name, "author_url": author_url,
                            "quote_url": site_url(link["href"], page_url)})
    return records


def remove_duplicates(records):
    unique, seen_urls, seen_texts = [], set(), set()
    for record in records:
        key = comparison_key(record["quote"])
        repeated = record["quote_url"] in seen_urls or key in seen_texts
        seen_urls.add(record["quote_url"])
        seen_texts.add(key)
        if not repeated:
            unique.append(record)
    return unique


# Q3: export the extracted records to CSV using pandas.
def question_3(records, output=OUTPUT):
    output = Path(output)
    temporary = output.with_name(output.name + ".tmp")
    pd.DataFrame(records, columns=COLUMNS).to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(output)
    progress(f"Q3: saved {len(records)} records to {output}.")


# Q4: reopen the CSV and check its records, excluding the header.
def question_4(expected_count, output=OUTPUT, target=TARGET,
               author_pages=None, author_target=AUTHOR_TARGET):
    frame = pd.read_csv(output, dtype=str, keep_default_na=False)
    if list(frame.columns) != COLUMNS or len(frame) != expected_count:
        raise ValueError("CSV columns or record count differ from the extracted data.")
    if frame.apply(lambda column: column.str.strip().eq("")).any().any():
        raise ValueError("CSV contains empty quotations, author names, or links.")
    if frame["quote"].map(comparison_key).duplicated().any() or frame["quote_url"].duplicated().any():
        raise ValueError("CSV contains repeated quotations.")
    if not frame["quote_url"].str.fullmatch(re.escape(BASE_URL) + r"/quote/\d+\.html").all():
        raise ValueError("CSV contains an unexpected quotation URL.")
    if not frame["author_url"].str.fullmatch(re.escape(BASE_URL) + r"/quotes/[^/]+/?").all():
        raise ValueError("CSV contains an unexpected author URL.")
    if author_pages is not None:
        if len(set(author_pages)) != len(author_pages):
            raise ValueError("The run visited a repeated author page.")
        if not set(frame["author_url"]).issubset(author_pages):
            raise ValueError("CSV contains an author page not visited in this run.")
        if len(author_pages) < author_target:
            raise ValueError(f"Only {len(author_pages)} author first pages; need {author_target}.")
        progress(f"Q4: verified {len(author_pages)} distinct author first pages.")
    progress(f"Q4: verified {len(frame)} distinct records; target is {target}.")
    return len(frame) >= target


def main():
    client = PageClient()
    started = time.monotonic()
    try:
        progress(f"Q1: first pages of at least {AUTHOR_TARGET} distinct authors; "
                 f"at least {TARGET} distinct CSV records.")
        client.check_robots()
        candidates = iter_authors(client)
        selected = list(islice(candidates, AUTHOR_TARGET))
        if len(selected) < AUTHOR_TARGET:
            raise ValueError(f"Only {len(selected)} authors found; need {AUTHOR_TARGET}.")
        progress(f"Selected {len(selected)} distinct authors in A-Z index order.")
        raw = []
        author_pages = []
        while True:
            pages = question_1(client, selected)
            author_pages.extend(author_url for author_url, _, _ in pages)
            progress("Q2: extract quotations and authors with BeautifulSoup.")
            raw.extend(question_2(pages))
            unique = remove_duplicates(raw)
            progress(f"Q2: {len(raw)} collected; {len(raw) - len(unique)} repeats removed; "
                     f"{len(unique)} distinct quotes.")
            for record in unique[:3]:
                print(f"{record['author']}: {record['quote']}", flush=True)
            progress("Q3: export with pandas.")
            question_3(unique, OUTPUT)
            progress("Q4: reopen and validate the CSV.")
            if question_4(len(unique), OUTPUT, target=TARGET,
                          author_pages=author_pages, author_target=AUTHOR_TARGET):
                progress(f"Complete: {len(unique)} distinct quotes, {len(author_pages)} distinct "
                         f"author first pages, {client.html_pages} HTML pages "
                         f"({client.network_pages} downloaded, {client.cache_hits} reused), "
                         f"{client.requests_made} HTTP requests; "
                         f"elapsed {time.monotonic() - started:.1f} seconds.")
                return
            author = next(candidates, None)
            if author is None:
                raise ValueError(f"Author indexes exhausted with only {len(unique)} distinct quotes.")
            selected = [author]
            progress(f"Below target; repeating Q1-Q4 for {selected[0].name}.")
    finally:
        client.session.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except KeyboardInterrupt:
        progress("Stopped by the user. Any existing CSV may be incomplete.")
        sys.exit(130)
    except (requests.RequestException, ValueError, OSError) as error:
        progress(f"Failed: {error}")
        sys.exit(1)
