"""
进程内状态持久化（依赖 sticky routing）。
同一 conversation_id 路由到同一实例，state 存在内存中。
"""

_states: dict[str, dict] = {}


def save_state(conversation_id: str, state_dict: dict, pending_feedback: dict | None = None):
    _states[conversation_id] = {
        "state": state_dict,
        "pending_feedback": pending_feedback,
    }


def load_state(conversation_id: str) -> dict | None:
    return _states.get(conversation_id)


def delete_state(conversation_id: str):
    _states.pop(conversation_id, None)
