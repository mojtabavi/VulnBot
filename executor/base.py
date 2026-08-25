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
import threading
import time
from typing import Callable, List, Optional, Sequence

from pomdp.belief_state import Action
from pomdp.observation import Observation, new_action_id

__all__ = ["Channel", "Executor", "ChannelError", "ChannelTimeout", "Router"]


class ChannelError(Exception):
    """A channel could not run the action (unreachable, auth, RPC down). The Executor catches
    it and either falls back to another capable channel or returns a failure `Observation`.

    A plain `ChannelError` means the tool did NOT execute (connect/auth failed *before* the
    command ran), so retrying the same channel is safe."""


class ChannelTimeout(ChannelError):
    """The channel exceeded its time budget. Distinct from `ChannelError` because the tool may
    have *already started* — so a timed-out call is NEVER auto-retried (a non-idempotent
    exploit must not fire twice); the Executor falls straight through to the next channel."""


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
    """Fallback router: every channel that supports the action, registration order preserved.
    Used only if the real policy router (`executor.router`, TL-1.4) can't be imported."""
    return [c for c in channels if c.supports(action)]


def _note_fallback(obs: Observation, errors: Sequence[str]) -> None:
    """Record the failed attempts that preceded a successful call under a reserved meta key in
    `structured`, so the R4 event log shows the retry/fallback trail. Non-destructive and
    best-effort: `raw`/`error`/`success` of the winning Observation are left untouched."""
    try:
        meta = dict(obs.structured) if isinstance(obs.structured, dict) else {}
        meta["_executor_fallback"] = list(errors)
        obs.structured = meta
    except Exception:  # noqa: BLE001 - trail is diagnostics; never break the run over it
        pass


def _make_default_router() -> Router:
    """The Executor's default: the TL-1.4 policy router (channel by action type + logged
    justification). Lazy import avoids a circular dependency (router imports this module);
    if it's unavailable for any reason, fall back to `_default_router` so the facade still runs."""
    try:
        from executor.router import channel_router
        return channel_router()
    except Exception:  # noqa: BLE001 - never let router import break the Executor
        return _default_router


class Executor:
    """Runs actions across pluggable channels behind `run(action) -> Observation`.

    - `channels`: the registered adapters (order = default preference).
    - `router`: picks the ordered candidate channels for an action (default: the TL-1.4 policy).
    - `timeout_s`: per-attempt wall-clock budget (None = no timeout). Enforced in a daemon worker
      thread — a blocking channel that overruns raises `ChannelTimeout` and the facade falls
      through; the stuck thread is abandoned (best-effort, can't kill arbitrary blocking I/O).
    - `retries`: extra attempts on the SAME channel after a plain `ChannelError` (default 0).
      A `ChannelTimeout` is never retried (the tool may have started); a channel *bug* (any other
      exception) is never retried either — both fall straight to the next capable channel.

    The Executor times every call, stamps `action_id`/`channel`/`duration_ms`, and NEVER raises
    into its caller — an unusable channel triggers fallback; if no channel succeeds it returns a
    failure `Observation` (so the belief loop always gets an O). When a call only succeeds after a
    retry or fallback, the earlier failures are recorded under `structured["_executor_fallback"]`
    (a reserved meta key) so the JSON event log shows the trail without corrupting the result."""

    def __init__(self, channels: Optional[Sequence[Channel]] = None, router: Optional[Router] = None,
                 timeout_s: Optional[float] = None, retries: int = 0, events: Optional[Any] = None):
        self.channels: List[Channel] = list(channels or [])
        self.router: Router = router or _make_default_router()
        self.timeout_s: Optional[float] = timeout_s
        self.retries: int = max(0, int(retries))
        # Optional R4 event sink (a `utils.events.EventLog`, or anything with `.append(type, **f)`).
        # Pass the SAME instance the BeliefAgent uses so `seq` stays a single monotonic sequence.
        self.events: Optional[Any] = events

    def register(self, channel: Channel) -> "Executor":
        self.channels.append(channel)
        return self

    def run(self, action: Action, action_id: Optional[str] = None) -> Observation:
        aid = action_id or new_action_id()
        candidates = self.router(action, self.channels)
        cand_names = [getattr(c, "name", "?") for c in candidates]
        if not candidates:
            obs = Observation.failure(
                aid, "none", getattr(action, "type", "?"),
                error=f"no channel supports action {getattr(action, 'name', '?')!r}",
                host=getattr(action, "host", None),
            )
            self._emit_decision(aid, action, cand_names, obs, [])
            return obs

        errors: List[str] = []
        for ch in candidates:
            obs = self._try_channel(ch, action, aid, errors)
            if obs is not None:
                if errors:  # succeeded only after a retry/fallback — record the trail, don't clobber
                    _note_fallback(obs, errors)
                self._emit_decision(aid, action, cand_names, obs, errors)
                return obs

        # every candidate channel was unusable → a normalized failure O, not an exception.
        obs = Observation.failure(
            aid, candidates[-1].name if candidates else "none", getattr(action, "type", "?"),
            error="; ".join(errors) or "all channels failed",
            host=getattr(action, "host", None),
        )
        self._emit_decision(aid, action, cand_names, obs, errors)
        return obs

    def _emit_decision(self, aid: str, action: Action, candidates: List[str],
                       obs: Observation, errors: List[str]) -> None:
        """Record the routing outcome as an R4 `decision` event (kind=route): the candidate order,
        the channel that actually produced the O, whether it succeeded, and the retry/fallback trail.
        Best-effort — a dead sink must never break a run (mirrors the agent's `_emit`)."""
        ev = self.events
        if ev is None:
            return
        try:
            ev.append("decision", kind="route", action_id=aid,
                      action=getattr(action, "name", None), action_type=getattr(action, "type", None),
                      candidates=candidates, channel=obs.channel,
                      ok=(obs.error is None), attempts=list(errors) or None,
                      duration_ms=obs.duration_ms)
        except Exception:  # noqa: BLE001 - logging is best-effort, never fatal
            pass

    def _try_channel(self, ch: Channel, action: Action, aid: str, errors: List[str]) -> Optional[Observation]:
        """Run one channel with the timeout budget + safe retries. Returns a stamped Observation
        on success, or None if the channel is unusable (errors appended for the fallback trail)."""
        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            t0 = time.time()
            try:
                obs = self._call_with_timeout(ch, action, aid)
            except ChannelTimeout as e:  # tool may have started — DO NOT retry, fall through
                errors.append(f"{ch.name}: {e}")
                return None
            except ChannelError as e:  # unusable before the tool ran — safe to retry this channel
                errors.append(f"{ch.name}#{attempt}: {e}")
                continue
            except Exception as e:  # noqa: BLE001 - a channel bug: never retry, fall to next channel
                errors.append(f"{ch.name}: {type(e).__name__}: {e}")
                return None
            # stamp what the facade owns (channel may leave these unset)
            if not obs.channel or obs.channel == "none":
                obs.channel = ch.name
            if obs.duration_ms is None:
                obs.duration_ms = int((time.time() - t0) * 1000)
            obs.action_id = obs.action_id or aid
            return obs
        return None  # retries exhausted on ChannelError

    def _call_with_timeout(self, ch: Channel, action: Action, aid: str) -> Observation:
        """`ch.run` under the per-attempt budget. No budget → direct call. With a budget, run in a
        daemon thread and `join(timeout)`; overrun → `ChannelTimeout`. Exceptions from `ch.run`
        (incl. `ChannelError`) are re-raised in this thread so the caller's handlers see them."""
        if not self.timeout_s or self.timeout_s <= 0:
            return ch.run(action, aid)

        box: dict = {}

        def _target() -> None:
            try:
                box["obs"] = ch.run(action, aid)
            except BaseException as e:  # noqa: BLE001 - ferry any failure back to the caller thread
                box["exc"] = e

        t = threading.Thread(target=_target, name=f"exec-{ch.name}", daemon=True)
        t.start()
        t.join(self.timeout_s)
        if t.is_alive():  # overran the budget — abandon the (daemon) thread, fall through
            raise ChannelTimeout(f"timeout after {self.timeout_s:g}s")
        if "exc" in box:
            raise box["exc"]
        return box["obs"]

    def close(self) -> None:
        for ch in self.channels:
            try:
                ch.close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass
