"""Poll Tuya event logs for new bird-detection events."""

import logging
import time

from .tuya_api import TuyaClient

logger = logging.getLogger(__name__)


class EventPoller:
    """Polls the Tuya event log API for new detection events."""

    def __init__(self, client: TuyaClient, poll_interval: int = 30) -> None:
        self.client = client
        self.poll_interval = poll_interval
        # Track the most recent event timestamp we've seen to avoid duplicates
        self._last_event_time: int = int(time.time() * 1000)

    def check_for_new_events(self) -> list[dict]:
        """Check for events newer than the last one we processed.

        Returns a list of new event dicts (may be empty).
        """
        now_ms = int(time.time() * 1000)
        events = self.client.get_event_logs(
            start_time_ms=self._last_event_time + 1,
            end_time_ms=now_ms,
            event_type="1",
            size=20,
        )

        if events:
            newest = max(e["event_time"] for e in events)
            self._last_event_time = newest
            logger.info("Found %d new event(s)", len(events))

        return events
