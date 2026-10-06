# TP01: Python Web Scraping Case-study

University of Eloued — second-year Master IA & Data Science, Big Data Analytics, 2026/2027.

This program collects quotations from [The Quotations Page](https://www.quotationspage.com/quotes/), keeping each quotation with its author and source links. It follows the four questions in the assignment and aims for at least **1,050 distinct records**, exceeding the required 1,000 rows.

## Setup

Use Python 3.x. The verified environment uses Python 3.13; the pinned pandas version requires Python 3.11 or newer.

From this project's folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The required external libraries are Requests, BeautifulSoup, and pandas. No browser automation or JavaScript execution is needed for the tested page layout.

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

The program displays complete HTML on standard output, as required by Q1. Progress and the final validation result appear on standard error. Expect substantial terminal output and a run lasting several minutes: requests are sequential and have a minimum three-second pause after each response.

`quotes.csv` is written beside `main.py`, even when the program is launched from another folder. The program finishes all pages for the last selected author, so the result can exceed 1,050 records.

The constants `TARGET`, `DELAY`, and `USER_AGENT` are near the top of `main.py`. The agreed defaults are 1,050 records, three seconds, and a descriptive project crawler name. Adjust the target only if the collection requirement changes.

## Q1 — fetch the pages and display their HTML

Requests downloads the site's robots file and checks its rules. It then downloads the featured author index and displays its full HTML.

The program reads author names, actual author-page URLs, and advertised quotation counts in displayed order. These counts estimate an initial selection; the actual usable record count is established later. It downloads every quotation page for the selected authors, follows the site's “Next Page” links, and displays each page's full HTML.

There is one network request at a time, with a three-second pause. HTTP errors are reported. Temporary failures have bounded retries; rate-limit responses honor `Retry-After`. Disallowed paths, pagination loops, and bot challenges stop the run.

**Collection boundary:** “all pages” means every quotation page for the selected authors. The program does not crawl the entire domain. An author's biography, individual quote detail pages, other linked collections, advertisements, and external websites are outside the collection.

## Q2 — extract all quotes with BeautifulSoup

BeautifulSoup parses the fetched HTML using Python's built-in HTML parser. Each `dt.quote` provides quotation text and a detail link; its associated `dd.author` supplies the author's name from bold text.

This keeps quotations separate from navigation, icons, references, and related links. Whitespace is cleaned without removing punctuation or accents. Repeated quote URLs and exact normalized quotation-text repeats are removed, keeping their first occurrence. Author order, page order, and quote order are preserved.

A missing author or unexpected quotation layout produces a clear error instead of silently pairing a quotation with the wrong attribution. The program displays three sample records after extraction.

## Q3 — save the results using pandas

pandas creates `quotes.csv` with these columns:

| Column | Meaning |
| --- | --- |
| `quote` | Complete cleaned quotation text |
| `author` | Author name displayed by the website |
| `author_url` | Author's quotation-page URL |
| `quote_url` | Individual quotation URL |

The CSV uses UTF-8 with a byte-order mark for convenient opening in Windows spreadsheet applications. It has a header and no extra DataFrame index column. pandas handles embedded commas and quotation marks.

## Q4 — ensure at least 1,000 rows

The program reopens the saved CSV with pandas, checks its columns and record count, and verifies non-empty values, unique quotations, and source-link formats. The header is excluded from the record count.

If the result has fewer than 1,050 distinct records, the program selects another author, completes that author's pages, and repeats Q1–Q4. Alphabetical author indexes are available if the featured list is exhausted. It never pads the dataset with duplicated or fabricated quotations.

A successful run ends with `Complete:` and the actual record, author, page, and request counts. A failed or interrupted run exits with a nonzero status; an existing CSV from an earlier export may be below the target and should not be presented as a successful new run.

## Verification

Focused checks cover author discovery, same-author pagination, correct attribution pairing, missing attributions, deduplication order, and CSV handling of commas, quotation marks, and Unicode.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The first live run completed on **3 October 2026**:

| Check | Result |
| --- | --- |
| CSV data records | **1,064** |
| Completed authors | **30** |
| HTML pages fetched | **68** (one featured index and 67 quotation pages) |
| HTTP requests | **69**, including robots.txt |
| Duplicate quotation texts | **0** |
| Empty required fields | **0** |
| Focused tests | **4 passed** |

pandas reopened and validated the CSV. All saved records and their order were also compared with the HTML captured during that run; they matched. The run covered all 15 John Adams records, all 232 Bible records, and all 27 Ellen DeGeneres records among the selected authors.

During development, standard output was redirected to `tmp/html-output.log` and progress to `tmp/run-progress.log`. The default run command above displays the full HTML directly in the terminal. These temporary logs are excluded from GitHub submission.

## Files and submission

- `main.py`: program, with Q1–Q4 labeled in order.
- `requirements.txt`: tested library versions.
- `quotes.csv`: generated and validated dataset.
- `tests/test_main.py`: focused verification checks.
- `PROJECT_PLAN.md`, `SITE_REVIEW.md`: agreed plan and website inspection.
- Original PDF: assignment reference.

The assignment requires submission through the student's GitHub account. The submission repository is [ggdh17934/TP01-Maaloul](https://github.com/ggdh17934/TP01-Maaloul), a private repository containing the program, validated CSV, tests, documentation, and original assignment PDF. The local environment, temporary HTML logs, and Python caches are excluded through `.gitignore`.

The site is acknowledged as the source. Its [FAQ](https://www.quotationspage.com/faq.php) describes restrictions on copying large portions; the original quotations and the site's compilation should not be represented as this project's original work. The prior website review records the published terms and robots checks.
