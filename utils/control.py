"""Loopback control channel — the CLI↔agent back-channel for human-in-the-loop (R2).

The observability lanes are one-way (Python → stdout markers, Python → events.jsonl). HITL
needs the CLI to talk BACK: approve/deny a high-impact action before it runs, pause/resume,
step, quit. That is this module.

Boundary (see PLAN §"process boundary"):
  1. The agent process opens a `ControlServer` on `127.0.0.1:<ephemeral>` and announces the port
     via a `##OCTO## control|port=N` marker (`utils.progress.emit`).
  2. The octopus CLI reads that marker and connects (`cli/src/control.ts`, TL-4.1).
  3. Frames are newline-delimited JSON, both directions:
        agent → CLI : {"event": "approval_request", "action": "...", "risk": "high"} / {"event":"paused"}
        CLI → agent : {"cmd": "approve" | "deny" | "pause" | "resume" | "step" | "quit"}

This module is the TRANSPORT only (TL-0.3) — no approval gate yet; the gate that blocks a
high-impact action on a reply is wired in TL-4.4. Stdlib-only (socket + json). Best-effort:
if the CLI never connects, callers treat "no client" as "no HITL" and proceed (auto behavior),
so a missing front-end never blocks a run.
"""
from __future__ import annotations

import json
import socket
from typing import Any, Dict, Optional

from utils.progress import emit

__all__ = ["ControlServer", "ControlClient", "CONTROL_CMDS", "CONTROL_EVENTS"]

# Commands the CLI may send to the agent (validated where it matters; kept as data here).
CONTROL_CMDS = ("approve", "deny", "pause", "resume", "step", "quit")
# Events the agent may send to the CLI.
CONTROL_EVENTS = ("approval_request", "paused", "resumed")

_LOOPBACK = "127.0.0.1"


class _FramedConn:
    """Newline-delimited JSON framing over one connected socket (shared send/recv logic)."""

    def __init__(self, conn: socket.socket):
        self._conn = conn
        self._buf = b""

    def send(self, obj: Dict[str, Any]) -> bool:
        try:
            self._conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))
            return True
        except OSError:
            return False

    def recv(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Read one JSON frame; None on timeout, close, or a malformed line."""
        try:
            self._conn.settimeout(timeout)
            while b"\n" not in self._buf:
                chunk = self._conn.recv(4096)
                if not chunk:
                    return None  # peer closed
                self._buf += chunk
        except (socket.timeout, OSError):
            return None
        line, _, self._buf = self._buf.partition(b"\n")
        try:
            return json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def close(self) -> None:
        try:
            self._conn.close()
        except OSError:
            pass


class ControlServer:
    """Agent-side control endpoint: bind a loopback port, announce it, accept ONE CLI client.

    A run has a single front-end, so one client is enough. All methods are non-fatal — a run
    with no connected CLI simply gets `connected() is False` and proceeds without HITL.
    """

    def __init__(self, host: str = _LOOPBACK, announce: bool = True):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((host, 0))  # 0 → OS picks a free ephemeral port
        self._srv.listen(1)
        self.port: int = self._srv.getsockname()[1]
        self._client: Optional[_FramedConn] = None
        if announce:
            try:
                emit("control", port=self.port)  # ##OCTO## control|port=N — the CLI connects on this
            except Exception:  # noqa: BLE001 - announcing is best-effort
                pass

    def wait_for_client(self, timeout: Optional[float] = None) -> bool:
        """Block until the CLI connects (or `timeout`). Returns True once connected."""
        try:
            self._srv.settimeout(timeout)
            conn, _ = self._srv.accept()
        except (socket.timeout, OSError):
            return False
        self._client = _FramedConn(conn)
        return True

    def connected(self) -> bool:
        return self._client is not None

    def send(self, obj: Dict[str, Any]) -> bool:
        """Send one event frame to the CLI (agent → CLI). False if no client / send failed."""
        return self._client.send(obj) if self._client else False

    def recv(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Receive one command frame from the CLI (CLI → agent). None if no client / timeout."""
        return self._client.recv(timeout) if self._client else None

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        try:
            self._srv.close()
        except OSError:
            pass


class ControlClient:
    """Test/utility client (the real front-end is `cli/src/control.ts`). Connects to a port and
    exchanges the same newline-JSON frames."""

    def __init__(self, port: int, host: str = _LOOPBACK, timeout: Optional[float] = 2.0):
        self._conn = _FramedConn(socket.create_connection((host, port), timeout=timeout))

    def send(self, obj: Dict[str, Any]) -> bool:
        return self._conn.send(obj)

    def recv(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        return self._conn.recv(timeout)

    def close(self) -> None:
        self._conn.close()
