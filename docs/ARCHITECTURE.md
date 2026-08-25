# VulnBot — Architecture Reference

![VulnBot current architecture & data flow](project_schematic.png)

*Source: [`../project_schematic.excalidraw`](../project_schematic.excalidraw) — gray = current
modules, orange = future belief-state attachment points (placeholders only).*

Documentation-only reference for the forked **VulnBot** framework (arXiv 2501.13411).
This file describes the project **as it currently is**. Nothing here is a belief-state
or POMDP implementation — the future belief modules are only *located*, not built
(see [Integration Points](#integration-points) and [Open Questions](#open-questions)).

---

## 1. What VulnBot Is

VulnBot is a multi-agent, LLM-driven autonomous penetration-testing framework. One run
walks three sequential **phases** — Reconnaissance → Vulnerability Scanning →
Exploitation — each phase driven by a role agent that plans a small task graph and then
executes tasks by generating shell commands and running them on a remote **Kali Linux**
host over SSH. State between tasks is a **Penetration Task Graph (PTG)**: a dependency-
ordered list of tasks persisted in MySQL.

The paper's conceptual modules map onto the code as follows:

| Paper module        | Code realization                                                            |
|---------------------|-----------------------------------------------------------------------------|
| Planner             | `roles/role.py::_plan` + `actions/planner.py` + `actions/write_plan.py`      |
| Memory-Retriever    | RAG path inside `server/chat/chat.py::_chat` + `rag/` (Milvus, reranker)     |
| Generator           | `actions/write_code.py::WriteCode`                                           |
| Executor            | `actions/execute_task.py::ExecuteTask` + `actions/shell_manager.py` + `actions/remote_shell.py` |
| Summarizer          | `actions/plan_summary.py::PlannerSummary` + `summary_result`/`check_success` prompts |
| Penetration Task Graph (PTG) | `db/models/plan_model.py::Plan` + `db/models/task_model.py::Task` (dependency DAG, topological sort) |

### 1.1 R1–R4 hardening (this fork) — shared-contract foundations (TL-0) + executor layer (TL-1)

On top of the belief layer, an in-progress pass turns the agent into a fully interactive POMDP
(details: `docs/POMDP_INTEGRATION.md`, `docs/EXECUTOR.md`, plan `~/.claude/plans/…joyful-scroll.md`).
TL-0 landed the shared contracts every later piece builds on:

| Contract | Module | Serves | Role |
|----------|--------|--------|------|
| Observation schema | `pomdp/observation.py` | R3 + R4 | the ONE normalized result every Executor channel returns; `raw` = observation O for the Updater; `to_dict()` = the `observation` event record |
| JSON event log | `utils/events.py` | R4 | `EventLog(run_id)` appends one JSON record per event to `data/runs/<id>/events.jsonl` (the on-disk source of truth the Ink `LogView` tails) + a compact `##OCTO##` marker mirror |
| Control channel | `utils/control.py` | R2 | loopback socket for CLI↔agent human-in-the-loop (approve/deny/pause/step/quit); announces its port via `##OCTO## control|port=N` |

**Process boundary — three clean lanes** (so the Node/Ink front-end and the Python agent stay decoupled):
1. **Live (Py→CLI):** `##OCTO##` stdout markers — the RunView ticker (phase/step/belief/decision/wait).
2. **Truth (Py→disk→CLI):** `events.jsonl` — full JSON records; the LogView tails the file.
3. **Control (CLI↔Py):** the loopback socket — HITL only.

**TL-1 — the R3 multi-channel executor (`executor/`, done).** One `Executor.run(action) → Observation`
facade over pluggable channels, so the belief loop always receives a normalized O regardless of transport:

| Piece | Module | Role |
|-------|--------|------|
| Facade | `executor/base.py` | `Channel` ABC + `Executor`; routes an action to ordered candidates, times each in a daemon-thread budget (`timeout_s` → `ChannelTimeout`), retries a plain `ChannelError` (never a timeout — non-idempotent-exploit safety), falls back to the next capable channel, records the trail in `structured["_executor_fallback"]`, and **never raises** (all-dead → a failure `Observation`) |
| Channel A — SSH | `executor/ssh_channel.py` | arbitrary shell tools via the reused `ShellManager`/`RemoteShell`; stdout → `Observation.raw` |
| Channel B — msfrpc | `executor/msf_channel.py` | Metasploit modules over `pymetasploit3`; structured RPC result → `Observation.structured` |
| Channel C — MCP | `executor/mcp_channel.py` | optional, **flag-gated `VULNBOT_MCP=0`**; a no-op until a server+version is verified — SSH+msfrpc are sufficient alone |
| Router | `executor/router.py` | picks per action type + logs the justification (recon→ssh; exploit/lateral/privesc naming an MSF module→msfrpc first, ssh fallback; no module→ssh) as a `##OCTO## decision|kind=route` marker |

This R3 executor is **distinct** from the legacy `actions/execute_task.py` pipeline path (§4); the
standalone `BeliefAgent` (R1, TL-2) drives it. Verified by `tests/test_executor.py` (23 tests, fakes).

**TL-2 — the R1 standalone POMDP loop (`pomdp/agent.py`, done).** `BeliefAgent.run` is the belief-first
control loop the whole thesis is about: `new_belief` + `priors.seed_vuln_priors` → repeat
`choose_action` (π) → HITL gate → `executor.run` (R3, → Observation) → `update_belief` (Z + soft Bayes) →
`BeliefStore.save` until a goal predicate or the step cap. It imports the belief MATH, never re-implements
it, and never branches on S. `belief_state.run_agent` now delegates here (lazy import); the loop is
selected by `pentest.py --agent` / octopus `/run --agent` and emits the full R4 event set through an
attached `EventLog`. Self-consistency (`VULNBOT_Z_SAMPLES`) and the T-effect are locked by
`tests/test_agent.py`; the tuple→code map is `docs/POMDP_INTEGRATION.md`.

Still to come: JSON-logging wired end-to-end (R4, TL-3) and the Ink HITL + LogView (R2/R4, TL-4/5).

---

## 2. Module Roles, Inputs & Outputs

### 2.1 Role agents — `roles/`
Three phase agents subclass `roles/role.py::Role`. Each only sets a `goal`, a `tools`
string (advisory tool list for the LLM), and a phase-specific prompt pair.

| Role | File | Phase | `RoleType` value |
|------|------|-------|------------------|
| `Collector` | `roles/collector.py` | Reconnaissance | `Collection` |
| `Scanner`   | `roles/scanner.py`   | Vulnerability scanning | `Scanning` |
| `Exploiter` | `roles/exploiter.py` | Exploitation | `Exploitation` |

- **Input:** a `Session` (init description + which role is current + history planner IDs).
- **Output:** side effects — a persisted `Plan` with executed `Task`s, plus a chained
  call into the next role.
- **Phase chaining:** `Collector.put_message` → `Scanner.run`, `Scanner.put_message` →
  `Exploiter.run`. So a single `vulnbot` command runs all three phases in order, each
  phase producing its own `Plan` and appending that plan's id to `history_planner_ids`.

### 2.2 `Role` base loop — `roles/role.py`
The engine shared by all three phases.
- `_plan(session)` — if the phase has no plan yet: builds prior-phase `context` via the
  Summarizer, opens **two** LLM conversations (`plan_chat_id`, `react_chat_id`) using the
  role's `init_plan_prompt` / `init_reasoning_prompt`, creates a `Plan` row, then calls
  `Planner.plan()`. Returns the first task's detailed instruction.
- `_react(next_task)` — one execute step: `WriteCode.run()` → run commands → optionally
  summarize long output (`>= 8192` chars) → `Planner.update_plan(result)`; returns the
  next task or `None`.
- `run(session)` — `_plan`, then loop `_react` up to `max_interactions`, then
  `put_message` (persist tasks + hand to next role).

### 2.3 Planner — `actions/planner.py`
Owns the current `Plan`.
- `plan()` → first task. Calls `WritePlan.run()` to get the initial task JSON, parses it
  into the PTG, returns `next_task_details()`.
- `update_plan(result)` → next task. Asks the LLM `check_success` (yes/no) on the tool
  output, marks the current task success/fail, calls `WritePlan.update()` to revise the
  PTG, `merge_tasks()` to fold the revision into existing tasks, returns the new current
  task's details.
- `next_task_details()` → LLM-expanded, RAG-augmented executable description of the
  current task (`DeepPentestPrompt.next_task_details`, on the `react_chat_id`
  conversation).
- **Input:** task results (strings). **Output:** the next task's instruction string; DB
  task-status updates.

### 2.4 WritePlan — `actions/write_plan.py`  *(the PTG builder)*
- `run()` — LLM emits a `<json>` list of `{id, dependent_task_ids, instruction, action}`;
  `parse_tasks` → `import_tasks_from_json` turns it into `Task`s with integer
  `dependencies` (the PTG edges).
- `update()` — LLM revises the plan given the last result + finished success/fail tasks;
  `merge_tasks` preserves completed-successful tasks and grafts new ones.
- `action` per task is one of the LLM-declared action types (`Shell`, `Web`).

### 2.5 Generator — `actions/write_code.py::WriteCode`
- **Input:** a task description string + its `action`.
- **Process:** LLM (`DeepPentestPrompt.write_code`) turns the task into concrete shell
  commands wrapped in `<execute>…</execute>` tags.
- **Output:** an `ExecuteResult` (from the Executor) — the raw command output.

### 2.6 Executor — `actions/execute_task.py`, `shell_manager.py`, `remote_shell.py`
- `ExecuteTask.parse_response()` extracts `<execute>` blocks.
- `run()` branches on `basic_config.mode`:
  - `auto` → run every command on the Kali shell;
  - `manual` → operator pastes results by hand (no auto-execution);
  - `semi` → shell auto-runs, non-shell actions are manual.
- `ShellManager` — singleton holding one paramiko SSH session to the Kali host
  (`basic_config.kali`).
- `RemoteShell` — sends commands, handles password/`[y/n]`/SMB/FTP prompts, cleans
  `dirb`/`msfconsole` output, and **blocks `apt`/`apt-get`** (`FORBIDDEN_COMMANDS`).
- **Output:** an `Action:/Observation:` transcript string.

### 2.7 Summarizer — `actions/plan_summary.py::PlannerSummary`
- `get_summary()` — reads finished tasks of prior phases' plans and asks the LLM
  (`DeepPentestPrompt.write_summary`) for a <1000-word phase summary; this becomes the
  `context` fed into the next phase's planning prompt.
- Also relevant: the long-output summarizer in `Role._react` (`summary_result` prompt) and
  the `check_success` judgment in `Planner.update_plan`.
- **Input:** finished `Task`s. **Output:** a natural-language summary string.

### 2.8 LLM access layer — `server/chat/chat.py::_chat`
Single choke point for every model call.
- Picks the client from `llm_config.llm_model`: `OpenAIChat` (OpenAI-compatible endpoints,
  incl. local vLLM/LM Studio) or `OllamaChat`.
- Loads conversation history from MySQL (last `history_len` messages), appends the query,
  calls the model, persists query+response.
- **If `enable_rag` and a `kb_name` is passed:** retrieves docs (`search_docs`), reranks
  (`LangchainReranker`), scrubs IPs to `<target>`, and injects them into the prompt — this
  is the **Memory-Retriever** in action.
- Returns `(text, conversation_id)` for new conversations, or just `text` when continuing
  one.

### 2.9 RAG / knowledge base — `rag/`, `server/`, `web/`
- `rag/kb/service/milvus_kb_service.py`, `rag/retriever/`, `rag/embedding/`,
  `rag/reranker/` — Milvus-backed vector store, embeddings, reranking, document parsers.
- `server/server.py` + `server/api/kb_route.py` — FastAPI service for KB CRUD.
- `web/webui.py` — Streamlit UI for knowledge-base management.
- Adapted from Langchain-Chatchat. **Only used when `enable_rag: true`.**

### 2.10 Persistence — `db/`, `utils/session.py`
SQLAlchemy over MySQL (`mysql+pymysql`). Tables: `sessions`, `plans`, `tasks`,
`conversations`, `messages`. `Plan`/`Task` pydantic models hold the PTG; `Plan.current_task`
returns the first unfinished task in topological order (`get_sorted_tasks`, Kahn's
algorithm; raises on cyclic dependencies).

### 2.11 Baselines — `experiment/`
`pentestgpt` (PentestGPT reimplementation) and `base` (single-agent "CTF player") are
comparison baselines, **not** part of the VulnBot pipeline. They share the Executor/shell
layer but have their own agent/session handling (`experiment/llm_ollama.py`).

---

## 3. Data Flow (plain language)

```
             ┌─────────────────────────── one `vulnbot` run ───────────────────────────┐
             │                                                                          │
 user  ──►  Session(init_description, role=Collector)                                   │
             │                                                                          │
             ▼                                                                          │
   ┌───────────────── PHASE (Collector → Scanner → Exploiter) ─────────────────┐        │
   │                                                                           │        │
   │  Summarizer.get_summary(prev phases)  ──► context                         │        │
   │            │                                                              │        │
   │            ▼                                                              │        │
   │  Role._plan:  init 2 LLM conversations (plan_chat, react_chat)            │        │
   │            │                                                              │        │
   │            ▼                                                              │        │
   │  WritePlan.run ──LLM──► <json> task graph ──► PTG (Plan + Task deps)      │        │
   │            │                                                              │        │
   │            ▼                                                              │        │
   │  Planner.next_task_details ──LLM(+RAG)──► detailed next task             │        │
   │            │                                                              │        │
   │            ▼   ╔══════════ react loop  (≤ max_interactions) ══════════╗   │        │
   │  WriteCode.run ──LLM──► <execute> shell cmds                          ║   │        │
   │            │                                                          ║   │        │
   │            ▼                                                          ║   │        │
   │  ExecuteTask ──► ShellManager/RemoteShell ──SSH──► Kali host ──► output║  │        │
   │            │                                                          ║   │        │
   │            ▼                                                          ║   │        │
   │  Planner.update_plan:  check_success(LLM) ─► WritePlan.update ─► merge║   │        │
   │            │                                    (revised PTG)         ║   │        │
   │            ╚═══════════════════ next task ══════════════════════════╝    │        │
   │            │                                                              │        │
   │            ▼                                                              │        │
   │  put_message: persist tasks ──► hand off to next role                     │        │
   └───────────────────────────────────────────────────────────────────────────┘      │
             │                                                                          │
             ▼                                                                          │
   save_session ──► MySQL                                                               │
             └──────────────────────────────────────────────────────────────────────────┘

  Cross-cutting: every LLM arrow goes through server/chat/chat.py::_chat
  (history from MySQL; optional RAG retrieval+rerank when enable_rag=true).
```

---

## 4. Entry Points & Run Commands

All commands go through `cli.py` (a `click` group).

| Command | Handler | Purpose |
|---------|---------|---------|
| `python cli.py init` | `cli.py::init` | Create data dirs, create MySQL tables, generate default config YAMLs. |
| `python cli.py start -a` | `startup.py::main` | Start the RAG API (FastAPI) and/or WebUI (Streamlit). `--api` / `-w` / `-a`. |
| `python cli.py vulnbot -m {N}` | `pentest.py::main` | **The main pentest run.** `N` = max react interactions per phase. |
| `python cli.py pentestgpt` | `experiment/pentestgpt.py::main` | PentestGPT baseline. |
| `python cli.py base` | `experiment/base.py::main` | Single-agent baseline. |

Typical order: `init` → (optional) `start -a` if RAG is enabled → `vulnbot -m 5`.

`vulnbot` prompts interactively: continue a previous session? then "describe the
penetration testing task" (include the target IP here).

---

## 5. Configuration & Model Swap

Config is file-driven via pydantic-settings (`config/config.py`,
`config/pydantic_settings_file.py`). Files live under `PENTEST_ROOT` (env var, defaults to
repo root `.`) and hot-reload on change.

| File | Class | Holds |
|------|-------|-------|
| `basic_config.yaml` | `BasicConfig` | mode (auto/manual/semi), `enable_rag`, Kali SSH creds, server hosts, log path |
| `db_config.yaml` | `DBConfig` | MySQL connection |
| `kb_config.yaml` | `KBConfig` | Milvus + retrieval params (RAG) |
| `model_config.yaml` | `LLMConfig` | **LLM selection** |

**Where the LLM is swapped — `model_config.yaml`:**
- `llm_model`: `openai` or `ollama` — selects the client in `server/chat/chat.py`
  (`LLMType` in `server/utils/utils.py`).
- `base_url`, `api_key`, `llm_model_name` — the actual endpoint + model. Any
  OpenAI-compatible server (vLLM, LM Studio, local gateways) works with `llm_model: openai`.
- `temperature`, `history_len`, `timeout` — generation + context settings.
- `embedding_models`, `rerank_model`, `embedding_type` — only used when RAG is on.

Sample copies of all four files (plus `.env.example`) are in `config_samples/`. Copy them
to `PENTEST_ROOT` and fill in real values, **or** run `python cli.py init` to have the
templates generated automatically. (Note: `*.yaml`/`*.json` are git-ignored, so live config
never gets committed; the `.example` samples are safe to commit.)

---

## 6. Where AutoPenBench Plugs In

AutoPenBench is the **evaluation environment**, not a code module in this repo. The wiring
is operational:
- The **Kali host** in `basic_config.kali` is the attacker box that executes tooling.
- The **target** is supplied in the interactive `init_description` (the task text, including
  the target IP). RAG context has IPs scrubbed to `<target>` in
  `server/utils/utils.py::replace_ip_with_targetip`.
- AutoPenBench provides the vulnerable target VMs; VulnBot reaches them from the Kali host.
- The `experiment/base.py` "CTF player" `auto_init` prompt is the AutoPenBench-style
  autonomous baseline harness.

There is **no explicit AutoPenBench driver/scoring code checked into this fork** — see
[Open Questions](#open-questions).

---

## 7. Setup & Runnability (this phase)

**Target runtime (per README):** Python 3.11.11 + full `requirements.txt`, plus external
services: **MySQL** (always), an **LLM endpoint** (OpenAI-compatible or Ollama), a **Kali
Linux SSH host** (to actually execute), and **Milvus** (only if `enable_rag`).

**What was done here (no real attack executed):**
- Created a `.venv` and installed the **core** dependency subset (click, rich, loguru,
  prompt-toolkit, pydantic + pydantic-settings + pyyaml, SQLAlchemy, PyMySQL, openai,
  ollama, httpx, tenacity, memoization, ruamel.yaml, paramiko, pexpect, fastapi, uvicorn,
  numexpr). On this Python 3.13 host the exact pins in `requirements.txt` don't all have
  wheels, so relaxed versions were used for the core set.
- **Verified working:** the config + init/template layer. `Configs.create_all_templates()`
  generates all four live YAMLs (`basic_config.yaml`, `db_config.yaml`, `kb_config.yaml`,
  `model_config.yaml`) and `make_dirs()` creates the data/log dirs — the non-DB part of
  `python cli.py init`.
- Wrote sample config files under `config_samples/` and `.env.example`.
- **Import boundary found:** `python cli.py --help` does **not** import cleanly, because
  `cli.py` eagerly imports `startup → server.server → rag.kb …`, which pulls in
  **langchain** (and the wider RAG/ML stack) at module load — *regardless of*
  `enable_rag`. So the full CLI cannot start until the RAG stack is present.
- The heavy RAG/ML stack (langchain*, milvus/pymilvus, sentence-transformers, transformers,
  rapidocr, opencv, unstructured, PyMuPDF, streamlit) was **not** installed here — those
  pins target Python 3.11. Install them on a **Python 3.11.11** environment via
  `pip install -r requirements.txt` to get a fully importable CLI.
- Note: newer `pydantic-settings` needs the `pyyaml` extra for its YAML source; the pinned
  2.6.1 on Python 3.11 does not.

**To run the full pipeline** (outside this documentation phase): provision MySQL, an LLM
endpoint, and a Kali host; fill `model_config.yaml` + `db_config.yaml` +
`basic_config.yaml`; `python cli.py init`; then `python cli.py vulnbot -m 5`.

---

## 7A. Dockerized lab (Phase 0 — this fork)

The lab runs in `docker compose` on an **isolated** network; the agent reaches a
containerized Kali tooling host instead of a host-local machine. Authoritative doc:
[`INFRA.md`](INFRA.md).

- **Services:** `kali-tools` (Kali + `kali-linux-headless`; exposes **SSH** and
  **msfrpcd:55553**), `target` (deliberately vulnerable), `ollama` (local LLM), and two agent
  variants — `agent-local` (labnet only) / `agent-api` (labnet + egress) — chosen by compose
  **profile** (`local`/`api`).
- **Isolation:** `labnet` is `internal: true` (no internet). Egress is attached to `agent-api`
  only; in the `local` profile nothing has egress. Target + kali never reach the internet.
- **Agent→kali channels:** **SSH** for arbitrary tools (nmap/enumeration/custom; raw stdout is
  the observation **O**); **msfrpc** via `pymetasploit3` for Metasploit modules. Rule + check:
  `docker/agent/smoke_channels.py`.
- **Lifecycle:** `lab.ps1` (Windows) / `make` (Linux/CI) — `up`/`dev-up`/`down`/`shell-*`/`smoke`.
- Secrets in `.env`; Kali apt mirror pinned via `KALI_MIRROR_HOST` (default mirror 403s in some
  regions).

## 7B. Belief layer (Phase 2.1–2.5 — this fork)

The POMDP belief-state. 2.1–2.5 are implemented; only `run_agent` (top-level control loop, wired
during eval) is still stubbed. See §8 for attach points.

- **`pomdp/belief_state.py`** — the factored-JSON belief `b` over hidden state S (per host: `os`,
  `services`, `vulns`, `access`, `honeypot_likelihood`). `new_belief`/`new_host_prior`/
  `add_host` build conventional b0 priors (uniform OS with mass on `unknown`); `Action` +
  `GAMMA` defined. **`update_belief` (2.2)** — LLM-likelihood (Z) soft Bayesian update via
  `Z_PROMPT_TEMPLATE`, code-normalized, ε-floored (soft). **`choose_action` (2.4, π)** — argmax
  utility: RECON valued by normalized entropy (info-gain) of the probed factor, EXPLOIT/LATERAL/
  PRIVESC by R. **`score_action` (2.5, R)** — `P(succeeds|b)·value − cost − detection`.
  `run_agent` remains **`NotImplementedError`** (top-level loop) or replaced by the author's file
  with the same names. **Never branches on S.**
- **`pomdp/priors.py` (2.5)** — stdlib-only, **offline** reward-priors source: CVSS +
  exploit-maturity → `value`/`cost`/`detection_risk` + b0 `vuln_prior_present`. Built-in CVE
  catalog + optional git-ignored `data/priors/exploit_catalog.json` override; `enrich_action`,
  `seed_vuln_priors`, `merge_catalog` (RAG-enrichment hook — no network, no eager `rag/` import).
- **`pomdp/belief_store.py`** — stdlib-only per-run JSON **Belief Store** under
  `data/beliefs/<run_id>/` (`save`/`load_latest`/`load_step`/`steps`/`history`); one file per
  step forms the belief trace.
- **`roles/role.py`** — guarded, best-effort hooks: `_belief_init` (in `_plan`) instantiates b;
  `_belief_persist` (in `_react`, the Updater) saves it each step; `_belief_choose_next` (the
  policy, set as `Planner.task_selector`) picks among dependency-ready PTG tasks;
  `_task_to_action_for` maps a task → `Action` and enriches its R inputs via `priors.enrich_action`.
  A belief failure never breaks a run; `VULNBOT_BELIEF_POLICY=0` disables belief-driven task
  selection (ablation).

---

## 8. Integration Points

> Attachment locations for the belief-state modules. **All four are implemented**
> (Belief Store 2.1, Updater 2.2, Belief-Conditioned Planner 2.4, Reward+priors 2.5); only the
> top-level `run_agent` control loop is still stubbed in `pomdp/belief_state.py`.

### 8.1 Summarizer → **Belief Updater**  *(DONE — Phase 2.2)*
- **Where:** `roles/role.py::Role._belief_persist` (called from `_react` with the observation O)
  → `pomdp/belief_state.py::update_belief`. `actions/plan_summary.py::PlannerSummary` documents the
  attach point and stays the cross-phase context signal.
- **How:** the LLM is the observation model — a `Z_PROMPT` asks for per-hypothesis LIKELIHOODS
  `P(O | h)` only; the CODE does the Bayesian normalization (posterior ∝ prior × Z). Z is floored
  at ε so the update is **soft** (a failed exploit moves 0.70 → ~0.57, never → 0). `samples > 1`
  averages several LLM calls (self-consistency). Formal partial-observability tests land in 2.3.

### 8.2 Memory → **Belief Store**  *(DONE — Phase 2.1)*
- **Where:** `pomdp/belief_store.py` (per-run JSON store) + the guarded hooks in `roles/role.py`
  (`_belief_init`, `_belief_persist`). Sibling to the RAG/Memory-Retriever path in
  `server/chat/chat.py::_chat` and the `db/` persistence layer.
- **Status:** implemented as an inspectable factored-JSON store under `data/beliefs/`, keyed by
  plan id, one snapshot per step (the belief trace). The belief *content* it stores comes from
  `pomdp/belief_state.py`; the update that changes that content lands in 2.2.

### 8.3 Planner → **Belief-Conditioned Planner**  *(DONE — Phase 2.4)*
- **Where:** `pomdp/belief_state.py::choose_action` (policy π) drives the PTG pick via
  `db/models/plan_model.py::Plan.ready_tasks` (dependency-ready frontier) +
  `actions/planner.py::Planner.task_selector` (optional callable, guarded in `next_task_details`,
  falls back to the deterministic topo pick on any failure) + `roles/role.py::_belief_choose_next`
  (set in `_plan`).
- **How:** among dependency-ready tasks, π scores candidate actions by **information-gain**
  (normalized entropy of the factor a recon probes) vs. **exploit-value** (`score_action`'s R),
  argmax. `VULNBOT_BELIEF_POLICY=0` disables it (the free with/without-belief ablation).

### 8.4 Reward + priors → **`score_action` + `pomdp/priors.py`**  *(DONE — Phase 2.5)*
- **Where:** `pomdp/belief_state.py::score_action` (R = `P(succeeds|b)·value − cost − detection`)
  fed by `pomdp/priors.py`; `roles/role.py::_task_to_action_for` calls `priors.enrich_action` to
  fill `value`/`cost`/`detection_risk`, and `priors.seed_vuln_priors` seeds b0 vuln priors.
- **How:** `pomdp/priors.py` is a stdlib-only, **offline** CVSS/exploit-maturity source (built-in
  CVE catalog + optional git-ignored `data/priors/exploit_catalog.json`; `merge_catalog` is a
  later RAG-enrichment hook, no network, no eager `rag/` import). Host `honeypot_likelihood` feeds
  the detection term, so the policy steers away from suspected honeypots.

---

## 9. Open Questions

1. **AutoPenBench harness.** No explicit AutoPenBench integration/scoring code is present
   in this fork. Is evaluation expected to be driven externally (manually pointing Kali +
   `init_description` at benchmark targets), or is a harness meant to be added?
2. **Python version.** README pins 3.11.11; only 3.13 is available on this machine. Full
   `requirements.txt` (numpy 1.26.4, pymilvus, sentence-transformers, etc.) targets 3.11.
   Confirm the intended runtime before attempting a full install.
3. **`config/pydantic_settings_file.py`** uses `__context: os.Any` in `model_post_init`
   (`os.Any` is not a real symbol). It parses because annotations aren't evaluated at
   runtime, but flag it as a latent typo — do not "fix" during this read-only phase.
4. **Two conversation memories.** The main pipeline stores history in MySQL
   (`server/chat/chat.py`) while `experiment/llm_ollama.py` keeps an in-memory
   `conversation_dict`. Confirm the belief work should target the MySQL path (VulnBot
   proper), not the experiment baselines.
5. **RAG default off.** `enable_rag` defaults to `false`, so the Memory-Retriever is
   inactive unless explicitly configured. Should the Belief Store reuse the RAG/Milvus
   machinery, or be an independent store? (Affects the 8.2 attachment.)
6. **Action types.** The planner prompt advertises actions `Shell, Web`, but the Executor
   only special-cases `Shell` (everything else falls through to manual in `semi` mode).
   Confirm whether `Web` is exercised in the benchmark runs.
7. **Eager RAG coupling.** `cli.py` imports `startup → server → rag → langchain` at load
   time, so *every* subcommand (even `vulnbot` with `enable_rag: false`) requires the full
   RAG/ML stack to be installed. Is this intended, or should RAG imports be lazy? (Not
   changed in this read-only phase — noted for the belief-work environment setup.)
