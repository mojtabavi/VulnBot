"""Explicit POMDP belief-state for the VulnBot belief agent.

╔══════════════════════════════════════════════════════════════════════════════╗
║  SCAFFOLD / STUB — Phase 2.1                                                    ║
║  This file defines the *interface* and the *belief data shape* only. The        ║
║  belief MATH (Bayesian update, reward, policy) is intentionally left as          ║
║  NotImplementedError for the thesis author to fill in Phases 2.2–2.5, or to      ║
║  be replaced wholesale by the author's own belief_state.py with the SAME public  ║
║  names. Nothing here branches on the hidden true state S — that is the point.    ║
╚══════════════════════════════════════════════════════════════════════════════╝

POMDP tuple  <S, A, O, T, Z, R, b, γ>  →  where it lives:
  S   hidden true config (OS/versions/vulns/access/honeypot). NEVER observed here;
      lab ground truth only.
  b   factored JSON belief over S. Produced by `new_belief` / `new_host_prior`,
      persisted by `belief_store.BeliefStore`.
  A   recon / exploit / lateral / privesc. Represented by `Action`; executed as
      tools in the kali container (Executor).
  O   raw tool output from kali. Passed into `update_belief` as `observation`.
  Z   P(O | hypothesis). Supplied by an LLM (per-hypothesis likelihoods) inside
      `update_belief`; the CODE normalizes (Bayes). Filled in Phase 2.2/2.3.
  T   effect of an action on state. Reasoned about inside `update_belief`.
  R   goal value − cost − detection risk. Computed by `score_action` (Phase 2.5).
  π   belief → action. `choose_action` (Phase 2.4).
  γ   discount factor. `GAMMA`.

Belief factoring (per host), all values are probabilities in [0, 1]:
  {
    "os":       {"linux": p, "windows": p, "other": p, "unknown": p},   # sums to 1
    "services": { "<port/name>": {"present": p, "absent": p} },         # each pair sums to 1
    "vulns":    { "<cve/id>":    {"present": p, "absent": p} },         # seeded from CVSS/
                                                                        #   exploit-maturity (2.5)
    "access":   {"none": p, "user": p, "root": p},                      # sums to 1
    "honeypot_likelihood": p,                                           # P(host is a honeypot)
  }
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "GAMMA", "OS_CLASSES", "ACCESS_LEVELS", "ActionType", "Action",
    "new_host_prior", "new_belief",
    "update_belief", "score_action", "choose_action", "run_agent",
]

# Discount factor γ for the (belief) MDP. Conventional default; author may tune.
GAMMA: float = 0.95

# OS hypothesis classes. "unknown" carries the "I don't know" mass in the b0 prior.
OS_CLASSES: tuple[str, ...] = ("linux", "windows", "other", "unknown")

# Access-level hypotheses on a host.
ACCESS_LEVELS: tuple[str, ...] = ("none", "user", "root")


# ── Actions (A) ───────────────────────────────────────────────────────────────
class ActionType:
    RECON = "recon"
    EXPLOIT = "exploit"
    LATERAL = "lateral"
    PRIVESC = "privesc"


@dataclass
class Action:
    """A candidate action the policy chooses among.

    `value`, `cost`, `detection_risk` are the reward ingredients R feeds on; they
    are populated from priors (exploit success-rate, honeypot likelihood) in
    Phase 2.5. `tool` / `params` describe how the Executor runs it (SSH or msfrpc).
    """
    name: str
    type: str                      # one of ActionType.*
    host: Optional[str] = None     # target host this action operates on
    tool: Optional[str] = None     # e.g. "nmap", or an msf module path
    params: Dict[str, Any] = field(default_factory=dict)
    value: float = 0.0             # goal value if it succeeds
    cost: float = 0.0              # time/effort cost
    detection_risk: float = 0.0    # P(detected) contribution (honeypot-aware)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Belief construction (b0 priors) ──────────────────────────────────────────
def new_host_prior(
    host: str,
    vuln_priors: Optional[Dict[str, float]] = None,
    service_priors: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Return the conventional b0 prior for a single host.

    These are *conventional priors, not measured data* (thesis §"where the numbers
    come from"): a uniform "I don't know" over OS, no access, low honeypot prior.
    `vuln_priors` (id -> P(present)) is seeded from public signals — CVSS / exploit
    maturity from CVE/ExploitDB — in Phase 2.5; here it is optional and defaults to
    empty. Bayes washes out imperfect priors after a few observations.
    """
    n = len(OS_CLASSES)
    os_dist = {k: 1.0 / n for k in OS_CLASSES}  # uniform: maximal ignorance

    services: Dict[str, Dict[str, float]] = {}
    for name, p in (service_priors or {}).items():
        services[name] = {"present": float(p), "absent": 1.0 - float(p)}

    vulns: Dict[str, Dict[str, float]] = {}
    for vid, p in (vuln_priors or {}).items():
        vulns[vid] = {"present": float(p), "absent": 1.0 - float(p)}

    return {
        "host": host,
        "os": os_dist,
        "services": services,
        "vulns": vulns,
        "access": {"none": 1.0, "user": 0.0, "root": 0.0},
        "honeypot_likelihood": 0.05,  # low conventional prior
    }


def new_belief(
    session_id: str,
    hosts: Optional[Sequence[str]] = None,
    vuln_priors: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Return a fresh factored belief b0 for a run/session.

    `hosts` may be empty at the start of recon; hosts are added as they are
    discovered (Phase 2.2). `vuln_priors` maps host -> {vuln_id: P(present)}.
    """
    hosts = list(hosts or [])
    vuln_priors = vuln_priors or {}
    return {
        "session_id": session_id,
        "step": 0,
        "hosts": {h: new_host_prior(h, vuln_priors.get(h)) for h in hosts},
        "meta": {"gamma": GAMMA},
    }


def add_host(belief: Dict[str, Any], host: str,
             vuln_priors: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Add a newly discovered host to the belief with its b0 prior (idempotent)."""
    b = copy.deepcopy(belief)
    if host not in b["hosts"]:
        b["hosts"][host] = new_host_prior(host, vuln_priors)
    return b


# ── Belief update (Z + Bayes), reward (R), policy (π) — AUTHOR FILLS ─────────
def update_belief(
    belief: Dict[str, Any],
    action: Action,
    observation: str,
    llm: Any = None,
    samples: int = 1,
) -> Dict[str, Any]:
    """Soft Bayesian belief update from observation O of `action`.

    CONTRACT (implement in Phase 2.2/2.3):
      1. Identify the belief factors `action`+`observation` bear on (e.g. the vuln
         targeted by an exploit, a service a scan probed, an OS a fingerprint saw).
      2. For each hypothesis value h of that factor, obtain the LIKELIHOOD
         Z = P(observation | h) FROM THE LLM (`llm`), not a hand-written table.
         Optionally average `samples` LLM calls (self-consistency) to de-noise.
      3. Posterior ∝ prior × Z; the CODE normalizes. This is a SOFT update:
         a failed exploit must move e.g. 0.70 → ~0.50, NEVER → 0. Z must be
         non-identity, and must satisfy  Z(fail|present) < Z(fail|absent).
      4. Return a NEW belief dict with `step` incremented; do not mutate in place.

    Must never read or branch on the hidden true state S.
    """
    raise NotImplementedError(
        "update_belief: implement the LLM-likelihood soft Bayesian update (Phase 2.2/2.3)."
    )


def score_action(action: Action, belief: Dict[str, Any]) -> float:
    """Reward R(action | belief) = goal value − cost − detection risk.

    CONTRACT (implement in Phase 2.5): combine `action.value` (weighted by the
    belief that it will succeed — e.g. P(target vuln present)), minus `action.cost`,
    minus a detection term driven by the target host's `honeypot_likelihood` and
    `action.detection_risk`. Return a scalar; higher is better.
    """
    raise NotImplementedError("score_action: implement R = value − cost − detection risk (Phase 2.5).")


def choose_action(candidates: Sequence[Action], belief: Dict[str, Any]) -> Action:
    """Policy π: pick the next action given the current belief.

    CONTRACT (implement in Phase 2.4): trade information gain (recon that sharpens
    b) against exploit value (`score_action`), e.g. argmax over candidates of a
    combination of expected info-gain and R. Replaces the deterministic PTG
    next-node pick. Must depend on `belief`.
    """
    raise NotImplementedError("choose_action: implement info-gain vs exploit-value policy (Phase 2.4).")


def run_agent(*args: Any, **kwargs: Any) -> Any:
    """Top-level belief-agent orchestration entry point (author-defined).

    Intended to loop: choose_action(belief) → execute in kali → observe O →
    update_belief(belief, action, O) → persist → repeat. Wired to the VulnBot
    Role loop / lab in later tasks.
    """
    raise NotImplementedError("run_agent: implement the belief-agent control loop.")
