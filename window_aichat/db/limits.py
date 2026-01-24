import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple


@dataclass
class RateLimitConfig:
    window_seconds: int = 60
    max_requests: int = 120


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> Tuple[bool, int, int]:
        now = time.time()
        window_start = now - self.config.window_seconds
        dq = self._hits[key]
        while dq and dq[0] < window_start:
            dq.popleft()
        if len(dq) >= self.config.max_requests:
            remaining = 0
            reset_in = int(max(0, dq[0] - window_start)) if dq else self.config.window_seconds
            return False, remaining, reset_in
        dq.append(now)
        remaining = self.config.max_requests - len(dq)
        reset_in = int(self.config.window_seconds)
        return True, remaining, reset_in

