# POMDP_INTEGRATION — the tuple ⟨S, A, O, T, Z, R, b, γ⟩ in code (R1)

> **Status:** COMPLETE (TL-2). The standalone `BeliefAgent` loop runs, `run_agent` delegates to it, the
> self-consistency + T-effect tests pass, and `pentest.py --agent` / `/run --agent` select it.

VulnBot's belief agent is a real POMDP, not a POMDP-flavored name. Each element of the tuple maps to a
concrete code path. The agent **never observes or branches on S** — it acts on the belief `b` only.

## Tuple → code

| Elem | Meaning | Where it lives |
|------|---------|----------------|
| **S** | hidden true config (OS, versions, vulns, access, honeypot) | lab ground truth only; never read by the agent |
| **b** | factored-JSON belief over S | `pomdp/belief_state.py::new_belief`/`new_host_prior`; persisted per step by `pomdp/belief_store.py` |
| **A** | recon / exploit / lateral / privesc | `pomdp/belief_state.py::Action`, `ActionType`; executed on Kali via the Executor (R3) |
| **O** | raw tool output | `pomdp/observation.py::Observation.raw`, produced by a channel adapter |
| **Z** | P(O \| hypothesis) — the observation model | LLM supplies per-hypothesis **likelihoods** (`Z_PROMPT_TEMPLATE`); CODE Bayes-normalizes in `update_belief` (ε-floored → soft) |
| **T** | effect of an action on state | which factor an observation updates is routed by the action (`_target_factor` in `update_belief`): exploit/lateral/privesc → that host's `vulns`; recon → a probed `service` or the `os` distribution. _T-effect test: `tests/test_agent.py`_ |
| **R** | goal value − cost − detection risk | `pomdp/belief_state.py::score_action`, fed by `pomdp/priors.py` (CVSS/exploit-maturity); emitted as the `score` event per step |
| **π** | belief → action | `pomdp/belief_state.py::choose_action` (info-gain vs exploit-value argmax) |
| **γ** | discount factor | `pomdp/belief_state.py::GAMMA` |
| **loop** | choose → (HITL gate) → execute → observe → update → persist | `pomdp/agent.py::BeliefAgent.run` (TL-2.1): b0 = `new_belief` + `priors.seed_vuln_priors`; default candidate gen (recon per host + priors-enriched exploits, overridable); default root goal; every side channel best-effort. `run_agent` delegates here (TL-2.2) |

## Where the numbers come from
- **b0 priors:** conventional — uniform "unknown" over OS; CVSS + exploit-maturity for vulns
  (`pomdp/priors.py::vuln_prior_present` / `seed_vuln_priors`). Bayes washes out imperfect priors.
- **Z:** the LLM as a learned observation model (answering Sarraute 2013 / CHECKMATE's "unobtainable
  Z tables"). Only the **direction/order** of likelihoods must be right, e.g. `Z(fail|present) <
  Z(fail|absent)`. Optional **self-consistency**: average Z over N LLM samples (`update_belief(samples=N)`,
  driven by `VULNBOT_Z_SAMPLES` — TL-2.3).

## Partial observability is provable (tests)

`tests/test_belief.py` (all passing) locks the four properties the thesis relies on:
1. a failed observation **softens** belief (0.70 → ~0.5), never collapses to 0 (EPS floor);
2. belief keeps mass on **multiple** hypotheses at once;
3. **Z is not the identity** (a scan can miss a present service; an exploit can fail with the vuln present);
4. the update follows the **direction/order** of the likelihoods.

`tests/test_agent.py` (all passing) adds the R1-loop guarantees: **self-consistency** (`samples>1`
averages Z — an alternating 0.9/0.1 likelihood collapses to a ~0.5 posterior at `samples=2`; and the
5-sample posterior variance is below the 1-sample variance over many noisy updates) and the explicit
**T-effect** (the same observation under an exploit vs a recon moves different belief factors). Ablation:
`VULNBOT_BELIEF_POLICY=0` disables belief-driven action selection (free with/without-belief eval).

## Running the belief agent

- **Standalone:** `python pentest.py --agent -m <step-cap> --description "<target-ip> <task>"` — drives
  `BeliefAgent` instead of the legacy 3-phase pipeline (still the default without `--agent`). Wires an R3
  `Executor` (SSH [+ msfrpc] [+ MCP if `VULNBOT_MCP`]), a `str→str` belief LLM over `server.chat.chat._chat`,
  a per-run `EventLog` (`data/runs/agent-<ts>/events.jsonl`) and `BeliefStore` (`data/beliefs/agent-<ts>/`).
- **From the octopus CLI:** `/run --agent <target-ip | task>`.
- **Programmatic:** `pomdp.agent.run_agent(executor, belief_llm, session_id, hosts=…, vuln_ids=…)`.
- **Knobs:** `VULNBOT_Z_SAMPLES` (self-consistency), `VULNBOT_BELIEF_POLICY=0` (ablation).

## Event trace (R4 link)

Every step emits JSON records (`utils/events.py`, schema below) so the belief evolution is inspectable
and the Ink `LogView` can render it. `belief_update` carries the factor's distribution **before and
after**; `llm_likelihoods` carries the Z the update used (`belief["meta"]["last_update"].z`).

Event `type` union: `run_start, phase, action_selected, observation, llm_likelihoods, belief_update,
score, decision, approval_request, approval_result, error, run_end` (see `EVENT_TYPES`).
