# POMDP_INTEGRATION — the tuple ⟨S, A, O, T, Z, R, b, γ⟩ in code (R1)

> **Status:** mapping + schemas pinned (TL-0.4). Standalone loop `run_agent`/`BeliefAgent` and the
> self-consistency + T-effect tests land in TL-2; this doc is completed in TL-2.7.

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
| **T** | effect of an action on state | reasoned about inside `update_belief` (belief transition); _T-effect test: TL-2.6_ |
| **R** | goal value − cost − detection risk | `pomdp/belief_state.py::score_action`, fed by `pomdp/priors.py` (CVSS/exploit-maturity) |
| **π** | belief → action | `pomdp/belief_state.py::choose_action` (info-gain vs exploit-value argmax) |
| **γ** | discount factor | `pomdp/belief_state.py::GAMMA` |
| **loop** | choose → execute → observe → update → persist | `pomdp/agent.py::BeliefAgent` (TL-2.1); `run_agent` delegates (TL-2.2) |

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

TL-2.6 adds: self-consistency (`samples>1` averages Z and lowers variance) and an explicit **T-effect**
assertion. Ablation: `VULNBOT_BELIEF_POLICY=0` disables belief-driven action selection (free
with/without-belief eval).

## Event trace (R4 link)

Every step emits JSON records (`utils/events.py`, schema below) so the belief evolution is inspectable
and the Ink `LogView` can render it. `belief_update` carries the factor's distribution **before and
after**; `llm_likelihoods` carries the Z the update used (`belief["meta"]["last_update"].z`).

Event `type` union: `run_start, phase, action_selected, observation, llm_likelihoods, belief_update,
score, decision, approval_request, approval_result, error, run_end` (see `EVENT_TYPES`).
