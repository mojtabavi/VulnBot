"""Unified Observation schema — the O of the POMDP tuple, shared by R3 and R4.

ONE normalized result type crosses three boundaries, so it is defined once here:
  - R3 (Executor): every channel adapter (SSH / msfrpc / MCP) returns an `Observation`,
    regardless of whether the underlying tool gave raw stdout or a structured RPC result.
  - R1 (Belief Updater): `update_belief` consumes `observation.raw` as the observation O
    (the tool output the LLM observation model Z reasons over). `structured` is advisory.
  - R4 (JSON event log): `Observation.to_dict()` is appended verbatim as the `observation`
    event record — JSON on disk is the source of truth.

Deliberately stdlib-only (dataclasses + time), so it imports without the RAG/ML stack — the
same constraint `pomdp/belief_store.py` and `pomdp/priors.py` hold. Holds no offensive code:
it is a data envelope, never a tool runner.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

__all__ = ["Observation", "new_action_id"]

# Channel names an adapter may stamp on its result (R3). "none" = produced without a channel
# (e.g. a synthesized/empty observation); MCP is flag-gated and only appears when enabled.
CHANNELS = ("ssh", "msfrpc", "mcp", "none")


def new_action_id() -> str:
    """Short correlation id tying an Action → its Observation → its event-log records."""
    return uuid.uuid4().hex[:12]


@dataclass
class Observation:
    """The normalized result of running one Action through a channel.

    Fields:
      action_id    correlation id (see `new_action_id`); links Action ↔ Observation ↔ events.
      channel      which adapter produced it — one of CHANNELS (the router's choice, R3).
      action_type  the POMDP ActionType the observation bears on (recon/exploit/…).
      host         target host the action ran against (may be None during early recon).
      tool         the concrete tool / MSF module invoked (e.g. "nmap", "exploit/unix/ftp/…").
      raw          raw tool output — the observation O fed to the Belief Updater (never empty
                   for a real run; a failed/timed-out call still carries its stderr/notice here).
      structured   parsed result when the channel returns structure (msfrpc/MCP), else None.
      success      True/False for actions with a clear success signal (exploit landed?), or
                   None when not applicable (recon always "succeeds" in yielding an O).
      exit_code    process/RPC exit status when meaningful, else None.
      duration_ms  wall-clock cost of the call (feeds cost/analytics, not the belief math).
      error        short failure note when the channel errored (also mirrored into `raw` so the
                   Updater still sees *something*); None on success.
      ts           epoch seconds when the observation was produced.
    """
    action_id: str
    channel: str
    action_type: str
    raw: str = ""
    host: Optional[str] = None
    tool: Optional[str] = None
    structured: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-ready dict (the `observation` event record body, R4)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Observation":
        """Rebuild from `to_dict()` output; ignores unknown keys so the schema can grow."""
        allowed = cls.__dataclass_fields__.keys()  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in (d or {}).items() if k in allowed})

    @classmethod
    def failure(cls, action_id: str, channel: str, action_type: str, error: str,
                host: Optional[str] = None, tool: Optional[str] = None) -> "Observation":
        """A normalized failure Observation — `error` is also surfaced as `raw` so the Belief
        Updater still receives a (soft-softening) observation instead of an empty string."""
        return cls(action_id=action_id, channel=channel, action_type=action_type,
                   host=host, tool=tool, raw=error or "", success=False, error=error)
