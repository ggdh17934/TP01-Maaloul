# TP01: Python Web Scraping Case-study — detailed plan

Updated: 3 October 2026.

**Stage: implementation authorized on 3 October 2026.** The user asked to start making the program after reviewing this plan. The agreed target, delay, dataset columns, and Q1-Q4 order remain unchanged.

This plan replaces the earlier Wikiquote proposal. The chosen source is **The Quotations Page**. The questions will be presented and implemented in the same order as the assignment: Q1, Q2, Q3, Q4, followed by GitHub submission.

## Agreed project scope

Create a small Python program for the university TP that downloads quotation pages, displays their HTML, extracts quotations and author names, saves a CSV with pandas, and checks its record count.

- Website: https://www.quotationspage.com/
- Starting point: https://www.quotationspage.com/quotes/
- Data target: **at least 1,050 distinct quotation records**, giving a 50-record margin above the PDF's minimum of 1,000.
- Request interval: **three seconds between consecutive requests**, with one request at a time.
- Discovery: read an author's name and actual page link first, then visit that author's quotation pages.
- Author order: the displayed order of the featured author list on the starting page. A letter index, such as `/quotes/A.html`, is available if more authors are needed.
- Page order: the first author page, then its actual “Next Page” links until that author's collection ends.
- CSV order: the same author/page/quotation order in which records were collected. Removing a repeat keeps its first occurrence.
- Finish the last selected author's pages, so the output can be slightly above 1,050. Do not discard extracted quotations solely to force an exact row count.

**Interpretation of “all pages”:** visit every quotation page belonging to each selected author. This is a defined subset of the website. The PDF does not explicitly define this boundary; if the instructor means every page of the entire website, a 1,050-quote subset does not satisfy that literal interpretation. State the selected-author boundary in the submission.

## Required tools

| PDF requirement | Planned use |
| --- | --- |
| Python 3.x | Execute the program |
| Requests | Download pages over HTTP |
| BeautifulSoup | Read HTML structure and extract quotations |
| pandas | Create and export the CSV, then reopen it for validation |

Although pandas is listed as optional in the prerequisite list, Q3 specifically asks to use it. It will therefore be included.

## Question 1 — fetch the pages and display their HTML

**Required result:** the program downloads the selected website pages and displays their HTML source on the screen.

### Steps

1. Check the site's robots rules using a descriptive project User-Agent.
2. Fetch the author-list starting page with Requests.
3. Display that page's URL and its complete HTML in the terminal.
4. Read the author names, author-page links, and displayed quotation counts from the list. Use the counts only to estimate a first group of authors; they are not proof of the final usable record count.
5. Select authors in the displayed order, initially enough to cover approximately 1,050 advertised quotations.
6. Fetch the first page for each selected author, display its URL and full HTML, and retain the HTML for Q2.
7. Follow the actual “Next Page” link and repeat until that author has no continuation page.
8. Wait three seconds between network requests. Do not request several pages concurrently.

BeautifulSoup may also help read author and pagination links in this question. Quote-record extraction belongs to Q2.

Only quote-list pages are needed. Individual quote detail links and author links can be retained as data without fetching additional biography or detail pages.

### Practical checks

- Use a request timeout so a failed connection cannot wait forever.
- Report HTTP failures clearly; do not count a failed page as collected.
- Avoid repeated pagination links and detect loops.
- Follow “Next Page” for the current author; do not mistake “Next Author” for pagination.
- Honor rate-limit responses and their requested waiting time.
- Stop and report a denial or challenge instead of attempting a bypass.

### Evidence for Q1

The terminal shows the URL and full HTML for every fetched index and selected quotation page. Progress messages alone, or saving HTML without displaying it, would not meet the display requirement.

## Question 2 — extract all quotations with BeautifulSoup

**Required result:** extract every quotation from the pages collected in Q1 and associate it with its author.

### Steps

1. Parse each retained HTML page with BeautifulSoup, using Python's built-in HTML parser.
2. Locate each quotation block and read the complete quotation text.
3. Associate the quotation with its following attribution block and extract the author's name.
4. Preserve the author's page URL and the individual quotation link for identifying and tracing the record.
5. Ignore advertisements, navigation, action icons, and unrelated links.
6. Normalize extra whitespace while preserving wording, punctuation, and readable Unicode text.
7. Remove repeated quote links/IDs and exact normalized quotation-text repeats, keeping the first occurrence.
8. Preserve the original collection order.

The PDF explicitly requires quote extraction. Author names and page links are the small additions requested by the user. Avoid adding other dataset fields unless they are requested later.

### Verified HTML locations

| Item | Observed location |
| --- | --- |
| Authors on a letter index | Links inside `div.authorrow` |
| Quotation text and individual quote link | `dt.quote` |
| Attribution | The associated `dd.author` |
| Author name | Bold text within the attribution |
| Continuation page | Anchor displaying “Next Page” |

The featured author list has a different surrounding layout from a letter index; its author links still point to `/quotes/...` pages. Read actual links instead of constructing paths from names.

Sample checks found 15 quotations on John Adams's page and 20 on each of the first two Mark Twain pages. These are prior sample observations, not a completed dataset count. Detailed access evidence is in `SITE_REVIEW.md`.

### Evidence for Q2

Display a small readable sample of extracted quote/author pairs and the collected count. Compare several records with the website, including a record from a continuation page, to ensure the author and quotation were paired correctly.

## Question 3 — save the results to CSV with pandas

**Required result:** export the extracted records using pandas.

### Steps

1. Build a pandas DataFrame from Q2's records.
2. Retain the collection order.
3. Export `quotes.csv` with a header and without a DataFrame index column.
4. Use UTF-8 encoding so accents and punctuation remain readable.
5. Let pandas handle commas, quotation marks, and any line breaks inside fields.

### CSV columns

| Column | Content |
| --- | --- |
| `quote` | Complete cleaned quotation text |
| `author` | Author name shown by the site |
| `author_url` | Author's quotation-page URL |
| `quote_url` | Individual quotation URL; also helps identify repeats |

An internal list of authors is sufficient. A separate author dataset, JSON report, database, or additional export is not required.

### Evidence for Q3

`quotes.csv` exists, opens correctly, and contains the four agreed columns with readable quotation and author text.

## Question 4 — ensure at least 1,000 rows

**Required result:** verify the saved CSV contains at least 1,000 data records. The agreed working target is 1,050 distinct records.

### Steps

1. Reopen `quotes.csv` with pandas after exporting it.
2. Count DataFrame records; exclude the header from the count.
3. Check for empty quote text, missing author names, repeated records, and missing source links.
4. Confirm that the saved record count agrees with the extracted record count.
5. Require at least 1,050 distinct quote records to meet the agreed target and therefore exceed the PDF's 1,000-row minimum.
6. If fewer than 1,050 remain after deduplication, select another author, repeat Q1 and Q2 for all of that author's pages, then repeat Q3 and Q4.
7. Display the actual final count and whether the target was met.

Never pad the file with duplicated or invented quotations. Do not count physical text-file lines: a CSV field may contain a newline, so line count is not necessarily record count.

### Evidence for Q4

A pandas read-back confirms the actual count is at least 1,050, with non-empty quotations and author names and no exact repeated quotation texts. Any incomplete selected author or failed page must be resolved before describing the collection as complete.

## Program and presentation order

Use one readable program, organized into clearly labeled sections/functions corresponding to Q1, Q2, Q3, and Q4.

The normal demonstration follows this sequence:

1. **Q1:** discover selected authors, fetch all their quotation pages, and display HTML.
2. **Q2:** extract quotations and author information from the fetched HTML.
3. **Q3:** export the records with pandas.
4. **Q4:** reopen and validate the CSV.

Additional authors are fetched only if the validated unique count is insufficient. This repeat is a continuation of collection, not a change to the assignment order. The README will explain the four questions in that same order.

## GitHub submission

The PDF separately requires all work to be uploaded to the student's GitHub account. That is the final submission step after implementation and validation.

The intended project files are:

| File | Purpose |
| --- | --- |
| `main.py` | One Python program, organized by Q1–Q4 |
| `requirements.txt` | The three external libraries: Requests, BeautifulSoup, pandas |
| `quotes.csv` | Validated quotation dataset |
| `README.md` | Project description, setup, execution, Q1–Q4 explanation, source, and actual final count |
| `PROJECT_PLAN.md` and `SITE_REVIEW.md` | Planning and website research already prepared |
| Original assignment PDF | Assignment reference |

Exclude the local Python environment and temporary files from the submission. The user selected the existing private repository [ggdh17934/TP01-Maaloul](https://github.com/ggdh17934/TP01-Maaloul) for the completed project.

The selected site's published reuse restriction remains recorded in `SITE_REVIEW.md`. It is separate from robots access. No owner has been contacted; the user authorized submission of the project and CSV to the selected private repository.

## Completion checklist

- [x] Python 3.x, Requests, BeautifulSoup, and pandas are used.
- [x] Q1 prints complete HTML for all selected fetched pages (captured to a temporary log for the development run; the default command displays it on screen).
- [x] Q2 extracts all quotations on those pages and associates the correct author.
- [x] Every selected author's continuation pages are completed.
- [x] Q3 produces `quotes.csv` using pandas.
- [x] Q4 verifies 1,064 distinct data rows, excluding the header.
- [x] Requests run sequentially with a three-second interval.
- [x] The README explains Q1, Q2, Q3, and Q4 in order and records the collection boundary.
- [x] The final work is submitted to the intended GitHub account in the private `ggdh17934/TP01-Maaloul` repository.

**Completed:** the assignment and website review, this plan, the Q1-Q4 program, local dependency setup, four passing focused tests, and a successful live run yielding 1,064 distinct quotes from 30 complete authors across 68 HTML pages. The CSV was reopened and validated, and all records were checked against the captured HTML in collection order.

**GitHub submission:** the completed project is submitted to `ggdh17934/TP01-Maaloul` on 6 October 2026. The repository remains private. Giving the teacher access, if required, is a separate step.
