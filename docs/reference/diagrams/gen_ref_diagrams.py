"""Generate the 4 reference-documentation diagrams as .excalidraw files.

Deterministic (no randomness, no browser) — the companion `docs/tools/render_png.py` rasterizes
each .excalidraw to a PNG. Same element schema / helper pattern as `docs/tools/gen_excalidraw.py`.

Diagrams:
  1. agents.excalidraw      — the multi-agent map (who talks to whom)
  2. architecture.excalidraw— full module / data-flow overview
  3. pomdp_loop.excalidraw  — the R1 belief loop + POMDP tuple + three process lanes
  4. executor.excalidraw    — the R3 executor facade / router / channels

Run:  python docs/reference/diagrams/gen_ref_diagrams.py
Then: for each, python docs/tools/render_png.py <name>.excalidraw <name>.png
"""
import json
import os

# ── palette (excalidraw skill conventions) ──────────────────────────────────────
UI      = ("#1971c2", "#a5d8ff")   # frontend / CLI
PROC    = ("#7048e8", "#d0bfff")   # roles / planner / processing
DB      = ("#2f9e44", "#b2f2bb")   # persistence
AI      = ("#9c36b5", "#e599f7")   # LLM / belief / AI
DANGER  = ("#e03131", "#ffc9c9")   # Kali / target / exploit
EXEC    = ("#e8590c", "#ffd8a8")   # executor / gate
DECIDE  = ("#f08c00", "#ffec99")   # decision / event log
GRAY    = ("#343a40", "#e9ecef")   # neutral / zone
ZONE    = ("#868e96", "#f1f3f5")

_c = [0]
def nid():
    _c[0] += 1
    return f"el{_c[0]:04d}"
def seed():
    _c[0] += 1
    return 1000 + _c[0] * 7

elements = []
nodes = {}

def reset():
    elements.clear()
    nodes.clear()

def node(key, x, y, w, h, label, color=GRAY, dashed=False):
    stroke, bg = color
    box_id = nid(); txt_id = nid()
    elements.append({
        "id": box_id, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "dashed" if dashed else "solid", "roughness": 1,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": {"type": 3},
        "seed": seed(), "version": 1, "versionNonce": seed(), "isDeleted": False,
        "boundElements": [{"type": "text", "id": txt_id}], "updated": 1, "link": None, "locked": False,
    })
    lines = label.count("\n") + 1
    fs = 15
    elements.append({
        "id": txt_id, "type": "text", "x": x + 8, "y": y + h / 2 - (lines * fs * 1.25) / 2,
        "width": w - 16, "height": lines * fs * 1.25, "angle": 0, "strokeColor": stroke,
        "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2,
        "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": None, "seed": seed(), "version": 1, "versionNonce": seed(), "isDeleted": False,
        "boundElements": [], "updated": 1, "link": None, "locked": False, "text": label,
        "fontSize": fs, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
        "containerId": box_id, "originalText": label, "lineHeight": 1.25, "baseline": fs,
    })
    nodes[key] = {"id": box_id, "x": x, "y": y, "w": w, "h": h}

def _edge_point(n, side):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    return {"t": (x + w / 2, y), "b": (x + w / 2, y + h),
            "l": (x, y + h / 2), "r": (x + w, y + h / 2)}[side]

def arrow(a, sa, b, sb, color=None, dashed=False, label=None):
    n1, n2 = nodes[a], nodes[b]
    p1 = _edge_point(n1, sa); p2 = _edge_point(n2, sb)
    stroke = color[0] if color else GRAY[0]
    elements.append({
        "id": nid(), "type": "arrow", "x": p1[0], "y": p1[1],
        "width": abs(p2[0] - p1[0]), "height": abs(p2[1] - p1[1]), "angle": 0,
        "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "dashed" if dashed else "solid", "roughness": 1,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": {"type": 2}, "seed": seed(),
        "version": 1, "versionNonce": seed(), "isDeleted": False, "boundElements": [], "updated": 1,
        "link": None, "locked": False, "points": [[0, 0], [p2[0] - p1[0], p2[1] - p1[1]]],
        "lastCommittedPoint": None, "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow",
    })
    if label:
        mx = (p1[0] + p2[0]) / 2; my = (p1[1] + p2[1]) / 2
        elements.append({
            "id": nid(), "type": "text", "x": mx - 45, "y": my - 9, "width": 90, "height": 16,
            "angle": 0, "strokeColor": stroke, "backgroundColor": "#ffffff", "fillStyle": "solid",
            "strokeWidth": 1, "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "seed": seed(), "version": 1, "versionNonce": seed(),
            "isDeleted": False, "boundElements": [], "updated": 1, "link": None, "locked": False,
            "text": label, "fontSize": 11, "fontFamily": 1, "textAlign": "center",
            "verticalAlign": "middle", "containerId": None, "originalText": label,
            "lineHeight": 1.25, "baseline": 11,
        })

def title(x, y, text, size=26, color=GRAY):
    elements.append({
        "id": nid(), "type": "text", "x": x, "y": y, "width": 900, "height": size * 1.3, "angle": 0,
        "strokeColor": color[0], "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100, "groupIds": [],
        "frameId": None, "roundness": None, "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None, "locked": False,
        "text": text, "fontSize": size, "fontFamily": 1, "textAlign": "left", "verticalAlign": "top",
        "containerId": None, "originalText": text, "lineHeight": 1.25, "baseline": size,
    })

def write(name):
    doc = {"type": "excalidraw", "version": 2, "source": "octopus-ref-diagrams",
           "elements": list(elements), "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
           "files": {}}
    out = os.path.join(os.path.dirname(__file__), name)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print("wrote", out, "elements:", len(elements))

W, H = 240, 88

# ══════════════════════════════════════════════════════════════════════════════
# 1. AGENT-CONNECTION GRAPH
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Octopus — Agent Connection Map", 26, GRAY)
title(40, 54, "Purple = pipeline agents  |  Magenta = belief/LLM  |  Orange = executor  |  Blue = front-end", 13, ZONE)

# front-end + entry
node("user",   40,  110, W, H, "User / Session\ntarget IP + task\n(pentest.py)", UI)
node("cli",    40,  260, W, H, "octopus CLI (Ink)\nlive view + HITL + LogView\n(cli/)", UI)

# the three phase agents (chain)
node("collector", 360, 110, W, H, "Collector\nRECON phase\n(roles/collector.py)", PROC)
node("scanner",   660, 110, W, H, "Scanner\nVULN-SCAN phase\n(roles/scanner.py)", PROC)
node("exploiter", 960, 110, W, H, "Exploiter\nEXPLOIT phase\n(roles/exploiter.py)", PROC)

# per-phase workers (shared)
node("planner",   360, 300, W, H, "Planner + WritePlan\nPTG task graph\n(actions/planner.py)", PROC)
node("generator", 660, 300, W, H, "Generator\nWriteCode -> <execute>\n(actions/write_code.py)", PROC)
node("executor",  960, 300, W, H, "Executor\nExecuteTask + ShellManager\n(actions/execute_task.py)", EXEC)
node("summarizer",360, 450, W, H, "Summarizer\nPlannerSummary\n(actions/plan_summary.py)", PROC)

# LLM + belief
node("llm",   660, 470, W, H, "LLM choke point  _chat\nOpenAI / Anthropic / Ollama\n(server/chat/chat.py)", AI)
node("kali",  960, 470, W, H, "Kali tools (Docker)\nSSH + msfrpc\n-> target", DANGER)

# belief agents (this fork)
node("beliefagent", 40, 470, W, H, "BeliefAgent (R1)\nstandalone POMDP loop\n(pomdp/agent.py)", AI)
node("updater", 40, 620, W, H, "Belief Updater\nupdate_belief (Z+Bayes)\n(pomdp/belief_state.py)", AI)
node("bcp",     360, 620, W, H, "Belief-Cond. Planner\nchoose_action (pi)\n(pomdp/belief_state.py)", AI)
node("store",   660, 620, W, H, "Belief Store\nper-step JSON trace\n(pomdp/belief_store.py)", AI)
node("priors",  960, 620, W, H, "Reward + Priors\nscore_action + priors\n(pomdp/priors.py)", AI)

# pipeline chain
arrow("user", "r", "collector", "l", PROC, label="session")
arrow("collector", "r", "scanner", "l", PROC, label="hand off")
arrow("scanner", "r", "exploiter", "l", PROC, label="hand off")
# per phase
arrow("collector", "b", "planner", "t", PROC)
arrow("planner", "r", "generator", "l", PROC, label="next task")
arrow("generator", "r", "executor", "l", PROC, label="commands")
arrow("executor", "b", "kali", "t", EXEC, label="SSH/msf")
arrow("summarizer", "t", "planner", "b", PROC, label="context")
# LLM edges
arrow("planner", "b", "llm", "l", AI, dashed=True)
arrow("generator", "b", "llm", "t", AI, dashed=True)
arrow("summarizer", "r", "llm", "l", AI, dashed=True)
# belief edges
arrow("beliefagent", "r", "executor", "l", AI, dashed=True, label="run(action)")
arrow("beliefagent", "b", "updater", "t", AI)
arrow("updater", "r", "bcp", "l", AI, dashed=True, label="belief b")
arrow("bcp", "r", "store", "l", AI, dashed=True)
arrow("priors", "t", "kali", "b", AI, dashed=True)
arrow("bcp", "t", "planner", "b", AI, dashed=True, label="task_selector")
arrow("cli", "r", "beliefagent", "l", UI, dashed=True, label="HITL socket")
arrow("cli", "t", "user", "b", UI, dashed=True)
write("agents.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 2. SYSTEM ARCHITECTURE OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Octopus — System Architecture & Data Flow", 26, GRAY)

node("user",  40,  110, W, H, "User / Session\ninit_description\n(pentest.py)", UI)
node("roles", 360, 110, W, H, "Role agents\nCollector>Scanner>Exploiter\n(roles/)", PROC)
node("planner", 660, 110, W, H, "Planner + WritePlan\nPTG (Kahn topo sort)\n(actions/)", PROC)
node("gen",   960, 110, W, H, "Generator\nWriteCode\n(write_code.py)", PROC)
node("exec",  1260, 110, W, H, "Executor\nExecuteTask\n(execute_task.py)", EXEC)

node("summ",  360, 280, W, H, "Summarizer\nPlannerSummary\n(plan_summary.py)", PROC)
node("llm",   660, 280, 300, H, "LLM choke point  _chat\nOpenAI/Anthropic/Ollama + retry\n(server/chat/chat.py)", AI)
node("rag",   1010, 280, W, H, "Memory-Retriever (RAG)\nMilvus + rerank + IP-scrub\n(rag/)", AI)
node("kali",  1260, 280, W, H, "kali-tools (Docker)\nSSH :2222 + msfrpc :55553", DANGER)

node("db",    660, 450, 300, H, "MySQL\nsessions/plans/tasks/\nconversations/messages (db/)", DB)
node("target",1260, 450, W, H, "target (Docker)\nvulnerable host\nlabnet (isolated)", DANGER)

# belief layer
node("belief", 40, 280, W, H, "Belief layer (POMDP)\nbelief_state / store / priors\n(pomdp/)", AI)
node("beliefagent", 40, 450, W, H, "BeliefAgent loop (R1)\nrun_agent --agent\n(pomdp/agent.py)", AI)
node("executor2", 360, 450, W, H, "R3 Executor\nSSH/msf/MCP + router\n(executor/)", EXEC)

# CLI + lanes
node("cli",   40,  620, W, H, "octopus CLI (Ink)\nsetup/model/run/log\n(cli/)", UI)
node("events",360, 620, W, H, "Event log (R4)\ndata/runs/<id>/events.jsonl\n(utils/events.py)", DECIDE)
node("control",660, 620, W, H, "Control socket (R2)\nloopback HITL\n(utils/control.py)", DECIDE)
node("beliefstore", 960, 620, W, H, "Belief trace\ndata/beliefs/<id>/*.json\n(belief_store.py)", AI)

# main flow
arrow("user", "r", "roles", "l", PROC)
arrow("roles", "r", "planner", "l", PROC)
arrow("planner", "r", "gen", "l", PROC, label="next task")
arrow("gen", "r", "exec", "l", PROC, label="commands")
arrow("exec", "b", "kali", "t", EXEC, label="SSH/msf")
arrow("kali", "b", "target", "t", DANGER, label="tools")
arrow("summ", "t", "roles", "b", PROC, label="context")
# llm/persistence
arrow("roles", "b", "llm", "t", AI, dashed=True)
arrow("gen", "b", "llm", "r", AI, dashed=True)
arrow("llm", "r", "rag", "l", AI, dashed=True, label="RAG if on")
arrow("llm", "b", "db", "b", DB, dashed=True, label="history")
# belief (kept as short, non-crossing edges; the belief->Kali detail is in the executor diagram)
arrow("belief", "r", "summ", "l", AI, dashed=True)
arrow("beliefagent", "r", "executor2", "l", AI, label="run(action)")
# cli lanes
arrow("cli", "r", "events", "l", UI, dashed=True, label="LogView tails")
arrow("control", "l", "cli", "b", DECIDE, dashed=True, label="approve/deny")
arrow("beliefagent", "b", "events", "t", DECIDE, dashed=True, label="writes")
write("architecture.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 3. POMDP BELIEF LOOP + THREE-LANE BOUNDARY
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "R1 Belief Loop  <S,A,O,T,Z,R,b,gamma,pi>  +  three process lanes", 24, GRAY)

# the loop (vertical cycle on the left)
node("b0",    120, 110, W, H, "b0 = new_belief\n+ priors.seed_vuln_priors\n(conventional prior b)", AI)
node("pi",    120, 250, W, H, "pi: choose_action\ninfo-gain vs exploit R\n(policy)", AI)
node("gate",  120, 390, W, H, "HITL gate (R2)\nhigh-impact -> approve?\n(_gate / control)", EXEC)
node("act",   480, 390, W, H, "A: Executor.run(action)\nSSH / msfrpc / MCP\n-> Kali (R3)", DANGER)
node("obs",   480, 250, W, H, "O: Observation.raw\nraw tool output", DECIDE)
node("upd",   480, 110, W, H, "Z + Bayes: update_belief\nLLM likelihoods, eps-floored\nsoft posterior over S", AI)
node("save",  120, 530, W, H, "belief_store.save\nper-step JSON trace\n(loop until goal / cap)", AI)

arrow("b0", "b", "pi", "t", AI)
arrow("pi", "b", "gate", "t", AI)
arrow("gate", "r", "act", "l", EXEC, label="approved")
arrow("act", "t", "obs", "b", DECIDE, label="O")
arrow("obs", "t", "upd", "b", AI, label="Z")
arrow("upd", "l", "pi", "r", AI, dashed=True, label="new b")
arrow("gate", "b", "save", "t", AI, dashed=True)

# tuple legend box
node("tuple", 820, 110, 340, 300,
     "POMDP tuple -> code\nS  hidden state (never read)\nb  factored JSON belief\nA  Action (recon/exploit/...)\nO  Observation.raw\nZ  LLM likelihoods (update_belief)\nT  action routing (_target_factor)\nR  score_action + priors\npi choose_action\ngamma  GAMMA discount", GRAY)

# three lanes
title(820, 440, "Three process lanes (Py <-> octopus CLI)", 15, ZONE)
node("lane1", 820, 480, 340, 70, "1. ##OCTO## stdout markers (live ticker)", DECIDE)
node("lane2", 820, 565, 340, 70, "2. events.jsonl on disk (source of truth)", DECIDE)
node("lane3", 820, 650, 340, 70, "3. loopback control socket (HITL)", DECIDE)
write("pomdp_loop.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 4. EXECUTOR CHANNELS + R3 ROUTING
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "R3 Executor — facade, router, channels, Observation", 24, GRAY)

node("action", 60, 140, W, H, "Action\n(pomdp.belief_state)\ntype + host + params", PROC)
node("facade", 380, 140, 260, H, "Executor.run(action)\ntimeout / retry / fallback\nnever raises (facade)", EXEC)
node("router", 720, 140, 260, H, "router.channel_router\npick by action type\n+ logged justification", DECIDE)

node("ssh",  1060, 60, W, H, "SshChannel\narbitrary tools\n(ShellManager)", DANGER)
node("msf",  1060, 180, W, H, "MsfChannel\nMetasploit modules\n(pymetasploit3)", DANGER)
node("mcp",  1060, 300, W, H, "McpChannel\nflag-gated OCTOPUS_MCP=0\n(stub)", GRAY)

node("obs",  720, 340, 260, H, "Observation\nraw=O, structured,\nsuccess, channel, error", DECIDE)
node("kali", 1060, 430, W, H, "Kali tools (Docker)\n-> target", DANGER)

arrow("action", "r", "facade", "l", PROC, label="run")
arrow("facade", "r", "router", "l", EXEC, label="candidates")
arrow("router", "r", "ssh", "l", DECIDE, label="recon / no-module")
arrow("router", "r", "msf", "l", DECIDE, label="exploit + module")
arrow("router", "r", "mcp", "l", GRAY, dashed=True, label="if enabled")
arrow("ssh", "b", "kali", "t", DANGER)
arrow("msf", "r", "kali", "t", DANGER)
arrow("ssh", "b", "obs", "r", DECIDE, dashed=True)
arrow("obs", "l", "facade", "b", EXEC, dashed=True, label="normalized O")

# policy note
node("policy", 60, 340, 300, 150,
     "Routing policy:\n- recon -> ssh\n- exploit/lateral/privesc\n  naming an MSF module -> msf\n  (ssh fallback), else -> ssh\nTimeout: daemon-thread budget\nRetry: ChannelError only\n(never after timeout)", GRAY)
write("executor.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 00-a  RUN LIFECYCLE — the legacy 3-phase pipeline
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Run lifecycle — the 3-phase pipeline (pentest.py)", 22, GRAY)
node("main",  60,  100, 260, 80, "pentest.py::main\npreflight MySQL + create_tables\nload/build Session (Collector)", UI)
node("plan",  60,  240, 260, 80, "Role._plan\nopen 2 chats, WritePlan.run\n-> _chat -> parse_tasks -> Plan", PROC)
node("react", 60,  400, 260, 80, "Role._react  (loop <= m)\nWriteCode -> ExecuteTask\n-> Kali -> update_plan", PROC)
node("hand",  60,  560, 260, 80, "Role.put_message\npersist tasks -> chain role\nCollector>Scanner>Exploiter", PROC)
node("gen",  420,  360, 240, 80, "WriteCode (Generator)\n_chat(write_code)\n-> <execute> commands", PROC)
node("exec", 420,  480, 240, 80, "ExecuteTask (Executor)\nShellManager SSH -> Kali\nraw stdout = observation", EXEC)
node("judge",420,  600, 240, 80, "Planner.update_plan\n_chat(check_success) + replan\n-> next ready task", PROC)
node("llm",  760,  360, 240, 80, "LLM choke point _chat\nMySQL history + persist\n(server/chat/chat.py)", AI)
node("kali", 760,  480, 240, 80, "Kali tools (Docker)\nSSH + msfrpc -> target", DANGER)
arrow("main", "b", "plan", "t", PROC)
arrow("plan", "b", "react", "t", PROC)
arrow("react", "b", "hand", "t", PROC, label="budget spent")
arrow("react", "r", "gen", "l", PROC)
arrow("gen", "b", "exec", "t", PROC, label="commands")
arrow("exec", "b", "judge", "t", EXEC, label="observation")
arrow("judge", "l", "react", "r", PROC, dashed=True, label="next task")
arrow("gen", "r", "llm", "l", AI, dashed=True)
arrow("judge", "r", "llm", "b", AI, dashed=True)
arrow("exec", "r", "kali", "l", EXEC, label="SSH")
arrow("hand", "t", "plan", "l", PROC, dashed=True, label="next phase")
write("00-lifecycle-pipeline.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 00-b  RUN LIFECYCLE — the --agent belief loop
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Run lifecycle — the R1 belief agent (pentest.py --agent)", 22, GRAY)
node("wire", 60, 100, 300, 92, "run_belief_agent (pentest.py)\nwire Executor(R3)+belief_llm(_chat)\n+EventLog+BeliefStore+ControlServer\nwait <=8s for the octopus CLI", UI)
node("b0",   60, 240, 300, 70, "b0 = new_belief +\npriors.seed_vuln_priors", AI)
node("loop", 60, 360, 300, 70, "BeliefAgent.run  (loop <= max_steps)", AI)
node("poll", 480, 250, 220, 70, "_poll_control\npause / quit (R2)", DECIDE)
node("pi",   480, 350, 220, 70, "choose_action (pi)\ninfo-gain vs exploit R", AI)
node("gate", 480, 450, 220, 70, "_gate (HITL R2)\napprove/deny/quit/step", EXEC)
node("run",  760, 450, 220, 70, "executor.run(action)\n-> Observation (R3)", DANGER)
node("upd",  760, 350, 220, 70, "update_belief\nZ + soft Bayes", AI)
node("save", 760, 250, 220, 70, "belief_store.save +\nEventLog.append (R4)", AI)
node("end",  60, 500, 300, 70, "goal or cap ->\nwrite_manifest, close", GRAY)
arrow("wire", "b", "b0", "t", UI)
arrow("b0", "b", "loop", "t", AI)
arrow("loop", "r", "pi", "l", AI)
arrow("poll", "b", "pi", "t", DECIDE, dashed=True)
arrow("pi", "b", "gate", "t", AI)
arrow("gate", "r", "run", "l", EXEC, label="approved")
arrow("run", "t", "upd", "b", AI, label="O")
arrow("upd", "t", "save", "b", AI)
arrow("save", "l", "loop", "r", AI, dashed=True, label="next step")
arrow("loop", "b", "end", "t", GRAY, dashed=True)
write("00-lifecycle-agent.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 01-a  FACTORED BELIEF TREE
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Factored belief  b  (per-host distributions) — a tree", 22, GRAY)
node("root", 60, 110, 240, 76, "belief b (dict)\nsession_id, step, meta", AI)
node("meta", 60, 240, 240, 60, "meta.last_update\nz / prior / posterior", GRAY)
node("hosts",380, 110, 220, 76, "hosts\n{ ip -> host belief }", AI)
node("host", 700, 110, 220, 76, "host belief\n(one target)", AI)
node("os",   980, 30, 240, 62, "os: {linux, windows,\nother, unknown} sum=1", AI)
node("svc",  980, 110, 240, 62, "services: {port ->\n{present, absent}}", AI)
node("vuln", 980, 190, 240, 62, "vulns: {cve ->\n{present, absent}}", AI)
node("acc",  980, 270, 240, 62, "access: {none,\nuser, root} sum=1", AI)
node("hp",   980, 350, 240, 62, "honeypot_likelihood\np in [0,1]", DANGER)
arrow("root", "b", "meta", "t", GRAY, dashed=True)
arrow("root", "r", "hosts", "l", AI)
arrow("hosts", "r", "host", "l", AI)
arrow("host", "r", "os", "l", AI)
arrow("host", "r", "svc", "l", AI)
arrow("host", "r", "vuln", "l", AI)
arrow("host", "r", "acc", "l", AI)
arrow("host", "r", "hp", "l", DANGER)
node("note", 60, 340, 240, 120, "S (hidden true state) is\nNEVER stored here.\nUpdates are soft: eps-floored\nso a failed obs softens a\nfactor but never zeroes it.", GRAY)
write("01-belief-structure.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 01-b  UPDATER — Z + soft Bayes
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "update_belief — LLM likelihood Z + soft Bayesian update", 22, GRAY)
node("in",   60, 120, 240, 84, "inputs:\nprior dist (factor)\naction + observation O", AI)
node("prompt",380, 120, 240, 84, "Z_PROMPT_TEMPLATE\nask per-hypothesis\nLIKELIHOODS (not posterior)", DECIDE)
node("llm",  700, 120, 240, 84, "LLM (belief_llm)\ncalled x samples\n(self-consistency)", AI)
node("parse",700, 260, 240, 70, "_parse_likelihoods\neps-floored, avg over samples\n-> z_avg", AI)
node("bayes",380, 260, 240, 84, "Bayes (code):\nunnorm = prior x z_avg\nnormalize -> posterior", PROC)
node("out",  60, 260, 240, 84, "posterior dist\nstep += 1\nmeta.last_update = {z,prior,post}", AI)
arrow("in", "r", "prompt", "l", AI)
arrow("prompt", "r", "llm", "l", DECIDE)
arrow("llm", "b", "parse", "t", AI, label="raw x N")
arrow("parse", "l", "bayes", "r", AI, label="z_avg")
arrow("in", "b", "bayes", "t", AI, dashed=True, label="prior")
arrow("bayes", "l", "out", "r", PROC)
node("note", 980, 150, 240, 150, "Why soft:\nZ floored at EPS=1e-3, so\nposterior never collapses to 0.\nOnly the ORDER of likelihoods\nmust be right (e.g. a failed\nexploit is more expected if the\nvuln is ABSENT).", GRAY)
write("01-updater.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 01-c  POLICY pi vs REWARD R
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "choose_action (pi)  and  score_action (R)", 22, GRAY)
node("cands", 60, 130, 240, 76, "candidates: [Action]\nrecon + priors-enriched\nexploits", PROC)
node("util",  380, 130, 260, 76, "for each: _action_utility\nrouted by action.type", DECIDE)
node("recon", 720, 40, 300, 76, "RECON:\nW_INFO x normalized entropy\nof the probed factor - detection", AI)
node("expl",  720, 150, 300, 90, "EXPLOIT/LATERAL/PRIVESC:\nscore_action = P(succeeds|b) x value\n- cost - detection\n(detection = honeypot + risk)", DANGER)
node("arg",   380, 280, 260, 70, "argmax utility\n-> chosen Action (pi)", AI)
arrow("cands", "r", "util", "l", PROC)
arrow("util", "r", "recon", "l", AI, label="type=recon")
arrow("util", "r", "expl", "l", DANGER, label="type=exploit")
arrow("recon", "b", "arg", "t", AI, dashed=True)
arrow("expl", "l", "arg", "r", DANGER, dashed=True)
node("note", 60, 290, 240, 120, "The SAME candidates yield\nDIFFERENT picks under\ndifferent beliefs: recon while\na factor is uncertain, exploit\nonce the belief is confident.", GRAY)
write("01-policy-reward.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 02-a  ROUTER decision
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "route(action, channels) -> RouteDecision", 22, GRAY)
node("act", 60, 130, 220, 76, "Action\ntype + params[module]", PROC)
node("filt",340, 130, 240, 76, "filter: c.supports(action)\n(capable channels)", DECIDE)
node("rank",640, 130, 260, 76, "sort by\n(_rank_for(type,name), name)", DECIDE)
node("dec", 960, 130, 260, 90, "RouteDecision\nordered (primary first)\n+ reason\n(##OCTO## decision marker)", EXEC)
node("r1",  640, 280, 260, 60, "recon -> [ssh]", AI)
node("r2",  960, 280, 260, 60, "exploit+module -> [msfrpc, ssh]", DANGER)
arrow("act", "r", "filt", "l", PROC)
arrow("filt", "r", "rank", "l", DECIDE)
arrow("rank", "r", "dec", "l", DECIDE)
arrow("rank", "b", "r1", "t", AI, dashed=True)
arrow("dec", "b", "r2", "t", DANGER, dashed=True)
node("note", 60, 280, 500, 90, "msfrpc outranks ssh for offensive types REGARDLESS of registration order\n(the sort key, not list order, decides). No supporting channel -> empty decision.\nchannel_router() is the Executor's default (lazy-imported in base.py).", GRAY)
write("02-router.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 02-b  ROBUSTNESS state machine
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Executor.run — timeout / retry / fallback (never raises)", 22, GRAY)
node("run",  60, 130, 220, 70, "run(action)\nrouter -> candidates", EXEC)
node("try",  360, 130, 240, 70, "_try_channel\n_call_with_timeout\n(daemon-thread budget)", EXEC)
node("ok",   700, 40, 240, 64, "OK -> stamp channel/\nduration/id -> return O", AI)
node("cerr", 700, 130, 240, 74, "ChannelError\n(tool did NOT run)\n-> retry <= retries", DECIDE)
node("tmo",  700, 230, 240, 74, "ChannelTimeout\n(tool may have started)\n-> NO retry, next channel", DANGER)
node("bug",  700, 330, 240, 64, "other Exception\n-> no retry, next channel", DANGER)
node("dead", 360, 300, 240, 74, "all candidates dead ->\nfailure Observation\n(never raises)", GRAY)
arrow("run", "r", "try", "l", EXEC)
arrow("try", "r", "ok", "l", AI, label="success")
arrow("try", "r", "cerr", "l", DECIDE)
arrow("try", "r", "tmo", "l", DANGER)
arrow("try", "r", "bug", "l", DANGER)
arrow("cerr", "l", "try", "b", DECIDE, dashed=True, label="retry")
arrow("try", "b", "dead", "t", GRAY, dashed=True, label="exhausted")
node("note", 60, 300, 260, 90, "A late success records the\nfailed attempts under\nstructured[_executor_fallback]\n(non-destructive trail).", GRAY)
write("02-robustness.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 03-a  ROLE loop state graph
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Role.run — plan -> react -> hand off (per phase)", 22, GRAY)
node("run",  60, 120, 220, 64, "Role.run(session)", PROC)
node("plan", 340, 120, 240, 80, "_plan\ninit/resume Planner+Plan\nWritePlan -> parse_tasks", PROC)
node("react",640, 120, 240, 80, "_react  (loop <= m)\nWriteCode -> ExecuteTask\n-> update_plan -> next", PROC)
node("hand", 940, 120, 260, 80, "put_message\npersist tasks + chain\nto the next role", PROC)
node("belief",640, 280, 240, 80, "belief hooks (best-effort)\n_belief_persist (Updater)\n_belief_choose_next (pi)", AI)
arrow("run", "r", "plan", "l", PROC)
arrow("plan", "r", "react", "l", PROC, label="first task")
arrow("react", "r", "hand", "l", PROC, label="budget spent")
arrow("react", "b", "react", "l", PROC, dashed=True, label="next task")
arrow("react", "b", "belief", "t", AI, dashed=True)
node("chain", 340, 280, 240, 90, "chain: Collector.put_message\n-> Scanner.run -> Scanner.\nput_message -> Exploiter.run\n(Exploiter is terminal)", GRAY)
write("03-role-loop.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 03-b  PTG — Penetration Task Graph (DAG + Kahn)
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Penetration Task Graph (PTG) — a dependency DAG, Kahn topo-sorted", 22, GRAY)
node("t1", 120, 120, 220, 70, "T1 recon\n(finished, success)", DB)
node("t2", 420, 60, 220, 70, "T2 enum svc\n(ready)", DECIDE)
node("t3", 420, 200, 220, 70, "T3 vuln scan\n(ready)", DECIDE)
node("t4", 740, 120, 220, 70, "T4 exploit\n(blocked: deps T2,T3)", DANGER)
node("t5", 1040, 120, 220, 70, "T5 privesc\n(blocked: dep T4)", GRAY)
arrow("t1", "r", "t2", "l", DB, label="dep")
arrow("t1", "r", "t3", "l", DB, label="dep")
arrow("t2", "r", "t4", "l", DECIDE)
arrow("t3", "r", "t4", "l", DECIDE)
arrow("t4", "r", "t5", "l", DANGER)
node("leg", 120, 300, 560, 120,
     "Plan.get_sorted_tasks() = Kahn topological sort over integer dependencies (raises on a cycle).\ncurrent_task = first unfinished task in topo order (the deterministic pick).\nready_tasks = unfinished tasks whose deps are all finished-success (the frontier = the belief\npolicy's candidate set). WritePlan.update + merge_tasks revise this graph after each result.", GRAY)
write("03-ptg.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 04-a  _chat choke point
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "_chat — the single LLM choke point", 22, GRAY)
node("q",   60, 120, 220, 70, "query (+ optional\nkb_name / conversation_id)", PROC)
node("rag", 340, 60, 240, 70, "RAG? search_docs +\nrerank + IP-scrub", AI)
node("trunc",340, 170, 240, 64, "truncate by\ncontext_length", GRAY)
node("hist",640, 120, 240, 70, "load history (MySQL)\nadd/loop conversation", DB)
node("prov",940, 120, 260, 90, "provider client\nOpenAIChat / AnthropicChat /\nOllamaChat (retry, thinking)", AI)
node("persist",640, 260, 240, 70, "persist Q + A\n(conversations/messages)", DB)
node("ret", 940, 260, 260, 70, "return response\nor (response, conv_id)", PROC)
arrow("q", "r", "rag", "l", AI, dashed=True, label="if enable_rag")
arrow("q", "r", "trunc", "l", GRAY)
arrow("trunc", "r", "hist", "l", GRAY)
arrow("rag", "r", "hist", "l", AI, dashed=True)
arrow("hist", "r", "prov", "l", DB)
arrow("prov", "b", "persist", "l", DB, label="summary")
arrow("prov", "b", "ret", "t", PROC)
write("04-chat.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 04-b  DB schema (ER graph)
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "MySQL schema — sessions / plans / tasks / conversations / messages", 22, GRAY)
node("sess", 60, 130, 240, 90, "sessions\nid, name, init_description\ncurrent_role_name\ncurrent_planner_id, history", DB)
node("plan", 400, 130, 240, 90, "plans\nid, goal, current_task_seq\nplan_chat_id, react_chat_id", DB)
node("task", 740, 130, 240, 90, "tasks\nid, plan_id (FK), sequence\naction, instruction, code\nresult, is_success/finished\ndependencies (JSON)", DB)
node("conv", 400, 320, 240, 76, "conversations\nid, name, chat_type\ncreate_time", DB)
node("msg",  740, 320, 240, 90, "messages\nid, conversation_id (FK)\nchat_type, query, response\nmeta_data, create_time", DB)
arrow("sess", "r", "plan", "l", DB, label="planner_id")
arrow("plan", "r", "task", "l", DB, label="1 : N")
arrow("conv", "r", "msg", "l", DB, label="1 : N")
node("note", 60, 320, 240, 90, "Written by db/repository/*\nvia utils.session.with_session.\n_chat persists conversations\n+ messages; roles persist\nplans + tasks.", GRAY)
write("04-db-schema.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 04-c  config reload + 3 emit lanes
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Config hot-reload  +  the three emit lanes", 22, GRAY)
node("yaml", 60, 120, 260, 90, "4 YAMLs\nbasic / db / kb / model_config", GRAY)
node("cache",380, 120, 260, 90, "settings_property\n_cached_settings (mtime key)\nre-__init__ on file change", PROC)
node("cfg",  700, 120, 240, 90, "Configs singleton\nread everywhere\n(hot reload)", PROC)
node("prog", 60, 300, 300, 70, "utils/progress.emit\n##OCTO## <kind>|k=v  (lane 1: live)", DECIDE)
node("ev",   400, 300, 300, 70, "utils/events.EventLog\ndata/runs/<id>/events.jsonl (lane 2: truth)", DECIDE)
node("ctl",  740, 300, 300, 70, "utils/control.ControlServer\nloopback socket (lane 3: HITL)", DECIDE)
arrow("yaml", "r", "cache", "l", PROC)
arrow("cache", "r", "cfg", "l", PROC)
write("04-config-lanes.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 05-a  three-lane process boundary
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "The three-lane process boundary (Python agent <-> octopus CLI)", 22, GRAY)
node("py", 60, 220, 240, 110, "Python agent\npentest.py / BeliefAgent\n(spawned by the CLI)", AI)
node("cli",900, 220, 240, 110, "octopus CLI (Ink)\nRunView / LogView /\nApprovalPrompt", UI)
node("l1", 420, 90, 340, 62, "1. ##OCTO## stdout markers  (live ticker)", DECIDE)
node("l2", 420, 240, 340, 62, "2. events.jsonl on disk  (source of truth)", DECIDE)
node("l3", 420, 390, 340, 62, "3. loopback control socket  (HITL)", DECIDE)
arrow("py", "r", "l1", "l", DECIDE, label="emit")
arrow("l1", "r", "cli", "l", DECIDE, label="parseRunLine")
arrow("py", "r", "l2", "l", DECIDE, label="append")
arrow("l2", "r", "cli", "l", DECIDE, label="tailEvents")
arrow("cli", "b", "l3", "r", UI, dashed=True, label="cmd")
arrow("l3", "l", "py", "r", DECIDE, dashed=True, label="approval")
write("05-three-lanes.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 05-b  CLI component tree
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "octopus CLI — component tree (App -> Repl -> overlays)", 22, GRAY)
node("app", 60, 200, 200, 64, "App\nsetup vs repl", UI)
node("setup",340, 60, 200, 60, "Setup wizard", PROC)
node("repl",340, 220, 200, 64, "Repl\n(main REPL)", UI)
node("static",620, 60, 220, 60, "<Static> transcript\nPipelineLine/LogLine", GRAY)
node("input",620, 140, 220, 60, "input + SlashMenu\n+ StatusBar", GRAY)
node("runv",620, 220, 220, 60, "RunView (live)", DECIDE)
node("ov",  620, 300, 220, 78, "overlays: FilterSelect,\nApprovalPrompt, LogView,\nBeliefPanel", DECIDE)
arrow("app", "r", "setup", "l", PROC)
arrow("app", "r", "repl", "l", UI)
arrow("repl", "r", "static", "l", GRAY)
arrow("repl", "r", "input", "l", GRAY)
arrow("repl", "r", "runv", "l", DECIDE)
arrow("repl", "r", "ov", "l", DECIDE)
write("05-repl.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 05-c  Setup wizard step machine
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Setup wizard — step machine (state graph)", 22, GRAY)
node("ex",  40, 120, 180, 60, "executor\n(docker/remote/local)", UI)
node("kali",250, 120, 180, 60, "kali host/port\nuser/pass", UI)
node("prov",460, 120, 180, 60, "provider", PROC)
node("base",670, 120, 180, 60, "base_url", PROC)
node("auth",880, 120, 180, 60, "auth / api_key", PROC)
node("fetch",460, 250, 180, 60, "model_fetch", AI)
node("pick",670, 250, 180, 60, "model_pick", AI)
node("think",880, 250, 180, 60, "thinking level\n(Anthropic)", AI)
node("mysql",670, 370, 180, 60, "mysql mode\n-> done", DB)
arrow("ex", "r", "kali", "l", UI)
arrow("kali", "r", "prov", "l", UI)
arrow("prov", "r", "base", "l", PROC)
arrow("base", "r", "auth", "l", PROC)
arrow("auth", "b", "fetch", "t", AI, dashed=True)
arrow("fetch", "r", "pick", "l", AI)
arrow("pick", "r", "think", "l", AI)
arrow("think", "b", "mysql", "t", DB, dashed=True)
node("note", 40, 250, 380, 90, "finalize() writes model_config.yaml;\ncommit() writes kali + db config + prefs.\nstartAt='provider' + llmOnly re-runs\njust the LLM config (/provider, /setup llm).", GRAY)
write("05-setup.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 06-a  compose services + networks
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Docker lab — services + network isolation", 22, GRAY)
node("labnet", 40, 90, 900, 60, "labnet  (internal: true — NO internet route)", ZONE)
node("kali", 80, 190, 220, 76, "kali-tools\nsshd :22 + msfrpcd :55553\n(labnet + egress)", DANGER)
node("target",340, 190, 220, 76, "target\nmetasploitable2\n(labnet only)", DANGER)
node("agent",600, 190, 220, 76, "agent-local / agent-api\nbelief agent (/app)", AI)
node("mysql",80, 300, 220, 70, "mysql :3306\n(profile data)", DB)
node("ollama",340, 300, 220, 70, "ollama\nlocal LLM", AI)
node("egress",980, 90, 300, 60, "egress  (outbound bridge)", ZONE)
node("host", 980, 200, 300, 90, "host publishes:\n127.0.0.1:2222 -> kali SSH\n127.0.0.1:3306 -> mysql", UI)
arrow("kali", "r", "egress", "l", DECIDE, dashed=True, label="egress")
arrow("agent", "r", "egress", "l", DECIDE, dashed=True, label="api only")
arrow("kali", "r", "host", "l", UI, dashed=True)
node("note", 600, 300, 340, 84, "target + ollama NEVER touch egress.\nkali joins egress only so Docker can\npublish a host port (internal nets\ncannot be published).", GRAY)
write("06-compose.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 06-b  agent -> kali channels
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Agent -> Kali channels (SSH + msfrpc)", 22, GRAY)
node("agent", 60, 180, 240, 80, "agent\n(host pipeline or\ncontainer)", AI)
node("ssh", 420, 90, 260, 76, "SSH (paramiko, key-only)\narbitrary tools: nmap,\nenum, shell", EXEC)
node("msf", 420, 230, 260, 76, "msfrpc (pymetasploit3)\nkali-tools:55553\nMetasploit modules", EXEC)
node("kali",760, 180, 240, 80, "kali-tools (Docker)\nsshd + msfrpcd", DANGER)
node("target",1060, 180, 240, 80, "target\nvulnerable host", DANGER)
arrow("agent", "r", "ssh", "l", EXEC, label="raw stdout = O")
arrow("agent", "r", "msf", "l", EXEC, label="structured")
arrow("ssh", "r", "kali", "l", EXEC)
arrow("msf", "r", "kali", "l", EXEC)
arrow("kali", "r", "target", "l", DANGER, label="tools")
write("06-channels.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 07-a  RAG retrieval pipeline
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "RAG retrieval pipeline (Memory-Retriever)", 22, GRAY)
node("q",   60, 150, 200, 64, "query\n(+ kb_name)", PROC)
node("search",300, 150, 240, 76, "search_docs\nMilvus top_k\n(score threshold)", AI)
node("rerank",600, 150, 240, 76, "LangchainReranker\nCrossEncoder top_n", AI)
node("scrub",900, 150, 240, 76, "replace_ip_with_targetip\nIP -> <target>", DECIDE)
node("chat",600, 300, 240, 70, "inject context into\n_chat -> LLM", AI)
arrow("q", "r", "search", "l", PROC)
arrow("search", "r", "rerank", "l", AI)
arrow("rerank", "r", "scrub", "l", AI)
arrow("scrub", "b", "chat", "t", DECIDE, dashed=True)
node("note", 60, 260, 480, 110,
     "Active only when enable_rag AND a kb_name is passed to _chat; else rag/ (and\nits heavy langchain imports) is never touched. The /kb/* FastAPI routes\n(rag/kb/api) build the knowledge bases. Because _chat is the single choke\npoint, RAG augmentation is transparent to every caller.", GRAY)
write("07-rag.excalidraw")

# ══════════════════════════════════════════════════════════════════════════════
# 07-b  baselines (PentestGPT PTT + BaseGPT)
# ══════════════════════════════════════════════════════════════════════════════
reset()
title(40, 20, "Baselines (experiment/) — comparison only, NOT the pipeline", 22, GRAY)
node("cli", 60, 160, 220, 76, "cli.py\npentestgpt / base", UI)
node("pgpt",360, 80, 260, 90, "PentestGPT\nreasoning/generation/parsing\nsessions + a PTT tree", PROC)
node("base",360, 230, 260, 76, "BaseGPT\nsingle-agent loop", PROC)
node("ptt", 700, 60, 260, 76, "PTT tree\n(pentest task tree,\nnode statuses)", DECIDE)
node("llm", 700, 200, 260, 76, "llm_ollama\nin-memory conversation_dict\n(no MySQL) + _chat", AI)
arrow("cli", "r", "pgpt", "l", PROC)
arrow("cli", "r", "base", "l", PROC)
arrow("pgpt", "r", "ptt", "l", DECIDE)
arrow("pgpt", "b", "llm", "l", AI, dashed=True)
arrow("base", "r", "llm", "l", AI, dashed=True)
node("note", 60, 300, 560, 84,
     "Neither is invoked by pentest.py. Both reuse actions/ (ShellManager, WriteCode) for\nexecution and _chat for the LLM, but do NOT join the multi-agent Octopus planning\npipeline — they exist purely to benchmark against Octopus.", GRAY)
write("07-baselines.excalidraw")
