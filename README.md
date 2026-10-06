# TP01: Python Web Scraping Case-study

University of Eloued — second-year Master IA & Data Science, Big Data Analytics, 2026/2027.

The program visits the **first quotation page of at least 1,050 different authors**, extracts **every quotation on those first pages**, and saves a validated CSV using pandas. Authors are discovered through [The Quotations Page's A–Z indexes](https://www.quotationspage.com/quotes/).

There are two independent targets: `AUTHOR_TARGET = 1050` author first pages and `TARGET = 1050` distinct quotation records. The PDF requires at least **1,000 CSV rows**, excluding the header; it does not require 1,000 website pages. The author-page target is the user's chosen collection scope.

## Setup and run

Use Python 3.x. The verified environment uses Python 3.13; the pinned pandas version requires Python 3.11 or newer.

From this project's folder in PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
~~~

If the environment is already installed, use only the last command. Requests downloads pages, BeautifulSoup parses HTML, and pandas writes and checks the CSV.

Complete HTML is printed to standard output; progress goes to standard error. Expect substantial terminal output. A fresh collection takes roughly an hour or longer: 1,050 author pages alone involve about 53 minutes of three-second request intervals, before indexes, download time, redirects, and retries.

## Q1 — discover authors, fetch first pages, and display HTML

Fetch robots.txt and check the applicable rules using a descriptive User-Agent. Read letter indexes in A–Z order and author links in HTML order, skipping repeated URLs and normalizing trailing slashes. Stop initial discovery once 1,050 authors are selected.

Download the first quotation page of each selected author, print its full HTML, and retain it for Q2. Do not follow Next Page or Next Author; do not fetch individual quotation details or biographies. Requests are sequential, with at least three seconds after a response before another request starts. Temporary failures have bounded retries; rate-limit responses respect Retry-After. Disallowed paths, detected challenges, and unexpected response types stop the run.

**Collection boundary:** first pages of selected authors. This does not collect every page of the website or every quotation by an author with continuation pages. The PDF's phrase “all pages” is broader than this chosen subset; teacher acceptance of that boundary has not been established. Q2 extracts every quotation on the pages actually collected.

### Resume a long collection

Downloaded HTML is cached under `tmp/first-page-cache/`. A rerun rechecks robots, reuses completed pages, prints their full HTML again, and downloads missing pages. The final summary separates newly downloaded pages from cache reuse. A cached page is not counted as a new HTTP request.

The cache is temporary, excluded from GitHub, and may reflect an earlier website version. For a fresh collection, remove only that cache folder before running. Do not run multiple copies concurrently. CSV replacement occurs after a complete temporary CSV is written.

## Q2 — extract every quotation on each first page

BeautifulSoup reads each page with Python's built-in HTML parser. `dt.quote` contains the quotation link and full text; the associated `dd.author` supplies the bold author attribution. Navigation, icons, references, and related links are excluded. Missing attribution or an unexpected layout stops the run.

Saved wording and punctuation are preserved while whitespace and Unicode are cleaned. Deduplication removes repeated quote URLs and texts equivalent after Unicode normalization, case folding, whitespace normalization, and punctuation removal. The first occurrence is retained in collection order. Different wording, even very similar wording, remains distinct; this is not semantic deduplication.

Author names repeat because an author can have multiple quotations. One CSV row represents one quotation, not one author. Attribution capitalization can vary; author URLs identify visited pages.

## Q3 — save using pandas

`quotes.csv` is written beside main.py with these columns:

| Column | Meaning |
| --- | --- |
| quote | Complete cleaned quotation text |
| author | Attribution displayed on the quotation page |
| author_url | Author's first quotation-page URL |
| quote_url | Individual quotation link, retained without downloading it |

pandas handles commas and quotation marks. The CSV has a header, no DataFrame index column, and UTF-8 with a byte-order mark for Windows spreadsheet applications.

## Q4 — reopen and validate

Read the CSV back with pandas. Check its columns, exact count, non-empty fields, unique normalized quotation texts, unique quote URLs, and expected source-link formats. Check at least 1,050 distinct author first-page visits and ensure every saved author URL belongs to that visit list.

If fewer than 1,050 distinct quotations remain, collect another author's first page and repeat Q1–Q4. Never fabricate records. An author may disappear from the final CSV if every quotation on its first page duplicates an earlier record; that does not undo its page visit.

A successful run ends with Complete and the actual quotation, author-page, HTML-page, request, cache, and elapsed-time counts. Failed or interrupted runs exit with a nonzero status. An older or below-target CSV is not proof of successful new collection.

## Verification

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

**Eight focused tests passed**, covering first-page-only behavior despite Next Page links, completing the author target despite enough rows already existing, discovery order and URL deduplication, all-quote extraction, missing attributions, punctuation-insensitive deduplication, cache reuse with robots checks, and CSV validation.

The live collection completed successfully on **6 October 2026**:

| Check | Verified result |
| --- | --- |
| Distinct author first pages visited | **1,050** |
| Letter indexes fetched | **6**, A through F |
| HTML pages downloaded and fully printed | **1,056** |
| HTTP requests, including robots.txt | **1,057** |
| Cached pages reused during this collection | **0** |
| Quotations extracted from source blocks | **3,249** |
| Repeated records removed | **14** |
| CSV data records, excluding header | **3,235** |
| Author-page URLs represented after deduplication | **1,048** |
| Empty required fields | **0** |
| Repeated normalized quote texts or quote URLs | **0** |
| Focused tests | **8 passed** |
| Collection time | **3,428.2 seconds**, about **57 minutes 8 seconds** |

Every saved field and the entire record order were compared with the downloaded source HTML and matched. The count of quotation blocks matched all 3,249 extracted records. All 1,050 final author response URLs were distinct and stayed on the requested first-page paths. Two author pages have no retained CSV row because their quotations duplicated records collected earlier; all 1,050 pages were still visited and extracted.

Development captures HTML in `tmp/first-pages-html.log` and progress in `tmp/first-pages-progress.log`. The normal run command prints complete HTML in the terminal. Logs, caches, and the local Python environment are excluded from submission.

## GitHub submission and source

The project is submitted to the private [ggdh17934/TP01-Maaloul](https://github.com/ggdh17934/TP01-Maaloul) repository. It includes the program, validated CSV, tests, requirements, documentation, .gitignore, and original PDF. Teacher access is a separate user-managed step.

The website is the source. Its [FAQ](https://www.quotationspage.com/faq.php) describes restrictions on copying large portions; the quotations and compilation are not this project's original work. See SITE_REVIEW.md for the recorded review.
