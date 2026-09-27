"""Tiny SVG toolkit for the profile: themes, embedded fonts, text measuring, icons.

Every SVG in assets/ is generated from code in this folder. Nothing here needs
network access; fonts are subset per image and embedded as base64 WOFF so the
images look identical on every machine (GitHub serves README images through a
proxy that blocks external fonts).
"""
from __future__ import annotations

import base64
import hashlib
import io
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT_DIR = HERE / "fonts"
ICON_DIR = HERE / "icons"
ASSETS = ROOT / "assets"

RAW_BASE = "https://raw.githubusercontent.com/ayeus/ayeus/main"


# --------------------------------------------------------------------------- themes
@dataclass(frozen=True)
class Theme:
    name: str
    bg0: str      # panel
    bg1: str      # raised / inset
    bg2: str      # chips
    line: str     # borders
    grid: str     # background grid dots / lines
    fg0: str      # primary text
    fg1: str      # secondary text
    fg2: str      # muted text
    ember: str    # accent 1
    ice: str      # accent 2
    lime: str     # ok / success
    rose: str     # alert / high
    amber: str    # warning / medium
    violet: str   # ml
    glow: float   # strength of glow effects (dark themes glow more)

    @property
    def dark(self) -> bool:
        return self.name == "dark"


DARK = Theme(
    name="dark",
    bg0="#0b1017", bg1="#111823", bg2="#172130", line="#243142", grid="#1a2432",
    fg0="#e8eef5", fg1="#9eabbc", fg2="#627083",
    ember="#ff7a45", ice="#43d1f5", lime="#9be564", rose="#ff5470", amber="#ffc857", violet="#a58bff",
    glow=1.0,
)
LIGHT = Theme(
    name="light",
    bg0="#ffffff", bg1="#f6f8fa", bg2="#eef2f6", line="#d5dce4", grid="#e3e9ef",
    fg0="#1b2330", fg1="#4f5d6e", fg2="#8391a2",
    ember="#e4572e", ice="#0a86b3", lime="#3f8f1c", rose="#d6284b", amber="#b7791f", violet="#6c4df0",
    glow=0.35,
)
THEMES = (DARK, LIGHT)


# --------------------------------------------------------------------------- fonts
FAMILIES = {
    # css family name: {weight: file}
    "AyDisplay": {500: "Unbounded-500.ttf", 700: "Unbounded-700.ttf", 800: "Unbounded-800.ttf"},
    "AyMono": {400: "JetBrainsMono-400.ttf", 500: "JetBrainsMono-500.ttf", 700: "JetBrainsMono-700.ttf", 800: "JetBrainsMono-800.ttf"},
    "AySans": {400: "SpaceGrotesk-400.ttf", 500: "SpaceGrotesk-500.ttf", 700: "SpaceGrotesk-700.ttf"},
}
FALLBACK = {
    "AyDisplay": "'Arial Black', 'Helvetica Neue', Arial, sans-serif",
    "AyMono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    "AySans": "'Helvetica Neue', Arial, sans-serif",
}


class _Font:
    def __init__(self, path: Path):
        from fontTools.ttLib import TTFont

        self.path = path
        self.tt = TTFont(str(path))
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"].metrics
        self.upm = self.tt["head"].unitsPerEm
        self.notdef = self.hmtx[".notdef"][0]

    def advance(self, ch: str) -> float:
        g = self.cmap.get(ord(ch))
        return (self.hmtx[g][0] if g else self.notdef) / self.upm

    def has(self, ch: str) -> bool:
        return ord(ch) in self.cmap


@lru_cache(maxsize=None)
def font(family: str, weight: int) -> _Font:
    return _Font(FONT_DIR / FAMILIES[family][weight])


def text_width(s: str, family: str, weight: int, size: float, spacing: float = 0.0) -> float:
    f = font(family, weight)
    return sum(f.advance(c) for c in s) * size + spacing * max(0, len(s) - 1)


@lru_cache(maxsize=None)
def _subset_b64(family: str, weight: int, chars: str) -> str:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    tt = TTFont(str(FONT_DIR / FAMILIES[family][weight]))
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern"]
    opts.hinting = False
    opts.desubroutinize = True
    opts.name_IDs = [1, 2]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=chars + " ")
    sub.subset(tt)
    buf = io.BytesIO()
    tt.flavor = "woff"
    tt.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


class Fonts:
    """Collects the characters each (family, weight) renders in one SVG."""

    def __init__(self):
        self.used: dict[tuple[str, int], set[str]] = {}

    def use(self, family: str, weight: int, s: str) -> None:
        self.used.setdefault((family, weight), set()).update(s)

    def css(self) -> str:
        out = []
        for (family, weight), chars in sorted(self.used.items()):
            f = font(family, weight)
            keep = "".join(sorted(c for c in chars if f.has(c)))
            if not keep:
                continue
            b64 = _subset_b64(family, weight, keep)
            out.append(
                f"@font-face{{font-family:{family};font-weight:{weight};"
                f"src:url(data:font/woff;base64,{b64}) format('woff');}}"
            )
        return "".join(out)


# --------------------------------------------------------------------------- svg helpers
def esc(s: str) -> str:
    return _xml_escape(str(s), {'"': "&quot;"})


def f2(x: float) -> str:
    """Compact float formatting for coordinates."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Svg:
    """An SVG document under construction."""

    def __init__(self, w: int, h: int, theme: Theme, title: str, desc: str = ""):
        self.w, self.h, self.t = w, h, theme
        self.title, self.desc = title, desc
        self.fonts = Fonts()
        self.defs: list[str] = []
        self.css: list[str] = []
        self.body: list[str] = []
        self._ids = 0

    # ids unique within the document
    def uid(self, prefix: str = "i") -> str:
        self._ids += 1
        return f"{prefix}{self._ids}"

    def add(self, *parts: str) -> "Svg":
        self.body.extend(parts)
        return self

    def text(
        self,
        x: float,
        y: float,
        s: str,
        *,
        family: str = "AyMono",
        weight: int = 400,
        size: float = 14,
        fill: str | None = None,
        anchor: str = "start",
        spacing: float = 0.0,
        cls: str = "",
        extra: str = "",
        opacity: float | None = None,
    ) -> str:
        self.fonts.use(family, weight, s)
        fill = fill or self.t.fg0
        attrs = [
            f'x="{f2(x)}"', f'y="{f2(y)}"',
            f'class="f-{family}{" " + cls if cls else ""}"',
            f'font-weight="{weight}"', f'font-size="{f2(size)}"', f'fill="{fill}"',
        ]
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if spacing:
            attrs.append(f'letter-spacing="{f2(spacing)}"')
        if opacity is not None:
            attrs.append(f'opacity="{f2(opacity)}"')
        if extra:
            attrs.append(extra)
        return f'<text {" ".join(attrs)}>{esc(s)}</text>'

    def tspan_text(self, x: float, y: float, runs: list[tuple[str, dict]], *, size: float = 14,
                   family: str = "AyMono", weight: int = 400, cls: str = "", extra: str = "") -> str:
        """One <text> made of differently coloured runs: [(text, {fill, weight}), ...]."""
        parts = []
        for s, st in runs:
            w = st.get("weight", weight)
            fam = st.get("family", family)
            self.fonts.use(fam, w, s)
            a = [f'fill="{st.get("fill", self.t.fg0)}"']
            if w != weight:
                a.append(f'font-weight="{w}"')
            if fam != family:
                a.append(f'class="f-{fam}"')
            if "opacity" in st:
                a.append(f'opacity="{st["opacity"]}"')
            parts.append(f'<tspan {" ".join(a)}>{esc(s)}</tspan>')
        c = f"f-{family}" + (f" {cls}" if cls else "")
        return (f'<text x="{f2(x)}" y="{f2(y)}" class="{c}" font-weight="{weight}" '
                f'font-size="{f2(size)}" {extra}>{"".join(parts)}</text>')

    def render(self) -> str:
        t = self.t
        fam_css = "".join(
            f".f-{fam}{{font-family:{fam},{FALLBACK[fam]};}}" for fam in FAMILIES
        )
        reduced = (
            "@media (prefers-reduced-motion: reduce){*{animation:none!important;"
            "transition:none!important}.rm-hide{display:none}.rm-show{opacity:1!important}}"
        )
        style = self.fonts.css() + fam_css + "".join(self.css) + reduced
        desc = f"<desc>{esc(self.desc)}</desc>" if self.desc else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'role="img" aria-label="{esc(self.title)}">'
            f"<title>{esc(self.title)}</title>{desc}"
            f"<defs><style>{style}</style>{''.join(self.defs)}</defs>"
            f"{''.join(self.body)}</svg>"
        )


# --------------------------------------------------------------------------- building blocks
def panel(svg: Svg, x=0.5, y=0.5, w=None, h=None, r=16, fill=None, stroke=None) -> str:
    t = svg.t
    w = svg.w - 1 if w is None else w
    h = svg.h - 1 if h is None else h
    return (f'<rect x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{f2(h)}" rx="{r}" '
            f'fill="{fill or t.bg0}" stroke="{stroke or t.line}"/>')


def dot_grid(svg: Svg, step=20, r=1.0, x=0, y=0, w=None, h=None, opacity=1.0, clip_r=16) -> str:
    """Background dot grid clipped to a rounded rect."""
    t = svg.t
    w = svg.w if w is None else w
    h = svg.h if h is None else h
    pid, cid = svg.uid("dots"), svg.uid("clip")
    svg.defs.append(
        f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="{step/2}" cy="{step/2}" r="{r}" fill="{t.grid}"/></pattern>'
        f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{clip_r}"/></clipPath>'
    )
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{pid})" '
            f'clip-path="url(#{cid})" opacity="{opacity}"/>')


def chip(svg: Svg, x: float, y: float, label: str, *, size=12.5, color=None, fill=None,
         stroke=None, pad_x=10, h=26, weight=500, family="AyMono", dot: str | None = None) -> tuple[str, float]:
    """Pill with a label. Returns (svg, width). (x, y) is the top-left corner."""
    t = svg.t
    tw = text_width(label, family, weight, size)
    dot_w = 14 if dot else 0
    w = tw + pad_x * 2 + dot_w
    parts = [f'<rect x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{h}" rx="{h/2}" '
             f'fill="{fill or t.bg2}" stroke="{stroke or t.line}"/>']
    if dot:
        parts.append(f'<circle cx="{f2(x + pad_x + 4)}" cy="{f2(y + h/2)}" r="3.5" fill="{dot}"/>')
    parts.append(svg.text(x + pad_x + dot_w, y + h / 2 + size * 0.36, label, size=size, weight=weight,
                          family=family, fill=color or t.fg1))
    return "".join(parts), w


def chips_row(svg: Svg, x: float, y: float, labels: list[str], gap=8, **kw) -> tuple[str, float]:
    out, cx = [], x
    for lab in labels:
        s, w = chip(svg, cx, y, lab, **kw)
        out.append(s)
        cx += w + gap
    return "".join(out), cx - gap - x


def short_hash(s: str, n=7) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:n]


# --------------------------------------------------------------------------- drawn icons (no emoji fonts in SVG images)
def icon_check(x, y, s, color, width=2.2) -> str:
    return (f'<path d="M{f2(x)} {f2(y + s*0.52)} L{f2(x + s*0.38)} {f2(y + s*0.88)} L{f2(x + s)} {f2(y + s*0.14)}" '
            f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def icon_star(cx, cy, r, color) -> str:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{f2(cx + rr*math.cos(a))},{f2(cy + rr*math.sin(a))}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'


def icon_cloud(x, y, s, color) -> str:
    # simple cloud from three circles + base
    return (f'<g fill="{color}"><circle cx="{f2(x+s*0.32)}" cy="{f2(y+s*0.62)}" r="{f2(s*0.22)}"/>'
            f'<circle cx="{f2(x+s*0.55)}" cy="{f2(y+s*0.48)}" r="{f2(s*0.28)}"/>'
            f'<circle cx="{f2(x+s*0.78)}" cy="{f2(y+s*0.64)}" r="{f2(s*0.2)}"/>'
            f'<rect x="{f2(x+s*0.12)}" y="{f2(y+s*0.62)}" width="{f2(s*0.82)}" height="{f2(s*0.22)}" rx="{f2(s*0.11)}"/></g>')


def icon_arrow_ne(x, y, s, color, width=2) -> str:
    return (f'<path d="M{f2(x)} {f2(y+s)} L{f2(x+s)} {f2(y)} M{f2(x+s*0.35)} {f2(y)} L{f2(x+s)} {f2(y)} L{f2(x+s)} {f2(y+s*0.65)}" '
            f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def skill_icon(name: str, theme: Theme, x: float, y: float, size: float, prefix: str) -> str:
    """A skill-icons logo (MIT, tandpfun/skill-icons) placed at x,y. Ids are namespaced
    with `prefix` so several icons can share one document."""
    import re

    for cand in (f"{name}-{'Dark' if theme.dark else 'Light'}.svg", f"{name}.svg"):
        p = ICON_DIR / cand
        if p.exists():
            raw = p.read_text()
            inner = raw[raw.index(">") + 1: raw.rindex("</svg>")]
            inner = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', inner)
            inner = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{prefix}{m.group(1)})", inner)
            inner = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}{m.group(1)}"', inner)
            return (f'<svg x="{f2(x)}" y="{f2(y)}" width="{f2(size)}" height="{f2(size)}" '
                    f'viewBox="0 0 256 256">{inner}</svg>')
    raise FileNotFoundError(name)


def write(path: Path, content: str) -> bool:
    """Write only when content changed (keeps git diffs quiet). Returns True if written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True
