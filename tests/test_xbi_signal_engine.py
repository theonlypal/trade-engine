from datetime import datetime, timezone

from src.models import FDAEvent
from src import xbi_signal_engine


def make_event() -> FDAEvent:
    return FDAEvent(
        id="evt-1",
        raw_title="FDA approves breakthrough therapy",
        raw_text="The FDA approved a major therapy for oncology.",
        url="https://example.com/fda",
        published_at=datetime.now(timezone.utc),
    )


def test_analyze_returns_signal_for_positive(monkeypatch):
    event = make_event()

    def dummy_call(_):
        return {
            "companies": ["ABC"],
            "sentiment": "positive",
            "expected_move_pct": 1.5,
            "confidence": 0.9,
            "window_hours": 24,
            "narrative": "Strong approval likely to lift XBI.",
        }

    monkeypatch.setattr(xbi_signal_engine, "_call_openai_for_signal", dummy_call)
    signal = xbi_signal_engine.analyze_fda_event_for_xbi(event)
    assert signal is not None
    assert signal.sentiment == "positive"


def test_analyze_returns_none_for_neutral(monkeypatch):
    event = make_event()

    monkeypatch.setattr(
        xbi_signal_engine,
        "_call_openai_for_signal",
        lambda _: {
            "companies": [],
            "sentiment": "neutral",
            "expected_move_pct": 0.0,
            "confidence": 0.8,
            "window_hours": 6,
            "narrative": "No impact",
        },
    )
    assert xbi_signal_engine.analyze_fda_event_for_xbi(event) is None


def test_analyze_filters_small_move(monkeypatch):
    event = make_event()

    monkeypatch.setattr(
        xbi_signal_engine,
        "_call_openai_for_signal",
        lambda _: {
            "companies": ["XYZ"],
            "sentiment": "positive",
            "expected_move_pct": 0.1,
            "confidence": 0.9,
            "window_hours": 10,
            "narrative": "Tiny impact",
        },
    )
    assert xbi_signal_engine.analyze_fda_event_for_xbi(event) is None


def test_analyze_filters_low_confidence(monkeypatch):
    event = make_event()

    monkeypatch.setattr(
        xbi_signal_engine,
        "_call_openai_for_signal",
        lambda _: {
            "companies": ["XYZ"],
            "sentiment": "positive",
            "expected_move_pct": 2.0,
            "confidence": 0.1,
            "window_hours": 10,
            "narrative": "Uncertain",
        },
    )
    assert xbi_signal_engine.analyze_fda_event_for_xbi(event) is None
