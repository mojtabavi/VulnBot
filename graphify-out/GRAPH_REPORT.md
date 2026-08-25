# Graph Report - .  (2026-08-25)

## Corpus Check
- 4 files · ~120,910 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1369 nodes · 2748 edges · 98 communities (90 shown, 8 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 122 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]

## God Nodes (most connected - your core abstractions)
1. `KBService` - 37 edges
2. `Executor` - 31 edges
3. `KnowledgeFile` - 30 edges
4. `BeliefAgent` - 29 edges
5. `Channel` - 26 edges
6. `Role` - 25 edges
7. `ChannelError` - 24 edges
8. `ApiRequest` - 22 edges
9. `MilvusKBService` - 20 edges
10. `AnthropicChat` - 20 edges

## Surprising Connections (you probably didn't know these)
- `ExecuteResult` --uses--> `Mode`  [INFERRED]
  actions/execute_task.py → config/config.py
- `ExecuteTask` --uses--> `Mode`  [INFERRED]
  actions/execute_task.py → config/config.py
- `PlannerSummary` --uses--> `DeepPentestPrompt`  [INFERRED]
  actions/plan_summary.py → prompts/prompt.py
- `BaseGPT` --uses--> `WriteCode`  [INFERRED]
  experiment/base.py → actions/write_code.py
- `BaseGPT` --uses--> `ShellManager`  [INFERRED]
  experiment/base.py → actions/shell_manager.py

## Import Cycles
- None detected.

## Communities (98 total, 8 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (40): CandidateFn, BeliefAgent, Run the belief loop for `session_id` and return the final belief.          `host, Recon (probe each host) + priors-enriched exploit actions for seeded vulns., Gate an action on human approval when it is high-impact (exploit/lateral/privesc, Decide whether to run `action`: returns "approve" | "deny" | "quit".          Pr, Block on control replies until the human approves/denies/quits. `step` runs this, Between steps: non-blocking check for a `pause`/`quit`/`step` command. A `pause` (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (32): BeliefStore, db_reachable(), _extract_target(), initialize_session(), main(), _mysql_dsn(), preload_session(), R1 belief-first run (`--agent`): drive the standalone `BeliefAgent` loop instead (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (31): BasicConfig, Path, PathLike, BeliefStore, _default_root(), Belief Store — persistence for the POMDP belief `b`.  Maps the Memory → Belief S, Full belief trace (all steps in order) for `run_id`., Persist and reload factored-JSON beliefs per run, one file per step. (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (31): Base, List, Message, Conversation, FileDocModel, KnowledgeFileModel, Config, Message (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (26): AsyncClient, Client, DataFrame, _GeneratorContextManager, GridOptionsBuilder, config_aggrid(), file_exists(), knowledge_base_page() (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (35): beliefsDir(), beliefView, Factor, fmtDist(), formatBelief(), listRuns(), loadLatest(), ClassifiedLog (+27 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (29): Executor, Runs actions across pluggable channels behind `run(action) -> Observation`., exploit_action(), Flaky, msf(), TL-1.7 — the Executor layer (R3): router policy, Observation normalization, and, Raises `err_cls` for the first `fail_n` calls, then succeeds. Counts calls., recon_action() (+21 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (12): AsyncCallbackManagerForRetrieverRun, Document, KBService, 使用content中的文件更新向量库         如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True, 传入参数为： {doc_id: Document, ...}         如果对应 doc_id 的值为 None，或其 page_content 为空，, 通过file_name或metadata检索Document, 保存向量库:FAISS保存到磁盘，milvus保存到数据库。PGVector暂未支持, 向知识库添加文件         如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (18): Exception, ChannelError, Executor facade + Channel adapter interface (R3, TL-1.1).  ONE contract turns a, A channel could not run the action (unreachable, auth, RPC down). The Executor c, Multi-channel Kali execution layer (R3).  `Executor.run(action) -> Observation`, _env_truthy(), McpChannel, MCP channel — flag-gated, OFF by default (R3, TL-1.6).  Channel C of the Executo (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (20): BaseSettings, CommentedBase, BaseFileSettings, _cached_settings(), import_yaml(), _lazy_load_key(), MyBaseModel, generate yaml template with default object         sub_comments indicate how to (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (10): ExecuteResult, ExecuteTask, RunCode, ShellManager, WriteCode, BaseModel, Execute, ExtractCode (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (19): get_kb_details(), Config, KnowledgeBaseModel, KnowledgeBaseSchema, delete_kb_from_db(), kb_exists(), list_kbs_from_db(), load_kb_from_db() (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (16): PlannerSummary, Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses, Planner, import_tasks_from_json(), merge_tasks(), merge_tasks_from_json(), parse_tasks(), preprocess_json_string() (+8 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (28): Any, Module-level convenience the `belief_state.run_agent` delegator (TL-2.2) will ca, run_agent(), _action_utility(), add_host(), _default_dist(), _entropy(), _get_dist() (+20 more)

### Community 14 - "Community 14"
Cohesion: 0.21
Nodes (24): Action, choose_action(), new_belief(), Return a fresh factored belief b0 for a run/session.      `hosts` may be empty a, Policy π: pick the next action given the current belief (argmax utility).      T, A candidate action the policy chooses among.      `value`, `cost`, `detection_ri, _exploit_action(), Phase 2.3 — partial observability must be provably real.  These lock the four pr (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (19): commandMeta(), CommandResult, COMMANDS, CommandSpec, fetchingLabel(), handleCommand(), getModel(), getModelConfig() (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (17): init(), Event, FastAPI, create_app(), main(), run_api_server(), run_webui(), _set_app_event() (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.26
Nodes (19): create_kb(), delete_kb(), list_kbs(), delete_docs(), download_doc(), list_files(), 通过多线程将上传的文件保存到对应知识库目录内。     生成器返回保存结果：{"code":200, "msg": "xxx", "data": {"know, _save_files_in_thread() (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (10): CSVLoader, FilteredCSVLoader, Load data into document objects., RapidOCRDocLoader, RapidOCRLoader, get_ocr(), RapidOCRPDFLoader, RapidOCRPPTLoader (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (18): Channel, _default_router(), _make_default_router(), One execution transport to Kali. Adapters: `ssh_channel` (1.2), `msf_channel` (1, True if this channel can run `action` (e.g. msfrpc only for actions naming an MS, Release any held resource (SSH session, RPC client). Best-effort., Fallback router: every channel that supports the action, registration order pres, The Executor's default: the TL-1.4 policy router (channel by action type + logge (+10 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (12): TL-0.3 — the loopback control channel round-trips a frame each direction (R2 tra, test_control_frame_roundtrip_both_directions(), test_no_client_is_non_fatal(), ControlClient, ControlServer, _FramedConn, Loopback control channel — the CLI↔agent back-channel for human-in-the-loop (R2), Send one event frame to the CLI (agent → CLI). False if no client / send failed. (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (15): clean_dirb_output(), clean_msfconsole_output(), Validates command against forbidden commands list., Executes command with improved output handling and error recovery., Handles normal command execution flow., Attempts to decode byte data using multiple encodings., Clean the output from the 'dirb' command., Clean the output from the 'msfconsole' command. (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (23): Belief-Cond. Planner [2.4] choose_action: info-gain vs exploit-value (pi), belief_state.py [2.1-2.5] b, Action, GAMMA; update/choose/score implemented, Belief Store [2.1] belief_store.py data/beliefs/*.json, Belief Updater [2.2] update_belief: LLM Z + soft Bayes, control.py [TL-0] loopback HITL socket (R2 back-channel), events.py [TL-0] JSONL event log (R4) data/runs/*.jsonl, Executor ExecuteTask (execute_task.py), Executor + channels SSH/msfrpc/MCP + router (executor/) [R3 TL-1] (+15 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (21): App(), DbSettings, DEFAULT_PREFS, dumpYaml(), getAuthMode(), getProviderId(), here, isFirstRun() (+13 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (22): au, bs, cmd, ef, evs, exFetch, failSummary, ids (+14 more)

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (16): asDist(), asNum(), asStr(), EventRecord, eventsPathFor(), firstLine(), latestRunId(), parseEventLine() (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (10): Action, _note_fallback(), Record the routing outcome as an R4 `decision` event (kind=route): the candidate, Run one channel with the timeout budget + safe retries. Returns a stamped Observ, `ch.run` under the per-attempt budget. No budget → direct call. With a budget, r, Run `action` and return a normalized `Observation` stamped with `action_id`., Record the failed attempts that preceded a successful call under a reserved meta, Run an action's shell command(s) on Kali over SSH; raw stdout → Observation. (+2 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (15): _anthropic_has_thinking(), _downgrade_thinking(), _effective_thinking(), _is_retryable(), _notify_llm_ok(), OpenAIChat, The configured level, capped by any downgrade forced by a prior rate limit., Lower the process-wide cap to one step below `current` (floor 'off') after a 429 (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.16
Nodes (20): _catalog_path(), _clamp(), enrich_action(), load_catalog(), _maturity_w(), merge_catalog(), Priors source (Phase 2.5): reward R ingredients from public exploit signals.  Fe, Return {value, cost, detection_risk} for an action from CVSS + maturity signals. (+12 more)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (14): AnthropicChat, Native Anthropic (Claude) client. Two auth modes:       - api_key: Anthropic(ap, _cfg(), _FakeAnthropic, _FakeMessages, Offline unit test for the native AnthropicChat wrapper (B5).  No live API call:, test_api_key_auth_uses_x_api_key(), test_chat_maps_history_and_concatenates_text() (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (14): JSONLoader, files2docs_in_thread(), get_doc_path(), get_kb_path(), get_loader(), get_LoaderClass(), get_vs_path(), JSONLinesLoader (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (19): AuthTokens, AuthUrl, b64url(), beginLogin(), buildAuthUrl(), completeLogin(), exchangeCode(), ExchangeOpts (+11 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (7): main(), PentestGPT, PentestGPTPrompt, prompt_ask(), prompt_continuation(), The continuation: display line numbers and '->' before soft wraps.     Notice t, A custom prompt function that adds a key binding to accept the input.     In si

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (17): ModelSettings, fetchModels(), FetchModelsOpts, headersFor(), parseModels(), AuthMode, BY_ID, firstLlmStep() (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (8): ABC, BaseRetriever, CallbackManagerForRetrieverRun, BaseRetrieverService, MilvusRetriever, MilvusVectorstoreRetrieverService, VectorStore, VectorStoreRetriever

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (11): BaseFileSettings, ConfigsContainer, DBConfig, KBConfig, LLMConfig, Mode, Enum, StrEnum (+3 more)

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (6): get_embeddings(), Embeddings, SupportedVSType, list_file_num_docs_id_by_kb_name_and_file_name(), 列出某知识库某文件对应的所有Document的id。     返回形式：[str, ...], MilvusKBService

### Community 37 - "Community 37"
Cohesion: 0.22
Nodes (16): getKali(), COMPOSE_BASE, dbReachable(), docker(), dockerAvailable(), ensureDb(), ensureKali(), initDb() (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (14): DEFAULT_DB, ExecutorMode, getDbConfig(), listProviders(), MysqlMode, savePrefs(), getProvider(), FilterSelect() (+6 more)

### Community 39 - "Community 39"
Cohesion: 0.23
Nodes (4): Conversation, Message, OLLAMAPI, OPENAI

### Community 40 - "Community 40"
Cohesion: 0.18
Nodes (12): Task DAG, Executor, Feedback (success/failure), Generated Plan, Generator, Memory Retriever, Next Task Details, Penetration Path Planning (+4 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (9): ApproveFn, BeliefLLM, GoalFn, _default_goal(), BeliefAgent — the standalone POMDP control loop (R1, TL-2.1).  This is the integ, # NOTE: `action_type` (not `type`) — `type` is EventLog.append's positional para, Z self-consistency sample count. Explicit arg wins; else the shared     `belief_, Default stop predicate: a host is believed rooted, or the last observation clear (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (8): _notify_llm_wait(), Human-ish status tag for a failed API call (HTTP code if we have one, else class, tenacity before_sleep hook: announce we're waiting on the API + will retry after, _status_of(), socket, _clean(), emit(), Structured run-progress markers for the octopus CLI.  The pentest pipeline strea

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (4): file_exists_in_db(), TextSplitter, KnowledgeFile, make_text_splitter()

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (10): Control Channel (utils/control.py, HITL), JSON Event Log (utils/events.py), Executor module, Generator module (WriteCode), R1-R4 Shared Contracts (TL-0), MCP Channel (optional efficiency layer), msfrpc Channel (pymetasploit3), Unified Observation Schema (pomdp/observation.py) (+2 more)

### Community 46 - "Community 46"
Cohesion: 0.20
Nodes (6): ChannelTimeout, The channel exceeded its time budget. Distinct from `ChannelError` because the t, Minimal EventLog stand-in capturing (type, fields) appends., Blocks `secs` before returning. Counts calls (proves no auto-retry on timeout)., _RecEvents, Slow

### Community 47 - "Community 47"
Cohesion: 0.28
Nodes (9): agent service (agent-local / agent-api), egress (outbound bridge network), kali-tools service, labnet (internal isolated network), ollama service (local LLM), target service (vulnerable victim), Kali Mirror Pin (KALI_MIRROR_HOST, 403 workaround), Network Isolation Model (labnet internal / egress) (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (9): Belief Store (Phase 2.1), Memory-Retriever (RAG path), Explicit-Belief-State Layer (pomdp/), Langchain-Chatchat, Multi-Agent Collaborative Framework, VulnBot Framework, VulnBot Paper (arXiv 2501.13411), LangChain RAG Stack (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.25
Nodes (9): Belief Updater (Phase 2.2), Summarizer module (PlannerSummary), Multi-Channel Kali Execution Layer (R3), BeliefAgent Loop (run_agent, stubbed), Observation Model Z (LLM likelihoods, soft Bayes), Partial-Observability Tests (tests/test_belief.py), Policy pi (choose_action, info-gain vs exploit-value), POMDP Tuple (S,A,O,T,Z,R,b,gamma) (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.31
Nodes (3): MsfChannel, Run an action's Metasploit module over msfrpc; structured RPC result → Observati, The MSF module path this action names, or None. `params['module']` wins over `to

### Community 51 - "Community 51"
Cohesion: 0.39
Nodes (8): _mcp_action(), mcp_env(), Helper to toggle the MCP flag + server/version env within a test., test_mcp_disabled_by_default_is_noop(), test_mcp_enabled_unverified_raises_channel_error(), test_mcp_unverified_falls_back_in_executor(), test_mcp_verified_with_client_returns_observation(), test_mcp_verified_without_transport_raises()

### Community 52 - "Community 52"
Cohesion: 0.32
Nodes (8): mysql service (data profile), LLM Access Choke Point (_chat), Four Config YAML Files, LLM Configuration (model_config.yaml), Extended Thinking (native Anthropic, version-gated), MySQL Provisioning (local vs docker), /run Crash Cascade (MySQL/LLM-sentinel root cause), anthropic>=0.49 dependency

### Community 53 - "Community 53"
Cohesion: 0.36
Nodes (3): BaseGPT, main(), 针对给定执行结果，传入模型，输出下一步任务

### Community 54 - "Community 54"
Cohesion: 0.25
Nodes (5): Observation, The normalized result of running one Action through a channel.      Fields:, JSON-ready dict (the `observation` event record body, R4)., Rebuild from `to_dict()` output; ignores unknown keys so the schema can grow., A normalized failure Observation — `error` is also surfaced as `raw` so the Beli

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (7): AutoPenBench (evaluation environment), Belief-Conditioned Planner (Phase 2.4), Planner module, Penetration Task Graph (PTG), Reward + Priors (Phase 2.5), Three Sequential Phases (Collector-Scanner-Exploiter), Reward R (score_action)

### Community 56 - "Community 56"
Cohesion: 0.62
Nodes (6): arrow(), edge_point(), nid(), node(), seed(), title()

### Community 57 - "Community 57"
Cohesion: 0.38
Nodes (3): rounded_rect(), tx(), ty()

### Community 58 - "Community 58"
Cohesion: 0.47
Nodes (5): main(), msfrpc_channel(), SSH into kali-tools and run nmap against the target; return raw output O., Connect to msfrpcd on kali-tools and return the number of exploit modules., ssh_channel()

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (3): LangchainReranker, Compress documents using Cohere's rerank API.          Args:             docu, Document compressor that uses `Cohere Rerank API`.

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): Exploitation Phase, Reconnaissance Phase, Role Profile (Name/Tools/Goal), Scanning Phase

## Knowledge Gaps
- **91 isolated node(s):** `Factor`, `FRAMES`, `Config`, `Config`, `Config` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BeliefAgent` connect `Community 0` to `Community 1`, `Community 42`, `Community 13`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `KBService` connect `Community 7` to `Community 34`, `Community 36`, `Community 11`, `Community 44`, `Community 17`, `Community 30`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `KBService` (e.g. with `KnowledgeBaseSchema` and `MatchDocument`) actually correct?**
  _`KBService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Action` (e.g. with `_exploit_cands()` and `_recon_cands()`) actually correct?**
  _`Action` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Executor` (e.g. with `FakeChannel` and `Flaky`) actually correct?**
  _`Executor` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `KnowledgeFile` (e.g. with `KBService` and `KBServiceFactory`) actually correct?**
  _`KnowledgeFile` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses`, `Handles SSH output processing with improved encoding detection and buffering.`, `Attempts to decode byte data using multiple encodings.` to the rest of the system?**
  _286 weakly-connected nodes found - possible documentation gaps or missing edges._