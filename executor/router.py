"""Channel-selection policy for the Executor (R3, TL-1.4).

Replaces the trivial `_default_router` in `executor/base.py`: instead of "every channel that
supports the action, in registration order", this picks a channel **by action type** and records
a human-readable justification.

Policy (mirrors the SSH-vs-msfrpc rule in `docs/INFRA.md` / `smoke_channels.py`):
  - **recon** (`ActionType.RECON`)                → SSH (nmap/enum/custom tooling; raw stdout = O).
  - **exploit / lateral / privesc** naming an MSF module → **msfrpc** first (structured RPC result),
    with SSH kept as a fallback for the same action if msfrpc is unusable.
  - **exploit / lateral / privesc** with NO module named → SSH (a hand-rolled exploit command).

The result is an ordered candidate list (primary first, then fallbacks) — the Executor tries them
in order, falling back on `ChannelError`. The chosen order + a one-line reason are exposed as a
`RouteDecision` (for tests) and, best-effort, mirrored as a `##OCTO## decision|…` marker so the
live RunView and the event log can show *why* a channel was picked. Routing itself is pure and
never raises into a run.

Stdlib-only apart from the lazy, best-effort `utils.progress.emit`; imports without the RAG stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from executor.base import Channel, Router
from pomdp.belief_state import Action, ActionType

__all__ = ["RouteDecision", "route", "channel_router"]

# Action types that prefer the Metasploit channel when a module is named.
_MSF_TYPES = (ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC)

# Channel names, matched against `Channel.name` (kept in sync with the adapters).
_MSF = "msfrpc"
_SSH = "ssh"


@dataclass
class RouteDecision:
    """The routing outcome: `ordered` channels to try (primary first) + why it was chosen."""

    ordered: List[Channel] = field(default_factory=list)
    reason: str = ""

    @property
    def primary(self) -> Optional[Channel]:
        return self.ordered[0] if self.ordered else None


def _rank_for(action: Action, name: str) -> int:
    """Preference rank for a channel `name` given the action (lower = tried first).

    exploit/lateral/privesc → msfrpc(0) before ssh(1); recon (and everything else) → ssh(0)
    before msfrpc(1). Unknown channel names sort last but stay usable as a final fallback.
    """
    if action.type in _MSF_TYPES:
        order = {_MSF: 0, _SSH: 1}
    else:  # recon and any non-offensive type: raw tooling over SSH
        order = {_SSH: 0, _MSF: 1}
    return order.get(name, 99)


def route(action: Action, channels: Sequence[Channel]) -> RouteDecision:
    """Pick the ordered candidate channels for `action` + a one-line justification (pure)."""
    supporting = [c for c in channels if c.supports(action)]
    if not supporting:
        return RouteDecision([], f"no channel supports {getattr(action, 'name', '?')!r} "
                                 f"(type={getattr(action.type, 'value', action.type)})")

    ordered = sorted(supporting, key=lambda c: (_rank_for(action, c.name), c.name))

    primary = ordered[0].name
    atype = getattr(action.type, "value", action.type)
    if action.type in _MSF_TYPES and primary == _MSF:
        why = f"{atype} action names an MSF module → msfrpc (structured RPC result)"
    elif action.type in _MSF_TYPES:
        why = f"{atype} action with no MSF module → {primary} (raw command)"
    else:
        why = f"{atype} action → {primary} (raw tooling over SSH)"
    if len(ordered) > 1:
        why += f"; fallback: {', '.join(c.name for c in ordered[1:])}"
    return RouteDecision(ordered, why)


def channel_router(emit: bool = True) -> Router:
    """Build a `Router` (the `Executor`'s plug point) from the policy above.

    When `emit` is set, each decision is mirrored best-effort as a `##OCTO## decision|…` marker so
    the live view / event log can surface the channel choice. Emission never breaks routing.
    """

    def _router(action: Action, channels: Sequence[Channel]) -> List[Channel]:
        decision = route(action, channels)
        if emit and decision.ordered:
            try:  # lazy + best-effort: routing must not depend on the marker sink
                from utils.progress import emit as _emit
                _emit("decision", kind="route", channel=decision.ordered[0].name,
                      reason=decision.reason)
            except Exception:  # noqa: BLE001 - a dead emit path never breaks a run
                pass
        return decision.ordered

    return _router
