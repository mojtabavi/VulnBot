"""TL-0.3 — the loopback control channel round-trips a frame each direction (R2 transport).

Locks the HITL back-channel contract before the gate rides on it (TL-4.4): the agent-side
`ControlServer` accepts one CLI client, sends an event frame (agent → CLI), and receives a
command frame (CLI → agent), both as newline-delimited JSON. `announce=False` keeps the port
marker off stdout during the test.
"""
import threading

from utils.control import ControlServer, ControlClient, CONTROL_CMDS, CONTROL_EVENTS


def test_control_frame_roundtrip_both_directions():
    srv = ControlServer(announce=False)
    got = {}

    def client_side():
        cli = ControlClient(srv.port)
        got["event"] = cli.recv(timeout=2)      # agent → CLI (approval_request)
        cli.send({"cmd": "approve"})            # CLI → agent (reply)
        cli.close()

    t = threading.Thread(target=client_side)
    t.start()
    try:
        assert srv.wait_for_client(timeout=2), "server must accept the CLI client"
        assert srv.connected()
        assert srv.send({"event": "approval_request", "action": "exploit CVE-X", "risk": "high"})
        reply = srv.recv(timeout=2)
        assert reply == {"cmd": "approve"}, "server receives the CLI command frame"
    finally:
        t.join(timeout=2)
        srv.close()

    assert got["event"]["event"] == "approval_request"
    assert got["event"]["action"] == "exploit CVE-X"


def test_no_client_is_non_fatal():
    # A run with no front-end connected must not block or raise: send is a no-op, recv is None.
    srv = ControlServer(announce=False)
    try:
        assert srv.connected() is False
        assert srv.send({"event": "approval_request"}) is False
        assert srv.recv(timeout=0.1) is None
    finally:
        srv.close()


def test_command_and_event_vocab():
    for c in ("approve", "deny", "pause", "resume", "step", "quit"):
        assert c in CONTROL_CMDS
    assert "approval_request" in CONTROL_EVENTS
