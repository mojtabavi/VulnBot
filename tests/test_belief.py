"""Phase 2.3 — partial observability must be provably real.

These lock the four properties the thesis relies on (Sarraute 2013 objection answered
by an LLM observation model): the belief keeps mass on multiple hypotheses, the
observation model Z is NOT the identity, a failed observation SOFTENS (never zeroes)
belief, and the soft Bayesian update follows the DIRECTION/ORDER of the likelihoods.

A mock `llm` returns fixed per-hypothesis likelihoods (JSON), so no live LLM/kali is
needed. Only the direction/order of the likelihoods matters, not the decimals.
"""
import json

from pomdp.belief_state import (
    new_belief, Action, ActionType, update_belief, choose_action, score_action,
    EPS, OS_CLASSES,
)
from pomdp.priors import (
    enrich_action, reward_params, vuln_prior_present, seed_vuln_priors,
)


# ── mock observation models (return LIKELIHOODS only; code normalizes) ───────
def z_vuln(present, absent):
    return lambda _prompt: json.dumps({"present": present, "absent": absent})


def z_os(dist):
    return lambda _prompt: json.dumps(dist)


def _vuln_belief(p_present=0.7):
    b = new_belief("t", hosts=["h"])
    b["hosts"]["h"]["vulns"]["CVE-X"] = {"present": p_present, "absent": 1 - p_present}
    return b


def _exploit_action():
    return Action(name="exploit CVE-X", type=ActionType.EXPLOIT, host="h",
                  params={"factor": "vulns", "key": "CVE-X"})


def _recon_action():
    return Action(name="os fingerprint", type=ActionType.RECON, host="h", params={"factor": "os"})


# ── 1. failed observation SOFTENS, never zeroes ──────────────────────────────
def test_failed_exploit_softens_not_zeroes():
    b = _vuln_belief(0.70)
    # Z(fail|present) < Z(fail|absent): a failed exploit is less expected if the vuln is present.
    b2 = update_belief(b, _exploit_action(), "exploit completed, no session", llm=z_vuln(0.4, 0.7))
    p = b2["hosts"]["h"]["vulns"]["CVE-X"]["present"]
    assert 0.0 < p < 0.70, "must move down but stay > 0 (soft, not a boolean flag)"
    assert p > 0.45, "softens toward ~0.5, not a hard collapse toward 0"
    assert abs(sum(b2["hosts"]["h"]["vulns"]["CVE-X"].values()) - 1.0) < 1e-9
    assert b2["step"] == b["step"] + 1


def test_even_zero_likelihood_does_not_zero_belief():
    # Extreme: Z(present)=0 → still floored at EPS, so belief never collapses to exactly 0.
    b = _vuln_belief(0.70)
    b2 = update_belief(b, _exploit_action(), "definitive failure", llm=z_vuln(0.0, 1.0))
    p = b2["hosts"]["h"]["vulns"]["CVE-X"]["present"]
    assert p > 0.0, "EPS floor keeps a hypothesis alive even on a 0 likelihood"
    assert p < 0.05, "but it should become small"


# ── 2. multi-hypothesis mass retained ────────────────────────────────────────
def test_multi_hypothesis_mass_retained():
    b = new_belief("t", hosts=["h"])
    b2 = update_belief(b, _recon_action(), "nmap -O: Linux 2.6 (88%)",
                       llm=z_os({"linux": 0.6, "windows": 0.2, "other": 0.1, "unknown": 0.3}))
    os_post = b2["hosts"]["h"]["os"]
    assert abs(sum(os_post.values()) - 1.0) < 1e-9
    assert all(v > 0.0 for v in os_post.values()), "no hypothesis collapses to 0"
    assert sum(1 for v in os_post.values() if v > 0.05) >= 2, "mass stays on >1 hypothesis"
    assert set(os_post) == set(OS_CLASSES)


# ── 3. Z is not the identity ─────────────────────────────────────────────────
def test_Z_is_not_identity():
    # A uniform prior + non-uniform Z must change the belief (identity Z would leave it uniform).
    b = new_belief("t", hosts=["h"])
    before = dict(b["hosts"]["h"]["os"])
    b2 = update_belief(b, _recon_action(), "os hints",
                       llm=z_os({"linux": 0.7, "windows": 0.1, "other": 0.1, "unknown": 0.2}))
    after = b2["hosts"]["h"]["os"]
    assert after != before, "non-identity Z must move the belief"
    assert max(after.values()) < 1.0 and min(after.values()) > 0.0, "not a one-hot collapse"

    # A scan can MISS a present service: obs 'not found' still leaves present-belief > 0.
    b3 = new_belief("t", hosts=["h"])
    act = Action(name="scan 445", type=ActionType.RECON, host="h",
                 params={"factor": "services", "key": "445/smb"})
    b4 = update_belief(b3, act, "445 filtered / no response", llm=z_vuln(0.4, 0.7))
    present = b4["hosts"]["h"]["services"]["445/smb"]["present"]
    assert 0.0 < present < 0.5, "a miss lowers but does not eliminate a possibly-present service"


# ── 4. update follows the DIRECTION/ORDER of the likelihoods ─────────────────
def test_update_follows_likelihood_ordering():
    prior = 0.5
    # ordering we require for a FAILED observation:
    z_fail_present, z_fail_absent = 0.3, 0.8
    assert z_fail_present < z_fail_absent, "Z(fail|present) < Z(fail|absent)"

    down = update_belief(_vuln_belief(prior), _exploit_action(), "failed",
                         llm=z_vuln(z_fail_present, z_fail_absent))
    assert down["hosts"]["h"]["vulns"]["CVE-X"]["present"] < prior, "lower Z lowers the posterior"

    # reverse the ordering → belief must move the other way (sanity that direction is honored)
    up = update_belief(_vuln_belief(prior), _exploit_action(), "success-ish",
                       llm=z_vuln(0.8, 0.3))
    assert up["hosts"]["h"]["vulns"]["CVE-X"]["present"] > prior, "higher Z raises the posterior"


# ── input belief is never mutated in place ───────────────────────────────────
def test_update_does_not_mutate_input():
    b = _vuln_belief(0.70)
    snapshot = json.dumps(b, sort_keys=True)
    _ = update_belief(b, _exploit_action(), "obs", llm=z_vuln(0.4, 0.7))
    assert json.dumps(b, sort_keys=True) == snapshot, "update_belief must return a new belief"


# ── 5. policy π (choose_action): belief drives the recon-vs-exploit choice ────
def _recon_probe_action():
    # recon that would SHARPEN the same CVE-X vuln belief the exploit targets
    return Action(name="scan CVE-X", type=ActionType.RECON, host="h",
                  params={"factor": "vulns", "key": "CVE-X"})


def test_choose_action_recon_when_uncertain():
    # vuln belief is a coin-flip → info-gain from probing beats a 50/50 exploit.
    b = _vuln_belief(0.50)
    chosen = choose_action([_recon_probe_action(), _exploit_action()], b)
    assert chosen.type == ActionType.RECON, "uncertain vuln belief → recon (reduce uncertainty first)"


def test_choose_action_exploit_when_confident():
    # vuln belief is high → exploiting a likely-present vuln beats more recon.
    b = _vuln_belief(0.90)
    chosen = choose_action([_recon_probe_action(), _exploit_action()], b)
    assert chosen.type == ActionType.EXPLOIT, "confident vuln belief → exploit (stop reconning)"


def test_choose_action_belief_drives_choice():
    # DoD: SAME candidate set, DIFFERENT beliefs → DIFFERENT choice (π depends on b, not the PTG).
    cands = [_recon_probe_action(), _exploit_action()]
    pick_uncertain = choose_action(cands, _vuln_belief(0.50))
    pick_confident = choose_action(cands, _vuln_belief(0.90))
    assert pick_uncertain.type != pick_confident.type, "the belief, not the candidate list, decides"


def test_choose_action_does_not_mutate_belief():
    b = _vuln_belief(0.50)
    snapshot = json.dumps(b, sort_keys=True)
    _ = choose_action([_recon_probe_action(), _exploit_action()], b)
    assert json.dumps(b, sort_keys=True) == snapshot, "choose_action must not mutate the belief"


# ── 6. reward R (score_action) + priors source (Phase 2.5) ───────────────────
def test_priors_ordering_from_cvss_and_maturity():
    # a high-CVSS weaponized vuln → higher b0 prior, higher value, lower cost than an
    # immature low-CVSS one (only the ORDER must be right, not the decimals).
    assert vuln_prior_present(9.8, "weaponized") > vuln_prior_present(4.0, "unproven")
    hi = reward_params(9.8, "weaponized")
    lo = reward_params(4.0, "unproven")
    assert hi["value"] > lo["value"], "weaponized high-CVSS is worth more"
    assert hi["cost"] < lo["cost"], "immature exploit costs more to land"
    # priors stay in sane ranges
    assert 0.05 <= vuln_prior_present(9.8, "weaponized") <= 0.95


def test_enrich_action_fills_reward_fields_without_mutating():
    a = Action(name="exploit CVE-2011-2523", type=ActionType.EXPLOIT, host="h",
               params={"factor": "vulns", "key": "CVE-2011-2523"})
    ea = enrich_action(a)
    assert ea.value > 0 and ea.cost > 0 and ea.detection_risk > 0, "priors populate R inputs"
    assert (a.value, a.cost, a.detection_risk) == (0.0, 0.0, 0.0), "input action not mutated"
    seeds = seed_vuln_priors(["CVE-2011-2523", "CVE-does-not-exist"])
    assert 0.05 <= seeds["CVE-2011-2523"] <= 0.95 and "CVE-does-not-exist" not in seeds


def test_score_action_penalizes_detection_risk():
    # DoD: detection risk influences the choice. Same vuln belief on two hosts; one is a
    # likely honeypot → its exploit scores lower and is NOT chosen.
    b = new_belief("t", hosts=["clean", "pot"])
    for h in ("clean", "pot"):
        b["hosts"][h]["vulns"]["CVE-X"] = {"present": 0.9, "absent": 0.1}
    b["hosts"]["clean"]["honeypot_likelihood"] = 0.05
    b["hosts"]["pot"]["honeypot_likelihood"] = 0.80

    def _exp(host):
        return Action(name="exploit CVE-X", type=ActionType.EXPLOIT, host=host, value=0.9,
                      params={"factor": "vulns", "key": "CVE-X"})

    assert score_action(_exp("pot"), b) < score_action(_exp("clean"), b), "honeypot penalizes R"
    chosen = choose_action([_exp("pot"), _exp("clean")], b)
    assert chosen.host == "clean", "policy avoids the honeypot-suspected host"
