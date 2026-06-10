import json
import sys
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """POST /history — 读取会话历史数据"""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            body = json.loads(body_bytes) if body_bytes else {}
        except (json.JSONDecodeError, ValueError):
            body = {}

        cid = body.get("conversation_id", "")
        if not cid:
            self._respond(200, {"conversation_id": "", "chat_history": [], "current_phase": "start"})
            return

        store = self.context.agent.store
        try:
            # 读取对话元信息（存储了 phase 和 cards）
            meta = store.get_conversation(conversation_id=cid)
            if meta and meta.metadata:
                # 读取消息历史
                messages = store.get_messages(conversation_id=cid, limit=100, order="asc")
                chat_history = []
                for m in messages:
                    meta_data = m.metadata or {}
                    if meta_data.get("type") == "init":
                        continue
                    # Skip ACTION: messages (internal control commands)
                    if m.content and m.content.startswith("ACTION:"):
                        continue
                    role = meta_data.get("agent", m.role)
                    chat_history.append({
                        "role": role,
                        "content": m.content,
                        "phase": meta_data.get("phase", ""),
                    })

                self._respond(200, {
                    "conversation_id": cid,
                    "chat_history": chat_history,
                    "current_phase": meta.metadata.get("current_phase", "start"),
                    "cards": meta.metadata.get("cards", {}),
                })
                return
        except Exception as e:
            print(f"[history] store error: {e}", file=sys.stderr, flush=True)

        # store 中没有数据
        self._respond(200, {"conversation_id": cid, "chat_history": [], "current_phase": "start"})

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
