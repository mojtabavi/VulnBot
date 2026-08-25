"""TL-1.7 — the Executor layer (R3): router policy, Observation normalization, and
timeout/retry/fallback robustness. All with fake channels — never touches a real Kali,
msfrpcd, or MCP server.

Locks the contracts the belief loop (R1) and the event log (R4) depend on:
  - the router picks msfrpc for offensive actions naming a module, ssh otherwise/for recon;
  - every channel result is a normalized `Observation` stamped with channel/action_id/duration;
  - a channel that raises `ChannelError` triggers fallback and the facade NEVER raises;
  - timeouts fall through (and are not auto-retried), plain `ChannelError` is retried;
  - the MCP channel is a flag-gated no-op unless explicitly enabled + verified.
"""
import time

import pytest

from pomdp.belief_state import Action, ActionType
from pomdp.observation import Observation
from executor.base import Executor, Channel, ChannelError, ChannelTimeout
from executor.router import route, channel_router
from executor.mcp_channel import McpChannel


# ── fakes ──────────────────────────────────────────────────────────────────────
class FakeChannel(Channel):
    """A channel supporting a fixed set of action types; records that it ran."""
    def __init__(self, name, types, raw="ok"):
        self.name = name
        self._types = set(types)
        self._raw = raw
        self.ran = False

    def supports(self, action):
        return action.type in self._types

    def run(self, action, action_id):
        self.ran = True
        return Observation(action_id=action_id, channel=self.name, action_type=action.type,
                           host=action.host, raw=self._raw)

    def close(self):
        pass


class Flaky(Channel):
    """Raises `err_cls` for the first `fail_n` calls, then succeeds. Counts calls."""
    def __init__(self, name, fail_n=0, err_cls=ChannelError, types=(ActionType.RECON, ActionType.EXPLOIT)):
        self.name = name
        self.fail_n = fail_n
        self.err_cls = err_cls
        self.calls = 0
        self._types = set(types)

    def supports(self, action):
        return action.type in self._types

    def run(self, action, action_id):
        self.calls += 1
        if self.calls <= self.fail_n:
            raise self.err_cls(f"{self.name} down (call {self.calls})")
        return Observation(action_id=action_id, channel=self.name, action_type=action.type,
                           host=action.host, raw="ok")

    def close(self):
        pass


class Slow(Channel):
    """Blocks `secs` before returning. Counts calls (proves no auto-retry on timeout)."""
    def __init__(self, name, secs, types=(ActionType.RECON, ActionType.EXPLOIT)):
        self.name = name
        self.secs = secs
        self.calls = 0
        self._types = set(types)

    def supports(self, action):
        return action.type in self._types

    def run(self, action, action_id):
        self.calls += 1
        time.sleep(self.secs)
        return Observation(action_id=action_id, channel=self.name, action_type=action.type,
                           host=action.host, raw="slow-ok")

    def close(self):
        pass


_ALL = (ActionType.RECON, ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC)
_OFFENSIVE = (ActionType.EXPLOIT, ActionType.LATERAL, ActionType.PRIVESC)


def ssh():
    return FakeChannel("ssh", _ALL, raw="ssh ran")


def msf():
    return FakeChannel("msfrpc", _OFFENSIVE, raw="msf ran")


def recon_action():
    return Action(name="scan", type=ActionType.RECON, host="target", tool="nmap")


def exploit_action():
    return Action(name="pop", type=ActionType.EXPLOIT, host="target",
                  params={"module": "exploit/unix/ftp/vsftpd_234_backdoor"})


# ── router policy (TL-1.4) ─────────────────────────────────────────────────────
def test_router_recon_prefers_ssh():
    d = route(recon_action(), [ssh(), msf()])
    assert d.primary.name == "ssh"
    assert "SSH" in d.reason


def test_router_exploit_prefers_msfrpc_regardless_of_registration_order():
    # ssh registered first, but msfrpc must outrank it for an offensive action naming a module.
    d = route(exploit_action(), [ssh(), msf()])
    assert [c.name for c in d.ordered] == ["msfrpc", "ssh"]
    assert "fallback: ssh" in d.reason


def test_router_exploit_with_only_ssh_falls_to_ssh():
    d = route(exploit_action(), [ssh()])
    assert d.primary.name == "ssh" and len(d.ordered) == 1


def test_router_no_supporting_channel_is_empty():
    # a channel that supports nothing → no candidates, reason explains.
    none_ch = FakeChannel("none", ())
    d = route(exploit_action(), [none_ch])
    assert d.ordered == [] and "no channel supports" in d.reason


def test_channel_router_returns_ordered_list():
    r = channel_router(emit=False)
    assert [c.name for c in r(exploit_action(), [ssh(), msf()])] == ["msfrpc", "ssh"]


# ── Executor default routing + normalization ───────────────────────────────────
def test_executor_routes_exploit_to_msfrpc():
    s, m = ssh(), msf()
    obs = Executor([s, m]).run(exploit_action(), "aid1")
    assert obs.channel == "msfrpc" and m.ran and not s.ran


def test_executor_routes_recon_to_ssh():
    s, m = ssh(), msf()
    obs = Executor([s, m]).run(recon_action(), "aid2")
    assert obs.channel == "ssh" and s.ran and not m.ran


def test_executor_stamps_channel_and_duration_and_action_id():
    obs = Executor([ssh()]).run(recon_action(), "aid3")
    assert obs.channel == "ssh"
    assert obs.action_id == "aid3"
    assert obs.duration_ms is not None and obs.duration_ms >= 0


def test_executor_generates_action_id_when_absent():
    obs = Executor([ssh()]).run(recon_action())
    assert obs.action_id and len(obs.action_id) >= 8


def test_executor_no_capable_channel_returns_failure_observation():
    # msfrpc can't serve recon → no candidate → normalized failure O, not a raise.
    obs = Executor([msf()]).run(recon_action(), "aid4")
    assert obs.success is False and "no channel supports" in (obs.error or "")


# ── fallback / retry / timeout (TL-1.5) ────────────────────────────────────────
def test_channel_error_retried_on_same_channel():
    f = Flaky("ssh", fail_n=1)
    obs = Executor([f], router=lambda a, cs: list(cs), retries=2).run(recon_action(), "aid5")
    assert obs.raw == "ok" and f.calls == 2


def test_retry_records_fallback_trail_in_structured():
    f = Flaky("ssh", fail_n=1)
    obs = Executor([f], router=lambda a, cs: list(cs), retries=2).run(recon_action(), "aid6")
    assert isinstance(obs.structured, dict) and "_executor_fallback" in obs.structured


def test_exhausted_retries_fall_back_to_next_channel():
    bad = Flaky("ssh", fail_n=5)
    good = Flaky("msfrpc", fail_n=0)
    obs = Executor([bad, good], router=lambda a, cs: list(cs), retries=1).run(recon_action(), "aid7")
    assert obs.channel == "msfrpc" and bad.calls == 2  # 1 + 1 retry, then fell back


def test_all_channels_dead_returns_failure_never_raises():
    bad = Flaky("ssh", fail_n=9)
    obs = Executor([bad], router=lambda a, cs: list(cs), retries=1).run(recon_action(), "aid8")
    assert obs.success is False and "ssh" in (obs.error or "")


def test_clean_success_has_no_fallback_trail():
    obs = Executor([Flaky("ssh", fail_n=0)], router=lambda a, cs: list(cs), retries=2).run(recon_action())
    assert obs.structured is None or "_executor_fallback" not in (obs.structured or {})


def test_timeout_falls_through_without_retry():
    slow = Slow("ssh", 1.0)
    fast = Flaky("msfrpc", fail_n=0)
    ex = Executor([slow, fast], router=lambda a, cs: list(cs), timeout_s=0.2, retries=3)
    t0 = time.time()
    obs = ex.run(recon_action(), "aid9")
    dt = time.time() - t0
    assert obs.channel == "msfrpc"        # fell back off the slow channel
    assert slow.calls == 1                # NOT auto-retried despite retries=3
    assert dt < 0.9                       # did not block the full 1.0s


def test_no_timeout_runs_to_completion():
    obs = Executor([Slow("ssh", 0.1)], router=lambda a, cs: list(cs)).run(recon_action())
    assert obs.raw == "slow-ok" and obs.duration_ms is not None


def test_channel_timeout_is_a_channel_error_subclass():
    assert issubclass(ChannelTimeout, ChannelError)


# ── event wiring (R4, TL-3.1) ───────────────────────────────────────────────────
class _RecEvents:
    """Minimal EventLog stand-in capturing (type, fields) appends."""
    def __init__(self):
        self.records = []

    def append(self, type, **fields):
        self.records.append({"type": type, **fields})


def test_executor_emits_route_decision_event():
    ev = _RecEvents()
    Executor([ssh(), msf()], events=ev).run(exploit_action(), "aid")
    routes = [r for r in ev.records if r["type"] == "decision" and r.get("kind") == "route"]
    assert len(routes) == 1
    d = routes[0]
    assert d["channel"] == "msfrpc"                 # ran on the routed primary
    assert d["candidates"] == ["msfrpc", "ssh"]     # ordered candidate list recorded
    assert d["ok"] is True and d["action_id"] == "aid"


def test_executor_decision_records_failure_and_attempts():
    ev = _RecEvents()
    bad = Flaky("ssh", fail_n=9)
    Executor([bad], router=lambda a, cs: list(cs), retries=1, events=ev).run(recon_action(), "aidf")
    d = [r for r in ev.records if r["type"] == "decision"][0]
    assert d["ok"] is False and d["attempts"]  # the fallback/retry trail is recorded


def test_executor_without_events_is_silent():
    # no events sink → no error, obs still returned
    obs = Executor([ssh()]).run(recon_action(), "aidq")
    assert obs.channel == "ssh"


# ── MCP flag-gating (TL-1.6) ───────────────────────────────────────────────────
@pytest.fixture
def mcp_env(monkeypatch):
    """Helper to toggle the MCP flag + server/version env within a test."""
    def _set(enabled=False, server=None, version=None):
        monkeypatch.setenv("OCTOPUS_MCP", "1" if enabled else "0")
        for k, v in (("OCTOPUS_MCP_SERVER", server), ("OCTOPUS_MCP_VERSION", version)):
            monkeypatch.delenv(k, raising=False)
            if v is not None:
                monkeypatch.setenv(k, v)
    return _set


def _mcp_action():
    return Action(name="probe", type=ActionType.EXPLOIT, host="target",
                  params={"mcp_tool": "scan_ports", "args": {"x": 1}})


def test_mcp_disabled_by_default_is_noop(mcp_env):
    mcp_env(enabled=False)
    assert McpChannel.is_enabled() is False
    assert McpChannel().supports(_mcp_action()) is False


def test_mcp_enabled_unverified_raises_channel_error(mcp_env):
    mcp_env(enabled=True)  # no server/version → unverified
    c = McpChannel()
    assert c.supports(_mcp_action()) is True
    with pytest.raises(ChannelError):
        c.run(_mcp_action(), "aid")


def test_mcp_unverified_falls_back_in_executor(mcp_env):
    mcp_env(enabled=True)
    ex = Executor([McpChannel(), FakeChannel("ssh", _ALL, raw="ssh ran")],
                  router=lambda a, cs: [x for x in cs if x.supports(a)])
    obs = ex.run(_mcp_action(), "aid")
    assert obs.channel == "ssh" and obs.raw == "ssh ran"


def test_mcp_verified_with_client_returns_observation(mcp_env):
    mcp_env(enabled=True, server="lab-mcp", version="0.1")

    class FakeClient:
        def call_tool(self, tool, args):
            return {"open": [22, 80], "tool": tool}

    c = McpChannel(client_provider=lambda: FakeClient())
    obs = c.run(_mcp_action(), "aid")
    assert obs.channel == "mcp" and obs.tool == "mcp:scan_ports"
    assert obs.structured["result"]["open"] == [22, 80]


def test_mcp_verified_without_transport_raises(mcp_env):
    mcp_env(enabled=True)
    c = McpChannel(verifier=lambda: True)  # verified, but no client_provider (stub)
    with pytest.raises(ChannelError):
        c.run(_mcp_action(), "aid")
