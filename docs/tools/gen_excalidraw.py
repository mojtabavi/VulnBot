import json

# deterministic pseudo-ids/seeds (no randomness -> reproducible)
_c = [0]
def nid():
    _c[0] += 1
    return f"el{_c[0]:03d}"
def seed():
    _c[0] += 1
    return 1000 + _c[0] * 7

GRAY_STROKE = "#343a40"
GRAY_BG = "#e9ecef"
FUT_STROKE = "#d9480f"   # distinct "future" color (burnt orange)
FUT_BG = "#ffe8cc"
IMPL_STROKE = "#1971c2"  # "implemented/scaffolded this phase" (blue)
IMPL_BG = "#a5d8ff"

elements = []
nodes = {}

def node(key, x, y, w, h, label, future=False, scaffold=False, bg=None):
    box_id = nid()
    txt_id = nid()
    if future:
        stroke, default_bg = FUT_STROKE, FUT_BG
    elif scaffold:
        stroke, default_bg = IMPL_STROKE, IMPL_BG
    else:
        stroke, default_bg = GRAY_STROKE, GRAY_BG
    background = bg if bg else default_bg
    box = {
        "id": box_id, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": background,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 3}, "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": [{"type": "text", "id": txt_id}],
        "updated": 1, "link": None, "locked": False,
    }
    lines = label.count("\n") + 1
    fs = 16
    txt = {
        "id": txt_id, "type": "text", "x": x + 8, "y": y + h/2 - (lines*fs*1.25)/2,
        "width": w - 16, "height": lines*fs*1.25, "angle": 0,
        "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": None, "seed": seed(),
        "version": 1, "versionNonce": seed(), "isDeleted": False, "boundElements": [],
        "updated": 1, "link": None, "locked": False, "text": label, "fontSize": fs,
        "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle",
        "containerId": box_id, "originalText": label, "lineHeight": 1.25, "baseline": fs,
    }
    elements.append(box); elements.append(txt)
    nodes[key] = {"id": box_id, "x": x, "y": y, "w": w, "h": h}
    return box_id

def edge_point(n, side):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    return {
        "t": (x + w/2, y), "b": (x + w/2, y + h),
        "l": (x, y + h/2), "r": (x + w, y + h/2),
    }[side]

def arrow(a, sa, b, sb, dashed=False, label=None, color=None):
    n1, n2 = nodes[a], nodes[b]
    p1 = edge_point(n1, sa); p2 = edge_point(n2, sb)
    aid = nid()
    stroke = color if color else GRAY_STROKE
    arr = {
        "id": aid, "type": "arrow", "x": p1[0], "y": p1[1],
        "width": abs(p2[0]-p1[0]), "height": abs(p2[1]-p1[1]), "angle": 0,
        "strokeColor": stroke, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 2}, "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None, "locked": False,
        "points": [[0, 0], [p2[0]-p1[0], p2[1]-p1[1]]], "lastCommittedPoint": None,
        "startBinding": {"elementId": n1["id"], "focus": 0, "gap": 4},
        "endBinding": {"elementId": n2["id"], "focus": 0, "gap": 4},
        "startArrowhead": None, "endArrowhead": "arrow",
    }
    # register binding
    for nn in (n1["id"], n2["id"]):
        for el in elements:
            if el["id"] == nn:
                el["boundElements"].append({"type": "arrow", "id": aid})
    elements.append(arr)
    if label:
        tid = nid()
        mx = (p1[0]+p2[0])/2; my = (p1[1]+p2[1])/2
        elements.append({
            "id": tid, "type": "text", "x": mx-40, "y": my-10, "width": 80, "height": 18,
            "angle": 0, "strokeColor": stroke, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid", "roughness": 1,
            "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
            "seed": seed(), "version": 1, "versionNonce": seed(), "isDeleted": False,
            "boundElements": [], "updated": 1, "link": None, "locked": False,
            "text": label, "fontSize": 12, "fontFamily": 1, "textAlign": "center",
            "verticalAlign": "middle", "containerId": None, "originalText": label,
            "lineHeight": 1.25, "baseline": 12,
        })

def title(x, y, text, size, color):
    elements.append({
        "id": nid(), "type": "text", "x": x, "y": y, "width": 600, "height": size*1.3,
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": None, "seed": seed(),
        "version": 1, "versionNonce": seed(), "isDeleted": False, "boundElements": [],
        "updated": 1, "link": None, "locked": False, "text": text, "fontSize": size,
        "fontFamily": 1, "textAlign": "left", "verticalAlign": "top", "containerId": None,
        "originalText": text, "lineHeight": 1.25, "baseline": size,
    })

W, H = 232, 88
# ---- titles ----
title(60, 20, "VulnBot — Architecture & Data Flow", 28, GRAY_STROKE)
title(60, 56, "Gray = current VulnBot modules   |   Blue = implemented this fork (Docker lab / belief updater, Phase 0-2.2)", 14, IMPL_STROKE)
title(60, 76, "Orange = FUTURE belief modules (attachment points; not yet implemented)", 14, FUT_STROKE)

# ---- current nodes ----
node("user",     60,  120, W, H, "User / Session\n(init_description,\ntarget IP)")
node("summ",     60,  300, W, H, "Summarizer\nPlannerSummary\n(plan_summary.py)")
node("roles",   340,  300, W, H, "Role Agents\nCollector>Scanner>Exploiter\n(roles/)")
node("planner", 620,  300, W, H, "Planner + WritePlan\nPTG / task graph\n(actions/planner.py)")
node("gen",     900,  300, W, H, "Generator\nWriteCode\n(write_code.py)")
node("exec",   1180,  300, W, H, "Executor\nExecuteTask\n(execute_task.py)")
node("kali",   1180,  470, W, H, "kali-tools (Docker)\nSSH + msfrpc:55553\nnmap / metasploit", scaffold=True)
node("target", 1180,  640, W, H, "target (Docker)\nvulnerable host\nlabnet (isolated)", scaffold=True)

node("llm",     560,  560, 260, H, "LLM Layer  _chat\nOpenAI / Ollama\n(server/chat/chat.py)")
node("mem",     900,  560, W, H, "Memory-Retriever\nRAG / Milvus + rerank\n(rag/)")
node("db",      220,  560, W, H, "MySQL\nsessions/plans/tasks\nconversations/messages")

# ---- belief nodes ----
# Scaffolded now (Phase 2.1): belief data + Store persistence.
node("bstate", 340, 470, W, H, "belief_state.py [2.1]\nb0 priors, Action, GAMMA\nupdate/score/choose = stub", scaffold=True)
node("bs",  620, 470, W, H, "Belief Store [2.1]\nbelief_store.py\ndata/beliefs/*.json", scaffold=True)
# Belief Updater implemented in 2.2 (Z likelihoods + Bayes):
node("bu",  60,  470, W, H, "Belief Updater [2.2]\nupdate_belief: LLM Z\n+ soft Bayes", scaffold=True)
# Future (attachment point only):
node("bcp", 620, 120, W, H, "Belief-Conditioned Planner\ninfo-gain vs exploit-value\n[future 2.4]", future=True)

# ---- main data flow (solid gray) ----
arrow("user", "b", "roles", "t", label="session")
arrow("summ", "r", "roles", "l", label="context")
arrow("roles", "r", "planner", "l")
arrow("planner", "r", "gen", "l", label="next task")
arrow("gen", "r", "exec", "l", label="shell cmds")
arrow("exec", "b", "kali", "t", label="SSH/msfrpc")
arrow("kali", "l", "exec", "b")  # output back (approx)
arrow("kali", "b", "target", "t", label="tools")
arrow("exec", "t", "planner", "t")
arrow("planner", "b", "roles", "b")  # react loop / next task

# ---- LLM + persistence (dashed gray) ----
arrow("roles", "b", "llm", "t", dashed=True)
arrow("planner", "b", "llm", "t", dashed=True)
arrow("gen", "b", "llm", "l", dashed=True)
arrow("summ", "b", "llm", "l", dashed=True)
arrow("llm", "r", "mem", "l", dashed=True, label="RAG (if on)")
arrow("llm", "l", "db", "r", dashed=True, label="history")
arrow("roles", "b", "db", "t", dashed=True, label="persist")

# ---- belief scaffold (Phase 2.1, blue) ----
arrow("bstate", "r", "bs", "l", dashed=True, color=IMPL_STROKE, label="belief b")
arrow("roles", "b", "bs", "t", dashed=True, color=IMPL_STROKE, label="persist b/step")

# ---- future attachment points (dashed orange) ----
arrow("bu", "t", "summ", "b", dashed=True, color=IMPL_STROKE, label="updates")
arrow("bcp", "b", "planner", "t", dashed=True, color=FUT_STROKE, label="attaches")

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "vulnbot-architecture-phase1",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {},
}

import os
out = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..")
# write directly to project via absolute path passed as arg
import sys
target = sys.argv[1]
with open(target, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print("wrote", target, "elements:", len(elements))
