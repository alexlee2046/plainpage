"""Static AEO checks. Run: python3 -m unittest discover -s tests -v."""
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://alexlee2046.github.io/plainpage/"
PAGES = {"index.html": "", "support.html": "support.html", "privacy.html": "privacy.html"}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.text = []
        self.json_ld = []
        self.in_json = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json = False

    def handle_data(self, data):
        (self.json_ld if self.in_json else self.text).append(data)


class SiteTests(unittest.TestCase):
    def test_metadata_and_local_links(self):
        for filename, route in PAGES.items():
            with self.subTest(page=filename):
                page = Page((ROOT / filename).read_text())
                canonicals = [a["href"] for t, a in page.tags if t == "link" and a.get("rel") == "canonical"]
                self.assertEqual(canonicals, [BASE + route])
                descriptions = [a.get("content") for t, a in page.tags if t == "meta" and a.get("name") == "description"]
                self.assertEqual(len(descriptions), 1)
                self.assertTrue(descriptions[0])
                self.assertIn(BASE + route, [a.get("content") for t, a in page.tags if t == "meta" and a.get("property") == "og:url"])
                self.assertIn(("html", {"lang": "zh-Hans"}), page.tags)
                for tag, attrs in page.tags:
                    url = attrs.get("href", "")
                    if tag in ("a", "link") and url and not url.startswith(("https://", "#")):
                        self.assertTrue((ROOT / ("index.html" if url == "./" else url)).is_file(), url)

    def test_schema_matches_visible_faq(self):
        page = Page((ROOT / "index.html").read_text())
        graph = json.loads("".join(page.json_ld))
        self.assertEqual(graph["@context"], "https://schema.org")
        app, faq = graph["@graph"]
        self.assertEqual(app["@type"], "SoftwareApplication")
        self.assertEqual(app["downloadUrl"], "https://apps.apple.com/app/id6815329484")
        self.assertEqual(app["offers"]["price"], "0")
        self.assertEqual(app["operatingSystem"], "iOS 17 or later")
        self.assertNotIn("aggregateRating", app)
        self.assertNotIn("review", app)
        visible = "".join("".join(page.text).split())
        self.assertEqual(faq["@type"], "FAQPage")
        self.assertEqual(len(faq["mainEntity"]), 6)
        self.assertEqual(sum(t == "h3" for t, _ in page.tags), 6)
        for question in faq["mainEntity"]:
            self.assertIn("".join(question["name"].split()), visible)
            self.assertIn("".join(question["acceptedAnswer"]["text"].split()), visible)

    def test_sitemap(self):
        tree = ET.parse(ROOT / "sitemap.xml")
        urls = [n.text for n in tree.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertCountEqual(urls, [BASE + route for route in PAGES.values()])

    def test_public_feedback_warning(self):
        source = (ROOT / "support.html").read_text()
        self.assertIn("GitHub Issues 是公开的", source)
        self.assertIn("GitHub Issues are public", source)
        self.assertNotIn("下个版本修正", source)
        self.assertNotIn("we'll fix it in the next update", source)


if __name__ == "__main__":
    unittest.main()
