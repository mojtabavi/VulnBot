# VulnBot — Architecture Reference

![VulnBot current architecture & data flow](docs/project_schematic.png)

*Source: [`project_schematic.excalidraw`](project_schematic.excalidraw) — gray = current
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

## 8. Integration Points

> These are **attachment locations only** for the three future belief-state modules.
> Nothing below is implemented in this phase.

### 8.1 Summarizer → **Belief Updater**
- **Where:** `actions/plan_summary.py::PlannerSummary.get_summary()` and the long-output
  summarization branch in `roles/role.py::Role._react` (the `summary_result` path), plus
  the `check_success` judgment in `actions/planner.py::Planner.update_plan`.
- **Why here:** this is exactly where raw tool output (the *observation*) is consumed and
  condensed. A Belief Updater would sit at this junction, using the LLM as an observation
  model to perform a Bayesian update of the factored belief after each task result.

### 8.2 Memory → **Belief Store**
- **Where:** the RAG/Memory-Retriever path in `server/chat/chat.py::_chat` (the
  `search_docs` + rerank block) and the `rag/` + `db/` persistence layers.
- **Why here:** the Memory-Retriever already assembles external context that is injected
  into prompts. The Belief Store (a factored JSON belief over hidden network state) would
  be a sibling store, persisted like the other `db/` entities and read into the prompt
  context the same way Memory is.

### 8.3 Planner → **Belief-Conditioned Planner**
- **Where:** `actions/planner.py::Planner.plan` / `update_plan` / `next_task_details` and
  the task ordering in `actions/write_plan.py` (`merge_tasks` / PTG topological order in
  `db/models/plan_model.py`).
- **Why here:** this is where the next action/task is selected and ordered. A
  belief-conditioned planner would score candidate actions by information-gain vs.
  exploit-value using the current belief, replacing or augmenting the current
  LLM-emitted task ordering.

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
