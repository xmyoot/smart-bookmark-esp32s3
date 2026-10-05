"""Build smart-bookmark-esp32s3.kicad_pcb from the schematic netlist: outline, footprints with
nets, hand placement, hand routing, zones.

Run with KiCad's bundled Python:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" scripts/build_pcb.py [place|route]
Coordinates in this file are board-local mm: origin = board top-left corner (100, 70 in the
KiCad sheet), x right, y down, seen from the component (top) side. The antenna end is y = 0.
This regenerates the board from scratch: edits made in the KiCad GUI are overwritten.
"""
import json
import re
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
PROJ = "smart-bookmark-esp32s3"
PCB = ROOT / f"{PROJ}.kicad_pcb"
KFP = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
NETLIST = ROOT / "build" / "bookmark.net"
OX, OY = 100.0, 70.0
W, H = 37.0, 52.0
CORNER_R = 2.0
CELL = (1.5, 10.0, 26.5, 40.0)      # assumed 25 x 30 x 2.5 mm pouch cell on the back (x0, y0, x1, y1)

def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))

def mm(v):
    return (round(pcbnew.ToMM(v.x) - OX, 3), round(pcbnew.ToMM(v.y) - OY, 3))

# ------------------------------------------------------------------ netlist
def parse_netlist(path):
    t = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
    comps = {}
    cpart = t[t.index("(components"):t.index("(libparts")]
    for blk in re.split(r"\(comp \(ref ", cpart)[1:]:
        ref = re.match(r'"([^"]+)"', blk).group(1)
        get = lambda k: (re.search(r'\(%s "([^"]*)"\)' % k, blk) or [None, ""])[1]
        fields = dict(re.findall(r'\(field \(name "([^"]+)"\) "([^"]*)"\)', blk))
        comps[ref] = dict(value=get("value"), footprint=get("footprint"), fields=fields,
                          sheet_ts=re.search(r'\(sheetpath \(names "[^"]*"\) \(tstamps "([^"]*)"\)', blk).group(1),
                          raw=blk)
        m = re.findall(r'\(tstamps "([0-9a-f-]{36})"\)', blk)
        comps[ref]["sym_ts"] = m[-1] if m else ""
        comps[ref]["dnp"] = '(property (name "dnp")' in blk
        comps[ref]["no_bom"] = '(property (name "exclude_from_bom")' in blk
        comps[ref]["no_pos"] = '(property (name "exclude_from_pos_files")' in blk
    nets = {}
    npart = t[t.index("(nets"):]
    for blk in re.split(r"\(net \(code ", npart)[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', blk):
            nets[(ref, pin)] = name
    return comps, nets

# ------------------------------------------------------------------ board
def _edge(b, shape, pts, layer=pcbnew.Edge_Cuts, width=0.1):
    d = pcbnew.PCB_SHAPE(b)
    d.SetLayer(layer)
    d.SetWidth(pcbnew.FromMM(width))
    if shape == "line":
        d.SetShape(pcbnew.SHAPE_T_SEGMENT)
        d.SetStart(V(*pts[0])); d.SetEnd(V(*pts[1]))
    else:
        d.SetShape(pcbnew.SHAPE_T_ARC)
        d.SetArcGeometry(V(*pts[0]), V(*pts[1]), V(*pts[2]))
    b.Add(d)

def fresh_board():
    """37 x 52 mm outline with R2 corners, 4 copper layers, 0.8 mm. (pcbnew.LoadBoard is avoided
    on purpose: it invalidates the SWIG types of footprints loaded earlier in the process.)"""
    b = pcbnew.NewBoard(str(ROOT / "build" / "_scratch.kicad_pcb"))
    b.SetCopperLayerCount(4)
    r, k = CORNER_R, CORNER_R * (1 - 0.70710678)
    _edge(b, "line", [(r, 0), (W - r, 0)])
    _edge(b, "line", [(W, r), (W, H - r)])
    _edge(b, "line", [(W - r, H), (r, H)])
    _edge(b, "line", [(0, H - r), (0, r)])
    _edge(b, "arc", [(W - r, 0), (W - k, k), (W, r)])
    _edge(b, "arc", [(W, H - r), (W - k, H - k), (W - r, H)])
    _edge(b, "arc", [(r, H), (k, H - k), (0, H - r)])
    _edge(b, "arc", [(0, r), (k, k), (r, 0)])
    x0, y0, x1, y1 = CELL                      # cell outline, drawing layer only
    for a, c in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        _edge(b, "line", [a, c], pcbnew.Dwgs_User, 0.15)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(pcbnew.FromMM(0.8))
    ds.m_TrackMinWidth = pcbnew.FromMM(0.15)
    ds.m_MinClearance = pcbnew.FromMM(0.15)
    ds.m_ViasMinSize = pcbnew.FromMM(0.45)
    ds.m_MinThroughDrill = pcbnew.FromMM(0.2)
    ds.m_ViasMinAnnularWidth = pcbnew.FromMM(0.1)
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.3)
    ds.m_HoleClearance = pcbnew.FromMM(0.2)
    ds.m_HoleToHoleMin = pcbnew.FromMM(0.25)
    ds.m_SolderMaskMinWidth = pcbnew.FromMM(0)
    ds.SetAuxOrigin(V(0, H))      # drill/place origin = board bottom-left (positive CPL coords)
    ds.m_MinResolvedSpokes = 1    # module/SOT-23 GND pads: one full spoke is acceptable
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(pcbnew.FromMM(0.15))
    nc.SetTrackWidth(pcbnew.FromMM(0.2))
    nc.SetViaDiameter(pcbnew.FromMM(0.5))
    nc.SetViaDrill(pcbnew.FromMM(0.3))
    return b

def load_fp(fpid):
    lib, name = fpid.split(":")
    libdir = ROOT / "lib" / "bookmark.pretty" if lib == "bookmark" else KFP / f"{lib}.pretty"
    fp = pcbnew.FootprintLoad(str(libdir), name)
    if fp is None:
        raise RuntimeError(f"footprint not found: {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

def add_components(b, comps, pin_nets, preloaded):
    netcodes = {}
    for n in sorted(set(pin_nets.values())):
        ni = pcbnew.NETINFO_ITEM(b, n)
        b.Add(ni)
        netcodes[n] = ni
    fps = {}
    for ref, c in comps.items():
        fp = preloaded[ref]
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for k in ("LCSC", "MPN"):
            if c["fields"].get(k):
                fp.SetField(k, c["fields"][k])
        path = pcbnew.KIID_PATH(f'{c["sheet_ts"].rstrip("/")}/{c["sym_ts"]}')
        fp.SetPath(path)
        fp.SetDNP(c["dnp"])
        fp.SetExcludedFromBOM(c["no_bom"])
        fp.SetExcludedFromPosFiles(c["no_pos"])
        b.Add(fp)
        for pad in fp.Pads():
            n = pin_nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netcodes[n])
        fps[ref] = fp
    return fps

# 3D models the stock/imported footprints lack, or reference by an absolute path.
# ref -> (path, offset mm, rotation deg). Offsets were set by eye against renders (scripts/render3d.py).
M3D = "${KIPRJMOD}/lib/bookmark.3dshapes/"
MODEL_OVERRIDES = {
    "U1": (M3D + "BULETM-SMD_ESP32-S3-MINI-1-N8.step", (0, 0, 0), (0, 0, 0)),
    "J1": (M3D + "USB-C_SMD-TYPE-C-31-M-12_1.step", (0, 1.575, 0), (0, 0, 180)),
    "SW1": (M3D + "SW-SMD_L3.9-W2.9-H2.0-LS4.8.step", (0, 0, 0), (0, 0, 0)),
    # T3902 has no vendor model at LCSC; the Knowles part is the same 3.5 x 2.65 x 0.98 mm can
    "MK1": ("${KICAD10_3DMODEL_DIR}/Sensor_Audio.3dshapes/Knowles_SPH0645LM4H-6_3.5x2.65mm.step", (0, 0, 0), (0, 0, 90)),
}

def apply_models(fps):
    for ref, (path, offset, rot) in MODEL_OVERRIDES.items():
        models = fps[ref].Models()
        while models.size() > 0:
            models.pop_back()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        m.m_Offset = pcbnew.VECTOR3D(*offset)
        m.m_Rotation = pcbnew.VECTOR3D(*rot)
        m.m_Show = True
        models.push_back(m)


# ------------------------------------------------------------------ text / silkscreen
# Only parts someone has to find by eye get a silkscreen designator, placed by hand in clear
# board area. Passives keep theirs on the Fab layer (assembly drawing), centred on the part.
SILK_REF = {   # ref: (x, y) of the text centre, top side
    "U1": (18.5, 21.75), "U6": (5.9, 21.9), "SW1": (18.5, 29.2), "D1": (5.6, 12.85), "MK1": (33.2, 28.7),
    "J1": (27.3, 36.9), "U2": (23.4, 38.9), "U3": (15.2, 49.4), "U4": (4.0, 39.4), "Q1": (4.0, 49.2),
    "U5": (26.0, 47.25), "Q2": (9.9, 31.0), "Q3": (9.9, 40.7),
}
SECTION_LABELS = [   # what each cluster of parts is, in plain words, placed in clear board area
    ("KEEP CLEAR", 5.4, 2.7), ("ANTENNA", 31.6, 2.7),
    ("ESP32-S3 BLE", 18.5, 23.2), ("STATUS LED", 5.3, 14.3), ("16MB FLASH", 7.4, 29.3),
    ("RECORD", 18.5, 27.9), ("MIC", 33.2, 30.0), ("USB-C", 32.6, 35.0),
    ("BATT", 3.7, 36.0), ("SENSE", 3.7, 37.2), ("PROTECT", 4.6, 50.7), ("CHARGER", 16.6, 50.8),
    ("3V3 REG", 32.4, 50.6),
]
BACK_LABEL = {  # back-side pads are labelled with what they are, not their designator
    "BT1": ("BAT+", 0, 2.2), "BT2": ("BAT-", 0, 2.2), "TP7": ("VBAT", 2.6, 0),
    "TP1": ("3V3", 0, -1.5), "TP2": ("GND", 0, -1.5), "TP3": ("EN", 0, -1.5),
    "TP4": ("BOOT", 0, 1.5), "TP5": ("TX", 0, 1.5), "TP6": ("RX", 0, 1.5),
}

def _size(t, h, thick):
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(h), pcbnew.FromMM(h)))
    t.SetTextThickness(pcbnew.FromMM(thick))

def _text(b, s, x, y, layer, h=0.8, mirror=False):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(V(x, y))
    _size(t, h, 0.13)
    t.SetMirrored(mirror)
    b.Add(t)

def tidy_text(b, fps):
    # U1 and J1 reach the board edge: drop the footprint silk lines that would be cut by it
    for ref in ("U1", "J1"):
        for g in list(fps[ref].GraphicalItems()):
            if g.GetLayer() == pcbnew.F_SilkS:
                bb = g.GetBoundingBox()
                x0, y0 = mm(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()))
                x1, y1 = mm(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
                if x0 < 0.4 or y0 < 0.4 or x1 > W - 0.4 or y1 > H - 0.4:
                    fps[ref].Remove(g)
    for ref, fp in fps.items():
        back = fp.IsFlipped()
        fab = pcbnew.B_Fab if back else pcbnew.F_Fab
        for f in fp.GetFields():
            if f.GetName() not in ("Reference", "Value"):
                f.SetVisible(False)              # MPN / LCSC stay as data for the BOM, never drawn
                f.SetLayer(fab)
        val = fp.Value()
        val.SetLayer(fab)
        val.SetVisible(False)
        r = fp.Reference()
        r.SetTextAngleDegrees(0)
        if ref in SILK_REF:
            r.SetLayer(pcbnew.F_SilkS)
            r.SetPosition(V(*SILK_REF[ref]))
            _size(r, 0.8, 0.13)
        else:
            r.SetLayer(fab)
            r.SetPosition(fp.GetPosition())
            _size(r, 0.4, 0.06)
        if ref in BACK_LABEL:
            label, dx, dy = BACK_LABEL[ref]
            x, y = mm(fp.GetPosition())
            _text(b, label, x + dx, y + dy, pcbnew.B_SilkS, 0.8, mirror=True)
    for label, x, y in SECTION_LABELS:
        _text(b, label, x, y, pcbnew.F_SilkS, 0.8)
    x0, y0, x1, y1 = CELL                      # where the cell goes, for whoever fits it
    for a, c in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        _edge(b, "line", [a, c], pcbnew.B_SilkS, 0.15)
    _text(b, "CELL 25 x 30", 14.0, 25.0, pcbnew.B_SilkS, 1.0, mirror=True)
    _text(b, "SMART BOOKMARK  REV A", 14.0, 4.0 + 2.6, pcbnew.B_SilkS, 0.9, mirror=True)
    _text(b, "CELL AREA - NO PADS", 14.0, 25.0, pcbnew.B_Fab, 1.0, mirror=True)


# ------------------------------------------------------------------ placement helpers
def cy_bbox(fp):
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    bb = fp.GetCourtyard(layer).BBox()
    return (pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY,
            pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)

def place(fp, x, y, rot=0, back=False):
    if back:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(V(x, y))

def pad_xy(fps, ref, num):
    return mm(fps[ref].FindPadByNumber(str(num)).GetPosition())


# =================================================================== PLACEMENT
# Floorplan (top side, all assembled parts):
#   y 0..5.0       antenna keep-out (module rule area, full board width, every layer)
#   y 0..20.75     U1 centred; left strip = 3V3 decoupling + LED; right strip = EN RC + mic series parts
#   y 21..29       left: clip flash U6; right edge: microphone MK1 (port hole through the board)
#   y 30..33       SW1 record button on the board centre line
#   y 31..41       left of centre: battery sense (Q2/Q3)
#   y 36..47       right edge: J1 USB-C (overhangs the edge by 1.0 mm), U2 ESD and CC resistors beside it
#   y 40..51       left: cell protection (U4/Q1); centre: charger U3; right: LDO U5
# Back side: nothing assembled. Cell lies in CELL; battery pads BT1/BT2 just below it; test pads in
# the top-right strip and one (VBAT) at the bottom, all outside the cell footprint.
TOP = {
    "U1": (18.5, 10.25, 0),      # real module is 20.5 long: 0.4 mm past the footprint outline at the antenna end
    # 3V3 decoupling at module pin 3, LED
    "C7": (8.6, 6.3, 180), "C8": (9.4, 8.55, 180), "R17": (8.6, 11.35, 180), "D1": (5.6, 11.35, 0),
    # EN RC, mic series parts (rows match module pins 38 / 37)
    "R13": (28.0, 6.85, 180), "C9": (27.97, 8.15, 0), "R15": (28.0, 12.8, 0), "R14": (30.5, 13.65, 0),
    # microphone + decoupling on the VDD drop
    "MK1": (33.2, 26.0, 0), "C10": (34.5, 21.6, 0), "C11": (34.5, 22.9, 0),
    # clip flash and its pull-ups
    "U6": (8.0, 25.5, 0), "R16": (9.0, 19.75, 90), "R18": (3.4, 26.135, 0), "R19": (11.95, 24.0, 270),
    "C12": (9.7, 21.8, 180),
    # button
    "SW1": (18.5, 31.5, 0),
    # battery sense
    "Q2": (9.9, 33.5, 0), "Q3": (9.9, 38.0, 180), "R9": (6.6, 33.06, 90), "R10": (12.9, 40.2, 180),
    "R11": (13.0, 33.5, 0), "R12": (13.0, 32.2, 180), "C6": (13.0, 30.9, 180),
    # USB-C, ESD, CC pull-downs, USB-present divider
    "J1": (34.3, 41.5, 90), "U2": (24.0, 41.5, 180), "R1": (26.6, 43.8, 180), "R2": (26.6, 39.2, 180),
    "R5": (20.6, 44.0, 180), "R6": (18.57, 44.0, 180),
    # charger
    "U3": (16.0, 46.5, 0), "R3": (19.2, 45.55, 0), "C2": (12.3, 47.45, 180), "C1": (19.7, 47.45, 0),
    # cell protection
    "U4": (4.0, 42.0, 180), "Q1": (4.0, 46.5, 0), "C3": (1.1, 42.5, 270), "R7": (1.1, 40.5, 270),
    "R8": (6.9, 42.51, 270),
    # LDO
    "U5": (26.0, 49.6, 0), "C4": (22.5, 49.6, 270), "C5": (29.7, 48.65, 0),
}
BACK = {
    "BT1": (11.5, 44.6, 0), "BT2": (3.5, 44.25, 0),
    "TP3": (28.6, 7.0, 0), "TP1": (31.6, 7.0, 0), "TP2": (34.6, 7.0, 0),
    "TP6": (28.6, 10.0, 0), "TP5": (31.6, 10.0, 0), "TP4": (34.6, 10.0, 0),
    "TP7": (8.1, 50.2, 0),
}


def build_place():
    comps, pin_nets = parse_netlist(NETLIST)
    # load library footprints before any board exists (pcbnew SWIG quirk: FootprintLoad
    # after LoadBoard returns an untyped plugin object)
    pre = {ref: load_fp(c["footprint"]) for ref, c in comps.items()}
    b = fresh_board()
    fps = add_components(b, comps, pin_nets, pre)
    for ref, (x, y, r) in TOP.items():
        place(fps[ref], x, y, r)
    for ref, (x, y, r) in BACK.items():
        place(fps[ref], x, y, r, back=True)
    missing = set(fps) - set(TOP) - set(BACK)
    if missing:
        raise RuntimeError(f"unplaced: {sorted(missing)}")
    apply_models(fps)
    tidy_text(b, fps)
    return b, fps


def report(b, fps, out):
    data = {}
    for ref, fp in sorted(fps.items()):
        data[ref] = {"pos": mm(fp.GetPosition()), "rot": fp.GetOrientationDegrees(),
                     "side": "B" if fp.IsFlipped() else "F", "courtyard": [round(v, 2) for v in cy_bbox(fp)],
                     "pads": {p.GetNumber() + ("" if p.GetNumber() else "MP"): [*mm(p.GetPosition()), p.GetNetname()]
                              for p in fp.Pads()}}
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")


def overlaps(fps):
    """Courtyard box overlaps between parts on the same side (U1's box includes its antenna zone)."""
    out = []
    items = sorted(fps.items())
    for i, (ra, fa) in enumerate(items):
        a = cy_bbox(fa)
        if ra == "U1":
            a = (10.55, 0.0, 26.45, 20.74)
        for rb, fb in items[i + 1:]:
            if fa.IsFlipped() != fb.IsFlipped():
                continue
            c = cy_bbox(fb)
            if rb == "U1":
                c = (10.55, 0.0, 26.45, 20.74)
            if a[0] < c[2] - 0.005 and c[0] < a[2] - 0.005 and a[1] < c[3] - 0.005 and c[1] < a[3] - 0.005:
                out.append((ra, rb))
    return out


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "place"
    b, fps = build_place()
    report(b, fps, ROOT / "build" / "placement.json")
    print("courtyard overlaps:", overlaps(fps))
    off = [r for r, fp in fps.items() if not fp.IsFlipped() and r not in ("U1", "J1")
           and (cy_bbox(fp)[0] < 0.3 or cy_bbox(fp)[1] < 5.0 or cy_bbox(fp)[2] > W - 0.3 or cy_bbox(fp)[3] > H - 0.3)]
    print("outside board / in antenna strip:", off)
    if stage == "route":
        import route_pcb
        route_pcb.route(b, fps)
    b.Save(str(PCB))
    print(f"saved {PCB.name}: {len(fps)} footprints, stage {stage}")
