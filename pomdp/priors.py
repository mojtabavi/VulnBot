"""Priors source (Phase 2.5): reward R ingredients from public exploit signals.

Feeds the belief agent's reward `R = P(succeeds|b)·value − cost − detection` and the b0
vuln priors from **CVSS + exploit-maturity** signals (CVE / ExploitDB style). These are the
thesis's *conventional priors, not measured data* — they need not be correct; Bayes washes
them out after a few observations (see `belief_state.update_belief`).

Design constraints (match the repo's hard rules):
  * **Stdlib-only, OFFLINE by design.** A small built-in catalog ships inline (committed);
    an optional local JSON override is read from `PENTEST_ROOT/data/priors/exploit_catalog.json`
    (git-ignored). NO network call is made — nothing here touches the attack path.
  * **No eager RAG import.** A live RAG/CVE lookup may enrich the catalog later via
    `merge_catalog(...)`, but `rag/` is heavy and import-coupled, so it is never imported here.
  * **Decision logic only** — no exploit code; just numbers that shape action choice.

Mapping (all outputs clamped to sane ranges):
  cvss ∈ [0,10], maturity ∈ MATURITY_WEIGHT  →
    prior_present  higher for a high-CVSS, weaponized vuln (seeds b0)
    value          goal value if the exploit lands (∝ cvss × maturity)
    cost           effort (higher when the exploit is immature)
    detection_risk noise the action makes (higher for a rough/immature exploit)
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, Optional

# Exploit maturity → weight in [0,1] (ExploitDB / CVSS-E style ordering).
MATURITY_WEIGHT: Dict[str, float] = {
    "weaponized": 1.0,   # reliable, public, metasploit module
    "high": 1.0,
    "functional": 0.75,  # works, some tuning
    "poc": 0.5,          # proof-of-concept only
    "proof-of-concept": 0.5,
    "unproven": 0.25,
    "none": 0.1,
    "unknown": 0.4,
}

# Built-in seed catalog (committed). Keyed by CVE id; values carry the public signals.
# Seeded with the metasploitable2 lab's well-known services so a real lab episode has priors.
BUILTIN_CATALOG: Dict[str, Dict[str, Any]] = {
    "CVE-2011-2523": {"cvss": 9.8, "maturity": "weaponized", "name": "vsftpd 2.3.4 backdoor"},
    "CVE-2007-2447": {"cvss": 9.8, "maturity": "weaponized", "name": "Samba usermap_script RCE"},
    "CVE-2010-2075": {"cvss": 9.8, "maturity": "weaponized", "name": "UnrealIRCd backdoor"},
    "CVE-2004-2687": {"cvss": 9.8, "maturity": "functional", "name": "distcc daemon RCE"},
    "CVE-1999-0502": {"cvss": 7.5, "maturity": "poc",        "name": "weak/default SSH creds"},
}

# Conservative default detection floors by action class (recon is quieter than exploiting).
_BASE_DETECTION = {"recon": 0.02, "exploit": 0.10, "lateral": 0.12, "privesc": 0.08}


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _maturity_w(maturity: Optional[str]) -> float:
    return MATURITY_WEIGHT.get((maturity or "unknown").strip().lower(), MATURITY_WEIGHT["unknown"])


def _catalog_path() -> str:
    root = os.environ.get("PENTEST_ROOT", ".")
    return os.path.join(root, "data", "priors", "exploit_catalog.json")


def load_catalog(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Built-in catalog, overlaid with an optional local JSON file (git-ignored).

    The local file lets an operator (or a later RAG/CVE enrichment step) extend/override
    priors without code changes. Missing/garbled file → built-in only (never raises).
    """
    cat = copy.deepcopy(BUILTIN_CATALOG)
    p = path or _catalog_path()
    try:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as fh:
                cat = merge_catalog(cat, json.load(fh))
    except Exception:  # noqa: BLE001 - priors are advisory, never fatal
        pass
    return cat


def merge_catalog(base: Dict[str, Dict[str, Any]],
                  extra: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Overlay `extra` onto `base` (per-CVE shallow merge). Enrichment hook for RAG/CVE."""
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict):
            out.setdefault(k, {}).update(v)
    return out


def vuln_prior_present(cvss: float, maturity: Optional[str]) -> float:
    """b0 prior P(vuln present) from CVSS + maturity. Conventional, clamped to [0.05, 0.95]."""
    w = _maturity_w(maturity)
    raw = 0.5 * (float(cvss) / 10.0) + 0.5 * w
    return _clamp(raw, 0.05, 0.95)


def reward_params(cvss: float, maturity: Optional[str],
                  action_type: str = "exploit") -> Dict[str, float]:
    """Return {value, cost, detection_risk} for an action from CVSS + maturity signals."""
    w = _maturity_w(maturity)
    c = float(cvss) / 10.0
    value = _clamp(c * (0.5 + 0.5 * w), 0.0, 1.0)          # high-impact + mature ⇒ worth more
    cost = _clamp(0.05 + 0.35 * (1.0 - w), 0.0, 1.0)        # immature ⇒ costlier to land
    base = _BASE_DETECTION.get(action_type, 0.10)
    detection = _clamp(base + 0.20 * (1.0 - w), 0.0, 1.0)   # rough exploits are noisier
    return {"value": round(value, 3), "cost": round(cost, 3), "detection_risk": round(detection, 3)}


def _vuln_id_of(action: Any) -> Optional[str]:
    """Best-effort extraction of a CVE/vuln id an action targets (params first, then name)."""
    params = getattr(action, "params", {}) or {}
    vid = params.get("vuln") or params.get("key")
    if vid:
        return str(vid)
    import re
    m = re.search(r"CVE-\d{4}-\d{4,7}", getattr(action, "name", "") or "", re.IGNORECASE)
    return m.group(0).upper() if m else None


def enrich_action(action: Any, catalog: Optional[Dict[str, Dict[str, Any]]] = None) -> Any:
    """Return a COPY of `action` with value/cost/detection_risk filled from priors.

    Looks up the action's target vuln in the catalog; if unknown, applies a conservative
    per-type default so R is still well-defined. Never mutates the input action.
    """
    from pomdp.belief_state import Action  # local import to avoid a cycle at module load
    cat = catalog if catalog is not None else load_catalog()
    a = copy.deepcopy(action)
    vid = _vuln_id_of(action)
    entry = cat.get(vid) if vid else None
    if entry is not None:
        rp = reward_params(entry.get("cvss", 5.0), entry.get("maturity"), getattr(a, "type", "exploit"))
    else:
        # unknown vuln: neutral value, conservative detection floor for the action class
        rp = {"value": 0.5, "cost": 0.1, "detection_risk": _BASE_DETECTION.get(getattr(a, "type", "exploit"), 0.10)}
    # only fill fields the caller left at their defaults (don't clobber explicit values)
    if not getattr(a, "value", 0.0):
        a.value = rp["value"]
    if not getattr(a, "cost", 0.0):
        a.cost = rp["cost"]
    if not getattr(a, "detection_risk", 0.0):
        a.detection_risk = rp["detection_risk"]
    return a


def seed_vuln_priors(vuln_ids, catalog: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
    """Map vuln ids → P(present) for `belief_state.new_belief(vuln_priors=...)` b0 seeding."""
    cat = catalog if catalog is not None else load_catalog()
    out: Dict[str, float] = {}
    for vid in (vuln_ids or []):
        entry = cat.get(vid)
        if entry is not None:
            out[vid] = vuln_prior_present(entry.get("cvss", 5.0), entry.get("maturity"))
    return out
