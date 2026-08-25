# Graph Report - .  (2026-08-25)

## Corpus Check
- 13 files · ~113,739 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1270 nodes · 2595 edges · 91 communities (85 shown, 6 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.58)
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
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]

## God Nodes (most connected - your core abstractions)
1. `KBService` - 37 edges
2. `Action` - 31 edges
3. `KnowledgeFile` - 30 edges
4. `Executor` - 26 edges
5. `Role` - 26 edges
6. `Channel` - 25 edges
7. `update_belief()` - 24 edges
8. `ChannelError` - 23 edges
9. `ApiRequest` - 22 edges
10. `McpChannel` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Collector` --uses--> `RoleType`  [INFERRED]
  roles/collector.py → utils/log_common.py
- `Scanner` --uses--> `RoleType`  [INFERRED]
  roles/scanner.py → utils/log_common.py
- `Dockerized Isolated Lab` --references--> `kali-tools service`  [INFERRED]
  README.md → docker-compose.yml
- `LangChain RAG Stack` --conceptually_related_to--> `Memory-Retriever (RAG path)`  [INFERRED]
  requirements.txt → docs/ARCHITECTURE.md
- `pymilvus / milvus vector store dep` --conceptually_related_to--> `Memory-Retriever (RAG path)`  [INFERRED]
  requirements.txt → docs/ARCHITECTURE.md

## Import Cycles
- None detected.

## Communities (91 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (81): App(), commandMeta(), CommandResult, COMMANDS, CommandSpec, fetchingLabel(), handleCommand(), DbSettings (+73 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (32): ExecuteResult, ExecuteTask, PlannerSummary, Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses, RunCode, ShellManager, WriteCode, BaseModel (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (29): BeliefStore, db_reachable(), _extract_target(), initialize_session(), main(), _mysql_dsn(), preload_session(), R1 belief-first run (`--agent`): drive the standalone `BeliefAgent` loop instead (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (31): Base, List, Message, Conversation, FileDocModel, KnowledgeFileModel, Config, Message (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (35): beliefsDir(), beliefView, Factor, fmtDist(), formatBelief(), listRuns(), loadLatest(), ClassifiedLog (+27 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (24): BasicConfig, Path, PathLike, BeliefStore, _default_root(), Belief Store — persistence for the POMDP belief `b`.  Maps the Memory → Belief S, Full belief trace (all steps in order) for `run_id`., Persist and reload factored-JSON beliefs per run, one file per step. (+16 more)

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (28): Executor, Runs actions across pluggable channels behind `run(action) -> Observation`., Pick the ordered candidate channels for `action` + a one-line justification (pur, route(), exploit_action(), Flaky, msf(), TL-1.7 — the Executor layer (R3): router policy, Observation normalization, and (+20 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (15): socket, TL-0.3 — the loopback control channel round-trips a frame each direction (R2 tra, test_control_frame_roundtrip_both_directions(), test_no_client_is_non_fatal(), ControlClient, ControlServer, _FramedConn, Loopback control channel — the CLI↔agent back-channel for human-in-the-loop (R2) (+7 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (20): BaseSettings, CommentedBase, BaseFileSettings, _cached_settings(), import_yaml(), _lazy_load_key(), MyBaseModel, generate yaml template with default object         sub_comments indicate how to (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (18): Any, ApproveFn, BeliefLLM, CandidateFn, GoalFn, BeliefAgent, Run the belief loop for `session_id` and return the final belief.          `host, Recon (probe each host) + priors-enriched exploit actions for seeded vulns. (+10 more)

### Community 10 - "Community 10"
Cohesion: 0.10
Nodes (20): Channel, _default_router(), _make_default_router(), Executor facade + Channel adapter interface (R3, TL-1.1).  ONE contract turns a, One execution transport to Kali. Adapters: `ssh_channel` (1.2), `msf_channel` (1, True if this channel can run `action` (e.g. msfrpc only for actions naming an MS, Release any held resource (SSH session, RPC client). Best-effort., Fallback router: every channel that supports the action, registration order pres (+12 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (9): KBService, 使用content中的文件更新向量库         如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True, 传入参数为： {doc_id: Document, ...}         如果对应 doc_id 的值为 None，或其 page_content 为空，, 通过file_name或metadata检索Document, 保存向量库:FAISS保存到磁盘，milvus保存到数据库。PGVector暂未支持, 向知识库添加文件         如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True, add_kb_to_db(), delete_kb_from_db() (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (13): Action, _note_fallback(), Run one channel with the timeout budget + safe retries. Returns a stamped Observ, `ch.run` under the per-attempt budget. No budget → direct call. With a budget, r, Run `action` and return a normalized `Observation` stamped with `action_id`., Record the failed attempts that preceded a successful call under a reserved meta, Drive the MCP tool via the injected client and normalize the result → Observatio, The MCP tool this action names, or None. `params['mcp_tool']` wins; otherwise a (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.22
Nodes (22): create_kb(), delete_kb(), list_kbs(), delete_docs(), download_doc(), list_files(), 通过多线程将上传的文件保存到对应知识库目录内。     生成器返回保存结果：{"code":200, "msg": "xxx", "data": {"know, _save_files_in_thread() (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (21): _anthropic_has_thinking(), _downgrade_thinking(), _effective_thinking(), _is_retryable(), _notify_llm_ok(), _notify_llm_wait(), The configured level, capped by any downgrade forced by a prior rate limit., Lower the process-wide cap to one step below `current` (floor 'off') after a 429 (+13 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (10): CSVLoader, FilteredCSVLoader, Load data into document objects., RapidOCRDocLoader, RapidOCRLoader, get_ocr(), RapidOCRPDFLoader, RapidOCRPPTLoader (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (23): _action_utility(), add_host(), _default_dist(), _entropy(), _get_dist(), new_host_prior(), _parse_likelihoods(), _peek_dist() (+15 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (15): clean_dirb_output(), clean_msfconsole_output(), Validates command against forbidden commands list., Executes command with improved output handling and error recovery., Handles normal command execution flow., Attempts to decode byte data using multiple encodings., Clean the output from the 'dirb' command., Clean the output from the 'msfconsole' command. (+7 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (23): Belief-Cond. Planner [2.4] choose_action: info-gain vs exploit-value (pi), belief_state.py [2.1-2.5] b, Action, GAMMA; update/choose/score implemented, Belief Store [2.1] belief_store.py data/beliefs/*.json, Belief Updater [2.2] update_belief: LLM Z + soft Bayes, control.py [TL-0] loopback HITL socket (R2 back-channel), events.py [TL-0] JSONL event log (R4) data/runs/*.jsonl, Executor ExecuteTask (execute_task.py), Executor + channels SSH/msfrpc/MCP + router (executor/) [R3 TL-1] (+15 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (8): BaseRetriever, get_embeddings(), Embeddings, SupportedVSType, list_file_num_docs_id_by_kb_name_and_file_name(), 列出某知识库某文件对应的所有Document的id。     返回形式：[str, ...], MilvusVectorstoreRetrieverService, MilvusKBService

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (8): Response, ApiRequest, api.py调用的封装（同步模式）,简化api调用方式, 转换同步或异步请求返回的响应         `as_json`: 返回json         `value_func`: 用户可以自定义返回值，该函数接, 对应api.py/knowledge_base/list_knowledge_bases接口, 对应api.py/knowledge_base/create_knowledge_base接口, 对应api.py/knowledge_base/search_docs接口, 对应api.py/knowledge_base/upload_docs接口

### Community 21 - "Community 21"
Cohesion: 0.26
Nodes (20): choose_action(), Policy π: pick the next action given the current belief (argmax utility).      T, _exploit_action(), Phase 2.3 — partial observability must be provably real.  These lock the four pr, _recon_action(), _recon_probe_action(), test_choose_action_belief_drives_choice(), test_choose_action_does_not_mutate_belief() (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (20): _catalog_path(), _clamp(), enrich_action(), load_catalog(), _maturity_w(), merge_catalog(), Priors source (Phase 2.5): reward R ingredients from public exploit signals.  Fe, Return {value, cost, detection_risk} for an action from CVSS + maturity signals. (+12 more)

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (20): AuthTokens, AuthUrl, b64url(), beginLogin(), buildAuthUrl(), completeLogin(), exchangeCode(), ExchangeOpts (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (20): au, bs, cmd, ef, exFetch, failSummary, ids, lc (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (10): AsyncCallbackManagerForRetrieverRun, CallbackManagerForRetrieverRun, Document, MilvusRetriever, TextSplitter, files2docs_in_thread_file2docs(), get_loader(), make_text_splitter() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (14): AnthropicChat, Native Anthropic (Claude) client. Two auth modes:       - api_key: Anthropic(ap, _cfg(), _FakeAnthropic, _FakeMessages, Offline unit test for the native AnthropicChat wrapper (B5).  No live API call:, test_api_key_auth_uses_x_api_key(), test_chat_maps_history_and_concatenates_text() (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (12): JSONLoader, get_kb_file_details(), get_file_detail(), list_files_from_db(), get_doc_path(), get_file_path(), get_kb_path(), get_LoaderClass() (+4 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (13): DataFrame, GridOptionsBuilder, get_kb_details(), config_aggrid(), file_exists(), knowledge_base_page(), check whether a doc file exists in local knowledge base folder.     return the, list_kbs_from_folder() (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (13): _env_truthy(), McpChannel, MCP channel — flag-gated, OFF by default (R3, TL-1.6).  Channel C of the Executo, Flag-gated MCP tool bridge. Disabled unless `VULNBOT_MCP` is truthy AND a server, True only when the operator has explicitly turned MCP on. Default OFF., _mcp_action(), mcp_env(), Helper to toggle the MCP flag + server/version env within a test. (+5 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (8): Exception, ChannelError, A channel could not run the action (unreachable, auth, RPC down). The Executor c, Confirm the exact server + version before enabling. Raise `ChannelError` (→ fall, MsfChannel, msfrpc channel — Metasploit modules over pymetasploit3 (R3, TL-1.3).  Channel B, Run an action's Metasploit module over msfrpc; structured RPC result → Observati, The MSF module path this action names, or None. `params['module']` wins over `to

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (11): add_docs_to_db(), add_file_to_db(), count_files_from_db(), delete_docs_from_db(), delete_file_from_db(), file_exists_in_db(), list_docs_from_db(), 列出某知识库某文件对应的所有Document。     返回形式：[{"id": str, "metadata": dict}, ...] (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (15): Action, new_belief(), Return a fresh factored belief b0 for a run/session.      `hosts` may be empty a, A candidate action the policy chooses among.      `value`, `cost`, `detection_ri, _belief_with_vuln(), TL-2.6 — R1 belief-loop guarantees: self-consistency (Z averaging + variance red, A Z-likelihood JSON with the given P(observation|present); absent is the complem, With a prior of 0.5 and Z that alternates 0.9 / 0.1 per call, averaging two samp (+7 more)

### Community 33 - "Community 33"
Cohesion: 0.27
Nodes (10): Planner, import_tasks_from_json(), merge_tasks(), merge_tasks_from_json(), parse_tasks(), preprocess_json_string(), WritePlan, Plan (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (8): BaseFileSettings, ConfigsContainer, DBConfig, KBConfig, LLMConfig, Enum, LoggerNameFilter, RoleType

### Community 35 - "Community 35"
Cohesion: 0.32
Nodes (12): Event, FastAPI, create_app(), main(), run_api_server(), run_webui(), _set_app_event(), start_main_server() (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (6): _chat(), OllamaChat, OpenAIChat, Client, StrEnum, LLMType

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (6): ChannelTimeout, The channel exceeded its time budget. Distinct from `ChannelError` because the t, FakeChannel, A channel supporting a fixed set of action types; records that it ran., Blocks `secs` before returning. Counts calls (proves no auto-retry on timeout)., Slow

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (12): Task DAG, Executor, Feedback (success/failure), Generated Plan, Generator, Memory Retriever, Next Task Details, Penetration Path Planning (+4 more)

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (6): Config, KnowledgeBaseModel, KnowledgeBaseSchema, kb_exists(), list_kbs_from_db(), load_kb_from_db()

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (9): _default_goal(), BeliefAgent — the standalone POMDP control loop (R1, TL-2.1).  This is the integ, # NOTE: `action_type` (not `type`) — `type` is EventLog.append's positional para, Z self-consistency sample count. Explicit arg wins; else the shared     `belief_, Default stop predicate: a host is believed rooted, or the last observation clear, _resolve_samples(), ActionType, Self-consistency Z-sample count from the env (`VULNBOT_Z_SAMPLES`), clamped to ≥ (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (10): Control Channel (utils/control.py, HITL), JSON Event Log (utils/events.py), Executor module, Generator module (WriteCode), R1-R4 Shared Contracts (TL-0), MCP Channel (optional efficiency layer), msfrpc Channel (pymetasploit3), Unified Observation Schema (pomdp/observation.py) (+2 more)

### Community 42 - "Community 42"
Cohesion: 0.28
Nodes (9): agent service (agent-local / agent-api), egress (outbound bridge network), kali-tools service, labnet (internal isolated network), ollama service (local LLM), target service (vulnerable victim), Kali Mirror Pin (KALI_MIRROR_HOST, 403 workaround), Network Isolation Model (labnet internal / egress) (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (9): Belief Store (Phase 2.1), Memory-Retriever (RAG path), Explicit-Belief-State Layer (pomdp/), Langchain-Chatchat, Multi-Agent Collaborative Framework, VulnBot Framework, VulnBot Paper (arXiv 2501.13411), LangChain RAG Stack (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (9): Belief Updater (Phase 2.2), Summarizer module (PlannerSummary), Multi-Channel Kali Execution Layer (R3), BeliefAgent Loop (run_agent, stubbed), Observation Model Z (LLM likelihoods, soft Bayes), Partial-Observability Tests (tests/test_belief.py), Policy pi (choose_action, info-gain vs exploit-value), POMDP Tuple (S,A,O,T,Z,R,b,gamma) (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.29
Nodes (3): ABC, BaseRetrieverService, VectorStore

### Community 46 - "Community 46"
Cohesion: 0.32
Nodes (8): mysql service (data profile), LLM Access Choke Point (_chat), Four Config YAML Files, LLM Configuration (model_config.yaml), Extended Thinking (native Anthropic, version-gated), MySQL Provisioning (local vs docker), /run Crash Cascade (MySQL/LLM-sentinel root cause), anthropic>=0.49 dependency

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (5): Observation, The normalized result of running one Action through a channel.      Fields:, JSON-ready dict (the `observation` event record body, R4)., Rebuild from `to_dict()` output; ignores unknown keys so the schema can grow., A normalized failure Observation — `error` is also surfaced as `raw` so the Beli

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (5): AsyncClient, Config, get_httpx_client(), helper to get httpx client with default proxies that bypass local addesses., replace_ip_with_targetip()

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (7): AutoPenBench (evaluation environment), Belief-Conditioned Planner (Phase 2.4), Planner module, Penetration Task Graph (PTG), Reward + Priors (Phase 2.5), Three Sequential Phases (Collector-Scanner-Exploiter), Reward R (score_action)

### Community 50 - "Community 50"
Cohesion: 0.62
Nodes (6): arrow(), edge_point(), nid(), node(), seed(), title()

### Community 51 - "Community 51"
Cohesion: 0.38
Nodes (3): rounded_rect(), tx(), ty()

### Community 52 - "Community 52"
Cohesion: 0.47
Nodes (5): main(), msfrpc_channel(), SSH into kali-tools and run nmap against the target; return raw output O., Connect to msfrpcd on kali-tools and return the number of exploit modules., ssh_channel()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (3): LangchainReranker, Compress documents using Cohere's rerank API.          Args:             docu, Document compressor that uses `Cohere Rerank API`.

### Community 55 - "Community 55"
Cohesion: 0.50
Nodes (4): Exploitation Phase, Reconnaissance Phase, Role Profile (Name/Tools/Goal), Scanning Phase

## Knowledge Gaps
- **84 isolated node(s):** `Factor`, `FRAMES`, `Config`, `Config`, `Config` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `KBService` connect `Community 11` to `Community 39`, `Community 45`, `Community 13`, `Community 19`, `Community 25`, `Community 27`, `Community 31`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `Role` connect `Community 2` to `Community 40`, `Community 1`, `Community 32`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `ApiRequest` connect `Community 20` to `Community 48`, `Community 56`, `Community 28`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `KBService` (e.g. with `KnowledgeBaseSchema` and `MatchDocument`) actually correct?**
  _`KBService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Action` (e.g. with `BeliefAgent` and `Role`) actually correct?**
  _`Action` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `KnowledgeFile` (e.g. with `KBService` and `KBServiceFactory`) actually correct?**
  _`KnowledgeFile` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Executor` (e.g. with `FakeChannel` and `Flaky`) actually correct?**
  _`Executor` has 3 INFERRED edges - model-reasoned connections that need verification._