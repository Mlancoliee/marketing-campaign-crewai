"""In-process FlowPersistence for pause/resume.

Sticky routing ensures same conversation_id → same instance → dict is reliable.
When the instance restarts, state is recovered from the external store
via load_pending_from_store() / sync_pending_to_store().
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from crewai.flow.async_feedback.types import PendingFeedbackContext
from crewai.flow.persistence.base import FlowPersistence

_state_store: dict[str, dict[str, Any]] = {}
_pending_store: dict[str, tuple[dict[str, Any], PendingFeedbackContext]] = {}


def _to_dict(state) -> dict[str, Any]:
    if isinstance(state, dict):
        return dict(state)
    if isinstance(state, BaseModel):
        return state.model_dump()
    return dict(state)


class PagesPersistence(FlowPersistence):
    """FlowPersistence backed by process-local dicts."""

    persistence_type: str = "pages-memory"

    def init_db(self) -> None:
        pass

    def save_state(self, flow_uuid: str, method_name: str, state_data) -> None:
        _state_store[flow_uuid] = _to_dict(state_data)

    def load_state(self, flow_uuid: str) -> dict[str, Any] | None:
        return _state_store.get(flow_uuid)

    def save_pending_feedback(self, flow_uuid: str, context, state_data) -> None:
        _pending_store[flow_uuid] = (_to_dict(state_data), context)

    def load_pending_feedback(self, flow_uuid: str):
        return _pending_store.get(flow_uuid)

    def clear_pending_feedback(self, flow_uuid: str) -> None:
        _pending_store.pop(flow_uuid, None)


_INSTANCE: PagesPersistence | None = None


def get_persistence() -> PagesPersistence:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PagesPersistence()
    return _INSTANCE


def has_pending(cid: str) -> bool:
    """Check if a conversation has pending feedback in memory."""
    return cid in _pending_store


# ─── External store sync (survives instance restarts) ───

FLOW_STATE_SUFFIX = ":flow_state"


async def load_pending_from_store(cid: str, store) -> bool:
    """Load pending state from external store into memory. Returns True if loaded."""
    if cid in _pending_store:
        return True
    state_cid = cid + FLOW_STATE_SUFFIX
    try:
        messages = await store.get_messages(
            conversation_id=state_cid, limit=1, order="desc"
        )
    except Exception:
        return False
    if not messages:
        return False
    try:
        data = json.loads(messages[0].content)
        state_data = data["state"]
        context = PendingFeedbackContext.from_dict(data["context"])
        _pending_store[cid] = (state_data, context)
        _state_store[cid] = state_data
        return True
    except (json.JSONDecodeError, KeyError, TypeError):
        return False


async def sync_pending_to_store(cid: str, store) -> None:
    """Sync in-memory pending state to external store.

    If pending exists: save it (append a message to virtual conversation).
    If not: clean up the virtual conversation (flow completed or errored).
    """
    state_cid = cid + FLOW_STATE_SUFFIX
    if cid in _pending_store:
        state_data, context = _pending_store[cid]
        data = {
            "state": _to_dict(state_data) if not isinstance(state_data, dict) else state_data,
            "context": context.to_dict(),
        }
        await store.append_message(
            conversation_id=state_cid, role="system",
            content=json.dumps(data, ensure_ascii=False),
        )
    else:
        try:
            await store.delete_conversation(conversation_id=state_cid)
        except Exception:
            pass
