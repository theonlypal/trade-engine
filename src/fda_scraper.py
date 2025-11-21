from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .models import FDAEvent

API_URL = "https://api.fda.gov/drug/drugsfda.json"
RSS_URL = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feed-press-announcements"
SEEN_IDS_PATH = Path(".data/seen_fda_ids.json")

logger = logging.getLogger(__name__)


def parse_fda_html(html: str) -> List[FDAEvent]:
    """Parse RSS/HTML content from FDA feed into FDAEvent objects."""
    soup = BeautifulSoup(html, "xml")
    events: list[FDAEvent] = []
    for item in soup.find_all("item"):
        title_tag = item.find("title")
        description_tag = item.find("description")
        link_tag = item.find("link")
        guid_tag = item.find("guid")
        pub_date_tag = item.find("pubDate")

        if not title_tag or not link_tag or not pub_date_tag:
            continue

        raw_title = title_tag.get_text(strip=True)
        raw_text = description_tag.get_text(strip=True) if description_tag else ""
        url = link_tag.get_text(strip=True)
        pub_date_text = pub_date_tag.get_text(strip=True)
        try:
            published_at = date_parser.parse(pub_date_text)
            if published_at.tzinfo is not None:
                published_at = published_at.astimezone(timezone.utc)
            else:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to parse pubDate '%s': %s", pub_date_text, exc)
            continue

        event_id = guid_tag.get_text(strip=True) if guid_tag else url
        events.append(
            FDAEvent(
                id=event_id,
                raw_title=raw_title,
                raw_text=raw_text,
                url=url,
                published_at=published_at,
            )
        )
    return events


def parse_fda_json(data: dict) -> List[FDAEvent]:
    events: list[FDAEvent] = []
    results = data.get("results", []) if isinstance(data, dict) else []
    for result in results:
        app_number = result.get("application_number") or result.get("appl_no")
        sponsor = result.get("sponsor_name", "Unknown sponsor")
        submissions = result.get("submissions", [])
        submission_desc = "; ".join(
            filter(None, (sub.get("submission_type") for sub in submissions))
        )
        submission_dates = [
            sub.get("submission_status_date") for sub in submissions if sub.get("submission_status_date")
        ]
        for idx, product in enumerate(result.get("products", [])):
            brand = product.get("brand_name") or product.get("generic_name") or "Unknown"
            generic = product.get("generic_name") or ""
            raw_title = f"FDA approval update: {brand}"
            raw_text_parts = [
                f"Generic: {generic}" if generic else None,
                f"Sponsor: {sponsor}" if sponsor else None,
                f"Submission: {submission_desc}" if submission_desc else None,
            ]
            raw_text = ". ".join(part for part in raw_text_parts if part)

            approval_date = (
                product.get("approval_date")
                or result.get("approval_date")
                or (max(submission_dates) if submission_dates else None)
            )
            try:
                published_at = date_parser.parse(approval_date)
                if published_at.tzinfo is not None:
                    published_at = published_at.astimezone(timezone.utc)
                else:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            link_app = app_number or ""
            url = (
                f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={link_app}"
                if link_app
                else "https://www.fda.gov/"
            )
            event_id = f"{app_number}-{idx}" if app_number else f"{brand}-{idx}"

            events.append(
                FDAEvent(
                    id=event_id,
                    raw_title=raw_title,
                    raw_text=raw_text,
                    url=url,
                    published_at=published_at,
                )
            )
    return events


def _load_seen_ids(seen_path: Path) -> set[str]:
    if not seen_path.exists():
        return set()
    try:
        content = json.loads(seen_path.read_text())
        return set(content)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load seen IDs: %s", exc)
        return set()


def _persist_seen_ids(seen_path: Path, seen_ids: set[str]) -> None:
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen_ids), indent=2))


def get_recent_fda_events(hours_back: int) -> list[FDAEvent]:
    """Fetch and return FDA events within the last `hours_back` hours, skipping seen IDs."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    try:
        response = requests.get(
            API_URL,
            params={"limit": 50, "sort": "submissions.submission_status_date:desc"},
            timeout=15,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to fetch FDA feed: %s", exc)
        return []

    try:
        data = response.json()
        all_events = parse_fda_json(data)
    except Exception:
        all_events = parse_fda_html(response.text)
    recent_events = [event for event in all_events if event.published_at >= cutoff]

    seen_ids_path = SEEN_IDS_PATH
    seen_ids = _load_seen_ids(seen_ids_path)

    new_events = [event for event in recent_events if event.id not in seen_ids]

    if new_events:
        seen_ids.update(event.id for event in new_events)
        _persist_seen_ids(seen_ids_path, seen_ids)

    return new_events
