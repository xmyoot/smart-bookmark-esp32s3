"""Schematic writer engine for smart-bookmark-esp32s3 (used by gen_schematic.py).

Hand-authored s-expression writer (no SkiDL / kicad_sch_api). The circuit below is the
source of truth lives in gen_schematic.py and mirrors docs/design_spec.md.

Every pin gets a stub ending in: a power symbol (GND/+3V3/VBUS/+BATT), a hierarchical
label (cross-sheet nets), a local label (sheet-local nets), or a no-connect flag.
"""
import math
import re
import uuid
from pathlib import Path

PROJ = "smart-bookmark-esp32s3"
ROOT_DIR = Path(__file__).resolve().parents[1]
KICAD_SYM = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
PROJ_SYM = ROOT_DIR / "lib" / "bookmark.kicad_sym"

# deterministic UUIDs so regenerating keeps annotation/PCB links stable
NS = uuid.UUID("2b7c9e14-5a3d-4f6b-9c21-b00c3a4c0001")
def uid(*key):
    return str(uuid.uuid5(NS, "/".join(map(str, key))))

ROOT_UUID = uid("root")
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3", "VBUS": "power:VBUS", "+BATT": "power:+BATT"}
STUB = 2.54

# ----------------------------------------------------------------- symbol library access
def _block(text, start):
    d = 0
    for j in range(start, len(text)):
        c = text[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return text[start:j + 1]
    raise ValueError("unbalanced")

_lib_cache = {}
def _lib_text(lib):
    if lib not in _lib_cache:
        p = PROJ_SYM if lib == "bookmark" else KICAD_SYM / f"{lib}.kicad_sym"
        _lib_cache[lib] = p.read_text(encoding="utf-8")
    return _lib_cache[lib]

def _raw_symbol(lib, name):
    t = _lib_text(lib)
    m = re.search(r'\n\s*\(symbol "%s"\s' % re.escape(name), t)
    if not m:
        raise KeyError(f"{lib}:{name}")
    return _block(t, m.start() + t[m.start():].index("("))

def _props(blk):
    """top-level property blocks of a symbol block, keyed by name"""
    out = {}
    for m in re.finditer(r'\(property "([^"]+)"', blk):
        # only direct children (depth 1)
        depth = blk[:m.start()].count("(") - blk[:m.start()].count(")")
        if depth == 1:
            out[m.group(1)] = _block(blk, m.start())
    return out

def flat_symbol(lib_id):
    """Symbol definition for the lib_symbols cache, flattened if it uses (extends)."""
    lib, name = lib_id.split(":")
    blk = _raw_symbol(lib, name)
    ext = re.search(r'\(extends "([^"]+)"\)', blk)
    if ext:
        parent = ext.group(1)
        pblk = flat_symbol(f"{lib}:{parent}")
        pblk = pblk.replace(f'(symbol "{lib}:{parent}"', f'(symbol "{lib}:{name}"', 1)
        pblk = re.sub(r'\(symbol "%s_(\d+_\d+)"' % re.escape(parent), r'(symbol "%s_\1"' % name, pblk)
        for k, v in _props(blk).items():
            old = _props(pblk).get(k)
            if old:
                pblk = pblk.replace(old, v)
            else:                      # property only the child has (e.g. Sim.* fields): add it
                last = list(_props(pblk).values())[-1]
                pblk = pblk.replace(last, last + "\n\t\t" + v)
        return pblk
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)

PIN_RE = re.compile(r'\(pin (\w+) (\w+)\s+\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s+\(length ([-\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]*)"', re.S)
def pins_of(lib_id):
    blk = flat_symbol(lib_id)
    pins = {}
    for m in PIN_RE.finditer(blk):
        typ, _, x, y, a, _, mid, pname, num = m.groups()
        pins[num] = dict(x=float(x), y=float(y), a=float(a), name=pname, type=typ,
                         hidden="(hide yes)" in mid)
    return pins

# ----------------------------------------------------------------- geometry
def rot(x, y, r):
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return x * c - y * s, x * s + y * c

def g(v):
    """snap to 0.01 mm to keep text clean"""
    return round(v + 0.0, 2)

def fmt(v):
    v = g(v)
    return ("%.2f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v))

# ----------------------------------------------------------------- s-expression emitters
def eff(size=1.27, justify=None, hide=False):
    j = f" (justify {justify})" if justify else ""
    return f"(effects (font (size {size} {size})){j}{' (hide yes)' if hide else ''})"

def prop(name, value, x, y, a=0, hide=False, justify=None):
    return (f'\t\t(property "{name}" "{value}" (at {fmt(x)} {fmt(y)} {a})'
            f'{" (hide yes)" if hide else ""} (show_name no) (do_not_autoplace no) {eff(justify=justify)})\n')

LABEL_JUST = {0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom"}
HLABEL_JUST = {0: "left", 90: "left", 180: "right", 270: "right"}

class Sheet:
    def __init__(self, key, title, hier_nets=(), page=None):
        self.key, self.title = key, title
        self.uuid = uid("sheetfile", key)
        self.sym_uuid = uid("sheetsym", key)
        self.hier = list(hier_nets)
        self.items = []
        self.lib_ids = set()
        self.page = page
        self.pwr_n = 0

    @property
    def path(self):
        return f"/{ROOT_UUID}/{self.sym_uuid}"

    # --- primitives
    def wire(self, x1, y1, x2, y2):
        self.items.append(f'\t(wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})) '
                          f'(stroke (width 0) (type default)) (uuid "{uid(self.key, "w", x1, y1, x2, y2)}"))\n')

    def label(self, net, x, y, a):
        self.items.append(f'\t(label "{net}" (at {fmt(x)} {fmt(y)} {a}) {eff(justify=LABEL_JUST[a])} '
                          f'(uuid "{uid(self.key, "l", net, x, y)}"))\n')

    def hlabel(self, net, x, y, a):
        self.items.append(f'\t(hierarchical_label "{net}" (shape bidirectional) (at {fmt(x)} {fmt(y)} {a}) '
                          f'{eff(justify=HLABEL_JUST[a])} (uuid "{uid(self.key, "h", net, x, y)}"))\n')

    def noconn(self, x, y):
        self.items.append(f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid(self.key, "nc", x, y)}"))\n')

    def text(self, s, x, y, size=1.27):
        s = s.replace('"', "'")
        self.items.append(f'\t(text "{s}" (exclude_from_sim no) (at {fmt(x)} {fmt(y)} 0) '
                          f'(effects (font (size {size} {size})) (justify left bottom)) (uuid "{uid(self.key, "t", s)}"))\n')

    def box(self, x1, y1, x2, y2, caption):
        self.items.append(f'\t(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
                          f'(stroke (width 0.2) (type dash)) (fill (type none)) (uuid "{uid(self.key, "box", caption)}"))\n')
        self.text(caption, x1 + 1.27, y1 - 1.27, 1.5)

    # --- symbols
    def _symbol(self, ref, lib_id, value, x, y, r=0, footprint="", fields=None,
                in_bom=True, on_board=True, dnp=False, pos=True, ref_hidden=False, vpos=None):
        self.lib_ids.add(lib_id)
        pins = pins_of(lib_id)
        su = uid(self.key, "sym", ref)
        # field placement: beside 2-pin vertical parts, else above/below the pin extent
        ys = [y - rot(p["x"], p["y"], r)[1] for p in pins.values()] or [y]
        xs = [x + rot(p["x"], p["y"], r)[0] for p in pins.values()] or [x]
        vertical2 = len(pins) <= 2 and max(xs) - min(xs) < 0.1 and not ref.startswith("#")
        if vertical2:
            rp, vp, just = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), "left"
        else:
            rp, vp, just = (x, min(ys) - 3.81), (x, max(ys) + 3.81), None
        if vpos:
            vp = vpos
        s = (f'\t(symbol (lib_id "{lib_id}") (at {fmt(x)} {fmt(y)} {r}) (unit 1) (body_style 1)\n'
             f'\t\t(exclude_from_sim no) (in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if on_board else "no"}) '
             f'(in_pos_files {"yes" if pos else "no"}) (dnp {"yes" if dnp else "no"})\n'
             f'\t\t(uuid "{su}")\n')
        fa = r % 180   # keep field text horizontal on rotated symbols
        s += prop("Reference", ref, *rp, a=fa, hide=ref_hidden, justify=just)
        s += prop("Value", value, *vp, a=fa, hide=ref.startswith("#FLG"), justify=just)
        s += prop("Footprint", footprint, x, y, hide=True)
        s += prop("Datasheet", "", x, y, hide=True)
        s += prop("Description", "", x, y, hide=True)
        for k, v in (fields or {}).items():
            s += prop(k, v, x, y, hide=True)
        for num in pins:
            s += f'\t\t(pin "{num}" (uuid "{uid(self.key, "pin", ref, num)}"))\n'
        s += (f'\t\t(instances (project "{PROJ}" (path "{self.path}" (reference "{ref}") (unit 1))))\n'
              f'\t)\n')
        self.items.append(s)
        return pins

    def power(self, net, x, y, outward):
        """power symbol whose pin sits at (x, y); body points in `outward` direction."""
        self.pwr_n += 1
        ref = f"#PWR_{self.key}_{self.pwr_n:02d}"
        body = 270 if net == "GND" else 90         # body direction at rotation 0
        r = (outward - body) % 360
        ox, oy = rot(5.08, 0, outward)
        self._symbol(ref, POWER_NETS[net], net, x, y, r, in_bom=False, pos=False, ref_hidden=True,
                     vpos=(x + ox + (1.27 if ox > 0 else -1.27 if ox < 0 else 0), y - oy))

    def part(self, ref, lib_id, value, x, y, nets, r=0, footprint="", lcsc=None, mpn=None,
             in_bom=True, dnp=False, pos=True, stub=None):
        fields = {}
        if mpn:
            fields["MPN"] = mpn
        if lcsc:
            fields["LCSC"] = lcsc
        pins = self._symbol(ref, lib_id, value, x, y, r, footprint, fields, in_bom=in_bom, dnp=dnp, pos=pos)
        missing = set(pins) - set(nets)
        extra = set(nets) - set(pins)
        if missing or extra:
            raise ValueError(f"{ref}: pins missing nets {sorted(missing)} / unknown pins {sorted(extra)}")
        seen = set()                                  # stacked pins (module GND pads) draw once
        for num, net in nets.items():
            p = pins[num]
            dx, dy = rot(p["x"], p["y"], r)
            px, py = x + dx, y - dy
            if net != "NC":
                if (g(px), g(py)) in seen:
                    continue
                seen.add((g(px), g(py)))
            if net == "NC":
                self.noconn(px, py)
                continue
            out = int((p["a"] + 180 + r) % 360)          # outward direction (lib angle convention)
            ox, oy = rot(stub or (STUB if len(pins) <= 2 else 2 * STUB), 0, out)
            ex, ey = px + ox, py - oy
            self.wire(px, py, ex, ey)
            if net in POWER_NETS:
                self.power(net, ex, ey, out)
            elif net in self.hier:
                self.hlabel(net, ex, ey, out)
            else:
                self.label(net, ex, ey, out)
        return pins

    def flag(self, net, x, y):
        """PWR_FLAG on a net (drawn as PWR_FLAG + stub + label/power symbol)."""
        self.pwr_n += 1
        self.lib_ids.add("power:PWR_FLAG")
        ref = f"#FLG_{self.key}_{self.pwr_n:02d}"
        self._symbol(ref, "power:PWR_FLAG", "PWR_FLAG", x, y, 0, in_bom=False, pos=False, ref_hidden=True)
        self.wire(x, y, x, y + STUB)
        if net in POWER_NETS:
            self.power(net, x, y + STUB, 270)
        else:
            self.label(net, x, y + STUB, 270)

    # --- file
    def render(self):
        libs = sorted(self.lib_ids | {POWER_NETS[n] for n in POWER_NETS if any(f'"{n}"' in i for i in self.items)})
        cache = "".join("\t\t" + flat_symbol(l).replace("\n", "\n\t\t") + "\n" for l in libs)
        return (f'(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n'
                f'\t(uuid "{self.uuid}")\n\t(paper "A4")\n'
                f'\t(title_block (title "{PROJ} - {self.title}") (date "2026-10-05") (rev "A") '
                f'(company "Smart bookmark voice recorder"))\n'
                f'\t(lib_symbols\n{cache}\t)\n' + "".join(self.items) + "\t(embedded_fonts no)\n)\n")


