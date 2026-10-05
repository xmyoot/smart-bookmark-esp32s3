"""Hand routing for smart-bookmark-esp32s3 (called by build_pcb.py route).

Every track/via below is placed deliberately; coordinates are board-local mm (see
build_pcb.py). Layer plan:
  F.Cu   - all parts, nearly all signals, GND pour
  In1.Cu - solid GND
  In2.Cu - +3V3 plane
  B.Cu   - battery/test pads, +BATT and VBUS trunks, the five signals that have to cross
           (BOOT, BTN_N, BAT_ADC, EN/TX/RX stubs to their test pads), GND pour
The module's GPIOs were assigned so that each group leaves the module on the side its parts
sit on; the top layer therefore has no crossings and needs no bridges.
"""
import pcbnew

OX, OY = 100.0, 70.0
W, H = 37.0, 52.0
F, B = pcbnew.F_Cu, pcbnew.B_Cu
ANTENNA_Y = 5.0            # module rule area: no copper above this line


def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


class Router:
    def __init__(self, b, fps):
        self.b, self.fps = b, fps
        self.nets = {}
        for name, ni in b.GetNetsByName().items():
            self.nets[str(name).split("/")[-1]] = ni

    def net(self, name):
        return self.nets[name]

    def P(self, p):
        if isinstance(p, str):
            ref, num = p.split(".")
            pos = self.fps[ref].FindPadByNumber(num).GetPosition()
            return (pcbnew.ToMM(pos.x) - OX, pcbnew.ToMM(pos.y) - OY)
        return p

    def T(self, net, layer, w, *pts):
        pts = [self.P(p) for p in pts]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(V(*a))
            t.SetEnd(V(*c))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(layer)
            t.SetNet(self.net(net))
            self.b.Add(t)

    def VIA(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(V(x, y))
        v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(d))
        v.SetDrill(pcbnew.FromMM(drill))
        v.SetNet(self.net(net))
        self.b.Add(v)

    def drop(self, net, pad, x, y, w=0.25, d=0.5):
        """Short top-layer track from a pad to a via at (x, y): plane connections."""
        self.T(net, F, w, pad, (x, y))
        self.VIA(net, x, y, d)


def route(b, fps):
    r = Router(b, fps)
    T, VIA, drop = r.T, r.VIA, r.drop

    # ------------------------------------------------------------- module supply, LED, EN
    T("+3V3", F, 0.3, "C7.1", "C8.1", "U1.3")
    T("+3V3", F, 0.3, (10.45, 8.55), (10.45, 7.65)); VIA("+3V3", 10.45, 7.65, 0.5)
    drop("GND", "C7.2", 6.6, 6.3)
    drop("GND", "C8.2", 7.9, 8.55)
    for x, y in ((17.675, 11.975), (19.325, 11.975), (17.675, 13.625), (19.325, 13.625)):
        VIA("GND", x, y, 0.5)                                   # module ground pads to In1

    T("LED", F, 0.2, "U1.6", (10.6, 11.1), "R17.1")
    T("LED_A", F, 0.2, "R17.2", "D1.2")
    drop("GND", "D1.1", 3.8, 11.35)

    T("EN", F, 0.2, "U1.45", "R13.2", "C9.1")
    VIA("EN", 26.6, 6.85, 0.5)
    T("EN", B, 0.2, (26.6, 6.85), "TP3.1")
    T("+3V3", F, 0.25, "R13.1", (31.2, 6.85)); VIA("+3V3", 31.2, 6.85, 0.5)     # inside TP1
    T("GND", F, 0.25, "C9.2", (29.5, 8.15), (30.1, 7.6)); VIA("GND", 30.1, 7.6, 0.5)
    VIA("GND", 34.6, 7.0, 0.5)                                                   # inside TP2

    # ------------------------------------------------------------- test pads / crossings on B.Cu
    T("BOOT", F, 0.2, "U1.4", (9.2, 9.4), (8.6, 9.75)); VIA("BOOT", 8.6, 9.75, 0.5)
    T("BOOT", B, 0.2, (8.6, 9.75), (9.85, 8.5), (33.2, 8.5), (33.2, 10.0), "TP4.1")
    T("UART_TX", F, 0.2, "U1.39", (26.7, 11.95)); VIA("UART_TX", 26.7, 11.95, 0.5)
    T("UART_TX", B, 0.2, (26.7, 11.95), (31.6, 11.95), "TP5.1")
    T("UART_RX", F, 0.2, "U1.40", (27.5, 11.1)); VIA("UART_RX", 27.5, 11.1, 0.5)
    T("UART_RX", B, 0.2, (27.5, 11.1), "TP6.1")

    T("BTN_N", F, 0.2, "U1.5", (10.35, 10.25)); VIA("BTN_N", 10.35, 10.25, 0.5)
    T("BTN_N", B, 0.2, (10.35, 10.25), (10.35, 23.93), (16.32, 29.9))
    VIA("BTN_N", 16.32, 29.9, 0.5)
    T("BTN_N", F, 0.2, (16.32, 29.9), "SW1.1")
    drop("GND", "SW1.2", 20.68, 33.2)

    T("BAT_ADC", F, 0.2, "U1.9", (9.6, 13.65)); VIA("BAT_ADC", 9.6, 13.65, 0.5)
    T("BAT_ADC", B, 0.2, (9.6, 13.65), (9.6, 26.0), (13.5, 29.9))
    VIA("BAT_ADC", 13.5, 29.9, 0.5)
    T("BAT_ADC", F, 0.2, (13.5, 29.9), "C6.1", "R12.1", "R11.2")

    # ------------------------------------------------------------- microphone (right strip)
    T("MIC_CLK", F, 0.2, "U1.38", "R15.1")
    T("MIC_CLK_R", F, 0.2, "R15.2", (36.0, 12.8), (36.0, 25.47), "MK1.4")
    T("MIC_PWR", F, 0.2, "U1.37", "R14.1")
    T("MIC_VDD", F, 0.25, "R14.2", (34.02, 13.65), "C10.1", "C11.1", (34.02, 24.0), "MK1.5")
    T("MIC_DATA", F, 0.2, "U1.36", (32.36, 14.5), "MK1.1")
    T("GND", F, 0.25, "C10.2", "C11.2", (35.1, 23.85)); VIA("GND", 35.1, 23.85, 0.5)
    drop("GND", "MK1.2", 31.3, 25.47)
    # The port ground ring is four separate pads in the vendor land pattern: tie each one to ground
    T("GND", F, 0.2, "MK1.2", (32.3, 26.3), (32.57, 26.73))
    T("GND", F, 0.2, "MK1.2", (33.19, 25.47), (33.19, 26.09))
    T("GND", F, 0.2, (33.83, 26.72), (34.6, 26.72), (34.6, 28.2))
    T("GND", F, 0.2, (33.21, 27.35), (33.21, 28.2), (34.6, 28.2)); VIA("GND", 34.6, 28.2, 0.5)

    # ------------------------------------------------------------- clip flash U6
    T("FLASH_SCK", F, 0.2, "U1.16", (12.55, 20.9), (13.0, 21.35), (13.0, 25.69), (12.55, 26.135), "U6.6")
    T("FLASH_MOSI", F, 0.2, "U1.17", (13.4, 20.9), (13.6, 21.1), (13.6, 27.0), (13.2, 27.405), "U6.5")
    T("FLASH_MISO", F, 0.2, "U1.14", (3.8, 17.9), (3.8, 24.865), "U6.2")
    T("FLASH_CS", F, 0.2, "U1.15", (4.4, 18.75), (4.4, 23.595), "U6.1")
    T("FLASH_CS", F, 0.2, "R16.2", (9.0, 18.75))
    T("FLASH_HOLD", F, 0.2, "U6.7", "R19.2")
    T("FLASH_WP", F, 0.2, "U6.3", "R18.2")
    drop("+3V3", "R16.1", 8.0, 20.26)
    T("+3V3", F, 0.25, "C12.1", (10.7, 22.6), "U6.8", "R19.1")
    T("+3V3", F, 0.25, (10.7, 22.6), (11.2, 22.3)); VIA("+3V3", 11.2, 22.3, 0.5)
    drop("+3V3", "R18.1", 1.9, 26.135)
    drop("GND", "C12.2", 8.3, 21.8)
    drop("GND", "U6.4", 4.2, 27.9)
    VIA("GND", 8.0, 25.5, 0.5)                                   # U6 exposed pad

    # ------------------------------------------------------------- power-status trio, left of SW1
    T("BAT_SENSE_EN", F, 0.2, "U1.20", (15.95, 20.9), (14.3, 22.55), (14.3, 38.95), "Q3.1")
    T("BAT_SENSE_EN", F, 0.2, (14.3, 38.95), (14.3, 40.2), "R10.1")
    T("CHG_STAT_N", F, 0.2, "U1.21", (16.8, 20.9), (14.8, 22.9), (14.8, 44.9), "U3.1")
    T("VBUS_DET", F, 0.2, "U1.22", (17.65, 20.9), (15.3, 23.25), (15.3, 33.6), (15.9, 34.2),
      (19.0, 34.2), (19.585, 34.785), (19.585, 44.0))
    T("VBUS_DET", F, 0.2, "R6.1", "R5.2")

    # ------------------------------------------------------------- USB
    T("USB_DN", F, 0.2, "U1.23", (18.5, 21.0), (22.4, 24.9), (22.4, 38.6), (21.7, 39.3), (21.7, 42.45),
      "U2.6", "U2.1", (26.4, 42.45), (26.6, 42.25), "J1.B7")
    T("USB_DN", F, 0.2, "J1.A7", (31.4, 41.25), (31.4, 42.25), "J1.B7")
    T("USB_DP", F, 0.2, "U1.24", (19.35, 20.6), (23.0, 24.25), (23.0, 40.1), "U2.4", "U2.3",
      (26.4, 40.55), (26.6, 40.75), "J1.B6")
    T("USB_DP", F, 0.2, (29.1, 40.75), (29.1, 41.75), "J1.A6")
    T("CC1", F, 0.2, "J1.A5", (28.2, 42.75), (27.4, 43.55), "R1.1")
    T("CC2", F, 0.2, "J1.B5", (28.2, 39.75), (27.6, 39.2), "R2.1")
    drop("GND", "R1.2", 26.09, 44.8)
    drop("GND", "R2.2", 26.09, 38.2)
    drop("GND", "U2.2", 26.3, 41.5)
    T("GND", F, 0.3, "J1.B1", (28.9, 38.25), (28.3, 37.7)); VIA("GND", 28.3, 37.7)
    T("GND", F, 0.3, "J1.A1", (28.9, 44.75), (28.3, 45.3)); VIA("GND", 28.3, 45.3)

    # VBUS: both connector pad pairs to vias, trunk on the back to U2, the divider and the charger
    T("VBUS", F, 0.3, "J1.B4", (28.7, 39.05), (28.7, 38.95)); VIA("VBUS", 28.7, 38.95)
    T("VBUS", F, 0.3, "J1.A4", (28.7, 43.95), (28.7, 44.05)); VIA("VBUS", 28.7, 44.05)
    T("VBUS", B, 0.4, (28.7, 38.95), (28.7, 44.05))
    T("VBUS", B, 0.4, (28.7, 43.0), (22.9, 43.0), (22.0, 43.9), (22.0, 46.6), (18.0, 46.6))
    T("VBUS", B, 0.3, (24.0, 43.0), (24.0, 41.5))
    T("VBUS", F, 0.25, "U2.5", (24.0, 41.5)); VIA("VBUS", 24.0, 41.5, 0.5)
    T("VBUS", F, 0.25, "R5.1", (22.0, 44.0)); VIA("VBUS", 22.0, 44.0, 0.5)
    VIA("VBUS", 18.0, 46.6)
    T("VBUS", F, 0.4, (18.0, 46.6), (18.0, 47.45))
    T("VBUS", F, 0.4, "U3.4", "C1.1")
    drop("GND", "R6.2", 17.2, 44.0)

    # ------------------------------------------------------------- charger
    T("CHG_PROG", F, 0.2, "U3.5", "R3.1")
    drop("GND", "R3.2", 20.6, 45.4)
    drop("GND", "U3.2", 16.0, 46.5)                              # under the SOT-23-5 body
    T("GND", F, 0.3, "C1.2", (21.4, 47.6)); VIA("GND", 21.4, 47.6)
    T("+BATT", F, 0.4, "U3.3", "C2.1", (13.075, 48.6)); VIA("+BATT", 13.075, 48.6)
    T("GND", F, 0.3, "C2.2", (10.6, 47.45)); VIA("GND", 10.6, 47.45)

    # ------------------------------------------------------------- LDO (fed along the bottom)
    T("+BATT", F, 0.4, (13.075, 48.6), (13.225, 48.75), (22.5, 48.75), "C4.1", "U5.1")
    T("+BATT", F, 0.25, (23.8, 48.72), (23.8, 50.55), "U5.3")
    drop("GND", "U5.2", 26.0, 49.6)                              # under the body
    T("GND", F, 0.3, "C4.2", (21.4, 50.4)); VIA("GND", 21.4, 50.4)
    T("+3V3", F, 0.4, "U5.5", "C5.1")
    T("+3V3", F, 0.4, (28.0, 48.65), (28.0, 49.7)); VIA("+3V3", 28.0, 49.7)
    T("GND", F, 0.3, "C5.2", (31.5, 48.65)); VIA("GND", 31.5, 48.65)

    # ------------------------------------------------------------- cell protection
    T("PROT_OD", F, 0.2, "U4.1", "Q1.6")
    T("BAT_N", F, 0.4, "U4.6", "Q1.1")
    VIA("BAT_N", 2.862, 44.25)                                   # to BT2 on the back
    T("BAT_N", F, 0.25, "C3.2", "U4.6")
    T("PROT_OC", F, 0.2, "U4.3", (8.2, 41.05), (8.2, 47.45), "Q1.4")
    T("PROT_VM", F, 0.2, "U4.2", "R8.1")
    drop("GND", "R8.2", 6.9, 44.0)
    T("PROT_VCC", F, 0.2, "U4.5", "C3.1", "R7.2")
    T("PROT_D", F, 0.4, "Q1.2", "Q1.5")
    T("GND", F, 0.4, "Q1.3", (1.5, 47.45)); VIA("GND", 1.5, 47.45)

    # ------------------------------------------------------------- battery sense
    T("BSENSE_G", F, 0.2, "Q3.3", (7.7, 38.0), (7.7, 32.55), "Q2.1")
    T("BSENSE_G", F, 0.2, (7.7, 32.55), "R9.2")
    T("BSENSE_SW", F, 0.2, "Q2.3", "R11.1")
    T("GND", F, 0.25, "C6.2", "R12.2", (11.6, 31.55)); VIA("GND", 11.6, 31.55, 0.5)
    drop("GND", "Q3.2", 12.3, 37.05)
    drop("GND", "R10.2", 12.39, 41.2)

    # ------------------------------------------------------------- +BATT distribution
    T("+BATT", F, 0.3, "R7.1", (1.1, 34.57), (2.1, 33.57), "R9.1")
    VIA("+BATT", 5.6, 33.57)
    T("+BATT", F, 0.3, "Q2.2", (8.962, 35.6)); VIA("+BATT", 8.962, 35.6)
    T("+BATT", B, 0.4, (10.8, 43.6), (10.6, 43.0), (10.6, 36.8), (9.4, 35.6), (8.962, 35.6),
      (6.932, 33.57), (5.6, 33.57))
    T("+BATT", B, 0.4, (12.2, 45.6), (13.075, 46.7), (13.075, 48.6))
    T("+BATT", B, 0.3, (10.5, 45.6), (8.1, 48.0), "TP7.1")

    stitch(r)
    add_zones(r)


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def stitch(r, step=3.0, via_r=0.25, gap=0.35):
    """GND stitching vias on a grid wherever there is clear space on every layer
    (not under any part or back-side pad, clear of every non-GND track/pad/via and the mic port)."""
    b, mm = r.b, pcbnew.ToMM
    segs, pads, vias, boxes = [], [], [], []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias.append((mm(t.GetPosition().x) - OX, mm(t.GetPosition().y) - OY, mm(t.GetWidth(pcbnew.F_Cu)) / 2))
        elif t.GetNetname() != "GND":
            segs.append((mm(t.GetStart().x) - OX, mm(t.GetStart().y) - OY, mm(t.GetEnd().x) - OX, mm(t.GetEnd().y) - OY, mm(t.GetWidth()) / 2))
    for fp in b.GetFootprints():
        if fp.GetReference() != "U1":
            for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                poly = fp.GetCourtyard(layer)
                if poly.OutlineCount():
                    bb = poly.BBox()
                    boxes.append((mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY))
        for pd in fp.Pads():
            bb = pd.GetBoundingBox()
            pads.append((mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY, pd.GetNetname() == "GND"))
    boxes.append((10.55, 0.0, 26.45, 20.74))                    # module body
    n = 0
    y = ANTENNA_Y + 1.2
    while y <= H - 1.2:
        x = 1.4
        while x <= W - 1.2:
            ok = (not any(x0 - 0.3 <= x <= x1 + 0.3 and y0 - 0.3 <= y <= y1 + 0.3 for x0, y0, x1, y1 in boxes)
                  and all(_seg_dist(x, y, ax, ay, bx, by) >= w + via_r + gap for ax, ay, bx, by, w in segs)
                  and all(max(x0 - x, 0, x - x1) ** 2 + max(y0 - y, 0, y - y1) ** 2 >= (via_r + gap) ** 2
                          for x0, y0, x1, y1, g in pads if not g)
                  and all((x - vx) ** 2 + (y - vy) ** 2 >= (via_r + vr + gap) ** 2 for vx, vy, vr in vias))
            if ok:
                r.VIA("GND", x, y, 0.5)
                vias.append((x, y, via_r))
                n += 1
            x += step
        y += step
    print(f"stitching vias: {n}")


def add_zones(r):
    b = r.b
    for layer, net in ((F, "GND"), (pcbnew.In1_Cu, "GND"), (pcbnew.In2_Cu, "+3V3"), (B, "GND")):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(r.net(net))
        z.SetLocalClearance(pcbnew.FromMM(0.2))
        z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetThermalReliefGap(pcbnew.FromMM(0.25))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0.0, 0.0), (W, 0.0), (W, H), (0.0, H)):
            ol.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
        b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
