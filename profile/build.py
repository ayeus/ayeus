"""Render every static SVG in assets/ from profile.toml.

    python profile/build.py            # all static assets
    python profile/build.py hero cards # only some

Telemetry (stats.py) and the arcade (arcade.py) render their own assets.
"""
from __future__ import annotations

import math
import random
import sys
import tomllib
from pathlib import Path

from svgkit import (ASSETS, DARK, HERE, LIGHT, THEMES, Svg, Theme, chip, chips_row, dot_grid, esc, f2,
                    icon_arrow_ne, icon_check, icon_cloud, icon_star, panel, short_hash, skill_icon,
                    text_width, write)

CFG = tomllib.loads((HERE / "profile.toml").read_text())
MONO_W = 0.6  # JetBrains Mono advance width (em)


# ============================================================================ shared bits
def glow_filter(svg: Svg, color: str, std: float = 3.0, strength: float | None = None) -> str:
    """Soft glow filter id (stronger on dark theme)."""
    fid = svg.uid("glow")
    k = svg.t.glow if strength is None else strength
    svg.defs.append(
        f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
        f'<feGaussianBlur stdDeviation="{std}" result="b"/>'
        f'<feComponentTransfer in="b" result="b2"><feFuncA type="linear" slope="{f2(1.2 * k)}"/></feComponentTransfer>'
        f'<feMerge><feMergeNode in="b2"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    return fid


def radial_glow(svg: Svg, cx, cy, r, color, opacity) -> str:
    gid = svg.uid("rg")
    svg.defs.append(
        f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="{f2(opacity)}"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
    )
    return f'<ellipse cx="{f2(cx)}" cy="{f2(cy)}" rx="{f2(r)}" ry="{f2(r*0.72)}" fill="url(#{gid})"/>'


def clip_round(svg: Svg, w, h, r=16) -> str:
    cid = svg.uid("cr")
    svg.defs.append(f'<clipPath id="{cid}"><rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{r}"/></clipPath>')
    return cid


def discrete_anim(attr: str, times: list[float], values: list[float], dur: float,
                  repeat: bool = True, begin: str = "0s") -> str:
    """SMIL <animate> with calcMode=discrete from absolute times (seconds)."""
    kt = ";".join(f"{max(0.0, min(1.0, t / dur)):.4f}" for t in times)
    vs = ";".join(f2(v) for v in values)
    rep = 'repeatCount="indefinite"' if repeat else 'fill="freeze"'
    return (f'<animate attributeName="{attr}" calcMode="discrete" dur="{f2(dur)}s" begin="{begin}" '
            f'keyTimes="{kt}" values="{vs}" {rep}/>')


def monotonic(times: list[float], values: list[float]) -> tuple[list[float], list[float]]:
    """Make keyTimes strictly increasing (SMIL requirement) by nudging ties."""
    out_t, out_v, last = [], [], -1.0
    for t, v in zip(times, values):
        if t <= last:
            t = last + 0.0005
        out_t.append(t)
        out_v.append(v)
        last = t
    return out_t, out_v


# ============================================================================ hero
def hero(t: Theme) -> str:
    W, H = 1000, 300
    me = CFG["me"]
    svg = Svg(W, H, t, "Aayush Namdeo — software engineer building infrastructure for AI",
              " / ".join(me["taglines"]))
    cid = clip_round(svg, W, H, 18)

    # ---- background
    svg.add(panel(svg, r=18))
    svg.add(f'<g clip-path="url(#{cid})">')
    svg.add(radial_glow(svg, 120, 300, 380, t.ember, 0.16 if t.dark else 0.10))
    svg.add(radial_glow(svg, 880, 20, 420, t.ice, 0.14 if t.dark else 0.09))
    svg.add(dot_grid(svg, step=22, r=1.1, clip_r=18))

    # ---- GPU mesh (right side), fades out towards the name
    rnd = random.Random(7)
    cols, rows = 7, 5
    x0, x1, y0, y1 = 470, 978, 34, 270
    nodes = []
    for c in range(cols):
        for r in range(rows):
            if rnd.random() < 0.12 and 0 < c < cols - 1:
                continue
            x = x0 + (x1 - x0) * (c + 0.5) / cols + rnd.uniform(-22, 22)
            y = y0 + (y1 - y0) * (r + 0.5) / rows + rnd.uniform(-14, 14)
            nodes.append((c, r, x, y))
    idx = {(c, r): i for i, (c, r, _, _) in enumerate(nodes)}
    edges = set()
    for i, (c, r, x, y) in enumerate(nodes):
        for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
            j = idx.get((c + dc, r + dr))
            if j is not None and (dc == 0 or dr == 0 or rnd.random() < 0.45):
                edges.add((i, j))
    mid = svg.uid("fade")
    svg.defs.append(
        f'<linearGradient id="{mid}g" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="0.16" stop-color="#fff" stop-opacity="0.15"/>'
        f'<stop offset="0.42" stop-color="#fff" stop-opacity="1"/></linearGradient>'
        f'<mask id="{mid}"><rect x="{x0-40}" y="0" width="{W-x0+40}" height="{H}" fill="url(#{mid}g)"/></mask>'
    )
    g = [f'<g mask="url(#{mid})">']
    for i, j in edges:
        _, _, ax, ay = nodes[i]
        _, _, bx, by = nodes[j]
        g.append(f'<line x1="{f2(ax)}" y1="{f2(ay)}" x2="{f2(bx)}" y2="{f2(by)}" stroke="{t.line}" stroke-width="1.1"/>')

    # routes: walk from the rightmost column to the leftmost along edges
    adj: dict[int, list[int]] = {}
    for i, j in edges:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    glow = glow_filter(svg, t.ice, 2.2)
    routes = []
    starts = [i for i, n in enumerate(nodes) if n[0] == cols - 1]
    for k in range(9):
        cur = starts[k % len(starts)]
        path = [cur]
        for _ in range(12):
            nxt = [j for j in adj.get(cur, []) if nodes[j][0] <= nodes[cur][0] and j not in path]
            if not nxt:
                break
            nxt.sort(key=lambda j: (nodes[j][0], rnd.random()))
            cur = nxt[0] if rnd.random() < 0.75 else rnd.choice(nxt)
            path.append(cur)
            if nodes[cur][0] == 0:
                break
        if len(path) > 2:
            routes.append(path)
    for k, path in enumerate(routes):
        d = "M" + " L".join(f"{f2(nodes[i][2])} {f2(nodes[i][3])}" for i in path)
        color = t.ice if k % 3 else t.ember
        dur = 3.2 + (k % 4) * 0.6
        begin = f"{f2(k * 0.73)}s"
        if k % 3 == 0:  # a few routes show their traffic as a moving dashed trail
            g.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" stroke-opacity="0.5" '
                     f'stroke-dasharray="6 10" class="flow" style="animation-duration:{f2(dur/2)}s"/>')
        g.append(f'<circle r="3" fill="{color}" filter="url(#{glow})">'
                 f'<animateMotion dur="{f2(dur)}s" begin="{begin}" repeatCount="indefinite" path="{d}"/></circle>')
    for n, (c, r, x, y) in enumerate(nodes):
        big = (c * 3 + r * 5) % 7 == 0
        s = 13 if big else 8
        fill = t.bg1 if big else t.bg2
        stroke = t.ember if big else t.fg2
        g.append(f'<rect x="{f2(x - s/2)}" y="{f2(y - s/2)}" width="{s}" height="{s}" rx="2.5" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{1.4 if big else 1}"/>')
        if big:
            g.append(f'<rect x="{f2(x - 2.5)}" y="{f2(y - 2.5)}" width="5" height="5" rx="1" fill="{t.ember}" class="blink" '
                     f'style="animation-delay:{f2((n % 5) * 0.4)}s"/>')
            g.append(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="9" fill="none" stroke="{t.ember}" stroke-width="1" '
                     f'class="ping" style="animation-delay:{f2((n % 6) * 0.55)}s"/>')
    g.append("</g>")
    svg.add(*g)
    svg.add("</g>")

    # ---- mesh caption
    cap = "ayeusann · gpu mesh"
    cx = W - 30 - text_width(cap, "AyMono", 500, 11)
    svg.add(f'<circle cx="{f2(cx - 11)}" cy="{H - 27}" r="3" fill="{t.ember}" class="blink"/>')
    svg.add(svg.text(cx, H - 23, cap, size=11, weight=500, fill=t.fg2, spacing=0.3))

    # ---- status pill
    status = me["status"]
    sw = text_width(status, "AyMono", 500, 12.5) + 46
    svg.add(f'<rect x="40" y="30" width="{f2(sw)}" height="28" rx="14" fill="{t.bg1}" stroke="{t.line}"/>')
    svg.add(f'<circle cx="57" cy="44" r="4" fill="{t.lime}"/>')
    svg.add(f'<circle cx="57" cy="44" r="4" fill="none" stroke="{t.lime}" class="ping-sm"/>')
    svg.add(svg.text(69, 48.5, status, size=12.5, weight=500, fill=t.fg1))

    # ---- name
    size = 60
    svg.add(svg.text(38, 132, me["name_top"], family="AyDisplay", weight=800, size=size, spacing=1, fill=t.fg0))
    svg.add(svg.text(38, 200, me["name_bottom"], family="AyDisplay", weight=800, size=size, spacing=1, fill=t.fg0))
    nb = text_width(me["name_bottom"], "AyDisplay", 800, size, 1)
    svg.add(f'<rect x="{f2(38 + nb + 10)}" y="191" width="30" height="9" rx="1.5" fill="{t.ember}" class="blink-hard"/>')

    # ---- typewriter taglines
    fs = 16.5
    cw = MONO_W * fs
    tx, ty = 62, 246
    svg.add(svg.text(40, ty, "›", size=fs + 2, weight=700, fill=t.ember))
    slot, char_t, back_t = 5.6, 0.042, 0.018
    lines = me["taglines"]
    dur = slot * len(lines)
    cursor_times, cursor_vals = [0.0], [tx]
    for i, line in enumerate(lines):
        n = len(line)
        start = i * slot
        type_end = start + n * char_t
        erase_start = start + slot - 0.35 - n * back_t
        times = [0.0]
        vals = [0.0]
        for k in range(n + 1):
            times.append(start + k * char_t)
            vals.append(k * cw)
        for k in range(1, n + 1):
            times.append(erase_start + k * back_t)
            vals.append((n - k) * cw)
        times, vals = monotonic(times, vals)
        cursor_times += times[1:]
        cursor_vals += [tx + v for v in vals[1:]]
        clip = svg.uid("tw")
        initial = n * cw if i == 0 else 0
        svg.defs.append(
            f'<clipPath id="{clip}"><rect x="{tx}" y="{ty - fs}" width="{f2(initial)}" height="{fs * 1.5}">'
            f"{discrete_anim('width', times, vals, dur)}</rect></clipPath>"
        )
        svg.add(f'<g clip-path="url(#{clip})">' + svg.text(tx, ty, line, size=fs, weight=500, fill=t.fg0) + "</g>")
        _ = type_end
    ct, cv = monotonic(cursor_times, cursor_vals)
    svg.add(f'<rect x="{f2(tx + len(lines[0]) * cw + 2)}" y="{ty - fs * 0.82}" width="{f2(cw * 0.9)}" height="{f2(fs * 1.02)}" '
            f'fill="{t.ice}" opacity="0.85" class="blink">'
            f"{discrete_anim('x', ct, [v + 2 for v in cv], dur)}</rect>")

    # ---- footer line
    svg.add(svg.text(40, 280, me["footer"], size=12, weight=400, fill=t.fg2, spacing=0.2))

    svg.css.append(
        ".blink{animation:blink 1.1s steps(1,end) infinite}"
        ".blink-hard{animation:blink 1s steps(1,end) infinite}"
        "@keyframes blink{50%{opacity:0}}"
        ".ping,.ping-sm{transform-box:fill-box;transform-origin:center;animation:ping 2.6s ease-out infinite}"
        ".ping-sm{animation-duration:2s}"
        "@keyframes ping{0%{transform:scale(.6);opacity:.9}70%,100%{transform:scale(2.4);opacity:0}}"
        ".flow{animation:flow 1.6s linear infinite}"
        "@keyframes flow{to{stroke-dashoffset:-32}}"
    )
    return svg.render()


# ============================================================================ cards
ANIM_CSS = (
    ".blink{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{50%{opacity:0}}"
    ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out infinite}"
    "@keyframes ping{0%{transform:scale(.6);opacity:.9}70%,100%{transform:scale(2.6);opacity:0}}"
    ".flow{animation:flow 1.4s linear infinite}@keyframes flow{to{stroke-dashoffset:-32}}"
    ".spin{transform-box:fill-box;transform-origin:center;animation:spin 14s linear infinite}"
    "@keyframes spin{to{transform:rotate(360deg)}}"
    ".util{transform-box:fill-box;transform-origin:left center;animation:util 3.2s ease-in-out infinite alternate}"
    "@keyframes util{0%{transform:scaleX(.2)}100%{transform:scaleX(1)}}"
    ".wave{transform-box:fill-box;transform-origin:center;animation:wave 1.1s ease-in-out infinite alternate}"
    "@keyframes wave{0%{transform:scaleY(.25)}100%{transform:scaleY(1)}}"
    ".sweep{transform-box:view-box;animation:sweep 4s linear infinite}"
    "@keyframes sweep{to{transform:rotate(360deg)}}"
)


def card_header(svg: Svg, p: dict, x0: float, x1: float, y: float = 20) -> None:
    t = svg.t
    svg.add(svg.text(x0, y + 17, p["kicker"], size=11.5, weight=700, fill=t.fg2, spacing=1.4))
    status = p["status"]
    w = text_width(status, "AyMono", 500, 11.5) + 34
    s, _ = chip(svg, x1 - w, y, status, size=11.5, dot=t.lime, h=25)
    svg.add(s)


def card_footer(svg: Svg, p: dict, x0: float, y_title: float, title_size=24) -> None:
    t = svg.t
    svg.add(svg.text(x0, y_title, p["title"], family="AyDisplay", weight=700, size=title_size, fill=t.fg0))
    for i, line in enumerate(p["desc"]):
        svg.add(svg.text(x0, y_title + 28 + i * 21, line, family="AySans", weight=500, size=15, fill=t.fg1))
    s, _ = chips_row(svg, x0, y_title + 28 + len(p["desc"]) * 21 + 6, p["chips"], size=11.5, h=24, gap=7)
    svg.add(s)
    svg.add(icon_arrow_ne(svg.w - 40, svg.h - 42, 13, t.fg2, 2))


def card_ayeusann(t: Theme) -> str:
    p = CFG["projects"]["ayeusann"]
    W, H = 1000, 350
    svg = Svg(W, H, t, "AyeusANN — data-center-as-a-service for AI compute", " ".join(p["desc"]))
    svg.css.append(ANIM_CSS)
    svg.add(panel(svg))
    svg.add(radial_glow(svg, 60, 330, 300, t.ember, 0.12 if t.dark else 0.07))
    # left: text
    svg.add(svg.text(32, 44, p["kicker"], size=11.5, weight=700, fill=t.fg2, spacing=1.4))
    svg.add(svg.text(30, 100, p["title"], family="AyDisplay", weight=800, size=38, fill=t.fg0))
    svg.add(svg.text(32, 128, p["subtitle"], size=13.5, weight=500, fill=t.ember))
    for i, line in enumerate(p["desc"]):
        svg.add(svg.text(32, 164 + i * 22, line, family="AySans", weight=500, size=15.5, fill=t.fg1))
    fx = 32
    for big, label in p["facts"]:
        bw = max(text_width(big, "AyDisplay", 700, 20), text_width(label, "AyMono", 500, 11)) + 26
        svg.add(f'<rect x="{fx}" y="238" width="{f2(bw)}" height="54" rx="10" fill="{t.bg1}" stroke="{t.line}"/>')
        svg.add(svg.text(fx + 13, 265, big, family="AyDisplay", weight=700, size=20, fill=t.fg0))
        svg.add(svg.text(fx + 13, 283, label, size=11, weight=500, fill=t.fg2))
        fx += bw + 10
    s, _ = chips_row(svg, 32, 306, p["chips"], size=11.5, h=24, gap=7)
    svg.add(s)

    # right: live topology
    ix, iy, iw, ih = 452, 22, 522, 306
    svg.add(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" rx="14" fill="{t.bg1}" stroke="{t.line}"/>')
    svg.add(dot_grid(svg, step=18, r=0.9, x=ix, y=iy, w=iw, h=ih, clip_r=14))
    svg.add(f'<circle cx="{ix+20}" cy="{iy+22}" r="3.5" fill="{t.lime}"/>'
            f'<circle cx="{ix+20}" cy="{iy+22}" r="3.5" fill="none" stroke="{t.lime}" class="ping"/>')
    svg.add(svg.text(ix + 32, iy + 26, "live topology", size=11, weight=500, fill=t.fg2, spacing=0.3))

    hosts = ["data centre", "college lab", "workstation", "personal rig"]
    hub = (770, 178)
    ep = (912, 178)
    glow = glow_filter(svg, t.ice, 2)
    paths = []
    for i, name in enumerate(hosts):
        cy = 78 + i * 62
        hx, hw, hh = 472, 138, 46
        svg.add(f'<rect x="{hx}" y="{cy-hh/2}" width="{hw}" height="{hh}" rx="10" fill="{t.bg0}" stroke="{t.line}"/>')
        # chip glyph
        svg.add(f'<rect x="{hx+12}" y="{cy-10}" width="20" height="20" rx="4" fill="none" stroke="{t.ember}" stroke-width="1.5"/>'
                f'<rect x="{hx+18}" y="{cy-4}" width="8" height="8" rx="1.5" fill="{t.ember}"/>')
        svg.add(svg.text(hx + 42, cy - 2, name, size=11.5, weight=500, fill=t.fg0))
        svg.add(f'<rect x="{hx+42}" y="{cy+6}" width="80" height="4" rx="2" fill="{t.bg2}"/>')
        svg.add(f'<rect x="{hx+42}" y="{cy+6}" width="80" height="4" rx="2" fill="{t.ember}" class="util" '
                f'style="animation-delay:-{f2(i*0.9)}s;animation-duration:{f2(2.6+i*0.5)}s"/>')
        d = f"M{hx+hw} {cy} C{hx+hw+70} {cy} {hub[0]-90} {hub[1]} {hub[0]-44} {hub[1]}"
        paths.append((d, cy, hx + hw))
        svg.add(f'<path d="{d}" fill="none" stroke="{t.line}" stroke-width="1.5"/>')
        svg.add(f'<path d="{d}" fill="none" stroke="{t.ice}" stroke-width="1.5" stroke-opacity="0.7" '
                f'stroke-dasharray="4 8" class="flow"/>')
    svg.add(svg.text(648, 104, "wireguard", size=10.5, weight=500, fill=t.fg2))
    # hub
    svg.add(f'<circle cx="{hub[0]}" cy="{hub[1]}" r="58" fill="none" stroke="{t.ember}" stroke-opacity="0.5" '
            f'stroke-dasharray="3 7" class="spin"/>')
    svg.add(f'<rect x="{hub[0]-44}" y="{hub[1]-44}" width="88" height="88" rx="16" fill="{t.bg0}" stroke="{t.ember}" stroke-width="1.6"/>')
    svg.add(svg.text(hub[0], hub[1] - 6, "control", size=12, weight=700, fill=t.fg0, anchor="middle"))
    svg.add(svg.text(hub[0], hub[1] + 9, "plane", size=12, weight=700, fill=t.fg0, anchor="middle"))
    svg.add(svg.text(hub[0], hub[1] + 28, "8 go svcs", size=10, weight=500, fill=t.fg2, anchor="middle"))
    # endpoint
    svg.add(f'<line x1="{hub[0]+44}" y1="{hub[1]}" x2="{ep[0]-44}" y2="{ep[1]}" stroke="{t.line}" stroke-width="1.5"/>')
    svg.add(f'<line x1="{hub[0]+44}" y1="{hub[1]}" x2="{ep[0]-44}" y2="{ep[1]}" stroke="{t.ember}" stroke-width="1.5" '
            f'stroke-dasharray="4 8" class="flow"/>')
    svg.add(f'<rect x="{ep[0]-44}" y="{ep[1]-22}" width="92" height="44" rx="10" fill="{t.bg0}" stroke="{t.ice}" stroke-width="1.4"/>')
    svg.add(svg.text(ep[0] + 2, ep[1] - 3, "POST", size=10.5, weight=700, fill=t.ice, anchor="middle"))
    svg.add(svg.text(ep[0] + 2, ep[1] + 12, "/v1/chat", size=11, weight=500, fill=t.fg0, anchor="middle"))
    svg.add(svg.text(ep[0] + 2, ep[1] - 34, "endpoint", size=10.5, weight=500, fill=t.fg2, anchor="middle"))
    # packets: request goes endpoint -> hub -> host, tokens come back
    for i, (d, cy, hx_end) in enumerate(paths):
        back = f"M{ep[0]-44} {ep[1]} L{hub[0]+44} {hub[1]} L{hub[0]-44} {hub[1]} C{hub[0]-90} {hub[1]} {hx_end+70} {cy} {hx_end} {cy}"
        fwd = f"M{hx_end} {cy} C{hx_end+70} {cy} {hub[0]-90} {hub[1]} {hub[0]-44} {hub[1]} L{hub[0]+44} {hub[1]} L{ep[0]-44} {ep[1]}"
        svg.add(f'<circle r="3.2" fill="{t.ice}" filter="url(#{glow})"><animateMotion dur="2.4s" begin="{f2(i*1.2)}s" '
                f'repeatCount="indefinite" path="{back}"/></circle>')
        svg.add(f'<circle r="3.2" fill="{t.ember}" filter="url(#{glow})"><animateMotion dur="2.4s" begin="{f2(i*1.2+0.6)}s" '
                f'repeatCount="indefinite" path="{fwd}"/></circle>')
    svg.add(svg.text(ix + iw / 2, iy + ih - 14, "idle GPU  →  wireguard mesh  →  scheduler  →  your endpoint",
                     size=10.5, weight=500, fill=t.fg2, anchor="middle"))
    return svg.render()


def card_max(t: Theme) -> str:
    p = CFG["projects"]["max"]
    W, H = 500, 362
    svg = Svg(W, H, t, "MAX — local-first macOS computer agent", " ".join(p["desc"]))
    svg.css.append(ANIM_CSS)
    svg.add(panel(svg))
    card_header(svg, p, 24, W - 24)
    vx, vy, vw, vh = 24, 58, W - 48, 144
    svg.add(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="12" fill="{t.bg1}" stroke="{t.line}"/>')
    # waveform
    svg.add(f'<circle cx="{vx+22}" cy="{vy+24}" r="9" fill="none" stroke="{t.violet}" stroke-width="1.6"/>'
            f'<rect x="{vx+19}" y="{vy+17}" width="6" height="10" rx="3" fill="{t.violet}"/>')
    for i in range(34):
        h = 6 + (math.sin(i * 1.7) * 0.5 + 0.5) * 16
        svg.add(f'<rect x="{vx+42+i*6}" y="{f2(vy+24-h/2)}" width="3" height="{f2(h)}" rx="1.5" fill="{t.violet}" '
                f'opacity="0.85" class="wave" style="animation-delay:-{f2((i*0.13)%1.1)}s"/>')
    svg.add(svg.text(vx + vw - 14, vy + 28, "listening", size=10.5, weight=500, fill=t.fg2, anchor="end"))
    colors = {"say": t.violet, "plan": t.ice, "act": t.amber, "ok": t.lime}
    cycle = 9.0
    for i, (tag, msg) in enumerate(p["log"]):
        y = vy + 60 + i * 22
        start = 0.5 + i * 1.1
        a, b = start / cycle * 100, (start + 0.15) / cycle * 100
        kf = svg.uid("ln")
        svg.css.append(f"@keyframes {kf}{{0%,{f2(a)}%{{opacity:0}}{f2(b)}%,88%{{opacity:1}}96%,100%{{opacity:0}}}}"
                       f".{kf}{{animation:{kf} {cycle}s linear infinite}}")
        g = [f'<g class="{kf} rm-show" opacity="0">']
        s, _ = chip(svg, vx + 12, y - 13, tag, size=10, h=18, pad_x=7, color=colors[tag], weight=700)
        g.append(s)
        if tag == "ok":
            g.append(icon_check(vx + 56, y - 9, 10, t.lime, 2))
            g.append(svg.text(vx + 74, y, msg, size=11.5, weight=500, fill=t.fg0))
        else:
            g.append(svg.text(vx + 62, y, msg, size=11.5, weight=500, fill=t.fg1))
        g.append("</g>")
        svg.add(*g)
    card_footer(svg, p, 24, 238)
    return svg.render()


def card_sentinel(t: Theme) -> str:
    import json
    p = CFG["projects"]["sentinel"]
    data = json.loads((HERE / "data" / "sentinel.json").read_text())
    W, H = 500, 362
    svg = Svg(W, H, t, "SentinelGIS — outbreak intelligence for India", " ".join(p["desc"]))
    svg.css.append(ANIM_CSS)
    svg.add(panel(svg))
    card_header(svg, p, 24, W - 24)
    vx, vy, vw, vh = 24, 58, W - 48, 144
    svg.add(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="12" fill="{t.bg1}" stroke="{t.line}"/>')
    # alert feed (left)
    fc = data["forecast_2024"]
    feed = sorted(fc.items(), key=lambda kv: (-kv[1][1], kv[0]))[:4] + [("Goa", fc["Goa"])]
    svg.add(svg.text(vx + 14, vy + 24, "2024 FORECAST", size=10, weight=700, fill=t.fg2, spacing=1.2))
    for i, (state, (label, conf)) in enumerate(feed):
        y = vy + 48 + i * 20
        col = t.rose if label == "High" else t.amber
        svg.add(f'<circle cx="{vx+18}" cy="{y-4}" r="3.5" fill="{col}"/>')
        svg.add(svg.text(vx + 28, y, state, size=11.5, weight=500, fill=t.fg0))
        svg.add(svg.text(vx + 184, y, f"{label.upper():<6} {conf:.2f}", size=11, weight=500, fill=col, anchor="end"))
    # constellation (right) — state centroids only, no borders drawn
    cen = data["centroids_lon_lat_area"]
    mx0, my0, mw, mh = vx + 196, vy + 8, vw - 206, vh - 16
    lon0, lon1, lat0, lat1 = 67.5, 97.8, 6.5, 36.5
    s = min(mw / (lon1 - lon0), mh / (lat1 - lat0))
    ox = mx0 + (mw - (lon1 - lon0) * s) / 2
    oy = my0 + (mh - (lat1 - lat0) * s) / 2

    def proj(lon, lat):
        return ox + (lon - lon0) * s, oy + (lat1 - lat) * s
    cx, cy = proj(80.5, 22)
    sid = svg.uid("sw")
    svg.defs.append(f'<linearGradient id="{sid}" x1="0" y1="0" x2="1" y2="0">'
                    f'<stop offset="0" stop-color="{t.lime}" stop-opacity="0"/>'
                    f'<stop offset="1" stop-color="{t.lime}" stop-opacity="{0.28 if t.dark else 0.2}"/></linearGradient>')
    R = 66
    cid = svg.uid("vc")
    svg.defs.append(f'<clipPath id="{cid}"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="12"/></clipPath>')
    for rr in (22, 44, 66):
        svg.add(f'<circle cx="{f2(cx)}" cy="{f2(cy)}" r="{rr}" fill="none" stroke="{t.line}" stroke-width="1" clip-path="url(#{cid})"/>')
    svg.add(f'<g clip-path="url(#{cid})"><g style="transform-origin:{f2(cx)}px {f2(cy)}px" class="sweep">'
            f'<path d="M{f2(cx)} {f2(cy)} L{f2(cx+R)} {f2(cy)} A{R} {R} 0 0 0 {f2(cx+R*math.cos(math.radians(-50)))} {f2(cy+R*math.sin(math.radians(-50)))} Z" '
            f'fill="url(#{sid})"/></g></g>')
    for i, (name, (lon, lat, area)) in enumerate(sorted(cen.items())):
        x, y = proj(lon, lat)
        if name in fc:
            col = t.rose if fc[name][0] == "High" else t.amber
            svg.add(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="3.4" fill="{col}"/>')
            svg.add(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="3.4" fill="none" stroke="{col}" class="ping" '
                    f'style="animation-delay:-{f2((i*0.37)%2.4)}s"/>')
        else:
            svg.add(f'<circle cx="{f2(x)}" cy="{f2(y)}" r="2.2" fill="{t.fg2}" opacity="0.7"/>')
    card_footer(svg, p, 24, 238)
    return svg.render()


# ============================================================================ registry
BUILDERS = {
    "hero": lambda t: ("hero", hero(t)),
    "cards": lambda t: [("card-ayeusann", card_ayeusann(t)), ("card-max", card_max(t)),
                        ("card-sentinel", card_sentinel(t))],
}


def main(argv: list[str]) -> None:
    wanted = argv or list(BUILDERS)
    changed = 0
    for key in wanted:
        for t in THEMES:
            out = BUILDERS[key](t)
            items = out if isinstance(out, list) else [out]
            for name, content in items:
                path = ASSETS / f"{name}-{t.name}.svg"
                if write(path, content):
                    changed += 1
                    print(f"wrote {path.relative_to(ASSETS.parent)} ({len(content)//1024} KB)")
    print(f"{changed} file(s) changed")


if __name__ == "__main__":
    main(sys.argv[1:])
