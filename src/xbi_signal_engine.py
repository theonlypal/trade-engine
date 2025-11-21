from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from .config import settings
from .models import FDAEvent, XBISignal

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


def _call_openai_for_signal(event: FDAEvent) -> Dict[str, Any]:
    system_prompt = (
        "You are an expert biotech trading analyst focused on the XBI ETF."
        " Given an FDA announcement, estimate the market impact on XBI."
        " Respond ONLY with valid JSON matching the schema."
    )
    user_prompt = (
        "FDA Announcement Title: {title}\n"
        "FDA Announcement Text: {text}\n\n"
        "Return JSON with keys: companies (tickers if available), sentiment"
        " (one of strong_positive, positive, neutral, negative, strong_negative),"
        " expected_move_pct (float, negative allowed), window_hours (integer),"
        " confidence (0-1), and narrative (1-3 sentences)."
    ).format(title=event.raw_title, text=event.raw_text)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from OpenAI")
    return json.loads(content)


def analyze_fda_event_for_xbi(event: FDAEvent) -> Optional[XBISignal]:
    """Analyze a single FDA event and return an actionable XBISignal or None."""
    try:
        data = _call_openai_for_signal(event)
    except Exception as exc:
        logger.error("OpenAI analysis failed for %s: %s", event.id, exc)
        return None

    sentiment = data.get("sentiment")
    expected_move_pct = float(data.get("expected_move_pct", 0) or 0)
    confidence = float(data.get("confidence", 0) or 0)
    window_hours = int(data.get("window_hours", 0) or 0)
    companies = data.get("companies") or []
    narrative = data.get("narrative") or ""

    if sentiment == "neutral":
        return None
    if abs(expected_move_pct) < settings.min_expected_move:
        return None
    if confidence < settings.min_confidence:
        return None

    try:
        signal = XBISignal(
            fda_event_id=event.id,
            companies=list(companies),
            sentiment=sentiment,
            expected_move_pct=expected_move_pct,
            confidence=confidence,
            window_hours=window_hours,
            narrative=narrative,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to map response to XBISignal for %s: %s", event.id, exc)
        return None

    return signal
