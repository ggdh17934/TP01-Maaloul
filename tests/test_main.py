"""Focused checks for author pairing, pagination, duplicates, and CSV records."""

import tempfile
import unittest
from pathlib import Path

import main


class ScraperTests(unittest.TestCase):
    def test_discovery_keeps_order_and_filters_navigation(self):
        html = '''<a href="/quotes/">Index</a><a href="/quotes/A.html">A</a>
        <div class="authorrow"><a href="/quotes/Example_Author/">Author, Example</a> (2)</div>
        <a href="https://elsewhere.example/quotes/Other/">Other</a>
        <a href="/quotes/Second_Author/">Second Author</a> (3)
        <a href="/quotes/Example_Author/">Repeated link</a> (2)'''
        authors = main.discover_authors(html, main.BASE_URL + "/quotes/A.html")
        self.assertEqual([a.name for a in authors], ["Author, Example", "Second Author"])
        self.assertEqual([a.advertised_count for a in authors], [2, 3])

    def test_extracts_quote_only_and_follows_same_author_pagination(self):
        author_url = main.BASE_URL + "/quotes/Example_Author/"
        html = '''<dl><dt class="quote"><a href="/quote/1.html">A &amp; B,
        <em>think</em> together.</a></dt><dd class="author"><div class="icons">Actions</div>
        <b>Example Author</b>, <i>A source</i><div class="related">More links</div></dd>
        <dt class="quote"><a href="/quote/2.html">A second thought.</a></dt>
        <dd class="author"><b>Example Author</b></dd></dl>
        <a href="/quotes/Example_Author/21">Next Page -&gt;</a>
        <a href="/quotes/Example_Author/21">Next Page -&gt;</a>
        <a href="/quotes/Someone_Else/">Next Author</a>'''
        records = main.question_2([(author_url, author_url, html)])
        self.assertEqual(records[0]["quote"], "A & B, think together.")
        self.assertEqual(records[0]["author"], "Example Author")
        self.assertEqual(len(records), 2)
        self.assertEqual(main.next_page(html, author_url, author_url), author_url + "21")
        wrong_link = '<a href="/quotes/Someone_Else/21">Next Page</a>'
        with self.assertRaises(ValueError):
            main.next_page(wrong_link, author_url, author_url)

    def test_missing_attribution_does_not_use_next_quotes_author(self):
        url = main.BASE_URL + "/quotes/Example_Author/"
        html = '''<dt class="quote"><a href="/quote/1.html">First.</a></dt>
        <dt class="quote"><a href="/quote/2.html">Second.</a></dt>
        <dd class="author"><b>Example Author</b></dd>'''
        with self.assertRaisesRegex(ValueError, "missing author"):
            main.question_2([(url, url, html)])

    def test_csv_round_trip_preserves_first_duplicate_and_quoted_fields(self):
        record = {"quote": 'Thought, with "quotation marks" and café.',
                  "author": "Example Author",
                  "author_url": main.BASE_URL + "/quotes/Example_Author/",
                  "quote_url": main.BASE_URL + "/quote/1.html"}
        duplicate = {**record, "quote": record["quote"].upper(),
                     "quote_url": main.BASE_URL + "/quote/2.html"}
        unique = main.remove_duplicates([record, duplicate])
        self.assertEqual(unique, [record])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.csv"
            main.question_3(unique, path)
            self.assertTrue(main.question_4(1, path, target=1))
            self.assertFalse(main.question_4(1, path, target=1050))
            restored = main.pd.read_csv(path, keep_default_na=False)
            self.assertEqual(restored.iloc[0]["quote"], record["quote"])


if __name__ == "__main__":
    unittest.main()
