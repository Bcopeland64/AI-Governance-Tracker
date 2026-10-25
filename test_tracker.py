import unittest
from datetime import timezone

from tracker import CATEGORIES, SOURCES, build_feed_url, parse_feed


class TrackerTests(unittest.TestCase):
    def test_source_directory_covers_every_category_and_requested_source(self):
        self.assertEqual(len(CATEGORIES), 5)
        self.assertEqual(len(SOURCES), 15)
        self.assertEqual({source.category for source in SOURCES}, set(CATEGORIES))
        names = {source.name for source in SOURCES}
        self.assertTrue(any("ISO/IEC JTC 1/SC 42" in name for name in names))
        self.assertTrue(any("UNESCO" in name for name in names))
        self.assertTrue(any("Gibson Dunn" in name for name in names))
        self.assertTrue(any("Latham" in name for name in names))

    def test_feed_url_is_scoped_to_the_official_domain(self):
        source = SOURCES[0]
        url = build_feed_url(source)
        self.assertIn("news.google.com/rss/search", url)
        self.assertIn("site%3Aiso.org", url)

    def test_parses_rss_entries_and_normalizes_dates(self):
        xml = b"""<?xml version="1.0"?>
        <rss><channel><item>
          <title>New AI standard</title>
          <link>https://example.org/update</link>
          <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
        </item></channel></rss>"""
        updates = parse_feed(xml, "Example")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["title"], "New AI standard")
        self.assertEqual(updates[0]["source"], "Example")
        self.assertEqual(updates[0]["published"].tzinfo, timezone.utc)

    def test_parses_atom_entries_and_ignores_unsafe_links(self):
        xml = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Convention update</title>
            <link href="https://example.org/convention" />
            <updated>2025-02-03T10:00:00Z</updated>
          </entry>
          <entry>
            <title>Unsafe link</title>
            <link href="javascript:alert(1)" />
          </entry>
        </feed>"""
        updates = parse_feed(xml, "Example")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["url"], "https://example.org/convention")
        self.assertIsNotNone(updates[0]["published"])

    def test_malformed_feed_raises_parse_error(self):
        with self.assertRaises(Exception):
            parse_feed(b"<not-closed>", "Example")


if __name__ == "__main__":
    unittest.main()
