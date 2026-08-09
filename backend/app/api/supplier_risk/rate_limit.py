"""Process-local bounded abuse control; gateway distribution remains deployment-owned."""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import RLock


class RateLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._entries: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = RLock()

    def admit(self, key: str, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        threshold = current - timedelta(minutes=1)
        with self._lock:
            entries = self._entries[key]
            while entries and entries[0] <= threshold:
                entries.popleft()
            if len(entries) >= self._limit:
                return False
            entries.append(current)
            return True
