from __future__ import annotations

import logging

import requests

from .config import settings
from .models import FDAEvent, XBISignal

logger = logging.getLogger(__name__)


def send_signal_notification(signal: XBISignal, event: FDAEvent) -> None:
    """Send an actionable signal to ntfy.sh"""
    direction = "UP" if signal.expected_move_pct > 0 else "DOWN"
    body_lines = [
        f"XBI SIGNAL: {direction} ({signal.expected_move_pct:+.2f}% expected)",
        f"Confidence: {signal.confidence:.2f}",
        f"Window: next {signal.window_hours} hours",
        f"Companies: {', '.join(signal.companies) if signal.companies else 'Unknown'}",
        f"Event: {event.raw_title}",
        f"URL: {event.url}",
        "Narrative:",
        signal.narrative,
    ]
    body = "\n".join(body_lines)

    headers = {"X-Title": "T0AE XBI Signal"}
    try:
        response = requests.post(settings.ntfy_topic_url, data=body.encode(), headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to send ntfy notification: %s", exc)
