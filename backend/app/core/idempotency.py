"""SupplyChain IQ - Idempotency Key Tracking for Sensitive State Changes."""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional, Tuple


class IdempotencyRecord:
    def __init__(self, key: str, status: str = "IN_PROGRESS"):
        self.key = key
        self.status = status
        self.created_at = datetime.now(timezone.utc)
        self.status_code: Optional[int] = None
        self.response_body: Optional[Any] = None


class IdempotencyStore:
    """Thread-safe in-memory idempotency store with TTL support."""

    def __init__(self):
        self._store: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def start_operation(self, key: str) -> Tuple[bool, Optional[IdempotencyRecord]]:
        """Atomically register a key.

        Returns (is_new, record). If is_new is False, record contains previous execution or in-progress state.
        """
        with self._lock:
            existing = self._store.get(key)
            if existing is not None:
                return False, existing
            new_record = IdempotencyRecord(key=key, status="IN_PROGRESS")
            self._store[key] = new_record
            return True, new_record

    def complete_operation(self, key: str, status_code: int, response_body: Any):
        """Mark an idempotency operation as completed with its response."""
        with self._lock:
            rec = self._store.get(key)
            if rec:
                rec.status = "COMPLETED"
                rec.status_code = status_code
                rec.response_body = response_body

    def release_operation(self, key: str):
        """Remove key upon failure so client can retry."""
        with self._lock:
            self._store.pop(key, None)

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        with self._lock:
            return self._store.get(key)

    def clear(self):
        with self._lock:
            self._store.clear()


# Global in-process idempotency registry
idempotency_store = IdempotencyStore()

