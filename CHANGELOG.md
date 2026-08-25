# Changelog

All notable changes to this thesis fork. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); one entry per commit. Newest first.

The **R1–R4** tags map to the cross-cutting requirements (see `docs/PLAN.md`): R1 full POMDP,
R2 interactive Ink CLI (HITL), R3 multi-channel executor, R4 JSON logging + Ink LogView.

## [Unreleased] — R1–R4 interactive-POMDP hardening

### Added
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
