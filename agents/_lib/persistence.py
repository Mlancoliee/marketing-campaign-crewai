"""
进程内 Flow 持久化（依赖 sticky routing）。
同一 conversation_id 路由到同一实例，state 和 pending feedback 存在内存中。
"""

_flow_states: dict[str, dict] = {}


def save_flow_state(conversation_id: str, state_dict: dict, pending_feedback: dict | None = None):
    _flow_states[conversation_id] = {
        "state": state_dict,
        "pending_feedback": pending_feedback,
    }


def load_flow_state(conversation_id: str) -> dict | None:
    return _flow_states.get(conversation_id)


def delete_flow_state(conversation_id: str):
    _flow_states.pop(conversation_id, None)
