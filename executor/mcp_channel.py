"""MCP channel — flag-gated, OFF by default (R3, TL-1.6).

Channel C of the Executor: an optional bridge to a Model-Context-Protocol tool server. It is
**disabled by default** (`OCTOPUS_MCP=0`) and stays a no-op until a specific server + version is
verified — the whole executor is fully functional on SSH + msfrpc alone (TL-1.2 / TL-1.3), so MCP
is strictly additive and never a dependency.

Gating, so the system is safe with MCP absent:
  - `OCTOPUS_MCP` unset / "0" / falsey  → `is_enabled()` is False → `supports()` returns False for
    every action → the router (TL-1.4) never routes here → pure no-op. SSH + msfrpc do everything.
  - `OCTOPUS_MCP` truthy → the channel offers itself only for actions that name an MCP tool, and
    `run()` FIRST verifies the configured server + version (`OCTOPUS_MCP_SERVER` /
    `OCTOPUS_MCP_VERSION`). Verification failure → `ChannelError` → the Executor falls back to a
    capable channel. Enabling the flag can never *break* a run; at worst it falls back.

This is deliberately a stub: it pins the capability/verification contract and the extension point
(`client_provider` builds the real MCP session) without shipping a half-wired transport. A future
task drops the concrete MCP client into `_run_tool` behind the same verification gate. Holds no
offensive code — it only forwards a named tool to an external server.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional

from executor.base import Channel, ChannelError
from pomdp.belief_state import Action
from pomdp.observation import Observation

_TRUTHY = ("1", "true", "yes", "on")


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUTHY


class McpChannel(Channel):
    """Flag-gated MCP tool bridge. Disabled unless `OCTOPUS_MCP` is truthy AND a server/version is
    verified. Only actions naming an MCP tool are ever offered here.

    Injection points for tests / a future real transport:
      - `verifier()` → truthy when the configured MCP server + version are present and acceptable.
        Default: both `OCTOPUS_MCP_SERVER` and `OCTOPUS_MCP_VERSION` are set (a placeholder check
        until a real handshake exists).
      - `client_provider()` → an object that actually runs an MCP tool. When omitted, `run()` raises
        `ChannelError` (the stub has no transport) and the Executor falls back — the SSH/msfrpc path
        stays sufficient.
    """

    name = "mcp"

    def __init__(self, client_provider: Optional[Callable[[], object]] = None,
                 verifier: Optional[Callable[[], bool]] = None):
        self._client_provider = client_provider
        self._verifier = verifier
        self._client: Optional[object] = None

    # ── gating ────────────────────────────────────────────────────────────────
    @staticmethod
    def is_enabled() -> bool:
        """True only when the operator has explicitly turned MCP on. Default OFF."""
        return _env_truthy("OCTOPUS_MCP")

    @staticmethod
    def _mcp_tool(action: Action) -> Optional[str]:
        """The MCP tool this action names, or None. `params['mcp_tool']` wins; otherwise a
        `mcp:<tool>` prefix on `action.tool`. A bare tool ("nmap") is NOT an MCP tool, so nothing
        gets misrouted here."""
        p = action.params or {}
        cand = p.get("mcp_tool")
        if cand:
            return str(cand)
        tool = action.tool or ""
        return tool.split(":", 1)[1] if tool.startswith("mcp:") else None

    def supports(self, action: Action) -> bool:
        # Disabled flag ⇒ invisible to the router. Enabled ⇒ only actions naming an MCP tool.
        return self.is_enabled() and self._mcp_tool(action) is not None

    # ── verification (before any real call) ───────────────────────────────────
    def _verify(self) -> None:
        """Confirm the exact server + version before enabling. Raise `ChannelError` (→ fallback)
        if it can't be verified — enabling the flag must never *break* a run."""
        ok = self._verifier() if self._verifier is not None else (
            bool(os.environ.get("OCTOPUS_MCP_SERVER")) and bool(os.environ.get("OCTOPUS_MCP_VERSION"))
        )
        if not ok:
            raise ChannelError(
                "mcp: server/version not verified "
                "(set OCTOPUS_MCP_SERVER + OCTOPUS_MCP_VERSION, or inject a verifier)"
            )

    # ── run ───────────────────────────────────────────────────────────────────
    def run(self, action: Action, action_id: str) -> Observation:
        if not self.is_enabled():
            # Defensive: the router shouldn't reach a disabled channel, but never pretend to run.
            return Observation.failure(
                action_id, self.name, action.type,
                error="mcp: channel disabled (OCTOPUS_MCP=0)",
                host=action.host, tool=action.tool,
            )
        tool = self._mcp_tool(action)
        if not tool:
            return Observation.failure(
                action_id, self.name, action.type,
                error="mcp: no MCP tool in action (expected params['mcp_tool'] or a 'mcp:' tool prefix)",
                host=action.host, tool=action.tool,
            )

        self._verify()  # raises ChannelError → Executor fallback if the server/version isn't confirmed

        if self._client_provider is None:
            # Stub: no real transport wired yet. Fall back (SSH/msfrpc are sufficient).
            raise ChannelError("mcp: no client transport configured (flag-gated stub)")

        return self._run_tool(action, action_id, tool)

    def _run_tool(self, action: Action, action_id: str, tool: str) -> Observation:
        """Drive the MCP tool via the injected client and normalize the result → Observation.
        The extension point for a real MCP transport; today it's exercised only by tests."""
        client = self._get_client()
        t0 = time.time()
        args: Dict[str, Any] = dict((action.params or {}).get("args") or {})
        try:
            result = client.call_tool(tool, args)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001 - mid-call failure → fall back to another channel
            raise ChannelError(f"mcp call failed on {tool!r}: {e}")

        structured: Dict[str, Any] = {"tool": tool, "args": args, "result": result}
        raw = f"Action: mcp {tool}\nArgs: {args or '(none)'}\nObservation: {result}"
        success: Optional[bool] = False if isinstance(result, dict) and result.get("error") else None
        return Observation(
            action_id=action_id, channel=self.name, action_type=action.type,
            host=action.host, tool=f"mcp:{tool}", raw=raw, structured=structured, success=success,
            duration_ms=int((time.time() - t0) * 1000),
        )

    def _get_client(self):
        if self._client is None and self._client_provider is not None:
            try:
                self._client = self._client_provider()
            except Exception as e:  # noqa: BLE001 - can't build the client → channel unusable (fallback)
                raise ChannelError(f"mcp client unavailable: {e}")
        return self._client

    def close(self) -> None:
        self._client = None
