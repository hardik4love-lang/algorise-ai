"""
Cellular Bulkhead Isolation Pool (Phase 1 Resilience)
Isolates critical execution pools (e.g. ARIA conversational ingress vs.
Bounty Hunter asynchronous solver batch runs) to strictly prevent
memory exhaustion or worker starvation across cell boundaries.
"""

import concurrent.futures
from typing import Callable, Any

class BulkheadFullException(Exception):
    """Raised when the bulkhead capacity or queue is saturated."""
    pass

class CellularBulkhead:
    def __init__(self, name: str, max_workers: int = 8, max_queue_size: int = 32):
        self.name = name
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"bulkhead-{name}"
        )
        self._active_tasks = 0

    def submit(self, fn: Callable, *args, **kwargs) -> concurrent.futures.Future:
        if self._executor._work_queue.qsize() >= self.max_queue_size:
            raise BulkheadFullException(
                f"Bulkhead cell '{self.name}' queue is saturated (limit {self.max_queue_size})."
            )
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)
