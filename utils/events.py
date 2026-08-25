"""JSON event log — the on-disk source of truth for a run (R4 persistence).

Every meaningful thing the agent does is appended as ONE JSON record (one line) to
`PENTEST_ROOT/data/runs/<run_id>/events.jsonl`. The file is the authoritative log; the
Ink `LogView` (R4 presentation) tails it and renders each record human-friendly — the TUI
never shows the raw JSON. Records are also mirrored as a *compact* `##OCTO##` marker on
stdout (via `utils.progress.emit`) so the live status view has a lightweight heartbeat
without pushing large observation/LLM blobs through the stream.

Record shape (a tagged union keyed by `type`):
    {"ts": <epoch>, "run_id": <str>, "seq": <int>, "type": <EVENT_TYPES>, ...fields}

Deliberately stdlib-only (json + time + pathlib), matching `pomdp/belief_store.py`, so it
imports without the RAG/ML stack. Best-effort by contract: a logging failure must NEVER
break a pentest run (the belief/emit layers hold the same invariant).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.progress import emit

__all__ = ["EventLog", "EVENT_TYPES"]

# The tagged-union `type` values a record may carry. Mirrors the plan's TL-0.2 list; the LogView
# switches on these to pick a renderer. Kept as data (not an enum) to stay dependency-light.
EVENT_TYPES = (
    "run_start", "phase", "action_selected", "observation", "llm_likelihoods",
    "belief_update", "score", "decision", "approval_request", "approval_result",
    "error", "run_end",
)

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _default_root() -> Path:
    # Independent of config.config so this stays importable without the full stack (same rule as
    # belief_store._default_root). PENTEST_ROOT defaults to the repo root ".".
    root = os.environ.get("PENTEST_ROOT", ".")
    return Path(root) / "data" / "runs"


def _safe_id(run_id: str) -> str:
    rid = _SAFE.sub("_", str(run_id)).strip("_")
    return rid or "default"


class EventLog:
    """Append-only JSONL event log for one run, plus a compact live-marker mirror.

    One instance per run. `append(type, **fields)` is the only writer; `seq` orders the
    records so the LogView (and the belief trace) stay in lockstep even under fast writes.
    """

    def __init__(self, run_id: str, root: Optional[os.PathLike | str] = None):
        self.run_id = str(run_id)
        base = Path(root) if root is not None else _default_root()
        self.dir = base / _safe_id(self.run_id)
        self.path = self.dir / "events.jsonl"
        self._seq = 0
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001 - logging is best-effort, never fatal
            pass

    # ── write ────────────────────────────────────────────────────────────────
    def append(self, type: str, **fields: Any) -> Dict[str, Any]:
        """Append one JSON record and mirror a compact `event` marker. Returns the record.

        Never raises: a disk/serialize failure is swallowed so a run is never broken by
        logging. Non-JSON-serializable values fall back to `str` (default=str)."""
        self._seq += 1
        record: Dict[str, Any] = {
            "ts": time.time(), "run_id": self.run_id, "seq": self._seq, "type": type,
        }
        record.update(fields)
        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:  # noqa: BLE001 - never let logging break the run
            pass
        # Compact live mirror: only the type + seq (the LogView reads the full record from the
        # file). Keeps big observation/LLM payloads OUT of the stdout stream. emit is best-effort.
        try:
            emit("event", type=type, seq=self._seq)
        except Exception:  # noqa: BLE001
            pass
        return record

    # ── manifest (R4, TL-3.3) ─────────────────────────────────────────────────
    def write_manifest(self, belief_dir: Optional[os.PathLike | str] = None,
                       steps: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Write `data/runs/<run_id>/manifest.json` — the ONE discoverable entry point for a run,
        pointing at the event log and the belief trace so a reader (the LogView, a post-run tool)
        can find both from one file. Idempotent (rewritten on each call). Best-effort: a write
        failure is swallowed, never breaking the run."""
        manifest: Dict[str, Any] = {
            "run_id": self.run_id,
            "events": self.path.name,                # "events.jsonl", relative to this dir
            "event_count": self._seq,
            "belief_trace": str(belief_dir) if belief_dir else None,
            "belief_latest": str(Path(belief_dir) / "latest.json") if belief_dir else None,
            "steps": steps,
            "updated": time.time(),
        }
        if extra:
            manifest.update(extra)
        try:
            (self.dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception:  # noqa: BLE001 - manifest is a convenience, never fatal
            pass
        return manifest

    # ── read (tests / CLI fallback) ──────────────────────────────────────────
    def read_all(self) -> List[Dict[str, Any]]:
        """Return every record in order (skips any partial/corrupt trailing line)."""
        out: List[Dict[str, Any]] = []
        if not self.path.is_file():
            return out
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a torn last line during a concurrent tail — skip it
        return out
