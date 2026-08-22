"""Belief Store — persistence for the POMDP belief `b`.

Maps the Memory → Belief Store integration point: the factored JSON belief is saved
per step so a run produces an inspectable **belief trace** (Phase 2 DoD, Phase 4.2
export). Deliberately dependency-light (stdlib only) so it imports and tests without
the RAG/ML stack.

Layout (under PENTEST_ROOT/data/beliefs/<run_id>/):
    step_0000.json, step_0001.json, ...   # full belief snapshot per step
    latest.json                            # copy of the most recent step

Fully implemented here (this is decision-plumbing, not belief logic). The belief
CONTENT comes from belief_state.py.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["BeliefStore"]

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _default_root() -> Path:
    # Independent of config.config so this stays importable without the full stack.
    root = os.environ.get("PENTEST_ROOT", ".")
    return Path(root) / "data" / "beliefs"


def _safe_id(run_id: str) -> str:
    rid = _SAFE.sub("_", str(run_id)).strip("_")
    return rid or "default"


class BeliefStore:
    """Persist and reload factored-JSON beliefs per run, one file per step."""

    def __init__(self, root: Optional[os.PathLike | str] = None):
        self.root = Path(root) if root is not None else _default_root()

    # ── paths ────────────────────────────────────────────────────────────────
    def run_dir(self, run_id: str) -> Path:
        return self.root / _safe_id(run_id)

    def _step_path(self, run_id: str, step: int) -> Path:
        return self.run_dir(run_id) / f"step_{int(step):04d}.json"

    def _latest_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "latest.json"

    # ── write ────────────────────────────────────────────────────────────────
    def save(self, belief: Dict[str, Any], run_id: Optional[str] = None) -> Path:
        """Persist `belief` as the step given by belief['step'] (and as latest.json).

        `run_id` defaults to belief['session_id']. Returns the step file path.
        """
        rid = run_id or belief.get("session_id")
        if not rid:
            raise ValueError("save(): belief has no 'session_id' and no run_id was given")
        step = int(belief.get("step", 0))
        d = self.run_dir(rid)
        d.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(belief, indent=2, sort_keys=False, default=str)
        step_path = self._step_path(rid, step)
        step_path.write_text(payload, encoding="utf-8")
        self._latest_path(rid).write_text(payload, encoding="utf-8")
        return step_path

    # ── read ─────────────────────────────────────────────────────────────────
    def load_latest(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent belief for `run_id`, or None if nothing saved."""
        p = self._latest_path(run_id)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def load_step(self, run_id: str, step: int) -> Optional[Dict[str, Any]]:
        p = self._step_path(run_id, step)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def steps(self, run_id: str) -> List[int]:
        """Sorted list of persisted step numbers for `run_id`."""
        d = self.run_dir(run_id)
        if not d.is_dir():
            return []
        out = []
        for f in d.glob("step_*.json"):
            m = re.match(r"step_(\d+)\.json$", f.name)
            if m:
                out.append(int(m.group(1)))
        return sorted(out)

    def history(self, run_id: str) -> List[Dict[str, Any]]:
        """Full belief trace (all steps in order) for `run_id`."""
        return [self.load_step(run_id, s) for s in self.steps(run_id)]
