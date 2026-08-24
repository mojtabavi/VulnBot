"""msfrpc channel — Metasploit modules over pymetasploit3 (R3, TL-1.3).

Channel B of the Executor: drives Metasploit exploit/auxiliary/post modules over msfrpcd's
RPC API and normalizes the **structured** RPC result into an `Observation`
(`structured` = the parsed module result; `raw` = a human/LLM-readable summary that the
Belief Updater reads as the observation O). Driving Metasploit over RPC is cleaner and more
robust than screen-scraping msfconsole over SSH, so MSF-module actions (exploit / lateral /
privesc that name a module) go through here instead of the SSH channel.

Which module to run comes from the `Action`: an `exploit/…`-style path in `action.params["module"]`
or `action.tool`. Options come from `action.params["options"]` (a dict), with `RHOSTS` defaulted
to `action.host`. No module named → a normalized failure Observation (the Updater still gets an O);
an unreachable msfrpcd → `ChannelError` so the Executor falls back to a capable channel (SSH).

`pymetasploit3` is imported LAZILY inside `_get_client`, so importing this module needs neither the
MSF client nor a live RPC endpoint — and tests inject a fake client via `client_provider`. Connection
params come from the environment (`.env`), never hard-coded. This module holds no offensive code of
its own; it only forwards a named module to the Kali-hosted Metasploit.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

from executor.base import Channel, ChannelError
from pomdp.belief_state import Action, ActionType
from pomdp.observation import Observation

# Action types that may legitimately be served by an MSF module. Recon stays on SSH.
_MSF_TYPES = (ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC)

# Recognized module-path prefixes → the pymetasploit3 module "type" argument.
_MODULE_PREFIXES = ("exploit", "auxiliary", "post", "encoder", "nop", "payload")


class MsfChannel(Channel):
    """Run an action's Metasploit module over msfrpc; structured RPC result → Observation.

    `client_provider` (optional) returns an object shaped like `pymetasploit3.msfrpc.MsfRpcClient`
    (needs `.modules.use(type, name)` → a module supporting `__setitem__` for options and
    `.execute(payload=…)` returning a dict). When omitted, a real `MsfRpcClient` is built from the
    environment on first use. Only actions that name an MSF module are supported; the router
    (TL-1.4) prefers this channel for those and leaves everything else to SSH.
    """

    name = "msfrpc"

    def __init__(self, client_provider: Optional[Callable[[], object]] = None):
        self._client_provider = client_provider
        self._client: Optional[object] = None

    # ── capability ────────────────────────────────────────────────────────────
    @staticmethod
    def _module_path(action: Action) -> Optional[str]:
        """The MSF module path this action names, or None. `params['module']` wins over `tool`.

        A bare tool like "nmap" is not a module path — only a "kind/rest" shape (an MSF prefix
        followed by a slash) counts, so SSH-style tool names never get misrouted to msfrpc.
        """
        p = action.params or {}
        cand = p.get("module") or action.tool
        if not cand:
            return None
        cand = str(cand)
        head = cand.split("/", 1)[0]
        return cand if ("/" in cand and head in _MODULE_PREFIXES) else None

    def supports(self, action: Action) -> bool:
        # Only exploit/lateral/privesc actions that actually name an MSF module belong here.
        return action.type in _MSF_TYPES and self._module_path(action) is not None

    # ── connection (lazy) ─────────────────────────────────────────────────────
    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            if self._client_provider is not None:
                self._client = self._client_provider()
            else:  # lazy: only a live MSF run needs pymetasploit3 + a reachable msfrpcd
                from pymetasploit3.msfrpc import MsfRpcClient
                password = os.environ.get("MSF_RPC_PASSWORD", "")
                if not password:
                    raise RuntimeError("MSF_RPC_PASSWORD not set in environment (.env)")
                self._client = MsfRpcClient(
                    password,
                    server=os.environ.get("KALI_HOST", "kali-tools"),
                    port=int(os.environ.get("MSF_RPC_PORT", "55553")),
                    ssl=False,
                )
        except Exception as e:  # noqa: BLE001 - unreachable/misconfigured msfrpcd → channel unusable (fallback)
            raise ChannelError(f"msfrpc unavailable: {e}")
        return self._client

    # ── run ───────────────────────────────────────────────────────────────────
    def run(self, action: Action, action_id: str) -> Observation:
        path = self._module_path(action)
        if not path:
            return Observation.failure(
                action_id, self.name, action.type,
                error="msfrpc: no MSF module in action (expected params['module'] or a module path in tool)",
                host=action.host, tool=action.tool,
            )
        mtype, modname = path.split("/", 1)  # e.g. "exploit", "unix/ftp/vsftpd_234_backdoor"

        client = self._get_client()  # raises ChannelError if msfrpcd is unreachable → Executor fallback
        t0 = time.time()

        # Build the options: caller-supplied, with RHOSTS defaulted to the action's target host.
        opts: Dict[str, Any] = dict((action.params or {}).get("options") or {})
        if action.host and not any(k.upper() in ("RHOSTS", "RHOST") for k in opts):
            opts["RHOSTS"] = action.host
        payload = (action.params or {}).get("payload")

        try:
            mod = client.modules.use(mtype, modname)
            for k, v in opts.items():
                mod[k] = v
            result = mod.execute(payload=payload) if payload else mod.execute()
        except Exception as e:  # noqa: BLE001 - a module/exec failure mid-run → fall back to another channel
            raise ChannelError(f"msfrpc exec failed on {path!r}: {e}")

        structured: Dict[str, Any] = {
            "module": path,
            "type": mtype,
            "options": opts,
            "payload": payload,
            "result": result,
        }
        # Keep the familiar "Action/Observation" shape the pipeline + Z prompt already expect.
        opt_str = ", ".join(f"{k}={v}" for k, v in opts.items()) or "(none)"
        raw = (
            f"Action: use {mtype} {modname}\n"
            f"Options: {opt_str}\n"
            f"Observation: {result}"
        )
        # A launched job/uuid is not a confirmed session; only an explicit error is a clear failure.
        # Otherwise leave success=None and let the Updater's Z reason over the result (like SSH recon).
        success: Optional[bool] = False if isinstance(result, dict) and result.get("error") else None
        return Observation(
            action_id=action_id, channel=self.name, action_type=action.type,
            host=action.host, tool=path, raw=raw, structured=structured, success=success,
            duration_ms=int((time.time() - t0) * 1000),
        )

    def close(self) -> None:
        # pymetasploit3 holds an RPC token; drop our handle so a fresh client is built if reused.
        # (No explicit logout — other channels/steps may share the same msfrpcd session.)
        self._client = None
