# TP01 implementation plan — first author pages

The user revised the scope on 6 October 2026: visit the **first page only** of at least **1,050 different authors**, and extract **all quotations on each visited first page**. Continuation pages are outside this version's scope.

## Assignment and chosen boundary

| Assignment item | Implementation |
| --- | --- |
| Python 3.x | Python program and local virtual environment |
| Requests | Sequential HTTP downloads |
| BeautifulSoup | HTML parsing and quotation extraction |
| Q1: fetch pages and display HTML | Full HTML for A–Z indexes and selected author first pages |
| Q2: extract all quotations | Every quotation on each fetched author first page |
| Q3: save with pandas | quotes.csv with four columns |
| Q4: at least 1,000 rows | At least 1,050 distinct data records, excluding the header |
| GitHub submission | Private ggdh17934/TP01-Maaloul repository |

The PDF asks for 1,000 rows, not 1,000 pages. The author-page target is the user's additional choice. First-page collection does not satisfy a literal interpretation of “all pages” across the entire website. State this boundary to the teacher; acceptance has not been confirmed.

## Q1 — download and display

1. Fetch robots rules using TP1QuotesBot/1.0.
2. Read A–Z indexes until 1,050 distinct author URLs are discovered.
3. Canonicalize trailing slashes and skip repeated author URLs.
4. Fetch the first page of each selected author, print complete HTML, and retain it for Q2.
5. Ignore Next Page, Next Author, detail pages, biographies, and external links.
6. Keep requests sequential, with a three-second minimum interval after each response and bounded retries.
7. Cache completed HTML under ignored tmp/first-page-cache/ for resuming. Recheck robots and distinguish reused pages from new downloads.

## Q2 — extract and clean

Parse HTML with BeautifulSoup. Extract every quotation text and detail URL from dt.quote, and its displayed author from the associated dd.author. Stop for missing required data.

Clean whitespace and Unicode without changing saved wording or punctuation. Remove repeated quote URLs and equivalent texts after Unicode, case, whitespace, and punctuation normalization. Preserve first-occurrence order. Similar but different wording is not automatically merged.

Each row represents one quotation. Repeated author names are expected. First-page visits and retained author URLs after quotation deduplication are separate counts.

## Q3 — save CSV

Create a pandas DataFrame with quote, author, author_url, and quote_url. Write UTF-8 with a header and no DataFrame index. Write a temporary CSV before replacing the final file. No separate author export, database, or web application is required.

## Q4 — validate

Reopen the CSV and verify columns, exact count, non-empty fields, URL formats, unique normalized quote texts, and unique quote URLs. Verify at least 1,050 distinct author first-page visits and that saved author URLs belong to that visit list.

If fewer than 1,050 distinct quotations remain, collect the next author's first page and repeat Q1–Q4. Display actual final metrics; never duplicate or invent rows to reach the target.

## Verification and submission

Eight focused tests passed. The completed collection visited 1,050 distinct author first pages and six letter indexes, making 1,057 HTTP requests including robots.txt. It extracted all 3,249 quotation blocks and saved 3,235 records after removing 14 repeats. Collection took 3,428.2 seconds (about 57 minutes 8 seconds).

The CSV was reopened and validated. All saved fields and their order match the downloaded HTML; all final author response URLs are distinct first-page paths. There are no empty required fields, repeated normalized quotation texts, or repeated quote URLs. The CSV represents 1,048 author-page URLs because two authors' quotations duplicated earlier records; 1,050 page visits were completed independently of that deduplication.

Commit the program, requirements, CSV, tests, README, plan, site review, .gitignore, and original PDF. Exclude the Python environment, caches, tmp/, and logs. Preserve repository privacy.

## Completion checklist

- [x] Separate targets for 1,050 author first pages and 1,050 distinct records.
- [x] Remove continuation-page fetching.
- [x] Extract all quotes on each visited first page.
- [x] Add resumable temporary HTML caching and atomic CSV replacement.
- [x] Ignore punctuation in duplicate-text comparisons.
- [x] Pass eight focused tests.
- [x] Complete the revised collection and validate its CSV.
- [x] Record actual revised-run metrics in README.
- [x] Submit the verified revision to the selected private repository.
