from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class FDAEvent:
    id: str
    raw_title: str
    raw_text: str
    url: str
    published_at: datetime


@dataclass
class XBISignal:
    fda_event_id: str
    companies: list[str]
    sentiment: Literal[
        "strong_positive", "positive", "neutral", "negative", "strong_negative"
    ]
    expected_move_pct: float
    confidence: float
    window_hours: int
    narrative: str
