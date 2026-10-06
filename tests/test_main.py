"""Checks for first-page scope, author discovery, caching, and CSV validation."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.robotparser import RobotFileParser

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

    def test_extracts_all_first_page_quotes_without_navigation_or_references(self):
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

    def test_question_1_never_follows_next_page(self):
        url = main.BASE_URL + "/quotes/Example_Author"
        html = '<a href="/quotes/Example_Author/21">Next Page</a>'
        client = Mock()
        client.fetch_html.return_value = html
        pages = main.question_1(client, [main.Author("Example Author", url, 50)])
        client.fetch_html.assert_called_once_with(url)
        self.assertEqual(pages, [(url, url, html)])

    def test_letter_discovery_deduplicates_author_urls_and_keeps_index_order(self):
        client = Mock()
        client.fetch_html.side_effect = [
            '<a href="/quotes/First/">First</a> (1)',
            '<a href="/quotes/First">First again</a> (1)'
            '<a href="/quotes/Second">Second</a> (2)',
        ]
        authors = list(main.iter_authors(client, letters="AB"))
        self.assertEqual([a.url for a in authors],
                         [main.BASE_URL + "/quotes/First", main.BASE_URL + "/quotes/Second"])

    def test_saved_html_can_resume_but_robots_rules_still_apply(self):
        url = main.BASE_URL + "/quotes/Example_Author"
        with tempfile.TemporaryDirectory() as directory:
            client = main.PageClient(cache_dir=directory)
            try:
                client.request = Mock(return_value=SimpleNamespace(url=url, text="<html>Saved</html>"))
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(client.fetch_html(url), "<html>Saved</html>")
                    self.assertEqual(client.fetch_html(url), "<html>Saved</html>")
                client.request.assert_called_once_with(url)
                self.assertEqual(client.cache_hits, 1)
                client.robots = RobotFileParser()
                client.robots.parse(["User-agent: *", "Disallow: /quotes/"])
                with self.assertRaisesRegex(ValueError, "disallowed"):
                    client.fetch_html(url)
            finally:
                client.session.close()

    def test_main_collects_author_target_even_when_row_target_is_already_met(self):
        first = main.BASE_URL + "/quotes/First"
        second = main.BASE_URL + "/quotes/Second"
        client = Mock()
        client.html_pages, client.network_pages, client.cache_hits, client.requests_made = 3, 3, 0, 4
        client.fetch_html.side_effect = [
            '<a href="/quotes/First">First</a> (1)<a href="/quotes/Second">Second</a> (1)',
            '<dt class="quote"><a href="/quote/1.html">First quote.</a></dt>'
            '<dd class="author"><b>First</b></dd><a href="/quotes/First/21">Next Page</a>',
            '<dt class="quote"><a href="/quote/2.html">Second quote.</a></dt>'
            '<dd class="author"><b>Second</b></dd>',
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "quotes.csv"
            with patch.object(main, "PageClient", return_value=client), \
                    patch.object(main, "AUTHOR_TARGET", 2), patch.object(main, "TARGET", 1), \
                    patch.object(main, "OUTPUT", output), redirect_stdout(io.StringIO()):
                main.main()
            self.assertEqual(main.pd.read_csv(output).author_url.tolist(), [first, second])
            self.assertEqual([call.args[0] for call in client.fetch_html.call_args_list],
                             [main.BASE_URL + "/quotes/A.html", first, second])

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
        punctuation_variant = {**record, "quote": record["quote"].replace(",", "").replace(".", ""),
                               "quote_url": main.BASE_URL + "/quote/3.html"}
        unique = main.remove_duplicates([record, duplicate, punctuation_variant])
        self.assertEqual(unique, [record])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.csv"
            main.question_3(unique, path)
            self.assertTrue(main.question_4(1, path, target=1))
            self.assertFalse(main.question_4(1, path, target=1050))
            with self.assertRaisesRegex(ValueError, "author first pages"):
                main.question_4(1, path, target=1, author_pages=[record["author_url"]], author_target=2)
            with self.assertRaisesRegex(ValueError, "repeated author"):
                main.question_4(1, path, target=1,
                                author_pages=[record["author_url"], record["author_url"]], author_target=2)
            restored = main.pd.read_csv(path, keep_default_na=False)
            self.assertEqual(restored.iloc[0]["quote"], record["quote"])


if __name__ == "__main__":
    unittest.main()
