"""Minimal reference agent implementing the evaluator's text protocol (stdlib only).

    python examples/echo_agent.py   # serves http://localhost:8765/chat
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

SESSIONS: dict[str, int] = {}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        sid, msg = body.get("session_id", ""), body.get("message", "")
        n = SESSIONS[sid] = SESSIONS.get(sid, -1) + 1
        if n == 0:
            reply, end = "Hi, thanks for calling! How can I help you today?", False
        elif any(w in msg.lower() for w in ("bye", "goodbye")):
            reply, end = "Thanks for calling, goodbye!", True
        else:
            reply, end = f"Got it, you said: {msg} Is there anything else?", False
        data = json.dumps({"reply": reply, "end_call": end}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
