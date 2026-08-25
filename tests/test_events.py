"""TL-0.2 — the JSON event log is the on-disk source of truth (R4).

Locks the contract the LogView relies on: append writes one valid JSON record per event,
`seq` orders them, a compact `event` marker is mirrored to stdout, and logging is best-effort
(a non-serializable field never raises into the run). Uses a tmp root — never touches data/runs.
"""
import json

from utils.events import EventLog, EVENT_TYPES


def test_append_writes_valid_ordered_jsonl(tmp_path):
    log = EventLog("run-1", root=tmp_path)
    log.append("run_start", target="target")
    log.append("observation", host="target", raw="80/tcp open http")

    recs = log.read_all()
    assert [r["seq"] for r in recs] == [1, 2], "seq orders the records"
    assert [r["type"] for r in recs] == ["run_start", "observation"]
    assert recs[0]["run_id"] == "run-1" and "ts" in recs[0]
    assert recs[1]["raw"] == "80/tcp open http"
    # one physical line per record (the LogView tails line-by-line)
    assert log.path.read_text(encoding="utf-8").strip().count("\n") == 1


def test_record_is_json_and_fields_merge(tmp_path):
    log = EventLog("r", root=tmp_path)
    rec = log.append("belief_update", host="h", dist={"present": 0.6, "absent": 0.4})
    on_disk = json.loads(log.path.read_text(encoding="utf-8").splitlines()[0])
    assert on_disk == rec
    assert on_disk["dist"]["present"] == 0.6


def test_append_is_best_effort_on_unserializable(tmp_path):
    log = EventLog("r", root=tmp_path)
    # a raw object isn't JSON-serializable; default=str must catch it, not raise.
    log.append("score", obj=object())
    recs = log.read_all()
    assert len(recs) == 1 and recs[0]["type"] == "score", "logging never breaks the run"


def test_append_mirrors_compact_marker(capsys):
    # importing tmp_path is not needed; use the default root but a unique id, then read stdout only.
    log = EventLog("marker-test")
    log.append("decision", mode="recon")
    out = capsys.readouterr().out
    assert "##OCTO##" in out and "type=decision" in out and "seq=1" in out
    # the compact mirror must NOT carry the full payload (kept out of the live stream)
    assert "mode=recon" not in out


def test_event_types_cover_the_union():
    for t in ("run_start", "observation", "belief_update", "approval_request", "run_end"):
        assert t in EVENT_TYPES


def test_write_manifest_links_events_and_belief_trace(tmp_path):
    log = EventLog("run-m", root=tmp_path)
    log.append("run_start")
    log.append("observation", raw="80 open")
    belief_dir = tmp_path / "beliefs" / "run-m"
    m = log.write_manifest(belief_dir=belief_dir, steps=2)

    import json
    on_disk = json.loads((log.dir / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk == m
    assert m["run_id"] == "run-m"
    assert m["events"] == "events.jsonl" and m["event_count"] == 2 and m["steps"] == 2
    assert m["belief_trace"] == str(belief_dir)
    assert m["belief_latest"].endswith("latest.json")


def test_write_manifest_is_best_effort_without_belief_dir(tmp_path):
    log = EventLog("run-n", root=tmp_path)
    m = log.write_manifest()  # no belief dir → null pointers, still writes
    assert m["belief_trace"] is None and m["belief_latest"] is None
    assert (log.dir / "manifest.json").is_file()
