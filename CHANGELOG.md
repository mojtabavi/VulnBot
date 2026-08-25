# Changelog

All notable changes to this thesis fork. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); one entry per commit. Newest first.

The **R1–R4** tags map to the cross-cutting requirements (see `docs/PLAN.md`): R1 full POMDP,
R2 interactive Ink CLI (HITL), R3 multi-channel executor, R4 JSON logging + Ink LogView.

## [Unreleased] — R1–R4 interactive-POMDP hardening

### Added
- **LogView selftest coverage + pure `summarizeEvent` (R4, TL-5.4 → TL-5 COMPLETE).** Moved the per-type
  render mapping into `logview.ts` (tested without Ink); selftest covers summaries, parse/filter/tail,
  control-frame round-trip, approval command frames, and `/log`. **R4 Ink LogView is done.** typecheck +
  selftest PASS.
- **`/log [run_id]` opens the LogView (R4, TL-5.3).** New `/log` command → the Repl resolves the run
  (arg or `latestRunId()`) and opens the `LogView` overlay. selftest asserts. typecheck + selftest PASS.
- **`cli/src/ui/LogView.tsx` — event-log render (R4, TL-5.2).** Self-tailing Ink component: per-type
  summaries, belief/Z posterior bars, expandable details (never raw JSON), scroll + type filter + expand.
  typecheck PASS.
- **`cli/src/logview.ts` — LogView data layer (R4, TL-5.1).** Pure parse (`parseEventLine`/`parseEvents`/
  `filterEvents`) + run-log resolvers (`runsDir`/`eventsPathFor`/`latestRunId`/`readEvents`) + `tailEvents`
  (fs.watch + poll fallback, byte-offset dedupe, truncation-safe). selftest: parse/filter + live tail.
  typecheck + selftest PASS.
- **`RunView` paused / awaiting-approval state (R2, TL-4.5 → TL-4 COMPLETE).** RunView renders an
  awaiting-approval or paused status line from `paused`/`awaiting` props. **R2 interactive HITL is done.**
  typecheck + selftest PASS.
- **Python HITL approval gate (R2, TL-4.4).** `BeliefAgent(control, step)` wires a `ControlServer` into
  the loop: high-impact (exploit/lateral/privesc) or step-mode actions send `approval_request` and block —
  approve runs, deny skips+logs, quit stops, step arms step-through, pause/resume acked; a between-steps
  poll handles pause/quit. No client → auto (never blocks). `pentest.py --agent` opens the server + `--step`
  flag. 8 pytest + 12-assert smoke; full suite 70 pass.
- **`p/r/s/q` run keybinds (R2, TL-4.3).** During a live run the Repl sends pause/resume/step/quit command
  frames over the control socket. typecheck + selftest PASS.
- **`cli/src/ui/ApprovalPrompt.tsx` + Repl HITL wiring (R2, TL-4.2).** The Repl connects a `ControlClient`
  on the `control|port=N` marker; `approval_request` frames render an approve/deny overlay (default deny),
  and the choice is relayed back over the socket. `paused`/`resumed` tracked for RunView. typecheck +
  selftest PASS.
- **`cli/src/control.ts` — HITL control-socket client (R2, TL-4.1).** `ControlClient` over node `net`:
  newline-JSON framing matching `utils/control.py`, event/connect/close/error callbacks,
  approve/deny/pause/resume/step/quit senders, best-effort. `parseControlPort` reads the
  `##OCTO## control|port=N` marker. selftest: loopback round-trip + port parse. typecheck + selftest PASS.
- **`EventLog.write_manifest` — per-run manifest (R4, TL-3.3 → TL-3 COMPLETE).** `data/runs/<id>/
  manifest.json` links `events.jsonl` (+ event_count) and the belief trace (dir + latest.json) with the
  step count; `BeliefAgent` writes it at run_end (best-effort). R4 JSON-logging persistence is done.
  2 tests; full suite 62 pass.

### Changed
- **`llm_likelihoods` is a self-contained evidence record (R4, TL-3.2).** Now carries Z + belief
  before/after (prior/posterior) + the action, and the belief events fire only on a real (step-advancing)
  update — no stale re-emit when an update fails (an `error` event fires instead). Full suite 60 pass.

### Added
- **`Executor` event sink — routing decisions in the R4 log (R4, TL-3.1).** `Executor(…, events=…)`
  appends a `decision(kind=route)` record per action (candidate order, chosen channel, ok, retry/fallback
  trail, duration). `pentest.py` shares ONE `EventLog` across the executor + agent so `seq` stays a single
  monotonic sequence. Best-effort. 3 tests; full suite 60 pass.
- **`docs/POMDP_INTEGRATION.md` — finished tuple→code map (R1, TL-2.7 → TL-2 COMPLETE).** The
  ⟨S,A,O,T,Z,R,b,γ,π⟩→code table (T routing, `BeliefAgent.run` loop, R→`score` event), the
  partial-observability/self-consistency/T-effect test references, and a "Running the belief agent"
  section. **The R1 full POMDP loop is done** — `run_agent` runs the standalone belief-first loop.
- **`tests/test_agent.py` — R1 belief-loop tests (R1, TL-2.6).** Self-consistency (samples>1 averages Z;
  5-sample posterior variance < 1-sample) + the T-effect (exploit vs recon move different belief factors
  from the same observation) + a fakes-only `BeliefAgent` loop smoke. Full suite 57 passed.
- **`pentest.py --agent` + CLI `/run --agent` (R1, TL-2.5).** `--agent` drives the standalone
  `BeliefAgent` loop (`run_belief_agent`: lazy R3 `Executor` SSH[+msf][+MCP-if-flagged] + `_chat` belief
  LLM + per-run `EventLog`/`BeliefStore`, target from the description) instead of the legacy 3-phase
  pipeline (still the default). `runPentest(…, agent)` appends the flag; the Repl parses `/run [--agent]`.
  CLI typecheck + selftest PASS.

### Changed
- **`BeliefAgent` emits the full R4 event set (R1+R4, TL-2.4).** Through the `EventLog` seam:
  `run_start`, per-step `action_selected` + `score`, gated `approval_request`/`approval_result`,
  `observation` (full `Observation.to_dict()`), `belief_update` (prior+posterior), `llm_likelihoods` (Z),
  `decision`/`error`/`run_end`. Fixed a `type=` kwarg collision with `EventLog.append(type,…)` (renamed the
  field to `action_type`) that a test fake had masked. Verified on-disk (9 types, monotonic seq) + 53 pass.
- **Self-consistency `VULNBOT_Z_SAMPLES` unified (R1, TL-2.3).** New `belief_state.z_samples()` (env,
  clamp ≥1) is the single source of truth for the Updater's Z-sample count; both `BeliefAgent` and the
  legacy Role updater `_belief_persist` (was hardcoded `samples=1`) now use it. `pomdp/agent.py` dropped
  its unused `os` import. Full suite 53 passed.
- **`pomdp/belief_state.py::run_agent` — now a delegator, no longer `NotImplementedError` (R1, TL-2.2).**
  Lazily imports and calls `pomdp.agent.run_agent` (lazy import breaks the agent↔belief_state cycle).
  Belief math untouched. Full suite 53 passed.

### Added
- **`pomdp/agent.py` — `BeliefAgent` standalone POMDP loop (R1, TL-2.1).** The integrator that ties π +
  Executor (R3) + Updater + Belief Store together: b0 = `new_belief` + `priors.seed_vuln_priors`, then
  `choose_action → (HITL gate) → executor.run → update_belief(llm, samples) → BeliefStore.save` until a
  goal predicate or step cap. Default candidate generation (recon per host + priors-enriched exploits) and
  a default root-goal make it runnable; every side channel (candidate gen, approve gate, executor raise,
  Z/update, event sink) is guarded so a failure never breaks the run. Belief math imported, never
  re-implemented; never branches on S. `samples` from arg / `VULNBOT_Z_SAMPLES` / 1 (TL-2.3 seam); emits
  the core event set if an `EventLog` is attached (TL-2.4 completes it). Smoke PASS (15 asserts).
- **`docs/EXECUTOR.md` — finished executor-layer write-up (R3, TL-1.8 → TL-1 COMPLETE).** Files table,
  `Action→Observation` data-flow, per-channel table, router ranking policy, TL-1.5 timeout/retry/fallback
  semantics + `_executor_fallback` trail, TL-1.6 MCP gating, the `Observation` schema, tests/smoke, and
  safety. **The R3 multi-channel executor is done**: one `Executor.run(action)→Observation` over
  SSH + msfrpc (+ flag-gated MCP), a policy router, timeout/retry/fallback — 23 executor tests, 53 total.
- **`tests/test_executor.py` — Executor-layer test suite (R3, TL-1.7).** 23 tests with fake channels
  (no real Kali/msfrpcd/MCP): router policy, `Observation` normalization + stamping, timeout/retry/
  fallback robustness (incl. timeout-not-auto-retried and all-dead→failure-never-raises), and MCP
  flag-gating via `monkeypatch`. Full suite 53 passed.
- **`executor/mcp_channel.py` — flag-gated MCP channel, OFF by default (R3, TL-1.6).** Channel C, an
  optional MCP tool bridge that is strictly additive (SSH+msfrpc stay sufficient). `VULNBOT_MCP` unset/
  falsey → `supports()` False → the router never routes here (pure no-op). Truthy → offered only for
  actions naming an MCP tool (`params['mcp_tool']` / `mcp:` prefix), and `run()` first verifies
  `VULNBOT_MCP_SERVER`+`VULNBOT_MCP_VERSION` (or an injected `verifier`) — a miss raises `ChannelError`→
  fallback, so enabling the flag can never break a run. No transport is wired yet (deliberate stub): no
  `client_provider` → `ChannelError`→fallback; `_run_tool` is the injectable extension point that
  normalizes `call_tool` results into an `Observation`. Smoke PASS (12 asserts).
- **`executor/base.py` — per-channel timeout + safe retry + fallback trail (R3, TL-1.5).**
  `Executor(timeout_s, retries)`. `timeout_s` runs each attempt in a daemon thread and `join`s the budget;
  an overrun raises the new `ChannelTimeout(ChannelError)` and the stuck thread is abandoned. Retry is
  safety-first: a plain `ChannelError` (tool didn't run) retries the SAME channel up to `retries` times; a
  `ChannelTimeout` is **never** auto-retried (the tool may have started — a non-idempotent exploit must not
  fire twice); a channel bug never retries. Exhaustion falls through to the next capable channel; all-dead
  still returns a normalized failure `Observation`. A late success records the earlier failures under the
  reserved `structured["_executor_fallback"]` meta key (non-destructive) so the R4 log shows the trail.
  Defaults (`timeout_s=None`, `retries=0`) preserve prior behaviour. Smoke PASS (9 asserts).
- **`executor/router.py` — channel-selection policy (R3, TL-1.4).** Replaces the trivial
  `_default_router`: `route(action, channels)` returns a `RouteDecision` (ordered candidates,
  primary-first, + a one-line justification). Policy — recon → SSH; exploit/lateral/privesc **naming an
  MSF module** → msfrpc first, SSH kept as fallback; exploit/etc. with no module → SSH. msfrpc outranks
  ssh for offensive types regardless of registration order. `channel_router()` becomes the `Executor`'s
  default router (lazy import in `base.py`, no circular-import break) and mirrors each pick as a
  best-effort `##OCTO## decision|kind=route` marker for the live view / event log. Smoke PASS (10 asserts).
- **`executor/msf_channel.py` — msfrpc channel (R3, TL-1.3).** Channel B: drives a Metasploit
  exploit/auxiliary/post module over `pymetasploit3` and normalizes the **structured** RPC result into
  `Observation.structured` (`raw` = `Action:/Observation:` summary). Module path from
  `params["module"]`/`tool` (only a real `prefix/rest` MSF shape routes here — a bare tool like `nmap`
  does not); options from `params["options"]` with `RHOSTS` defaulted to `action.host`; optional
  `payload`. No module → failure O; unreachable msfrpcd → `ChannelError` (Executor falls back to SSH).
  Lazy `pymetasploit3` import, `.env`-sourced connection, injectable `client_provider` for tests. Smoke
  PASS (20 asserts incl. dead-msf → capable-SSH fallback).
- **`executor/ssh_channel.py` — SSH channel (R3, TL-1.2).** Channel A: runs the action's shell
  command(s) on Kali via the reused `ShellManager`/`RemoteShell` singleton and normalizes raw stdout →
  `Observation`. Missing command → failure O; unusable/failed session → `ChannelError` (Executor
  fallback). Lazy `ShellManager` import + injectable `shell_provider` for tests.
- **`executor/` package — Channel ABC + Executor facade (R3, TL-1.1).** `executor/base.py`:
  `Channel` adapter interface (`name`/`supports`/`run(action, action_id)→Observation`/`close`),
  `ChannelError` (unusable-channel → fallback), and the `Executor` facade — routes an `Action` to a
  capable channel, times it, stamps `channel`/`duration_ms`/`action_id`, falls back on `ChannelError`,
  and never raises (all-dead → a normalized failure `Observation`). Stdlib-only.
- **`utils/control.py` — loopback CLI↔agent control socket (R2, TL-0.3).** `ControlServer` binds
  `127.0.0.1:<ephemeral>`, announces `##OCTO## control|port=N`, exchanges newline-JSON frames
  (`approval_request`/`paused` out; `approve|deny|pause|resume|step|quit` in). `ControlClient` for
  tests. Transport only (gate = TL-4.4); no-client is non-fatal. `tests/test_control.py` (3 pass).
- **`utils/events.py` — JSONL event log (R4, TL-0.2).** `EventLog(run_id)` appends one JSON record per
  event to `data/runs/<id>/events.jsonl` (the source of truth the Ink LogView will tail) + a compact
  `##OCTO## event|…` marker mirror. `EVENT_TYPES` union; stdlib-only, best-effort. `tests/test_events.py`
  (5 pass).
- **`pomdp/observation.py` — unified Observation schema (R3+R4, TL-0.1).** The one normalized channel
  result: `raw` = observation O for the Updater, `to_dict()` = the `observation` event record.
  `to_dict`/`from_dict` (forward-compatible) + `failure()` (error→raw). Stdlib-only.
- **Deliverable docs (TL-0.4):** `docs/EXECUTOR.md` (channels/router/Observation schema), and the
  `docs/PLAN.md`/`docs/TODO.md` R1–R4 execution plan (TL-0…TL-6).

### Changed
- **Docs + schematic sync (TL-0 milestone):** `docs/ARCHITECTURE.md` §1.1 (shared-contract table +
  three-lane process boundary), `CLAUDE.md` new "R1–R4 hardening" section, `docs/POMDP_INTEGRATION.md`
  (tuple→code map). Regenerated `project_schematic.excalidraw` + `docs/project_schematic.png` (blue TL-0
  foundation nodes; orange R1–R4 lanes). Refreshed the graphify knowledge graph (1081 nodes / 79
  communities).
