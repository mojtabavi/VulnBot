"""TL-2.6 — R1 belief-loop guarantees: self-consistency (Z averaging + variance reduction) and
the T-effect (the ACTION, not just the observation, decides which belief factor moves). Plus a
fakes-only smoke of the `BeliefAgent` loop. No real Kali / LLM / MySQL.
"""
import json
import statistics

from pomdp.belief_state import Action, ActionType, new_belief, update_belief
from pomdp.observation import Observation
from pomdp.belief_store import BeliefStore
from pomdp.agent import BeliefAgent


def _belief_with_vuln(vid="CVE-2011-2523", present=0.5):
    return new_belief("s", ["h"], {"h": {vid: present}})


def _z(present):
    """A Z-likelihood JSON with the given P(observation|present); absent is the complement."""
    return json.dumps({"present": present, "absent": 1.0 - present})


# ── self-consistency: samples>1 AVERAGES the Z likelihoods ──────────────────────
def test_samples_average_z():
    """With a prior of 0.5 and Z that alternates 0.9 / 0.1 per call, averaging two samples gives
    z_present ≈ 0.5 → posterior stays ≈ 0.5; a single sample (0.9) moves it to ≈ 0.9."""
    calls = {"n": 0}

    def alt_llm(_prompt):
        calls["n"] += 1
        return _z(0.9 if calls["n"] % 2 == 1 else 0.1)  # odd→0.9, even→0.1

    act = Action(name="CVE-2011-2523", type=ActionType.EXPLOIT, host="h", params={"vuln": "CVE-2011-2523"})

    calls["n"] = 0
    b1 = update_belief(_belief_with_vuln(), act, "obs", llm=alt_llm, samples=1)
    p1 = b1["hosts"]["h"]["vulns"]["CVE-2011-2523"]["present"]
    assert p1 > 0.8, f"single sample follows the one draw (0.9) → {p1:.3f}"

    calls["n"] = 0
    b2 = update_belief(_belief_with_vuln(), act, "obs", llm=alt_llm, samples=2)
    p2 = b2["hosts"]["h"]["vulns"]["CVE-2011-2523"]["present"]
    assert abs(p2 - 0.5) < 0.02, f"two samples average 0.9 and 0.1 → ~0.5 (got {p2:.3f})"


def test_samples_reduce_variance():
    """Across many independent updates driven by an alternating-noise Z, averaging 5 samples per
    update yields a far tighter spread of posteriors than a single noisy sample."""
    counter = {"n": 0}

    def noisy_llm(_prompt):
        counter["n"] += 1
        # deterministic alternating noise: consecutive calls swing 0.85 / 0.15
        return _z(0.85 if counter["n"] % 2 == 1 else 0.15)

    act = Action(name="CVE-2011-2523", type=ActionType.EXPLOIT, host="h", params={"vuln": "CVE-2011-2523"})

    def spread(samples, trials=40):
        out = []
        for _ in range(trials):
            b = update_belief(_belief_with_vuln(), act, "obs", llm=noisy_llm, samples=samples)
            out.append(b["hosts"]["h"]["vulns"]["CVE-2011-2523"]["present"])
        return statistics.pvariance(out)

    counter["n"] = 0
    var1 = spread(1)
    counter["n"] = 0
    var5 = spread(5)
    assert var5 < var1, f"5-sample variance {var5:.4f} should be < 1-sample variance {var1:.4f}"


# ── T-effect: the ACTION decides which belief factor the observation updates ─────
def test_action_type_determines_updated_factor():
    """Same observation, different action → different factor moves. An EXPLOIT naming a vuln
    updates hosts.h.vulns[vid] and leaves the OS distribution untouched; a RECON probing a service
    updates hosts.h.services[svc] and leaves that vuln untouched. This is the transition/observation
    routing (T) shaping the belief, not the raw text alone."""
    llm = lambda _p: _z(0.2)  # a "failed/absent-leaning" likelihood either way

    b0 = _belief_with_vuln(present=0.5)
    os0 = dict(b0["hosts"]["h"]["os"])

    exploit = Action(name="CVE-2011-2523", type=ActionType.EXPLOIT, host="h", params={"vuln": "CVE-2011-2523"})
    b_exp = update_belief(b0, exploit, "connection refused", llm=llm)
    assert b_exp["hosts"]["h"]["vulns"]["CVE-2011-2523"]["present"] < 0.5, "exploit moved the vuln factor"
    assert b_exp["hosts"]["h"]["os"] == os0, "exploit left the OS distribution untouched"

    recon = Action(name="scan", type=ActionType.RECON, host="h", params={"service": "ssh"})
    b_rec = update_belief(b0, recon, "22/tcp open ssh", llm=llm)
    assert "ssh" in b_rec["hosts"]["h"]["services"], "recon created/updated the service factor"
    assert b_rec["hosts"]["h"]["vulns"]["CVE-2011-2523"]["present"] == 0.5, "recon left the vuln factor untouched"


# ── loop smoke (fakes only) ──────────────────────────────────────────────────────
def test_belief_agent_loop_advances_and_persists(tmp_path):
    class FakeExec:
        def run(self, action, action_id=None):
            raw = "80/tcp open" if action.type == ActionType.RECON else "connection refused"
            return Observation(action_id="x", channel="ssh", action_type=action.type, host=action.host, raw=raw)

    store = BeliefStore(root=tmp_path)
    agent = BeliefAgent(FakeExec(), lambda _p: _z(0.3), store=store, max_steps=3)
    belief = agent.run("run-x", hosts=["10.0.0.5"], vuln_ids=["CVE-2011-2523"])
    assert belief["step"] >= 1
    assert len(store.steps("run-x")) >= 2  # b0 + at least one update persisted


# ── HITL approval gate (R2, TL-4.4) ──────────────────────────────────────────────
class _Fx:
    def __init__(self):
        self.ran = []

    def run(self, action, action_id=None):
        self.ran.append(action.name)
        return Observation(action_id="x", channel="ssh", action_type=action.type, host=action.host, raw="out")


class _Ctrl:
    """Scripted control server: `awaits` feeds blocking recv, `polls` feeds the non-blocking poll."""
    def __init__(self, awaits=None, polls=None, connected=True):
        self.awaits = list(awaits or [])
        self.polls = list(polls or [])
        self.sent = []
        self._c = connected

    def connected(self):
        return self._c

    def send(self, o):
        self.sent.append(o)
        return True

    def recv(self, timeout=None):
        if timeout == 0 or timeout == 0.0:
            return self.polls.pop(0) if self.polls else None
        return self.awaits.pop(0) if self.awaits else None


def _exploit_cands(_b):
    return [Action(name="pop", type=ActionType.EXPLOIT, host="h", params={"vuln": "x"})]


def _recon_cands(_b):
    return [Action(name="scan", type=ActionType.RECON, host="h", tool="nmap")]


def _mk(control, tmp_path, **kw):
    return BeliefAgent(_Fx(), lambda _p: _z(0.3), store=BeliefStore(root=tmp_path),
                       control=control, max_steps=kw.pop("max_steps", 1), **kw)


def test_gate_high_impact_approve_runs(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "approve"}])
    a = _mk(c, tmp_path)
    a.run("g1", hosts=["h"], candidates_fn=_exploit_cands)
    assert a.executor.ran == ["pop"]
    assert any(s.get("event") == "approval_request" for s in c.sent)


def test_gate_deny_skips(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "deny"}])
    a = _mk(c, tmp_path, max_steps=1)
    a.run("g2", hosts=["h"], candidates_fn=_exploit_cands)
    assert a.executor.ran == []


def test_gate_quit_stops(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "quit"}])
    a = _mk(c, tmp_path, max_steps=3)
    b = a.run("g3", hosts=["h"], candidates_fn=_exploit_cands)
    assert a.executor.ran == [] and b["step"] == 0


def test_gate_step_arms_step_mode(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "step"}])
    a = _mk(c, tmp_path)
    a.run("g4", hosts=["h"], candidates_fn=_exploit_cands)
    assert a.executor.ran == ["pop"] and a.step_mode is True


def test_gate_low_impact_auto_approves(tmp_path):
    c = _Ctrl()
    a = _mk(c, tmp_path)
    a.run("g5", hosts=["h"], candidates_fn=_recon_cands)
    assert a.executor.ran == ["scan"]
    assert not any(s.get("event") == "approval_request" for s in c.sent)


def test_gate_step_mode_gates_recon(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "approve"}])
    a = _mk(c, tmp_path, step=True)
    a.run("g6", hosts=["h"], candidates_fn=_recon_cands)
    assert any(s.get("event") == "approval_request" for s in c.sent)


def test_gate_pause_resume_between_steps(tmp_path):
    c = _Ctrl(awaits=[{"cmd": "resume"}], polls=[{"cmd": "pause"}])
    a = _mk(c, tmp_path)
    a.run("g7", hosts=["h"], candidates_fn=_recon_cands)
    assert {"event": "paused"} in c.sent and {"event": "resumed"} in c.sent
    assert a.executor.ran == ["scan"]


def test_gate_disconnected_control_never_blocks(tmp_path):
    c = _Ctrl(connected=False)
    a = _mk(c, tmp_path)
    a.run("g8", hosts=["h"], candidates_fn=_exploit_cands)
    assert a.executor.ran == ["pop"]  # high-impact but no client → auto-approve
