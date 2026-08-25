# Octopus: A POMDP Belief-State Agent for Autonomous Penetration Testing

<p align="center">
  <a href=''><img src='https://img.shields.io/badge/license-MIT-000000.svg'></a>
  <a href='https://arxiv.org/abs/2501.13411'><img src='https://img.shields.io/badge/upstream-arXiv%3A2501.13411-b31b1b.svg'></a>
</p>

> **Octopus** is a thesis fork of **VulnBot** ([arXiv 2501.13411](https://arxiv.org/abs/2501.13411),
> He Kong et al.) — the multi-agent LLM autonomous penetration-testing framework. It keeps VulnBot's
> Collector → Scanner → Exploiter pipeline and adds an **explicit POMDP belief-state**, a fully
> interactive **octopus** CLI, a multi-channel executor, and a JSON event log. See
> [Attribution](#attribution) for the upstream work this builds on.

## Table of Contents

- [Overview](#overview)
- [Architecture (this fork)](#architecture-this-fork)
- [Dockerized lab (this fork)](#dockerized-lab-this-fork)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Attribution](#attribution)
- [Citation](#citation)
- [Contact](#contact)

---

## Overview

**Note:**
- ⭐ **If you find this project useful, please consider giving it a <font color='orange'>STAR</font>!** ⭐
- If you encounter any <font color='red'>errors</font> or <font color='red'>issues</font>, feel free to open an issue or submit a pull request.

Octopus is an automated penetration-testing framework that uses Large Language Models (LLMs) to
replicate the workflow of a human penetration-testing team within a multi-agent system. On top of the
upstream VulnBot pipeline, Octopus reasons over an **explicit belief-state** `b` — a factored posterior
over the hidden state of the target (its OS, services, vulnerabilities, access, and honeypot risk) — and
picks actions with a belief-conditioned policy that trades information-gain (recon) against
expected reward (exploit). This makes the agent's information-state inspectable and its decisions
auditable.

*The RAG implementation is based on [Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat). Special thanks to the authors.*

### Architecture (this fork)

Current module layout and data flow. Gray = modules inherited from VulnBot; blue = implemented in this
fork — the belief-state layer `pomdp/`, the **R1 standalone `BeliefAgent` loop `pomdp/agent.py`**, the
**R3 multi-channel executor `executor/`**, the **R4 JSON event log** (`utils/events.py` +
`data/runs/<id>/events.jsonl`) with the Ink **LogView** (`cli/src/logview.ts` + `LogView.tsx`, `/log`),
and the **R2 HITL** loopback control socket (`utils/control.py` + `cli/src/control.ts` +
`ApprovalPrompt.tsx`). **All R1–R4 modules are implemented**; the only remaining step is a live-lab
end-to-end run (the code path is covered by `tests/test_e2e.py`). Full write-up in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), the executor deep-dive
[`docs/EXECUTOR.md`](docs/EXECUTOR.md), and the POMDP mapping
[`docs/POMDP_INTEGRATION.md`](docs/POMDP_INTEGRATION.md); editable source in
[`project_schematic.excalidraw`](project_schematic.excalidraw).

![Octopus current architecture & data flow](docs/project_schematic.png)

### Dockerized lab (this fork)

This fork runs the whole lab in `docker compose` on an **isolated** network (no internet on
the attack path). See [`docs/INFRA.md`](docs/INFRA.md) for details.

```powershell
cp .env.example .env         # fill MSF_RPC_PASSWORD, AGENT_SSH_PUBKEY, LLM backend/keys
./lab.ps1 dev-up             # start kali-tools + target + agent (Windows; or `make dev-up`)
./lab.ps1 smoke              # verify agent->kali channels (SSH nmap + msfrpc modules)
./lab.ps1 down
```

- **kali-tools** exposes SSH (arbitrary tools) and `msfrpcd:55553` (Metasploit RPC);
  **target** is a deliberately vulnerable image; **agent** is the Octopus + belief app.
- LLM backend is switchable via `.env` `LLM_BACKEND=local|api` (compose profiles).

The explicit-belief-state layer (`pomdp/belief_state.py`, `belief_store.py`, `priors.py`) is
implemented (Phase 2.1–2.5: Belief Store, LLM-likelihood soft-Bayes Updater, belief-conditioned
policy π, and reward R + offline CVSS priors), and the **R1 standalone belief loop** now runs:
`pomdp/agent.py::BeliefAgent` drives choose→execute→observe→update→persist (`run_agent` delegates
to it; select it with `pentest.py --agent` / octopus `/run --agent`). The **R3 executor**
(`executor/`) is also in — one `Executor.run(action) → Observation`
over SSH + msfrpc (+ a flag-gated MCP stub, `OCTOPUS_MCP=0`), a policy router, and per-channel
timeout/retry/fallback; see [`docs/EXECUTOR.md`](docs/EXECUTOR.md). Both described in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Quick Start

### Prerequisites

- **Programming Language:** Python 3.11.11
- **Package Manager:** Pip

### Build from Source

1. Clone the repository (replace with your fork's URL):

   ```sh
   git clone https://github.com/<your-account>/octopus
   cd octopus
   ```

2. Install the dependencies:

   ```sh
   pip install -r requirements.txt
   ```

### Configuration Guide

Before initializing Octopus, configure the system settings. Refer to the
[Configuration Guide](Configuration%20Guide.md) for detailed instructions on modifying:

- **Kali Linux configuration** (hostname, port, username, password)
- **MySQL database settings** (host, port, user, password, database)
- **LLM settings** (base_url, llm_model_name, api_key)
- **Enabling RAG** (set `enable_rag` to `true` and configure `milvus` and `kb_name`)

### Initialize the Project

```sh
python cli.py init
```

**MySQL is required** (sessions/plans/tasks/conversations/messages). With the **octopus** CLI you
choose once at setup where MySQL runs — a **docker** container it manages (compose `mysql` service,
profile `data`) or your **local** install — and `/run` preflights it, auto-starting + creating tables
in docker mode. To create the tables directly without the RAG stack: `python pentest.py --init-db`.
See [docs/INFRA.md](docs/INFRA.md#mysql-provisioning-local-vs-docker).

### Start the RAG Module (optional)

```sh
python cli.py start -a
```

### Run Octopus

The multi-agent pipeline (Collector → Scanner → Exploiter):

```sh
python cli.py octopus -m {max_interactions}
```

The R1 belief-first loop (the standalone `BeliefAgent` POMDP loop):

```sh
python pentest.py --agent -m 20 --description "authorized pentest of 10.0.0.5"
```

Or drive everything from the interactive **octopus** CLI (setup wizard → REPL → `/run [--agent] <target>` → `/log`):

```sh
./octopus            # or ./octopus.ps1 on Windows
```

Replace `{max_interactions}` with the desired number of react steps per phase.

---

## Documentation

- [`docs/reference/`](docs/reference/README.md) — a from-scratch, function-by-function reference for the
  whole platform, with a diagram per subsystem.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the authoritative module / data-flow write-up.
- [`docs/EXECUTOR.md`](docs/EXECUTOR.md) — the R3 multi-channel executor deep-dive.
- [`docs/POMDP_INTEGRATION.md`](docs/POMDP_INTEGRATION.md) — the POMDP tuple → code mapping.
- [`docs/INFRA.md`](docs/INFRA.md) — the Dockerized lab.

---

## Attribution

Octopus is a research fork of **VulnBot**:

> He Kong, Die Hu, Jingguo Ge, Liangxiong Li, Tong Li, Bingzhen Wu.
> *VulnBot: Autonomous Penetration Testing for a Multi-Agent Collaborative Framework.*
> arXiv:2501.13411 (2025). Upstream repository: <https://github.com/KHenryAegis/VulnBot>.

The upstream VulnBot pipeline, prompts, and RAG stack are retained (the RAG stack itself derives from
[Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat)). This fork adds the POMDP
belief-state, the octopus CLI, the multi-channel executor, and the JSON event log described above.

---

## Citation

If you use this framework for academic purposes, please cite the original VulnBot paper:

```
@misc{kong2025vulnbotautonomouspenetrationtesting,
      title={VulnBot: Autonomous Penetration Testing for a Multi-Agent Collaborative Framework},
      author={He Kong and Die Hu and Jingguo Ge and Liangxiong Li and Tong Li and Bingzhen Wu},
      year={2025},
      eprint={2501.13411},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2501.13411},
}
```

---

## Contact

If you have any questions or suggestions, please open an issue on GitHub. Contributions, discussions, and improvements are always welcome!
