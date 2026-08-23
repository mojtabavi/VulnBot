"""Executor facade + Channel adapter interface (R3, TL-1.1).

ONE contract turns a POMDP `Action` into a normalized `Observation`:

    obs = Executor(channels).run(action)

Each execution channel (SSH, msfrpc, flag-gated MCP) implements `Channel`; the `Executor`
routes an action to the right channel, runs it, and guarantees a normalized `Observation`
back even on failure (so the Belief Updater always receives an O). The router policy
(TL-1.4) and per-channel timeout/retry/fallback (TL-1.5) refine the trivial defaults here.

`Action` is `pomdp.belief_state.Action`; `Observation` is `pomdp.observation.Observation`.
Both are stdlib-only, so this module imports without the RAG/ML stack.
"""
from __future__ import annotations

import abc
import time
from typing import Callable, List, Optional, Sequence

from pomdp.belief_state import Action
from pomdp.observation import Observation, new_action_id

__all__ = ["Channel", "Executor", "ChannelError", "Router"]


class ChannelError(Exception):
    """A channel could not run the action (unreachable, auth, RPC down). The Executor catches
    it and either falls back to another capable channel or returns a failure `Observation`."""


class Channel(abc.ABC):
    """One execution transport to Kali. Adapters: `ssh_channel` (1.2), `msf_channel` (1.3),
    `mcp_channel` (1.6). A channel MUST normalize its result into an `Observation` and MUST NOT
    let a tool failure escape as a bare exception unless the channel itself is unusable (raise
    `ChannelError` then, so the Executor can fall back)."""

    #: short stable name stamped onto `Observation.channel` ("ssh" | "msfrpc" | "mcp").
    name: str = "channel"

    @abc.abstractmethod
    def supports(self, action: Action) -> bool:
        """True if this channel can run `action` (e.g. msfrpc only for actions naming an MSF module)."""

    @abc.abstractmethod
    def run(self, action: Action, action_id: str) -> Observation:
        """Run `action` and return a normalized `Observation` stamped with `action_id`.
        Raise `ChannelError` only when the channel itself is unusable (→ Executor fallback)."""

    def close(self) -> None:  # optional; SSH holds a session, msfrpc an RPC client
        """Release any held resource (SSH session, RPC client). Best-effort."""


# A router maps (action, channels) → the ordered list of channels to try (primary first,
# then fallbacks). Defined as a plug point so TL-1.4 can drop in the real policy.
Router = Callable[[Action, Sequence["Channel"]], List["Channel"]]


def _default_router(action: Action, channels: Sequence[Channel]) -> List[Channel]:
    """Trivial default (TL-1.4 replaces): every channel that supports the action, registration
    order preserved. Keeps the facade usable + testable before the real policy lands."""
    return [c for c in channels if c.supports(action)]


class Executor:
    """Runs actions across pluggable channels behind `run(action) -> Observation`.

    - `channels`: the registered adapters (order = default preference).
    - `router`: picks the ordered candidate channels for an action (default: all that support it).
    The Executor times every call, stamps `action_id`/`channel`/`duration_ms`, and NEVER raises
    into its caller — a channel that raises `ChannelError` triggers fallback; if no channel
    succeeds it returns a failure `Observation` (so the belief loop always gets an O)."""

    def __init__(self, channels: Optional[Sequence[Channel]] = None, router: Optional[Router] = None):
        self.channels: List[Channel] = list(channels or [])
        self.router: Router = router or _default_router

    def register(self, channel: Channel) -> "Executor":
        self.channels.append(channel)
        return self

    def run(self, action: Action, action_id: Optional[str] = None) -> Observation:
        aid = action_id or new_action_id()
        candidates = self.router(action, self.channels)
        if not candidates:
            return Observation.failure(
                aid, "none", getattr(action, "type", "?"),
                error=f"no channel supports action {getattr(action, 'name', '?')!r}",
                host=getattr(action, "host", None),
            )

        errors: List[str] = []
        for ch in candidates:
            t0 = time.time()
            try:
                obs = ch.run(action, aid)
            except ChannelError as e:  # channel unusable → try the next capable one (TL-1.5 refines)
                errors.append(f"{ch.name}: {e}")
                continue
            except Exception as e:  # noqa: BLE001 - never let a channel bug escape the facade
                errors.append(f"{ch.name}: {type(e).__name__}: {e}")
                continue
            # stamp what the facade owns (channel may leave these unset)
            if not obs.channel or obs.channel == "none":
                obs.channel = ch.name
            if obs.duration_ms is None:
                obs.duration_ms = int((time.time() - t0) * 1000)
            obs.action_id = obs.action_id or aid
            return obs

        # every candidate channel was unusable → a normalized failure O, not an exception.
        return Observation.failure(
            aid, candidates[-1].name if candidates else "none", getattr(action, "type", "?"),
            error="; ".join(errors) or "all channels failed",
            host=getattr(action, "host", None),
        )

    def close(self) -> None:
        for ch in self.channels:
            try:
                ch.close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass
