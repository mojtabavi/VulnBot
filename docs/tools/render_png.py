import json, math, sys
from PIL import Image, ImageDraw, ImageFont

SRC = sys.argv[1]
OUT = sys.argv[2]
S = 2.0            # supersample scale for crispness
PAD = 40

d = json.load(open(SRC, encoding="utf-8"))
els = [e for e in d["elements"] if not e.get("isDeleted")]

# bounds
xs, ys = [], []
for e in els:
    xs += [e["x"], e["x"] + e.get("width", 0)]
    ys += [e["y"], e["y"] + e.get("height", 0)]
minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
W = int((maxx - minx) * S + PAD * 2)
H = int((maxy - miny) * S + PAD * 2)

img = Image.new("RGB", (W, H), "#ffffff")
dr = ImageDraw.Draw(img)

def tx(x): return (x - minx) * S + PAD
def ty(y): return (y - miny) * S + PAD

def font(size, bold=False):
    p = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
    return ImageFont.truetype(p, int(size * S))

def rounded_rect(x, y, w, h, r, fill, outline, width):
    dr.rounded_rectangle([tx(x), ty(y), tx(x + w), ty(y + h)],
                         radius=r * S, fill=fill, outline=outline, width=int(width * S))

def dline(p1, p2, fill, width, dash):
    x1, y1 = p1; x2, y2 = p2
    if not dash:
        dr.line([x1, y1, x2, y2], fill=fill, width=int(width * S)); return
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0: return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    on, off = 10 * S, 7 * S
    p = 0
    while p < dist:
        a = p; b = min(p + on, dist)
        dr.line([x1 + dx * a, y1 + dy * a, x1 + dx * b, y1 + dy * b], fill=fill, width=int(width * S))
        p += on + off

def arrowhead(p_from, p_to, color):
    x1, y1 = p_from; x2, y2 = p_to
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 13 * S; spread = math.radians(26)
    for s in (+1, -1):
        ax = x2 - L * math.cos(ang + s * spread)
        ay = y2 - L * math.sin(ang + s * spread)
        dr.line([x2, y2, ax, ay], fill=color, width=int(2 * S))

# draw rectangles first
for e in els:
    if e["type"] == "rectangle":
        r = 12
        rounded_rect(e["x"], e["y"], e["width"], e["height"], r,
                     e.get("backgroundColor", "#ffffff"), e["strokeColor"], e.get("strokeWidth", 2))

# arrows
for e in els:
    if e["type"] == "arrow":
        pts = e["points"]
        ox, oy = tx(e["x"]), ty(e["y"])
        abspts = [(ox + px * S, oy + py * S) for px, py in pts]
        dash = e.get("strokeStyle") == "dashed"
        for i in range(len(abspts) - 1):
            dline(abspts[i], abspts[i + 1], e["strokeColor"], e.get("strokeWidth", 2), dash)
        if e.get("endArrowhead"):
            arrowhead(abspts[-2], abspts[-1], e["strokeColor"])

# text last
for e in els:
    if e["type"] == "text":
        lines = e["text"].split("\n")
        fs = e.get("fontSize", 16)
        bold = e.get("containerId") is not None  # box labels bold-ish? keep regular
        f = font(fs, bold=False)
        # bold for big titles
        if fs >= 24:
            f = font(fs, bold=True)
        lh = fs * 1.25 * S
        cid = e.get("containerId")
        align = e.get("textAlign", "left")
        total_h = len(lines) * lh
        if cid:
            # center within container box
            box = next((b for b in els if b["id"] == cid), None)
            cx = tx(box["x"] + box["width"] / 2)
            cy = ty(box["y"] + box["height"] / 2) - total_h / 2
            for i, ln in enumerate(lines):
                w = dr.textlength(ln, font=f)
                dr.text((cx - w / 2, cy + i * lh), ln, fill=e["strokeColor"], font=f)
        else:
            x0 = tx(e["x"]); y0 = ty(e["y"])
            for i, ln in enumerate(lines):
                if align == "center":
                    w = dr.textlength(ln, font=f)
                    dr.text((x0 - w / 2, y0 + i * lh), ln, fill=e["strokeColor"], font=f)
                else:
                    dr.text((x0, y0 + i * lh), ln, fill=e["strokeColor"], font=f)

# downscale for anti-alias
final = img.resize((int(W / S * 1.35), int(H / S * 1.35)), Image.LANCZOS)
final.save(OUT)
print("wrote", OUT, final.size)
