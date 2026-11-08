"""Talks to a team's agent over the text-mode HTTP protocol (see submissions/README.md)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx


@dataclass
class AgentTurn:
    reply: str
    end_call: bool
    latency_s: float
    error: str | None = None


class AgentClient:
    def __init__(self, endpoint: str, auth_env: str = "", timeout: float = 30):
        headers = {}
        if auth_env and os.environ.get(auth_env):
            headers["Authorization"] = f"Bearer {os.environ[auth_env]}"
        self.endpoint = endpoint
        self.http = httpx.Client(timeout=timeout, headers=headers)

    def send(self, session_id: str, message: str) -> AgentTurn:
        start = time.perf_counter()
        try:
            r = self.http.post(self.endpoint, json={"session_id": session_id, "message": message})
            latency = time.perf_counter() - start
            r.raise_for_status()
            body = r.json()
            return AgentTurn(str(body.get("reply", "")), bool(body.get("end_call", False)), latency)
        except (httpx.HTTPError, ValueError) as e:
            return AgentTurn("", True, time.perf_counter() - start, error=f"{type(e).__name__}: {e}")
