# Graph Report - .  (2026-08-23)

## Corpus Check
- 129 files · ~71,767 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 832 nodes · 1741 edges · 69 communities (61 shown, 8 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Planner & Summarizer Loop|Planner & Summarizer Loop]]
- [[_COMMUNITY_POMDP Belief-State Core|POMDP Belief-State Core]]
- [[_COMMUNITY_Octopus CLI (Ink UI)|Octopus CLI (Ink UI)]]
- [[_COMMUNITY_Knowledge Base Web UI|Knowledge Base Web UI]]
- [[_COMMUNITY_Config YAML Templating|Config YAML Templating]]
- [[_COMMUNITY_Architecture Concept Map|Architecture Concept Map]]
- [[_COMMUNITY_KB Service Layer|KB Service Layer]]
- [[_COMMUNITY_Session Model & Entry|Session Model & Entry]]
- [[_COMMUNITY_KB File Repository|KB File Repository]]
- [[_COMMUNITY_KB Doc API|KB Doc API]]
- [[_COMMUNITY_Remote Shell Handling|Remote Shell Handling]]
- [[_COMMUNITY_Document LoadersParsers|Document Loaders/Parsers]]
- [[_COMMUNITY_LLM Chat & Reranker|LLM Chat & Reranker]]
- [[_COMMUNITY_Milvus Retriever|Milvus Retriever]]
- [[_COMMUNITY_PentestGPT Baseline|PentestGPT Baseline]]
- [[_COMMUNITY_Shell Manager & BaseGPT|Shell Manager & BaseGPT]]
- [[_COMMUNITY_Task Execution Runner|Task Execution Runner]]
- [[_COMMUNITY_Config Settings Classes|Config Settings Classes]]
- [[_COMMUNITY_Milvus KB Service|Milvus KB Service]]
- [[_COMMUNITY_Belief Attach Points (schematic)|Belief Attach Points (schematic)]]
- [[_COMMUNITY_Experiment LLM Baselines|Experiment LLM Baselines]]
- [[_COMMUNITY_FastAPI  WebUI Startup|FastAPI / WebUI Startup]]
- [[_COMMUNITY_Knowledge File Handling|Knowledge File Handling]]
- [[_COMMUNITY_Framework Figure (model.png)|Framework Figure (model.png)]]
- [[_COMMUNITY_KB Repository Models|KB Repository Models]]
- [[_COMMUNITY_ExecuteTask|ExecuteTask]]
- [[_COMMUNITY_Excalidraw Generator|Excalidraw Generator]]
- [[_COMMUNITY_PNG Renderer|PNG Renderer]]
- [[_COMMUNITY_Agent to Kali Smoke Channels|Agent to Kali Smoke Channels]]
- [[_COMMUNITY_HTTPX Client Helper|HTTPX Client Helper]]
- [[_COMMUNITY_CLI Banner  Octopus Logo|CLI Banner / Octopus Logo]]
- [[_COMMUNITY_CLI Entry (cli.py)|CLI Entry (cli.py)]]
- [[_COMMUNITY_Pentest Phase Diagram|Pentest Phase Diagram]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `KBService` - 37 edges
2. `KnowledgeFile` - 30 edges
3. `Role` - 29 edges
4. `_chat()` - 24 edges
5. `ApiRequest` - 22 edges
6. `Plan` - 20 edges
7. `MilvusKBService` - 20 edges
8. `Action` - 19 edges
9. `build_logger()` - 19 edges
10. `Task` - 18 edges

## Surprising Connections (you probably didn't know these)
- `ExtractCode` --uses--> `ExecuteTask`  [INFERRED]
  experiment/extract_code.py → actions/execute_task.py
- `Execute` --uses--> `RunCode`  [INFERRED]
  experiment/execute.py → actions/run_code.py
- `PentestGPT` --uses--> `ShellManager`  [INFERRED]
  experiment/pentestgpt.py → actions/shell_manager.py
- `BaseGPT` --uses--> `WriteCode`  [INFERRED]
  experiment/base.py → actions/write_code.py
- `ExtractCode` --uses--> `DeepPentestPrompt`  [INFERRED]
  experiment/extract_code.py → prompts/prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Per-Phase React Execution Loop** — architecture_role_base_loop, architecture_planner_module, architecture_generator_module, architecture_executor_module, architecture_penetration_task_graph [EXTRACTED 0.90]
- **POMDP Belief-State Modules** — architecture_belief_updater, architecture_belief_store, architecture_belief_conditioned_planner, architecture_reward_priors [EXTRACTED 0.90]
- **Agent to Kali Communication Channels** — docker_compose_agent_local, docker_compose_kali_tools, infra_ssh_channel, infra_msfrpc_channel [EXTRACTED 0.85]
- **Planner-Generator-Executor-Summarizer ReAct loop** — images_model_planner, images_model_generator, images_model_executor, images_model_summarizer [INFERRED 0.85]
- **Three sequential pentest phases** — images_model_reconnaissance, images_model_scanning, images_model_exploitation [EXTRACTED 1.00]

## Communities (69 total, 8 thin omitted)

### Community 0 - "Planner & Summarizer Loop"
Cohesion: 0.06
Nodes (44): PlannerSummary, Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses, Planner, WriteCode, import_tasks_from_json(), merge_tasks(), merge_tasks_from_json(), parse_tasks() (+36 more)

### Community 1 - "POMDP Belief-State Core"
Cohesion: 0.07
Nodes (71): Any, Action, _action_utility(), ActionType, add_host(), choose_action(), _default_dist(), _entropy() (+63 more)

### Community 2 - "Octopus CLI (Ink UI)"
Cohesion: 0.07
Nodes (47): App(), beliefsDir(), beliefView, Factor, fmtDist(), formatBelief(), listRuns(), loadLatest() (+39 more)

### Community 3 - "Knowledge Base Web UI"
Cohesion: 0.06
Nodes (32): DataFrame, _GeneratorContextManager, GridOptionsBuilder, JSONLoader, get_kb_details(), config_aggrid(), file_exists(), knowledge_base_page() (+24 more)

### Community 4 - "Config YAML Templating"
Cohesion: 0.07
Nodes (27): CommentedBase, BasicConfig, _cached_settings(), import_yaml(), generate yaml template with default object         sub_comments indicate how to, the sesstings is cached, and refreshed when configuration files changed, parameter defines howto create template for sub model, create yaml configuration template for pydantic model object (+19 more)

### Community 5 - "Architecture Concept Map"
Cohesion: 0.07
Nodes (42): AutoPenBench Evaluation Environment, Belief-Conditioned Planner (policy pi), POMDP Belief-State Layer, Belief Store (per-run JSON), Belief Updater (soft Bayesian), Collector Role (Reconnaissance), Config & Model Swap Layer, Eager RAG Import Coupling (+34 more)

### Community 6 - "KB Service Layer"
Cohesion: 0.10
Nodes (11): Document, KBService, 使用content中的文件更新向量库         如果指定了docs，则使用自定义docs，并将数据库对应条目标为custom_docs=True, 传入参数为： {doc_id: Document, ...}         如果对应 doc_id 的值为 None，或其 page_content 为空，, 通过file_name或metadata检索Document, 保存向量库:FAISS保存到磁盘，milvus保存到数据库。PGVector暂未支持, 向知识库添加文件         如果指定了docs，则不再将文本向量化，并将数据库对应条目标为custom_docs=True, MatchDocument (+3 more)

### Community 7 - "Session Model & Entry"
Cohesion: 0.11
Nodes (19): Enum, List, ArrayField, Config, Session, SessionModel, initialize_session(), main() (+11 more)

### Community 8 - "KB File Repository"
Cohesion: 0.13
Nodes (18): ABC, get_kb_file_details(), add_docs_to_db(), add_file_to_db(), count_files_from_db(), delete_docs_from_db(), delete_file_from_db(), get_file_detail() (+10 more)

### Community 9 - "KB Doc API"
Cohesion: 0.23
Nodes (21): create_kb(), delete_kb(), list_kbs(), delete_docs(), download_doc(), list_files(), 通过多线程将上传的文件保存到对应知识库目录内。     生成器返回保存结果：{"code":200, "msg": "xxx", "data": {"know, _save_files_in_thread() (+13 more)

### Community 10 - "Remote Shell Handling"
Cohesion: 0.11
Nodes (15): clean_dirb_output(), clean_msfconsole_output(), Validates command against forbidden commands list., Executes command with improved output handling and error recovery., Handles normal command execution flow., Attempts to decode byte data using multiple encodings., Clean the output from the 'dirb' command., Clean the output from the 'msfconsole' command. (+7 more)

### Community 11 - "Document Loaders/Parsers"
Cohesion: 0.12
Nodes (10): CSVLoader, FilteredCSVLoader, Load data into document objects., RapidOCRDocLoader, RapidOCRLoader, get_ocr(), RapidOCRPDFLoader, RapidOCRPPTLoader (+2 more)

### Community 12 - "LLM Chat & Reranker"
Cohesion: 0.12
Nodes (10): OllamaChat, OpenAIChat, LangchainReranker, Compress documents using Cohere's rerank API.          Args:             docu, Document compressor that uses `Cohere Rerank API`., StrEnum, api_address(), Config (+2 more)

### Community 13 - "Milvus Retriever"
Cohesion: 0.12
Nodes (8): AsyncCallbackManagerForRetrieverRun, BaseRetriever, CallbackManagerForRetrieverRun, BaseRetrieverService, MilvusRetriever, MilvusVectorstoreRetrieverService, VectorStore, VectorStoreRetriever

### Community 14 - "PentestGPT Baseline"
Cohesion: 0.18
Nodes (7): main(), PentestGPT, PentestGPTPrompt, prompt_ask(), prompt_continuation(), The continuation: display line numbers and '->' before soft wraps.     Notice t, A custom prompt function that adds a key binding to accept the input.     In si

### Community 15 - "Shell Manager & BaseGPT"
Cohesion: 0.20
Nodes (6): ShellManager, BaseGPT, main(), 针对给定执行结果，传入模型，输出下一步任务, Execute, ExtractCode

### Community 16 - "Task Execution Runner"
Cohesion: 0.22
Nodes (4): RunCode, build_logger(), LoggerNameFilter, build a logger with colorized output and a log file, for example:      logger

### Community 17 - "Config Settings Classes"
Cohesion: 0.18
Nodes (9): BaseSettings, ConfigsContainer, DBConfig, KBConfig, LLMConfig, BaseFileSettings, _lazy_load_key(), MyBaseModel (+1 more)

### Community 18 - "Milvus KB Service"
Cohesion: 0.17
Nodes (6): get_embeddings(), Embeddings, SupportedVSType, list_file_num_docs_id_by_kb_name_and_file_name(), 列出某知识库某文件对应的所有Document的id。     返回形式：[str, ...], MilvusKBService

### Community 19 - "Belief Attach Points (schematic)"
Cohesion: 0.16
Nodes (15): Belief-Conditioned Planner info-gain vs exploit-value [future 2.4], belief_state.py [2.1] b0 priors, Action, GAMMA update/score/choose = stub, Belief Store [2.1] belief_store.py data/beliefs/*.json, Belief Updater [2.2] update_belief: LLM Z + soft Bayes, Executor ExecuteTask (execute_task.py), Generator WriteCode (write_code.py), kali-tools (Docker) SSH + msfrpc:55553 nmap / metasploit, LLM Layer _chat OpenAI / Ollama (server/chat/chat.py) (+7 more)

### Community 20 - "Experiment LLM Baselines"
Cohesion: 0.23
Nodes (4): Conversation, Message, OLLAMAPI, OPENAI

### Community 21 - "FastAPI / WebUI Startup"
Cohesion: 0.32
Nodes (12): Event, FastAPI, create_app(), main(), run_api_server(), run_webui(), _set_app_event(), start_main_server() (+4 more)

### Community 22 - "Knowledge File Handling"
Cohesion: 0.23
Nodes (6): file_exists_in_db(), TextSplitter, get_loader(), KnowledgeFile, make_text_splitter(), 根据loader_name和文件路径或内容返回文档加载器。

### Community 23 - "Framework Figure (model.png)"
Cohesion: 0.18
Nodes (12): Task DAG, Executor, Feedback (success/failure), Generated Plan, Generator, Memory Retriever, Next Task Details, Penetration Path Planning (+4 more)

### Community 24 - "KB Repository Models"
Cohesion: 0.20
Nodes (7): Config, KnowledgeBaseModel, KnowledgeBaseSchema, add_kb_to_db(), kb_exists(), list_kbs_from_db(), load_kb_from_db()

### Community 25 - "ExecuteTask"
Cohesion: 0.43
Nodes (3): ExecuteResult, ExecuteTask, Mode

### Community 26 - "Excalidraw Generator"
Cohesion: 0.62
Nodes (6): arrow(), edge_point(), nid(), node(), seed(), title()

### Community 27 - "PNG Renderer"
Cohesion: 0.38
Nodes (3): rounded_rect(), tx(), ty()

### Community 28 - "Agent to Kali Smoke Channels"
Cohesion: 0.47
Nodes (5): main(), msfrpc_channel(), SSH into kali-tools and run nmap against the target; return raw output O., Connect to msfrpcd on kali-tools and return the number of exploit modules., ssh_channel()

### Community 29 - "HTTPX Client Helper"
Cohesion: 0.40
Nodes (4): AsyncClient, Client, get_httpx_client(), helper to get httpx client with default proxies that bypass local addesses.

### Community 32 - "Pentest Phase Diagram"
Cohesion: 0.50
Nodes (4): Exploitation Phase, Reconnaissance Phase, Role Profile (Name/Tools/Goal), Scanning Phase

## Knowledge Gaps
- **44 isolated node(s):** `Factor`, `CommandSpec`, `CommandResult`, `here`, `OCTOPUS_JSON` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_logger()` connect `Task Execution Runner` to `Planner & Summarizer Loop`, `Knowledge Base Web UI`, `KB File Repository`, `KB Doc API`, `LLM Chat & Reranker`, `FastAPI / WebUI Startup`, `KB Repository Models`, `CLI Entry (cli.py)`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `ApiRequest` connect `Knowledge Base Web UI` to `Task Execution Runner`, `LLM Chat & Reranker`, `HTTPX Client Helper`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `KBService` connect `KB Service Layer` to `KB File Repository`, `KB Doc API`, `Milvus KB Service`, `Knowledge File Handling`, `KB Repository Models`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `KBService` (e.g. with `KnowledgeBaseSchema` and `MatchDocument`) actually correct?**
  _`KBService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `KnowledgeFile` (e.g. with `KBService` and `KBServiceFactory`) actually correct?**
  _`KnowledgeFile` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Role` (e.g. with `main()` and `Collector`) actually correct?**
  _`Role` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Summarizer → Belief Updater attach point (POMDP).      `get_summary` condenses`, `Handles SSH output processing with improved encoding detection and buffering.`, `Attempts to decode byte data using multiple encodings.` to the rest of the system?**
  _145 weakly-connected nodes found - possible documentation gaps or missing edges._