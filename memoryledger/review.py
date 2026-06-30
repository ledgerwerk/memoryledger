from __future__ import annotations

from .errors import MemoryledgerError
from .guardrails import validate_memory
from .models import STATUSES, Memory
from .storage import Store


def transition(store: Store, memory_id: str, status: str, reason: str) -> Memory:
    if status not in STATUSES:
        raise MemoryledgerError("INVALID_STATUS", f"Invalid status: {status}")
    if not reason.strip():
        raise MemoryledgerError("MISSING_REASON", "review transition requires a reason")
    memory = store.get(memory_id)
    content = store.read_content(memory_id)
    evidence = store.read_evidence(memory_id) + f"\nReview reason: {reason}\n"
    if status == "accepted":
        validate_memory(memory, content, evidence, store.config.root)
    return store.update_status(memory_id, status, reason)
