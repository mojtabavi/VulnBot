"""TL-6.1 (automatable core) — end-to-end integration of R1–R4 with the REAL components:
the `BeliefAgent` loop (R1) driving a real `Executor` (R3) over a fake channel, writing a real
`EventLog` / belief trace (R4), gated by a real `ControlServer`/`ControlClient` over an actual
loopback socket (R2). Only the real Kali tool and the real LLM are faked — everything else is the
production code path. The live-lab run (real kali-tools container + LLM endpoint) stays a manual
check, like the octopus real-terminal verification.

Proves: events.jsonl is written with the full event sequence + a manifest; a FAILED exploit
*softens* the vuln belief (moves it down but never to zero — partial observability); and the HITL
approve round-trips over a real socket before the action runs.
"""
import json
import threading

from pomdp.belief_state import Action, ActionType
from pomdp.observation import Observation
from pomdp.belief_store import BeliefStore
from pomdp.agent import BeliefAgent
from executor.base import Executor, Channel
from utils.events import EventLog
from utils.control import ControlServer, ControlClient


class _FailingExploitChannel(Channel):
    """A real Channel that stands in for Kali: every exploit 'fails' (connection refused)."""
    name = "ssh"

    def supports(self, action):
        return True

    def run(self, action, action_id):
        return Observation(action_id=action_id, channel="ssh", action_type=action.type,
                           host=action.host, tool="exploit/x", raw="connection refused", success=False)

    def close(self):
        pass


def _failed_exploit_llm(_prompt):
    # Z for a FAILED exploit: the observation is far more expected if the vuln is ABSENT.
    return json.dumps({"present": 0.15, "absent": 0.85})


def _exploit_only(_belief):
    return [Action(name="CVE-2011-2523", type=ActionType.EXPLOIT, host="10.0.0.5",
                   params={"vuln": "CVE-2011-2523"})]


def test_e2e_hitl_logging_and_soft_update(tmp_path):
    events = EventLog("e2e-run", root=tmp_path / "runs")
    store = BeliefStore(root=tmp_path / "beliefs")
    executor = Executor([_FailingExploitChannel()], events=events)  # shared event log (R3+R4)

    server = ControlServer(announce=False)  # real loopback socket (R2)
    port = server.port

    # The "octopus CLI": connect, receive the approval_request, approve it.
    client_seen = {}

    def cli():
        c = ControlClient(port, timeout=5.0)
        client_seen["event"] = c.recv(timeout=5.0)  # the agent's approval_request frame
        c.send({"cmd": "approve"})
        c.close()

    t = threading.Thread(target=cli)
    t.start()
    assert server.wait_for_client(timeout=5.0), "control client did not connect"

    agent = BeliefAgent(executor, _failed_exploit_llm, store=store, events=events,
                        control=server, max_steps=1)
    belief = agent.run("e2e-run", hosts=["10.0.0.5"], vuln_ids=["CVE-2011-2523"],
                       candidates_fn=_exploit_only)
    t.join(timeout=5.0)
    server.close()

    # ── HITL: the CLI saw the approval request before the action ran ──
    assert client_seen.get("event", {}).get("event") == "approval_request"

    # ── R4: events.jsonl written with the full sequence + manifest ──
    recs = events.read_all()
    types = [r["type"] for r in recs]
    for t_ in ("run_start", "action_selected", "approval_request", "approval_result",
               "decision", "observation", "belief_update", "llm_likelihoods", "run_end"):
        assert t_ in types, f"missing event: {t_}"
    assert [r["seq"] for r in recs] == sorted(r["seq"] for r in recs), "seq monotonic"
    approved = [r for r in recs if r["type"] == "approval_result"][0]
    assert approved["approved"] is True, "the exploit was approved over the socket"
    route = [r for r in recs if r["type"] == "decision" and r.get("kind") == "route"][0]
    assert route["channel"] == "ssh"
    assert (events.dir / "manifest.json").is_file(), "run manifest written"

    # ── R1 partial observability: the failed exploit SOFTENED the vuln belief ──
    present = belief["hosts"]["10.0.0.5"]["vulns"]["CVE-2011-2523"]["present"]
    assert 0.0 < present < 0.95, f"failed exploit should soften the prior (0.95), got {present:.3f}"

    # ── belief trace persisted per step ──
    assert len(store.steps("e2e-run")) >= 2  # b0 + the post-exploit update
