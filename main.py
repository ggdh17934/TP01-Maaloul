"""TP01: fetch HTML, extract quotes, save CSV, and verify at least 1,050 rows."""

import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.quotationspage.com"
TARGET = 1050
DELAY = 3.0
USER_AGENT = "TP1QuotesBot/1.0 (University of Eloued educational TP)"
OUTPUT = Path(__file__).resolve().parent / "quotes.csv"
COLUMNS = ["quote", "author", "author_url", "quote_url"]


def progress(message):
    print(message, file=sys.stderr, flush=True)


def clean_text(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def comparison_key(text):
    return clean_text(unicodedata.normalize("NFKC", text)).casefold()


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


def next_page(html, page_url, author_url):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for link in soup.select("a[href]"):
        if "Next Page" not in link.get_text(" ", strip=True):
            continue
        url = site_url(link["href"], page_url)
        prefix = urlsplit(author_url).path.rstrip("/") + "/"
        if not urlsplit(url).path.startswith(prefix):
            raise ValueError(f"Next Page changes author at {page_url}")
        links.add(url)
    if len(links) > 1:
        raise ValueError(f"Conflicting Next Page links at {page_url}")
    return next(iter(links), None)


class PageClient:
    """Sequential Requests downloads, robots checking, and a three-second pause."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.robots = None
        self.delay = DELAY
        self.last_finished = None
        self.requests_made = 0
        self.html_pages = 0

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
        response = self.request(url)
        self.html_pages += 1
        progress(f"[HTML page {self.html_pages}] {response.url}")
        # Q1 explicitly asks to display the full source, not just a preview.
        print(f"\n--- HTML SOURCE: {response.url} ---\n", flush=True)
        print(response.text, flush=True)
        return response.text


# Q1: fetch all pages for selected authors and display their complete HTML.
def question_1(client, authors):
    pages = []
    for author in authors:
        url, visited = author.url, set()
        while url:
            if url in visited:
                raise ValueError(f"Pagination loop: {url}")
            visited.add(url)
            html = client.fetch_html(url)
            pages.append((author.url, url, html))
            url = next_page(html, url, author.url)
        progress(f"Fetched all {len(visited)} page(s) for {author.name}.")
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
    pd.DataFrame(records, columns=COLUMNS).to_csv(output, index=False, encoding="utf-8-sig")
    progress(f"Q3: saved {len(records)} records to {output}.")


# Q4: reopen the CSV and check its records, excluding the header.
def question_4(expected_count, output=OUTPUT, target=TARGET):
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
    progress(f"Q4: verified {len(frame)} distinct records; target is {target}.")
    return len(frame) >= target


def main():
    client = PageClient()
    try:
        progress("Q1: discover authors, fetch their pages, and display HTML.")
        client.check_robots()
        index_url = BASE_URL + "/quotes/"
        candidates = discover_authors(client.fetch_html(index_url), index_url)
        progress(f"Discovered {len(candidates)} featured authors, in displayed order.")
        count, estimated, selected = 0, 0, []
        while count < len(candidates) and estimated < TARGET:
            author = candidates[count]
            selected.append(author)
            estimated += author.advertised_count or 1
            count += 1
        raw = []
        all_author_urls = {author.url for author in candidates}
        extra_letter = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        completed_authors = 0
        while True:
            pages = question_1(client, selected)
            completed_authors += len(selected)
            progress("Q2: extract quotations and authors with BeautifulSoup.")
            raw.extend(question_2(pages))
            unique = remove_duplicates(raw)
            progress(f"Q2: {len(raw)} collected; {len(raw) - len(unique)} repeats removed; "
                     f"{len(unique)} distinct quotes.")
            for record in unique[:3]:
                print(f"{record['author']}: {record['quote']}", flush=True)
            progress("Q3: export with pandas.")
            question_3(unique)
            progress("Q4: reopen and validate the CSV.")
            if question_4(len(unique)):
                progress(f"Complete: {len(unique)} distinct quotes, {completed_authors} authors, "
                         f"{client.html_pages} HTML pages, {client.requests_made} HTTP requests.")
                return
            while count >= len(candidates):
                letter = next(extra_letter, None)
                if letter is None:
                    raise ValueError(f"Author indexes exhausted with only {len(unique)} distinct quotes.")
                progress(f"Q1: discover additional authors under {letter}.")
                url = BASE_URL + f"/quotes/{letter}.html"
                for author in discover_authors(client.fetch_html(url), url):
                    if author.url not in all_author_urls:
                        candidates.append(author)
                        all_author_urls.add(author.url)
            selected = [candidates[count]]
            count += 1
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
