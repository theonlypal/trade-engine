import json
from datetime import datetime, timedelta, timezone

import pytest

from src import fda_scraper
from src.fda_scraper import get_recent_fda_events, parse_fda_html


SAMPLE_HTML_TEMPLATE = """
<rss version="2.0">
  <channel>
    <title>FDA Press Announcements</title>
    <item>
      <title>FDA approves new therapy</title>
      <link>https://example.com/press/therapy</link>
      <guid isPermaLink="false">test-id</guid>
      <pubDate>{pub_date}</pubDate>
      <description>Important approval for a biotech firm.</description>
    </item>
  </channel>
</rss>
"""


def test_parse_fda_html_creates_events():
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    html = SAMPLE_HTML_TEMPLATE.format(pub_date=pub_date)
    events = parse_fda_html(html)
    assert events, "Expected at least one event from sample HTML"
    assert isinstance(events[0].published_at, datetime)


def test_get_recent_fda_events_respects_seen(monkeypatch, tmp_path):
    pub_date = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    html = SAMPLE_HTML_TEMPLATE.format(pub_date=pub_date)

    class DummyResponse:
        status_code = 200
        text = html

        def raise_for_status(self):
            return None

    seen_file = tmp_path / "seen.json"
    seen_file.write_text(json.dumps(["test-id"]))
    monkeypatch.setattr(fda_scraper, "SEEN_IDS_PATH", seen_file)
    monkeypatch.setattr(fda_scraper.requests, "get", lambda *_, **__: DummyResponse())

    events = get_recent_fda_events(hours_back=5)
    assert events == []
