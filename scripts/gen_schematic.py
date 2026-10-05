"""Generate the smart-bookmark-esp32s3 KiCad 10 schematic (root + 6 hierarchical sheets).

The circuit below is the source of truth and mirrors docs/design_spec.md and
docs/reference_designs.md. Run with any Python 3:  python scripts/gen_schematic.py
"""
from sch_engine import (LABEL_JUST, PROJ, ROOT_DIR, ROOT_UUID, Sheet, eff, fmt, pins_of, uid)

FP = dict(
    R0402="Resistor_SMD:R_0402_1005Metric", C0402="Capacitor_SMD:C_0402_1005Metric",
    C0603="Capacitor_SMD:C_0603_1608Metric", C0805="Capacitor_SMD:C_0805_2012Metric",
    LED0603="LED_SMD:LED_0603_1608Metric", SOT23="Package_TO_SOT_SMD:SOT-23",
    SOT235="Package_TO_SOT_SMD:SOT-23-5", TSOT235="Package_TO_SOT_SMD:TSOT-23-5",
    SOT236="Package_TO_SOT_SMD:SOT-23-6",
    TP="TestPoint:TestPoint_Pad_D1.5mm", BATPAD="TestPoint:TestPoint_Pad_2.5x2.5mm",
)
CAP = {  # value -> (footprint, LCSC, MPN)   all JLCPCB basic parts
    "100nF": (FP["C0402"], "C1525", "CL05B104KO5NNNC"),
    "1uF": (FP["C0402"], "C52923", "CL05A105KA5NQNC"),
    "10uF": (FP["C0603"], "C19702", "CL10A106KP8NNNC"),
    "22uF": (FP["C0805"], "C45783", "CL21A226MAQNNNE"),
}
RES = {  # 0402 1 %, all JLCPCB basic parts
    "33": ("C25105", "0402WGF330JTCE"), "100": ("C25076", "0402WGF1000TCE"),
    "1k": ("C11702", "0402WGF1001TCE"), "5.1k": ("C25905", "0402WGF5101TCE"),
    "10k": ("C25744", "0402WGF1002TCE"), "100k": ("C25741", "0402WGF1003TCE"),
    "1M": ("C26083", "0402WGF1004TCE"),
}


def C(sh, ref, val, x, y, n1, n2, dnp=False):
    fp, lcsc, mpn = CAP[val]
    sh.part(ref, "Device:C", val, x, y, {"1": n1, "2": n2}, footprint=fp, lcsc=lcsc, mpn=mpn,
            dnp=dnp, in_bom=not dnp, pos=not dnp)


def R(sh, ref, val, x, y, n1, n2, r=0, dnp=False):
    lcsc, mpn = RES[val]
    sh.part(ref, "Device:R", val, x, y, {"1": n1, "2": n2}, r=r, footprint=FP["R0402"], lcsc=lcsc, mpn=mpn,
            dnp=dnp, in_bom=not dnp, pos=not dnp)


def TP(sh, ref, name, x, y, net, fp="TP"):
    sh.part(ref, "Connector:TestPoint", name, x, y, {"1": net}, footprint=FP[fp], in_bom=False, pos=False)


# ---- usb --------------------------------------------------------------------
usb = Sheet("usb", "USB-C input, CC, ESD", ["USB_DP", "USB_DN"])
usb.box(20.32, 45.72, 280, 150, "J1 USB-C (charge + native USB flashing/logs on GPIO19/20). 5.1k on each CC = sink, 5 V default current")
usb.part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C 16P", 60.96, 96.52,
         {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
          "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2",
          "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN", "A8": "NC", "B8": "NC"},
         footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", lcsc="C165948", mpn="TYPE-C-31-M-12")
R(usb, "R1", "5.1k", 111.76, 86.36, "CC1", "GND")
R(usb, "R2", "5.1k", 127, 86.36, "CC2", "GND")
usb.part("U2", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", 172.72, 96.52,
         {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "5": "VBUS", "2": "GND"},
         footprint=FP["SOT236"], lcsc="C7519", mpn="USBLC6-2SC6")
C(usb, "C1", "10uF", 218.44, 96.52, "VBUS", "GND")
usb.flag("VBUS", 248.92, 68.58)
usb.text("U2 next to J1, D+/D- routed through its pads. C1 is the only bulk on VBUS (USB limit 10 uF).", 25.4, 144.78)

# ---- power ------------------------------------------------------------------
power = Sheet("power", "Charger, cell protection, 3V3 LDO, battery sense",
              ["VBUS_DET", "CHG_STAT_N", "BAT_ADC", "BAT_SENSE_EN"])
p = power
p.box(15.24, 20.32, 185.42, 78.74, "U3 charger: 4.2 V, Ichg = 1000 V / R3 = 100 mA. STAT open-drain, low = charging (MCU pull-up). R5/R6 = USB-present sense")
p.part("U3", "bookmark:MCP73832T-2ACI_OT", "MCP73832T-2ACI/OT", 55.88, 43.18,
       {"1": "CHG_STAT_N", "2": "GND", "3": "+BATT", "4": "VBUS", "5": "CHG_PROG"},
       footprint=FP["SOT235"], lcsc="C38066", mpn="MCP73832T-2ACI/OT")
R(p, "R3", "10k", 99.06, 60.96, "CHG_PROG", "GND")
C(p, "C2", "10uF", 114.3, 60.96, "+BATT", "GND")
R(p, "R5", "100k", 152.4, 60.96, "VBUS", "VBUS_DET")
R(p, "R6", "100k", 170.18, 60.96, "VBUS_DET", "GND")

p.box(193.04, 20.32, 284.48, 78.74, "U5 3V3 LDO, 2 uA Iq, always on (EN = +BATT)")
p.part("U5", "bookmark:RT9080-33GJ5", "RT9080-33GJ5", 233.68, 40.64,
       {"1": "+BATT", "2": "GND", "3": "+BATT", "4": "NC", "5": "+3V3"},
       footprint=FP["TSOT235"], lcsc="C841192", mpn="RT9080-33GJ5")
C(p, "C4", "10uF", 218.44, 63.5, "+BATT", "GND")
C(p, "C5", "10uF", 259.08, 63.5, "+3V3", "GND")

p.box(15.24, 88.9, 240.03, 129.54, "Cell protection in the negative leg: BT2 (cell -) = BAT_N -> Q1 -> GND. 2.5 V cut-off, 4.3 V over-charge, short-circuit")
TP(p, "BT1", "BAT+", 27.94, 111.76, "+BATT", fp="BATPAD")
TP(p, "BT2", "BAT-", 43.18, 111.76, "BAT_N", fp="BATPAD")
p.part("U4", "bookmark:DW01A_C351410", "DW01A", 86.36, 109.22,
       {"1": "PROT_OD", "2": "PROT_VM", "3": "PROT_OC", "4": "NC", "5": "PROT_VCC", "6": "BAT_N"},
       footprint=FP["SOT236"], lcsc="C351410", mpn="DW01A")
p.part("Q1", "bookmark:FS8205A_C908265", "FS8205A", 149.86, 109.22,
       {"1": "BAT_N", "2": "PROT_D", "5": "PROT_D", "3": "GND", "4": "PROT_OC", "6": "PROT_OD"},
       footprint=FP["SOT236"], lcsc="C908265", mpn="FS8205A")
R(p, "R7", "100", 193.04, 111.76, "+BATT", "PROT_VCC")
C(p, "C3", "100nF", 208.28, 111.76, "PROT_VCC", "BAT_N")
R(p, "R8", "1k", 223.52, 111.76, "PROT_VM", "GND")

p.box(15.24, 139.7, 173.99, 182.88, "Battery sense: BAT_SENSE_EN high -> Q3 on -> Q2 on -> +BATT / 2 on BAT_ADC (ADC1). Off = no divider current")
p.part("Q2", "Transistor_FET:AO3401A", "AO3401A", 45.72, 160.02, {"1": "BSENSE_G", "2": "+BATT", "3": "BSENSE_SW"},
       footprint=FP["SOT23"], lcsc="C15127", mpn="AO3401A")
R(p, "R9", "1M", 63.5, 162.56, "+BATT", "BSENSE_G")
p.part("Q3", "Transistor_FET:2N7002", "2N7002", 93.98, 160.02, {"1": "BAT_SENSE_EN", "2": "GND", "3": "BSENSE_G"},
       footprint=FP["SOT23"], lcsc="C8545", mpn="2N7002")
R(p, "R10", "100k", 119.38, 162.56, "BAT_SENSE_EN", "GND")
R(p, "R11", "100k", 137.16, 162.56, "BSENSE_SW", "BAT_ADC")
R(p, "R12", "100k", 152.4, 162.56, "BAT_ADC", "GND")
C(p, "C6", "100nF", 165.1, 162.56, "BAT_ADC", "GND")
p.flag("+BATT", 254, 101.6)
p.flag("GND", 266.7, 101.6)
p.flag("+3V3", 279.4, 101.6)
p.text("Load sits on the cell (no power path): firmware sleeps when idle", 182.88, 147.32)
p.text("on USB so the charge current can fall to the termination level.", 182.88, 152.4)

# ---- mcu --------------------------------------------------------------------
MCU_IO = {  # module pin name -> net. Chosen so every group leaves the module on the side its parts sit on
    "3V3": "+3V3", "EN": "EN", "IO0": "BOOT",
    "IO1": "BTN_N", "IO2": "LED",                         # same GPIOs as the XIAO prototype (D0, D1)
    "IO5": "BAT_ADC",                                     # ADC1_CH4
    "IO10": "FLASH_MISO", "IO11": "FLASH_CS", "IO12": "FLASH_SCK", "IO13": "FLASH_MOSI",
    "IO16": "BAT_SENSE_EN", "IO17": "CHG_STAT_N", "IO18": "VBUS_DET",   # RTC GPIOs: USB plug can wake
    "USB_D-": "USB_DN", "USB_D+": "USB_DP",
    "IO40": "MIC_DATA", "IO41": "MIC_PWR", "IO42": "MIC_CLK",
    "TXD0": "UART_TX", "RXD0": "UART_RX",
}
MCU_HIER = [n for n in MCU_IO.values() if n != "+3V3"]
mcu = Sheet("mcu", "ESP32-S3-MINI-1-N8", MCU_HIER)
mcu.box(96.52, 40.64, 200.66, 170.18, "U1 ESP32-S3-MINI-1-N8. Straps: IO0 pull-up (BOOT pad), IO3 float, IO45/IO46 internal pull-down - all left open")
mcu.part("U1", "RF_Module:ESP32-S3-MINI-1", "ESP32-S3-MINI-1-N8", 148.59, 105.41,
         {num: "GND" if pin["name"] == "GND" else MCU_IO.get(pin["name"], "NC")
          for num, pin in pins_of("RF_Module:ESP32-S3-MINI-1").items()},
         footprint="RF_Module:ESP32-S2-MINI-1", lcsc="C2913206", mpn="ESP32-S3-MINI-1-N8")
mcu.box(20.32, 40.64, 86.36, 86.36, "3V3 decoupling at module pin 3")
C(mcu, "C7", "22uF", 40.64, 63.5, "+3V3", "GND")
C(mcu, "C8", "100nF", 60.96, 63.5, "+3V3", "GND")
mcu.box(20.32, 99.06, 86.36, 144.78, "EN power-up delay: 10k / 1 uF")
R(mcu, "R13", "10k", 40.64, 121.92, "+3V3", "EN")
C(mcu, "C9", "1uF", 60.96, 121.92, "EN", "GND")

# ---- audio ------------------------------------------------------------------
audio = Sheet("audio", "PDM MEMS microphone", ["MIC_PWR", "MIC_CLK", "MIC_DATA"])
audio.box(40.64, 60.96, 248.92, 144.78, "MK1 T3902 bottom-port PDM mic, powered from a GPIO (MIC_PWR) so it draws nothing in deep sleep")
audio.part("MK1", "bookmark:MMICT390200012", "T3902", 149.86, 99.06,
           {"1": "MIC_DATA", "2": "GND", "3": "GND", "4": "MIC_CLK_R", "5": "MIC_VDD"},
           footprint="bookmark:MIC-SMD_5P-L3.5-W2.7-TL_MMICT390200012", lcsc="C3171752", mpn="MMICT390200012")
R(audio, "R14", "100", 71.12, 83.82, "MIC_PWR", "MIC_VDD")
R(audio, "R15", "33", 71.12, 116.84, "MIC_CLK", "MIC_CLK_R")
C(audio, "C10", "1uF", 200.66, 106.68, "MIC_VDD", "GND")
C(audio, "C11", "100nF", 220.98, 106.68, "MIC_VDD", "GND")
audio.text("SELECT = GND: data valid after the CLK rising edge (right slot). C11 at pin 5. PCB port hole 0.8 mm under the mic.", 45.72, 139.7)

# ---- storage ----------------------------------------------------------------
storage = Sheet("storage", "Optional external SPI flash (DNP)", ["FLASH_CS", "FLASH_MOSI", "FLASH_SCK", "FLASH_MISO"])
storage.box(60.96, 55.88, 248.92, 149.86, "U6 optional 16 MB NOR on SPI2 (FSPI pins). NOT FITTED by default: clips live on the module's 8 MB flash")
storage.part("U6", "Memory_Flash:W25Q128JVP", "W25Q128JVPIQ", 149.86, 101.6,
             {"1": "FLASH_CS", "2": "FLASH_MISO", "3": "FLASH_WP", "4": "GND", "5": "FLASH_MOSI", "6": "FLASH_SCK",
              "7": "FLASH_HOLD", "8": "+3V3", "9": "GND"},
             footprint="Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4.3mm", lcsc="C190862", mpn="W25Q128JVPIQ",
             dnp=True, in_bom=False, pos=False)
C(storage, "C12", "100nF", 205.74, 101.6, "+3V3", "GND", dnp=True)
R(storage, "R16", "100k", 226.06, 101.6, "+3V3", "FLASH_CS", dnp=True)
R(storage, "R18", "10k", 86.36, 124.46, "+3V3", "FLASH_WP", dnp=True)
R(storage, "R19", "10k", 104.14, 124.46, "+3V3", "FLASH_HOLD", dnp=True)

# ---- ui_test ----------------------------------------------------------------
ui = Sheet("ui_test", "Button, LED, test pads", ["BTN_N", "LED", "EN", "BOOT", "UART_TX", "UART_RX"])
ui.box(30.48, 55.88, 132.08, 104.14, "SW1 record button to GND (internal pull-up, deep-sleep wake on low)")
ui.part("SW1", "bookmark:TS-1088-AR02016", "TS-1088-AR02016", 78.74, 81.28, {"1": "BTN_N", "2": "GND"},
        footprint="bookmark:SW-SMD_L3.9-W3.0-P4.45", lcsc="C720477", mpn="TS-1088-AR02016")
ui.box(30.48, 116.84, 132.08, 160.02, "D1 status LED, active high, about 1.3 mA")
R(ui, "R17", "1k", 60.96, 137.16, "LED", "LED_A")
ui.part("D1", "Device:LED", "RED", 99.06, 137.16, {"1": "GND", "2": "LED_A"},
        footprint=FP["LED0603"], lcsc="C2286", mpn="KT-0603R")
ui.box(144.78, 55.88, 271.78, 104.14, "Factory programming / test pads (1.5 mm, bottom side)")
for k, (ref, name, net) in enumerate([("TP1", "3V3", "+3V3"), ("TP2", "GND", "GND"), ("TP3", "EN", "EN"),
                                      ("TP4", "BOOT", "BOOT"), ("TP5", "TX", "UART_TX"), ("TP6", "RX", "UART_RX"),
                                      ("TP7", "VBAT", "+BATT")]):
    TP(ui, ref, name, 157.48 + 17.78 * k, 83.82, net)
ui.text("Hold BOOT low while pulsing EN low for ROM download mode over UART or USB.", 147.32, 100.33)

SHEETS = [mcu, usb, power, audio, storage, ui]


# ================================================================================ root
def render_root():
    items = []
    w = 50.8
    height = {sh.key: max(20.32, 2.54 * (len(sh.hier) + 3)) for sh in SHEETS}
    # mcu on the left (pins on its right edge); the peripheral sheets stacked on the right
    layout = {"mcu": (45.72, 50.8, "R")}
    ry = 35.56
    for key in ("usb", "power", "audio", "storage", "ui_test"):
        layout[key] = (190.5, ry, "L")
        ry += height[key] + 10.16
    for k, sh in enumerate(SHEETS):
        sx, sy, side = layout[sh.key]
        h = height[sh.key]
        pins = ""
        for i, net in enumerate(sh.hier):
            py = sy + 5.08 + 2.54 * i
            if side == "R":   # pin text inside the box -> right-justified on the right edge
                px, ang, pj, ex, la = sx + w, 0, "right", sx + w + 12.7, 0
            else:
                px, ang, pj, ex, la = sx, 180, "left", sx - 12.7, 180
            pins += (f'\t\t(pin "{net}" bidirectional (at {fmt(px)} {fmt(py)} {ang}) '
                     f'(uuid "{uid("root", "sp", sh.key, net)}") {eff(justify=pj)})\n')
            items.append(f'\t(wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(py)})) '
                         f'(stroke (width 0) (type default)) (uuid "{uid("root", "w", sh.key, net)}"))\n')
            items.append(f'\t(label "{net}" (at {fmt(ex)} {fmt(py)} {la}) {eff(justify=LABEL_JUST[la])} '
                         f'(uuid "{uid("root", "l", sh.key, net)}"))\n')
        items.append(
            f'\t(sheet (at {fmt(sx)} {fmt(sy)}) (size {fmt(w)} {fmt(h)}) (exclude_from_sim no) (in_bom yes) '
            f'(on_board yes) (dnp no) (fields_autoplaced yes)\n'
            f'\t\t(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0))\n'
            f'\t\t(uuid "{sh.sym_uuid}")\n'
            f'\t\t(property "Sheetname" "{sh.key}" (at {fmt(sx)} {fmt(sy - 0.71)} 0) (show_name no) (do_not_autoplace no) {eff(justify="left bottom")})\n'
            f'\t\t(property "Sheetfile" "sheets/{sh.key}.kicad_sch" (at {fmt(sx)} {fmt(sy + h + 0.59)} 0) (show_name no) (do_not_autoplace no) {eff(justify="left top")})\n'
            f'{pins}'
            f'\t\t(instances (project "{PROJ}" (path "/{ROOT_UUID}" (page "{k + 2}"))))\n\t)\n')
    notes = ("Smart bookmark voice recorder - root sheet. Power nets GND / +3V3 / VBUS / +BATT are global power symbols; "
             "signals cross sheets via hierarchical pins joined by the labels here.")
    items.append(f'\t(text "{notes}" (exclude_from_sim no) (at 25.4 25.4 0) (effects (font (size 1.5 1.5)) (justify left bottom)) '
                 f'(uuid "{uid("root", "note")}"))\n')
    return (f'(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n'
            f'\t(uuid "{ROOT_UUID}")\n\t(paper "A4")\n'
            f'\t(title_block (title "{PROJ} - root") (date "2026-10-05") (rev "A") '
            f'(company "Smart bookmark voice recorder"))\n'
            f'\t(lib_symbols)\n' + "".join(items) +
            '\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n')


def main():
    (ROOT_DIR / "sheets").mkdir(exist_ok=True)
    for sh in SHEETS:
        (ROOT_DIR / "sheets" / f"{sh.key}.kicad_sch").write_text(sh.render(), encoding="utf-8")
    (ROOT_DIR / f"{PROJ}.kicad_sch").write_text(render_root(), encoding="utf-8")
    print("wrote root +", ", ".join(s.key for s in SHEETS))


if __name__ == "__main__":
    main()
