# EXECUTOR — multi-channel Kali execution layer (R3)

> **Status:** COMPLETE (TL-1). One `Executor.run(action) → Observation` facade over pluggable
> channels (SSH, msfrpc, flag-gated MCP), a policy router, and per-channel timeout/retry/fallback.
> Verified by `tests/test_executor.py` (23 tests) + the live `docker/agent/smoke_channels.py`.

The Executor turns a POMDP **Action** into an **Observation** by running the right tool through the
right channel, then normalizing every channel's result into ONE schema before it reaches the Belief
Updater. One interface, pluggable channels, a router that picks per action type, and robustness
(timeout + retry + fallback) so a single dead channel never stalls the belief loop.

```
Action ──▶ Executor.run(action) ──▶ router(action, channels) = ordered candidates
                                          │   [ssh | msfrpc | mcp], primary first
                                          ▼
                                   for each candidate:
                                     _call_with_timeout (daemon-thread budget)
                                     ├─ ok            ──▶ stamp channel/action_id/duration ──▶ Observation
                                     ├─ ChannelError  ──▶ retry same channel (≤ retries), then next
                                     ├─ ChannelTimeout──▶ next channel (NEVER auto-retried)
                                     └─ other Exception──▶ next channel (channel bug, no retry)
                                   all candidates dead ──▶ normalized failure Observation (never raises)
```

`Action` = `pomdp/belief_state.py::Action`; `Observation` = `pomdp/observation.py::Observation`.
Both are stdlib-only, so `executor/` imports without the RAG/ML stack.

## Files

| File | Role |
|------|------|
| `executor/base.py` | `Channel` ABC, `ChannelError`/`ChannelTimeout`, the `Executor` facade (routing + timeout/retry/fallback), `Router` type + `_default_router` fallback |
| `executor/ssh_channel.py` | **Channel A** — arbitrary shell tools on Kali via `ShellManager`/`RemoteShell`; stdout → `Observation` |
| `executor/msf_channel.py` | **Channel B** — Metasploit modules over `pymetasploit3`; structured RPC result → `Observation` |
| `executor/mcp_channel.py` | **Channel C** — optional MCP tool bridge, OFF by default (`OCTOPUS_MCP=0`) |
| `executor/router.py` | the policy router: `route()` → `RouteDecision`, `channel_router()` (Executor default) |

## Channels (adapters)

Each channel implements `Channel`: `name`, `supports(action) -> bool`, `run(action, action_id) ->
Observation`, `close()`. A channel MUST normalize its result to an `Observation`; it raises
`ChannelError` only when the channel *itself* is unusable (so the Executor can fall back), never for
an ordinary tool failure (which is a normal `Observation` with `success=False`).

| Channel | Transport | Best for | Output | Unusable → |
|---------|-----------|----------|--------|------------|
| **SSH** | paramiko (`actions/shell_manager.py` + `actions/remote_shell.py`) | arbitrary tools: nmap, enum, custom shell | raw stdout → `Observation.raw` | `ChannelError` (dead/failed session) |
| **msfrpc** | `pymetasploit3` → `msfrpcd:55553` (pattern: `docker/agent/smoke_channels.py`) | Metasploit modules (exploit/lateral/privesc naming a module) | structured RPC result → `Observation.structured` (+ summary in `raw`) | `ChannelError` (unreachable/mid-exec) |
| **MCP** *(flag-gated `OCTOPUS_MCP=0`)* | MCP server — verify exact server + version before enabling | optional efficiency layer only | normalized like the others | `ChannelError` (disabled/unverified/no transport) |

**SSH + msfrpc are sufficient on their own.** MCP is strictly additive; if unavailable/unstable the
system runs fully on SSH + msfrpc.

Lazy imports keep the channels independent: `pymetasploit3` (msfrpc) and `ShellManager` (SSH) are
imported only on first use, and each channel takes an injectable provider (`client_provider` /
`shell_provider` / MCP `client_provider` + `verifier`) so tests never touch a real endpoint.

## Router policy (TL-1.4)

`route(action, channels)` returns a **`RouteDecision`** — the ordered candidate channels (primary
first, then fallbacks) plus a one-line justification. It ranks only the channels that
`supports(action)`, by `(_rank_for(action.type, name), name)`:

- **recon** → **SSH** first (nmap/enum/custom); msfrpc after, if it somehow supports it.
- **exploit / lateral / privesc** → **msfrpc** first, **SSH** kept as fallback — but msfrpc only
  `supports()` these when the action actually names an MSF module (`params['module']` or a
  `prefix/rest` module path in `tool`). With **no module named**, only SSH supports the action, so
  it routes to SSH.
- msfrpc outranks SSH for offensive types **regardless of channel registration order** (the sort key,
  not list order, decides).

`channel_router(emit=True)` wraps `route()` into the `Router` the `Executor` uses by default (lazily
imported in `base.py::_make_default_router`; falls back to `_default_router` — "every supporting
channel, registration order" — if the policy module can't import, so the facade always runs). Each
pick is mirrored as a best-effort `##OCTO## decision|kind=route` marker for the live view / event
log; routing stays pure — a dead emit path never breaks a run.

## Robustness — timeout, retry, fallback (TL-1.5)

`Executor(channels, router=None, timeout_s=None, retries=0)`:

- **timeout** — `timeout_s` is a per-attempt wall-clock budget. Each attempt runs in a daemon worker
  thread that the facade `join`s for `timeout_s`; an overrun raises **`ChannelTimeout`** and the stuck
  (daemon) thread is abandoned — Python can't kill arbitrary blocking I/O, so this is best-effort. `None`
  (default) = no budget.
- **retry** — safety-first, keyed on *why* a channel failed:
  - a plain **`ChannelError`** means the tool did **not** run (connect/auth/RPC-down *before* execution) →
    retried on the SAME channel up to `retries` times;
  - a **`ChannelTimeout`** is **never** auto-retried — the tool may already have started, and a
    non-idempotent exploit must not fire twice → fall straight to the next channel;
  - any **other exception** is a channel *bug* → never retried, fall to the next channel.
- **fallback** — on exhaustion the Executor moves to the next candidate from the router. If every
  candidate is unusable it returns a **normalized failure `Observation`** (joined error trail in
  `error`, `success=False`) — it **never raises** into the belief loop.
- **fallback trail** — when a call only succeeds after a retry/fallback, the preceding failures are
  recorded under the reserved meta key `structured["_executor_fallback"]` (non-destructive — `raw` /
  `error` / `success` of the winning `Observation` are untouched), so the R4 event log shows the trail.

Defaults (`timeout_s=None`, `retries=0`) preserve the plain single-attempt behaviour.

## MCP gating (TL-1.6)

`McpChannel` is a **flag-gated stub**, OFF by default, so MCP is never a dependency:

- `OCTOPUS_MCP` unset / falsey → `is_enabled()` False → `supports()` False for every action → the
  router never routes here (pure no-op). SSH + msfrpc do everything.
- `OCTOPUS_MCP` truthy → the channel offers itself only for actions naming an MCP tool
  (`params['mcp_tool']` or a `mcp:<tool>` prefix on `tool`), and `run()` **first verifies** the
  configured server + version (`OCTOPUS_MCP_SERVER` + `OCTOPUS_MCP_VERSION`, or an injected `verifier`).
  A verification miss raises `ChannelError` → the Executor falls back. Enabling the flag can never
  *break* a run; at worst it falls back.
- No real transport is wired yet: with no `client_provider`, `run()` raises `ChannelError` → fallback.
  `_run_tool` (exercised by tests via an injected client) is the extension point for a future MCP
  session and normalizes `call_tool` results into an `Observation`.

## Unified Observation schema

The single normalized result type — defined in **`pomdp/observation.py`** (stdlib-only), shared with
the JSON event log (R4). One `Observation` = the body of an `observation` event record.

| Field | Type | Meaning |
|-------|------|---------|
| `action_id` | str | correlation id (Action ↔ Observation ↔ events); `new_action_id()` |
| `channel` | str | `ssh` \| `msfrpc` \| `mcp` \| `none` — the adapter that produced it |
| `action_type` | str | POMDP ActionType the observation bears on (recon/exploit/…) |
| `host` | str? | target host (may be None during early recon) |
| `tool` | str? | tool / MSF module invoked |
| `raw` | str | **raw tool output = observation O** fed to the Belief Updater |
| `structured` | dict? | parsed result when the channel returns structure (msfrpc/MCP); also carries `_executor_fallback` when a call fell back |
| `success` | bool? | clear success signal (exploit landed?) or None (recon) |
| `exit_code` | int? | process/RPC status when meaningful |
| `duration_ms` | int? | wall-clock cost of the call (stamped by the facade if unset) |
| `error` | str? | failure note (also mirrored into `raw` so the Updater still sees an O) |
| `ts` | float | epoch seconds |

Helpers: `Observation.to_dict()` / `from_dict()` (forward-compatible) / `failure(...)` (error→raw).
The facade always stamps `channel`, `action_id`, and `duration_ms` if a channel left them unset.

## Tests & smoke

- **`tests/test_executor.py` (23 tests, part of the 53-test suite)** — fake channels, no real Kali:
  router policy (recon→ssh, exploit→[msfrpc,ssh] regardless of registration order, only-ssh fallback,
  no-supporting-channel empty, ordered list), `Observation` normalization + stamping, the TL-1.5
  robustness (same-channel retry, fallback trail, exhaust→fallback, all-dead→failure-never-raises,
  clean-no-trail, timeout falls through and is NOT auto-retried, no-timeout completes,
  `ChannelTimeout ⊂ ChannelError`), and MCP flag-gating (disabled-no-op, enabled+unverified→ChannelError,
  Executor fallback, verified+client→Observation, verified-but-no-transport→raise). Run:
  `python -m pytest tests/test_executor.py -q`.
- **`docker/agent/smoke_channels.py`** — exercises both live channels against the lab (SSH
  nmap-against-`target`; msfrpc module list) and documents the SSH-vs-msfrpc rule.

## Safety

Offensive tooling lives ONLY in the Kali container; this layer is a router/normalizer and holds no
exploits. Authorized lab targets only (the isolated `target` container, labnet `internal:true`).
Secrets via `.env`; the git-ignored agent SSH key is a lab credential, never committed. Every
router/emit/fallback path is best-effort — a failure there must never break a run.
