# INFRA — Dockerized Pentest Lab

Reproducible, isolated lab for the belief-state pentest agent. Everything runs in
`docker compose`; the agent reaches a containerized Kali tooling host over SSH + msfrpc and
attacks a deliberately vulnerable target on a network with **no route to the public internet**.

> Phase 0 deliverable. Belief-state code (Phase 2+) is not here yet — this is the ground it runs on.

## Services

| Service | Image / build | Role | Networks | Profile |
|---------|---------------|------|----------|---------|
| **kali-tools** | `docker/kali` (kalilinux/kali-rolling + `kali-linux-headless`) | Tooling host. Exposes **SSH (22)** for arbitrary commands and **msfrpcd (55553)** for Metasploit RPC. SSH is also **published on the host at `127.0.0.1:2222`** so the host-side pipeline (octopus spawns python on the host) can reach it — a containerized agent still uses `kali-tools:22`. **Joins `egress`** too: Docker can't bind a host port to an internal-only network, so publishing `:2222` requires a non-internal bridge (this also gives kali outbound internet — the tool host, not the target). | `labnet` + `egress` + host `:2222` | always |
| **target** | `tleemcjr/metasploitable2` (example) | Deliberately vulnerable victim. No internet by design. | `labnet` | always |
| **mysql** | `mysql:8` | Sessions/plans/tasks/conversations/messages store. On `labnet` (a containerized agent reaches it as `mysql:3306`) **and** published on the host (`127.0.0.1:3306`, so the host-side pipeline connects over loopback — same rationale as kali's `:2222`). | `labnet` + host `:3306` | `data` |
| **ollama** | `ollama/ollama` | Local LLM server on the RTX 5080 (used when `LLM_BACKEND=local`). | `labnet` | `local` |
| **agent-local** | `docker/agent` (Python 3.11) | Octopus + belief app. Repo mounted at `/app`. **No egress.** | `labnet` | `local` |
| **agent-api** | `docker/agent` | Same agent, hosted-LLM variant. Joins egress for API calls. | `labnet`, `egress` | `api` |

Both agent variants use `container_name: agent`, so only one runs at a time (selected by profile)
and all tooling refers to it as `agent`.

## Network isolation model

```
        ┌───────────────────────── labnet (internal: true — NO internet) ─────────────────────────┐
        │                                                                                          │
        │   agent ───SSH:22────►  kali-tools  ───tools (nmap, msf, …)───►  target                 │
        │     │   ───msfrpc:55553►                                                                  │
        │     │                                                                                     │
        │     └─(local) ──►  ollama   (local LLM; no internet needed)                               │
        └──────────────────────────────────────────────────────────────────────────────────────────┘
              │
   (api only) └────────────►  egress (bridge, has internet)  ────►  hosted LLM API
```

- **`labnet`** is `internal: true` → Docker gives it **no gateway to the host/internet**. The
  **target** can never reach the public internet. This keeps the attack path isolated by construction.
- **`egress`** (normal bridge, has internet) is attached to **`agent-api`** (under the `api` profile)
  **and to `kali-tools`** (always). kali joins it for one structural reason: Docker cannot publish a
  host port from an internal-only container, and the host-side pipeline needs to SSH kali at
  `127.0.0.1:2222`. Side effect: kali has outbound internet. **The target never touches egress** —
  the property that matters (an isolated victim) holds.
- In the **`local`** profile the agent has no egress; kali still does (for the published SSH port).
  If you need kali fully offline too, run the pipeline inside the `agent` container instead (SSH to
  `kali-tools:22` on labnet — no host port needed) and drop `egress` from kali-tools.

Verify the invariant at any time:

```powershell
docker compose --profile api  config | Select-String 'egress'   # only under agent-api
docker network inspect pentest-pomdp-lab_labnet --format '{{.Internal}}'   # -> true
```

Current labnet subnet: `172.20.0.0/16` (gateway `172.20.0.1`). Prefer **hostnames** (`kali-tools`,
`target`, `ollama`, `agent`) over IPs — compose DNS resolves them on labnet.

## How the agent reaches kali (two channels)

| Channel | Client | Use for | Why |
|---------|--------|---------|-----|
| **SSH (22)** | `ssh` / paramiko, key-based | Arbitrary tools: nmap, enumeration, custom shell. Raw stdout is the observation **O**. | General-purpose; agent shells into kali and runs the tool there. |
| **msfrpc (55553)** | `pymetasploit3` | Metasploit exploit modules (exploit / lateral / privesc). | Driving MSF over its RPC API beats screen-scraping msfconsole. |

- SSH is **key-based only** (`PasswordAuthentication no`). The agent's private key is mounted
  read-only at `/root/.ssh/id_ed25519`; its public key is authorized on kali via `AGENT_SSH_PUBKEY`
  in `.env` (installed by `docker/kali/entrypoint.sh`).
- **Host-side pipeline (docker executor mode):** octopus runs `python pentest.py` on the host and
  SSHes to kali over the published `127.0.0.1:2222` using the **same key** at
  `docker/agent/keys/agent_ed25519`. Setup writes `basic_config.yaml` `kali:` with
  `hostname: 127.0.0.1`, `port: 2222`, `key_filename: docker/agent/keys/agent_ed25519`;
  `ShellManager` prefers key auth when `key_filename` is set + present, else falls back to password
  (remote-Kali mode). octopus TCP-preflights `127.0.0.1:2222` (and the key file) before a run, so a
  down lab surfaces as one clear line instead of a paramiko `getaddrinfo failed` traceback.
- msfrpcd is started by the kali entrypoint with `-S` (no SSL — acceptable on the isolated labnet)
  and the password from `MSF_RPC_PASSWORD`.

**Smoke test both channels** (from the agent):

```powershell
./lab.ps1 smoke          # or: docker exec agent python /app/docker/agent/smoke_channels.py
```

Expected: SSH runs `nmap target` and captures O; msfrpc lists the exploit modules; `RESULT: PASS`.

## One-command lifecycle

Windows (no `make` needed): **`lab.ps1`**. Linux/CI/inside-agent: **`make`** (same targets).

| Action | Windows | Linux |
|--------|---------|-------|
| Full stack up (pulls ollama first run) | `./lab.ps1 up` | `make up` |
| Fast dev up (kali+target+agent, no ollama) | `./lab.ps1 dev-up` | `make dev-up` |
| Tear down | `./lab.ps1 down` | `make down` |
| Validate compose | `./lab.ps1 config` | `make config` |
| Shell into kali / agent | `./lab.ps1 shell-kali` / `shell-agent` | `make shell-kali` / `shell-agent` |
| Channel smoke test | `./lab.ps1 smoke` | `make smoke` |

Select the backend/profile with `-Backend local|api` (PowerShell) or `PROFILE=local|api` (make).

## LLM backend switch

`.env` `LLM_BACKEND`:
- `local` → run `./lab.ps1 up` (starts `ollama` on labnet); point Octopus's `model_config.yaml`
  at `http://ollama:11434` with `llm_model: ollama`. No internet.
- `api` → run `./lab.ps1 up -Backend api`; set `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` in `.env`; the
  agent (and only the agent) has egress.

**Extended thinking (native Anthropic).** `llm_model: anthropic` with a non-`off` `thinking_level`
needs **`anthropic>=0.47`** for the `thinking=` request param (`requirements.txt` pins
`anthropic>=0.49,<1`). On an older SDK, `server/chat/chat.py::AnthropicChat` degrades to a normal
call and logs one warning instead of crashing. The old `anthropic==0.40.0` pin raised
`Messages.create() got an unexpected keyword argument 'thinking'`, which `_chat` returned as the
`**ERROR**` sentinel and broke planning — `pip install -U anthropic` (or reinstall requirements)
enables thinking again.

## MySQL provisioning (local vs docker)

Octopus **always** needs MySQL (sessions/plans/tasks/conversations/messages). The octopus CLI asks
once, at setup, where it runs and persists the choice (`mysqlMode` in `cli/.octopus.json`):

- **docker** (recommended) — the compose `mysql` service (profile `data`), on `labnet` + published
  on `127.0.0.1:3306`. octopus provisions it **on startup** (and again as a `/run` preflight): if the
  DB is unreachable it runs `docker compose --profile data up -d mysql`, waits for it, then creates
  the tables via `python pentest.py --init-db` (langchain-free — it does **not** go through `cli.py`,
  which would pull the FastAPI/RAG stack). Already-reachable = silent no-op. The host-side pipeline
  connects at `127.0.0.1:3306`; a containerized agent would use `mysql:3306` on labnet. Creds come
  from the `MYSQL_*` vars in `.env`; `db_config.yaml` is written to match (`127.0.0.1:3306`,
  `octopus/octopus`).
- **local** — you run your own MySQL on `127.0.0.1:3306`. `/run` only checks reachability; if it's
  down it prints one line (*"start your local MySQL, then retry /run"*) and does **not** spawn.
  Create the tables once with `python pentest.py --init-db`.

The `mysql` service is opt-in (`--profile data`), so `./lab.ps1 up` / `dev-up` (kali+target+ollama)
don't start it; octopus starts it on demand in docker mode.

## Troubleshooting — the `/run` crash cascade

A single dead dependency (almost always **MySQL not running**) used to surface as a confusing
4-error stack: `pymysql OperationalError 2003` → `too many values to unpack (expected 2)` →
`'NoneType' has no attribute 'current_task'` → `'NoneType' has no attribute 'tasks'`. Root cause: the
LLM choke point `server/chat/chat.py::_chat` swallows the DB error and returns an error **string**
where callers unpack a **tuple**, so planning fails, `current_plan` stays `None`, and every later
deref crashes.

This is now fixed two ways: **(1)** `pentest.py` preflights MySQL (`SELECT 1`) and exits with one
clear line if it's down; the pipeline also fails fast (`run` aborts on a null plan, `put_message` is
guarded). **(2)** octopus preflights the DB before spawning (see above). If you still see the old
cascade, you're running stale code — pull and retry. If `--init-db` says *"MySQL unreachable"*, the
container/server isn't up yet or `db_config.yaml` points at the wrong host/port.

A second variant of the same class had the LLM error sentinel as the root cause: an old
`anthropic` SDK rejecting `thinking=` → `_chat` returns `**ERROR**: …` → `WritePlan` finds no
`<json>` → `parse_tasks(None)` → `json.loads(None)`. Fixed by version-gating thinking (degrade,
don't crash) **and** hardening the parse path (`WritePlan.run`/`parse_tasks` treat a falsy/`**ERROR**`
response as a clean planning failure, so `run` aborts with one message). See *Extended thinking*
above.

## Secrets

All secrets live in **`.env`** (git-ignored), never in code or images:
`MSF_RPC_PASSWORD`, `AGENT_SSH_PUBKEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MYSQL_*`. Template is
`.env.example`. The agent SSH keypair lives in `docker/agent/keys/` (git-ignored); regenerate on a
fresh clone with:

```sh
ssh-keygen -t ed25519 -N "" -f docker/agent/keys/agent_ed25519
# paste docker/agent/keys/agent_ed25519.pub into .env AGENT_SSH_PUBKEY
```

## Kali mirror (build note)

The default Kali mirrors (`http.kali.org` / `kali.download`) are Cloudflare-fronted and return
**403 in some regions**, breaking `apt-get update`. `docker/kali/Dockerfile` rewrites the deb822
`kali.sources` URI to a reachable mirror via the `KALI_MIRROR_HOST` build arg
(default `kali.mirror.rafal.ca`). Override for a closer mirror:

```powershell
docker compose build --build-arg KALI_MIRROR_HOST=<your.kali.mirror> kali-tools
```

## Adding a new target

1. Add a service block to `docker-compose.yml` (labnet only — **no** egress):

   ```yaml
     target-web:
       image: vulhub/…            # or another deliberately-vulnerable image
       container_name: target-web
       hostname: target-web
       networks: [labnet]
       restart: unless-stopped
   ```

2. Bring it up: `./lab.ps1 dev-up` (or `docker compose --profile local up -d target-web`).
3. Point the agent at it by hostname (`target-web`) in the task description.

**Note on the example target:** `tleemcjr/metasploitable2` exposed only `80/tcp` in this lab (its
extra services may not auto-start in the container build). For richer attack surface, swap in a
[Vulhub](https://github.com/vulhub/vulhub) scenario or a full Metasploitable VM and update this
section. Only ever point the agent at authorized lab targets on `labnet`.
