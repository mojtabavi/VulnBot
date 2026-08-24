"""SSH channel — arbitrary Kali tooling over the existing paramiko session (R3, TL-1.2).

Channel A of the Executor: runs nmap / enumeration / custom shell commands on kali-tools and
normalizes raw stdout into an `Observation` (`raw` = the observation O the Belief Updater reads).
It reuses the project's singleton SSH session (`actions/shell_manager.py::ShellManager` +
`actions/remote_shell.py::RemoteShell`) rather than opening its own — same auth (key in the docker
lab, else password), same session across the run.

The command(s) come from the `Action`: `params["command"]` (str) or `params["commands"]` (list),
else `action.tool` as a bare command. A missing command → a normalized failure Observation (the
Updater still gets an O); an unusable SSH session → `ChannelError` so the Executor can fall back.

`ShellManager` is imported LAZILY inside `_get_shell`, so importing this module needs neither
paramiko nor the config layer — and tests inject a fake shell via `shell_provider`.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional

from executor.base import Channel, ChannelError
from pomdp.belief_state import Action, ActionType
from pomdp.observation import Observation


class SshChannel(Channel):
    """Run an action's shell command(s) on Kali over SSH; raw stdout → Observation.

    `shell_provider` (optional) returns an object exposing `execute_cmd(cmd) -> str`; when omitted,
    the project `ShellManager` singleton supplies it. SSH is the universal channel (it can run any
    tool), so `supports` is True for everything — the router (TL-1.4) sets the preference order and
    keeps msfrpc as the primary for MSF-module actions.
    """

    name = "ssh"

    def __init__(self, shell_provider: Optional[Callable[[], object]] = None):
        self._shell_provider = shell_provider
        self._shell: Optional[object] = None

    def supports(self, action: Action) -> bool:
        return True

    def _get_shell(self):
        if self._shell is not None:
            return self._shell
        try:
            if self._shell_provider is not None:
                self._shell = self._shell_provider()
            else:  # lazy: only a live run needs paramiko + the Kali config
                from actions.shell_manager import ShellManager
                self._shell = ShellManager.get_instance().get_shell()
        except Exception as e:  # noqa: BLE001 - unreachable/misconfigured SSH → channel unusable (fallback)
            raise ChannelError(f"ssh unavailable: {e}")
        return self._shell

    @staticmethod
    def _commands(action: Action) -> List[str]:
        p = action.params or {}
        if p.get("commands"):
            return [str(c) for c in p["commands"]]
        if p.get("command"):
            return [str(p["command"])]
        if action.tool:
            return [str(action.tool)]
        return []

    def run(self, action: Action, action_id: str) -> Observation:
        cmds = self._commands(action)
        if not cmds:
            return Observation.failure(
                action_id, self.name, action.type,
                error="ssh: no command in action.params (expected 'command' or 'commands')",
                host=action.host, tool=action.tool,
            )
        shell = self._get_shell()  # raises ChannelError if the session is unusable → Executor fallback
        t0 = time.time()
        parts: List[str] = []
        for c in cmds:
            try:
                out = shell.execute_cmd(c)
            except Exception as e:  # noqa: BLE001 - a broken session mid-run → fall back
                raise ChannelError(f"ssh exec failed on {c!r}: {e}")
            # Keep the familiar "Action/Observation" shape the pipeline + Z prompt already expect.
            parts.append(f"Action:{c}\nObservation: {out}")
        raw = "\n".join(parts)
        tool = action.tool or (cmds[0].split()[0] if cmds and cmds[0].split() else None)
        # recon yields an O but has no intrinsic success flag → leave success=None (the Updater's Z decides).
        return Observation(
            action_id=action_id, channel=self.name, action_type=action.type,
            host=action.host, tool=tool, raw=raw, success=None,
            duration_ms=int((time.time() - t0) * 1000),
        )

    def close(self) -> None:
        # The ShellManager singleton owns the shared session (closed by the run's lifecycle); do not
        # tear it down here or we'd kill a session other channels/steps still use.
        self._shell = None
