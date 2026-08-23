# EXECUTOR — multi-channel Kali execution layer (R3)

> **Status:** schema pinned (TL-0.4). Channels/router/fallback filled in TL-1; smoke in TL-1.7–1.8.

The Executor turns a POMDP **Action** into an **Observation** by running the right tool through the
right channel, then normalizing every channel's result into ONE schema before it reaches the Belief
Updater. One interface, pluggable channels, a router that picks per action type.

```
Action ──▶ Executor.run(action) ──▶ [router picks a Channel] ──▶ Channel.run(action) ──▶ Observation
                                          │  ssh / msfrpc / mcp                    (normalized)
                                          └─ on failure: fall back to a capable channel
```

## Channels (adapters)

| Channel | Transport | Best for | Output |
|---------|-----------|----------|--------|
| **SSH** | paramiko (`actions/shell_manager.py` + `actions/remote_shell.py`) | arbitrary tools: nmap, enum, custom shell | raw stdout → `Observation.raw` |
| **msfrpc** | `pymetasploit3` → `msfrpcd:55553` (pattern: `docker/agent/smoke_channels.py`) | Metasploit modules (exploit/lateral/privesc) | structured RPC result → `Observation.structured` (+ summary in `raw`) |
| **MCP** *(optional, flag-gated `VULNBOT_MCP=0`)* | MCP server (TBD — verify exact server + version before enabling) | efficiency layer only | normalized like the others |

**SSH + msfrpc are sufficient on their own.** MCP is an efficiency add-on; if unavailable/unstable the
system runs fully on SSH + msfrpc. _(Router policy, timeouts, retry, and fallback order: TL-1.4–1.6.)_

## Router policy (TL-1.4)

Selects a channel by `action.type` and logs the justification:
- `recon` → **SSH** (nmap/enum/custom).
- `exploit` / `lateral` / `privesc` → **msfrpc** when the action names an MSF module, else **SSH**.
- MCP, when enabled, may pre-empt as an efficiency layer for supported tools.

On a channel failure the Executor falls back to the next channel that `supports(action)`, recording the
switch in `Observation.channel` / `Observation.error`.

## Unified Observation schema

The single normalized result type — defined in **`pomdp/observation.py`** (stdlib-only), shared with the
JSON event log (R4). One `Observation` = the body of an `observation` event record.

| Field | Type | Meaning |
|-------|------|---------|
| `action_id` | str | correlation id (Action ↔ Observation ↔ events); `new_action_id()` |
| `channel` | str | `ssh` \| `msfrpc` \| `mcp` \| `none` — the adapter that produced it |
| `action_type` | str | POMDP ActionType the observation bears on (recon/exploit/…) |
| `host` | str? | target host (may be None during early recon) |
| `tool` | str? | tool / MSF module invoked |
| `raw` | str | **raw tool output = observation O** fed to the Belief Updater |
| `structured` | dict? | parsed result when the channel returns structure (msfrpc/MCP) |
| `success` | bool? | clear success signal (exploit landed?) or None (recon) |
| `exit_code` | int? | process/RPC status when meaningful |
| `duration_ms` | int? | wall-clock cost of the call |
| `error` | str? | failure note (also mirrored into `raw` so the Updater still sees an O) |
| `ts` | float | epoch seconds |

Helpers: `Observation.to_dict()` / `from_dict()` (forward-compatible) / `failure(...)` (error→raw).

## Smoke test (TL-1.7–1.8)

`docker/agent/smoke_channels.py` already exercises both live channels (SSH nmap-against-`target`; msfrpc
module list). TL-1.7 adds `tests/test_executor.py` (fake channels: router pick, normalization, fallback —
no real Kali). _(Full write-up: TL-1.8.)_

## Safety

Offensive tooling lives ONLY in the Kali container; this layer is a router/normalizer and holds no
exploits. Authorized lab targets only (the isolated `target` container). Secrets via `.env`.
