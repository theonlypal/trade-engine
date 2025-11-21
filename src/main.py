from __future__ import annotations

from .config import settings
from .fda_scraper import get_recent_fda_events
from .notify import send_signal_notification
from .xbi_signal_engine import analyze_fda_event_for_xbi


def main() -> None:
    events = get_recent_fda_events(hours_back=settings.fda_lookback_hours)
    if not events:
        print("No new FDA events found.")
        return

    for event in events:
        signal = analyze_fda_event_for_xbi(event)
        if signal is not None:
            send_signal_notification(signal, event)
            print(f"Sent signal for FDA event {event.id}")
        else:
            print(f"No actionable signal for FDA event {event.id}")


if __name__ == "__main__":
    main()
