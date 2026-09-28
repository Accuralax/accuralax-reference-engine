from __future__ import annotations
from dataclasses import dataclass
import random

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter: float = 0.0

    def __post_init__(self):
        if self.max_attempts < 1: raise ValueError("max_attempts_must_be_positive")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0: raise ValueError("delay_must_not_be_negative")
        if self.jitter < 0: raise ValueError("jitter_must_not_be_negative")

    def should_retry(self, attempt: int, *, retryable: bool) -> bool:
        return bool(retryable and 1 <= attempt < self.max_attempts)

    def delay(self, attempt: int, *, random_fn=random.random) -> float:
        if attempt < 1: raise ValueError("attempt_must_be_positive")
        raw=min(self.max_delay_seconds,self.base_delay_seconds*(2**(attempt-1)))
        return min(self.max_delay_seconds, raw + raw*self.jitter*random_fn()) if self.jitter else raw
