"""Rate limiting: 600 запросов в минуту на токен.

Порог выставлен так, что руками его не достать: ни работой в Postman,
ни несколькими API-тестами. Совсем снимать нельзя — сервер один на всех.
Счётчик в памяти процесса: бэкенд работает одним инстансом.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from wallet.config import settings

_WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > _WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter(settings.rate_limit_per_minute)
