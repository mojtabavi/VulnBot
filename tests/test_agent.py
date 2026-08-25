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
