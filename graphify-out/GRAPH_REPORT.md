# Graph Report - .  (2026-08-24)

## Corpus Check
- 43 files · ~102,357 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1081 nodes · 2123 edges · 79 communities (74 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 83 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]

## God Nodes (most connected - your core abstractions)
1. `KBService` - 37 edges
2. `KnowledgeFile` - 30 edges
3. `Role` - 25 edges
4. `ApiRequest` - 22 edges
5. `_chat()` - 21 edges
6. `MilvusKBService` - 20 edges
7. `AnthropicChat` - 20 edges
8. `Action` - 16 edges
9. `update_belief()` - 16 edges
10. `build_logger()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `ExtractCode` --uses--> `ExecuteTask`  [INFERRED]
  experiment/extract_code.py → actions/execute_task.py
- `BaseGPT` --uses--> `WriteCode`  [INFERRED]
  experiment/base.py → actions/write_code.py
- `BaseGPT` --uses--> `ShellManager`  [INFERRED]
  experiment/base.py → actions/shell_manager.py
- `PentestGPT` --uses--> `ShellManager`  [INFERRED]
  experiment/pentestgpt.py → actions/shell_manager.py
- `Role` --uses--> `Planner`  [INFERRED]
  roles/role.py → actions/planner.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Three-Phase Pentest Pipeline** — docs_architecture_three_phases, docs_architecture_planner, docs_architecture_generator, docs_architecture_executor, docs_architecture_summarizer, docs_architecture_ptg [EXTRACTED 1.00]
- **POMDP Belief Agent Loop** — docs_pomdp_integration_pomdp_tuple, docs_pomdp_integration_observation_model_z, docs_pomdp_integration_policy, docs_pomdp_integration_reward, docs_pomdp_integration_belief_agent, docs_executor_observation_schema [EXTRACTED 1.00]
- **Isolated Docker Lab Topology** — docker_compose_labnet, docker_compose_egress, docker_compose_kali_tools, docker_compose_target, docker_compose_agent, docs_infra_network_isolation [EXTRACTED 1.00]
- **** — docs_project_schematic_planner_writeplan, docs_project_schematic_generator, docs_project_schematic_executor, docs_project_schematic_kali_tools, docs_project_schematic_target [EXTRACTED 1.00]
- **** — docs_project_schematic_belief_updater, docs_project_schematic_belief_state, docs_project_schematic_belief_store, docs_project_schematic_priors, docs_project_schematic_belief_cond_planner [INFERRED 0.85]

## Communities (79 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (82): App(), commandMeta(), CommandResult, COMMANDS, CommandSpec, fetchingLabel(), handleCommand(), DbSettings (+74 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (73): Any, Action, _action_utility(), ActionType, add_host(), choose_action(), _default_dist(), _entropy() (+65 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (38): ABC, _anthropic_has_thinking(), AnthropicChat, _downgrade_thinking(), _effective_thinking(), _is_retryable(), _notify_llm_ok(), _notify_llm_wait() (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (31): Base, List, Message, Conversation, FileDocModel, KnowledgeFileModel, Config, Message (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (25): AsyncClient, DataFrame, _GeneratorContextManager, GridOptionsBuilder, get_kb_details(), config_aggrid(), file_exists(), knowledge_base_page() (+17 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (19): CollectorPrompt, ExploiterPrompt, ScannerPrompt, Collector, Exploiter, Policy hook (Phase 2.4): let the belief pick among dependency-ready tasks., Stream the policy's pick (π) as a `decision` marker so the CLI can show, in plai, Stream the just-updated belief factor as a `belief` marker so the CLI renders th (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (35): beliefsDir(), beliefView, Factor, fmtDist(), formatBelief(), listRuns(), loadLatest(), ClassifiedLog (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (21): Path, PathLike, BeliefStore, _default_root(), Belief Store — persistence for the POMDP belief `b`.  Maps the Memory → Belief S, Full belief trace (all steps in order) for `run_id`., Persist and reload factored-JSON beliefs per run, one file per step., Persist `belief` as the step given by belief['step'] (and as latest.json). (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (15): socket, TL-0.3 — the loopback control channel round-trips a frame each direction (R2 tra, test_control_frame_roundtrip_both_directions(), test_no_client_is_non_fatal(), ControlClient, ControlServer, _FramedConn, Loopback control channel — the CLI↔agent back-channel for human-in-the-loop (R2) (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (20): BaseSettings, CommentedBase, BaseFileSettings, _cached_settings(), import_yaml(), _lazy_load_key(), MyBaseModel, generate yaml template with default object         sub_comments indicate how to (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (9): Document, KBService, 使用content中的文件更新向量库         如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True, 传入参数为： {doc_id: Document, ...}         如果对应 doc_id 的值为 None，或其 page_content 为空，, 通过file_name或metadata检索Document, 保存向量库:FAISS保存到磁盘，milvus保存到数据库。PGVector暂未支持, 向知识库添加文件         如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True, MatchDocument (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.23
Nodes (21): create_kb(), delete_kb(), list_kbs(), delete_docs(), download_doc(), list_files(), 通过多线程将上传的文件保存到对应知识库目录内。     生成器返回保存结果：{"code":200, "msg": "xxx", "data": {"know, _save_files_in_thread() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.16
Nodes (8): ExecuteResult, ExecuteTask, RunCode, ShellManager, BaseModel, Mode, Execute, RemoteShell

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (10): CSVLoader, FilteredCSVLoader, Load data into document objects., RapidOCRDocLoader, RapidOCRLoader, get_ocr(), RapidOCRPDFLoader, RapidOCRPPTLoader (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (15): clean_dirb_output(), clean_msfconsole_output(), Validates command against forbidden commands list., Executes command with improved output handling and error recovery., Handles normal command execution flow., Attempts to decode byte data using multiple encodings., Clean the output from the 'dirb' command., Clean the output from the 'msfconsole' command. (+7 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (23): Belief-Cond. Planner [2.4] choose_action: info-gain vs exploit-value (pi), belief_state.py [2.1-2.5] b, Action, GAMMA; update/choose/score implemented, Belief Store [2.1] belief_store.py data/beliefs/*.json, Belief Updater [2.2] update_belief: LLM Z + soft Bayes, control.py [TL-0] loopback HITL socket (R2 back-channel), events.py [TL-0] JSONL event log (R4) data/runs/*.jsonl, Executor ExecuteTask (execute_task.py), Executor + channels SSH/msfrpc/MCP + router (executor/) [R3 TL-1] (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (7): BaseGPT, main(), 针对给定执行结果，传入模型，输出下一步任务, Conversation, Message, OLLAMAPI, OPENAI

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (20): AuthTokens, AuthUrl, b64url(), beginLogin(), buildAuthUrl(), completeLogin(), exchangeCode(), ExchangeOpts (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (20): au, bs, cmd, ef, exFetch, failSummary, ids, lc (+12 more)

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (9): PlannerSummary, Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses, WriteCode, ExtractCode, DeepPentestPrompt, get_planner_by_id(), build_logger(), LoggerNameFilter (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (11): Planner, import_tasks_from_json(), merge_tasks(), merge_tasks_from_json(), parse_tasks(), preprocess_json_string(), WritePlan, _chat() (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (7): main(), PentestGPT, PentestGPTPrompt, prompt_ask(), prompt_continuation(), The continuation: display line numbers and '->' before soft wraps.     Notice t, A custom prompt function that adds a key binding to accept the input.     In si

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (15): get_kb_file_details(), add_docs_to_db(), add_file_to_db(), count_files_from_db(), delete_docs_from_db(), delete_file_from_db(), delete_files_from_db(), get_file_detail() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (8): AsyncCallbackManagerForRetrieverRun, BaseRetriever, CallbackManagerForRetrieverRun, BaseRetrieverService, MilvusRetriever, MilvusVectorstoreRetrieverService, VectorStore, VectorStoreRetriever

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (6): get_embeddings(), Embeddings, SupportedVSType, list_file_num_docs_id_by_kb_name_and_file_name(), 列出某知识库某文件对应的所有Document的id。     返回形式：[str, ...], MilvusKBService

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (10): JSONLoader, get_doc_path(), get_file_path(), get_kb_path(), get_loader(), get_LoaderClass(), get_vs_path(), JSONLinesLoader (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (9): BaseFileSettings, BasicConfig, ConfigsContainer, DBConfig, KBConfig, LLMConfig, Enum, Config (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (7): Config, KnowledgeBaseModel, KnowledgeBaseSchema, add_kb_to_db(), delete_kb_from_db(), list_kbs_from_db(), load_kb_from_db()

### Community 28 - "Community 28"
Cohesion: 0.22
Nodes (11): init(), db_reachable(), initialize_session(), main(), _mysql_dsn(), preload_session(), host:port from db_config - for clear preflight/error messages., Cheap 'SELECT 1' so a dead MySQL fails with one clear message, not a deref casca (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.32
Nodes (12): Event, FastAPI, create_app(), main(), run_api_server(), run_webui(), _set_app_event(), start_main_server() (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (12): Belief Store (Phase 2.1), Control Channel (utils/control.py, HITL), JSON Event Log (utils/events.py), Memory-Retriever (RAG path), R1-R4 Shared Contracts (TL-0), Explicit-Belief-State Layer (pomdp/), Langchain-Chatchat, Multi-Agent Collaborative Framework (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (12): Task DAG, Executor, Feedback (success/failure), Generated Plan, Generator, Memory Retriever, Next Task Details, Penetration Path Planning (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.27
Nodes (5): file_exists_in_db(), TextSplitter, files2docs_in_thread_file2docs(), KnowledgeFile, make_text_splitter()

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (8): new_action_id(), Observation, Unified Observation schema — the O of the POMDP tuple, shared by R3 and R4.  ONE, Short correlation id tying an Action → its Observation → its event-log records., The normalized result of running one Action through a channel.      Fields:, JSON-ready dict (the `observation` event record body, R4)., Rebuild from `to_dict()` output; ignores unknown keys so the schema can grow., A normalized failure Observation — `error` is also surfaced as `raw` so the Beli

### Community 34 - "Community 34"
Cohesion: 0.28
Nodes (9): agent service (agent-local / agent-api), egress (outbound bridge network), kali-tools service, labnet (internal isolated network), ollama service (local LLM), target service (vulnerable victim), Kali Mirror Pin (KALI_MIRROR_HOST, 403 workaround), Network Isolation Model (labnet internal / egress) (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.32
Nodes (8): mysql service (data profile), LLM Access Choke Point (_chat), Four Config YAML Files, LLM Configuration (model_config.yaml), Extended Thinking (native Anthropic, version-gated), MySQL Provisioning (local vs docker), /run Crash Cascade (MySQL/LLM-sentinel root cause), anthropic>=0.49 dependency

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (8): Executor module, Generator module (WriteCode), Multi-Channel Kali Execution Layer (R3), MCP Channel (optional efficiency layer), msfrpc Channel (pymetasploit3), Unified Observation Schema (pomdp/observation.py), Channel Router Policy (TL-1.4), SSH Channel (paramiko)

### Community 37 - "Community 37"
Cohesion: 0.29
Nodes (8): Reward + Priors (Phase 2.5), BeliefAgent Loop (run_agent, stubbed), Observation Model Z (LLM likelihoods, soft Bayes), Partial-Observability Tests (tests/test_belief.py), Policy pi (choose_action, info-gain vs exploit-value), POMDP Tuple (S,A,O,T,Z,R,b,gamma), Reward R (score_action), Sarraute 2013 / CHECKMATE (unobtainable Z tables)

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (7): AutoPenBench (evaluation environment), Belief-Conditioned Planner (Phase 2.4), Belief Updater (Phase 2.2), Planner module, Penetration Task Graph (PTG), Summarizer module (PlannerSummary), Three Sequential Phases (Collector-Scanner-Exploiter)

### Community 39 - "Community 39"
Cohesion: 0.62
Nodes (6): arrow(), edge_point(), nid(), node(), seed(), title()

### Community 40 - "Community 40"
Cohesion: 0.38
Nodes (3): rounded_rect(), tx(), ty()

### Community 41 - "Community 41"
Cohesion: 0.47
Nodes (5): main(), msfrpc_channel(), SSH into kali-tools and run nmap against the target; return raw output O., Connect to msfrpcd on kali-tools and return the number of exploit modules., ssh_channel()

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (3): LangchainReranker, Compress documents using Cohere's rerank API.          Args:             docu, Document compressor that uses `Cohere Rerank API`.

### Community 44 - "Community 44"
Cohesion: 0.50
Nodes (4): Exploitation Phase, Reconnaissance Phase, Role Profile (Name/Tools/Goal), Scanning Phase

## Knowledge Gaps
- **84 isolated node(s):** `Factor`, `FRAMES`, `Config`, `Config`, `Config` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `emit()` connect `Community 5` to `Community 1`, `Community 2`, `Community 7`, `Community 8`, `Community 19`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `KBService` connect `Community 10` to `Community 32`, `Community 2`, `Community 11`, `Community 22`, `Community 24`, `Community 25`, `Community 27`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `KBService` (e.g. with `KnowledgeBaseSchema` and `MatchDocument`) actually correct?**
  _`KBService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `KnowledgeFile` (e.g. with `KBService` and `KBServiceFactory`) actually correct?**
  _`KnowledgeFile` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Role` (e.g. with `main()` and `Collector`) actually correct?**
  _`Role` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses`, `Handles SSH output processing with improved encoding detection and buffering.`, `Attempts to decode byte data using multiple encodings.` to the rest of the system?**
  _212 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05446727185857621 - nodes in this community are weakly interconnected._