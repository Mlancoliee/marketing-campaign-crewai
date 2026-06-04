import json
import sys
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """POST /delete — 删除会话数据（store + 内存）"""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            body = json.loads(body_bytes) if body_bytes else {}
        except (json.JSONDecodeError, ValueError):
            body = {}

        cid = body.get("conversation_id", "")
        if not cid:
            self._respond(400, {"error": "Missing conversation_id"})
            return

        store = self.context.agent.store
        try:
            store.delete_conversation(conversation_id=cid)
        except Exception as e:
            print(f"[delete] error: {e}", file=sys.stderr, flush=True)

        self._respond(200, {"deleted": True, "conversation_id": cid})

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
