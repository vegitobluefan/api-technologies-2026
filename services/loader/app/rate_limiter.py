import threading, time

class RateLimiter:
    """Общий лимитер: не больше rps вызовов в секунду на процесс."""
    def __init__(self, rps: int):
        self.interval = 1.0 / rps
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if delay:
            time.sleep(delay)
