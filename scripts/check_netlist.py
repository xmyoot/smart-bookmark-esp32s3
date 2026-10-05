"""Verify the exported netlist against docs/design_spec.md (pin map + key circuits).
The table below is typed from the datasheet pinouts, independently of gen_schematic.py.
Usage: python scripts/check_netlist.py build/bookmark.net"""
import re, sys
txt = open(sys.argv[1] if len(sys.argv) > 1 else "build/bookmark.net", encoding="utf-8").read()
pin_net = {}
txt = re.sub(r"\s+", " ", txt[txt.index("(nets"):])
for blk in re.split(r'\(net \(code', txt)[1:]:
    name = re.search(r'\(name "([^"]*)"\)', blk).group(1).split("/")[-1]
    for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', blk):
        pin_net[f"{ref}.{pin}"] = name
exp = {
 # U1 ESP32-S3-MINI-1 (module datasheet table 3-1: pin number -> GPIO)
 "U1.3": "+3V3", "U1.45": "EN", "U1.4": "BOOT", "U1.5": "BTN_N", "U1.6": "LED",
 "U1.9": "BAT_ADC", "U1.20": "BAT_SENSE_EN", "U1.21": "CHG_STAT_N", "U1.22": "VBUS_DET",
 "U1.14": "FLASH_MISO", "U1.15": "FLASH_CS", "U1.16": "FLASH_SCK", "U1.17": "FLASH_MOSI",
 "U1.23": "USB_DN", "U1.24": "USB_DP", "U1.36": "MIC_DATA", "U1.37": "MIC_PWR", "U1.38": "MIC_CLK",
 "U1.39": "UART_TX", "U1.40": "UART_RX",
 # J1 USB-C
 "J1.A4": "VBUS", "J1.A9": "VBUS", "J1.B4": "VBUS", "J1.B9": "VBUS",
 "J1.A1": "GND", "J1.A12": "GND", "J1.B1": "GND", "J1.B12": "GND", "J1.SH": "GND",
 "J1.A5": "CC1", "J1.B5": "CC2", "J1.A6": "USB_DP", "J1.B6": "USB_DP", "J1.A7": "USB_DN", "J1.B7": "USB_DN",
 "R1.1": "CC1", "R1.2": "GND", "R2.1": "CC2", "R2.2": "GND",
 "U2.1": "USB_DN", "U2.6": "USB_DN", "U2.3": "USB_DP", "U2.4": "USB_DP", "U2.5": "VBUS", "U2.2": "GND",
 # U3 MCP73832 (1 STAT 2 VSS 3 VBAT 4 VDD 5 PROG)
 "U3.1": "CHG_STAT_N", "U3.2": "GND", "U3.3": "+BATT", "U3.4": "VBUS", "U3.5": "CHG_PROG",
 "R3.1": "CHG_PROG", "R3.2": "GND",
 "R5.1": "VBUS", "R5.2": "VBUS_DET", "R6.1": "VBUS_DET", "R6.2": "GND",
 # U4 DW01A (1 OD 2 VM 3 OC 4 TD 5 VCC 6 GND) + Q1 FS8205A (1 S1 2 D 3 S2 4 G2 5 D 6 G1)
 "U4.1": "PROT_OD", "U4.2": "PROT_VM", "U4.3": "PROT_OC", "U4.5": "PROT_VCC", "U4.6": "BAT_N",
 "Q1.1": "BAT_N", "Q1.6": "PROT_OD", "Q1.2": "PROT_D", "Q1.5": "PROT_D", "Q1.3": "GND", "Q1.4": "PROT_OC",
 "R7.1": "+BATT", "R7.2": "PROT_VCC", "C3.1": "PROT_VCC", "C3.2": "BAT_N", "R8.1": "PROT_VM", "R8.2": "GND",
 "BT1.1": "+BATT", "BT2.1": "BAT_N",
 # U5 RT9080 (1 VIN 2 GND 3 EN 5 VOUT)
 "U5.1": "+BATT", "U5.2": "GND", "U5.3": "+BATT", "U5.5": "+3V3",
 # battery sense: Q2 AO3401A / Q3 2N7002 (1 G 2 S 3 D)
 "Q2.1": "BSENSE_G", "Q2.2": "+BATT", "Q2.3": "BSENSE_SW", "R9.1": "+BATT", "R9.2": "BSENSE_G",
 "Q3.1": "BAT_SENSE_EN", "Q3.2": "GND", "Q3.3": "BSENSE_G", "R10.1": "BAT_SENSE_EN", "R10.2": "GND",
 "R11.1": "BSENSE_SW", "R11.2": "BAT_ADC", "R12.1": "BAT_ADC", "R12.2": "GND", "C6.1": "BAT_ADC",
 # MK1 T3902 (1 DATA 2 SELECT 3 GND 4 CLK 5 VDD)
 "MK1.1": "MIC_DATA", "MK1.2": "GND", "MK1.3": "GND", "MK1.4": "MIC_CLK_R", "MK1.5": "MIC_VDD",
 "R14.1": "MIC_PWR", "R14.2": "MIC_VDD", "R15.1": "MIC_CLK", "R15.2": "MIC_CLK_R", "C11.1": "MIC_VDD",
 # U6 W25Q128JV (1 CS 2 DO 3 WP 4 GND 5 DI 6 CLK 7 HOLD 8 VCC)
 "U6.1": "FLASH_CS", "U6.2": "FLASH_MISO", "U6.3": "FLASH_WP", "U6.4": "GND", "U6.5": "FLASH_MOSI",
 "U6.6": "FLASH_SCK", "U6.7": "FLASH_HOLD", "U6.8": "+3V3",
 # UI + test pads
 "SW1.1": "BTN_N", "SW1.2": "GND", "R17.1": "LED", "R17.2": "LED_A", "D1.2": "LED_A", "D1.1": "GND",
 "R13.1": "+3V3", "R13.2": "EN", "C9.1": "EN", "C9.2": "GND",
 "TP1.1": "+3V3", "TP2.1": "GND", "TP3.1": "EN", "TP4.1": "BOOT", "TP5.1": "UART_TX", "TP6.1": "UART_RX",
 "TP7.1": "+BATT",
}
for gp in [1, 2, 42, 43] + list(range(46, 66)):   # every module ground pad
    exp[f"U1.{gp}"] = "GND"
bad = [(k, v, pin_net.get(k)) for k, v in exp.items() if pin_net.get(k) != v]
used = {int(k.split(".")[1]) for k in exp if k.startswith("U1.")}
nc_bad = [p for p in range(1, 66) if p not in used and not pin_net.get(f"U1.{p}", "unconnected").startswith("unconnected")]
for b in bad: print("MISMATCH", b)
for p in nc_bad: print("U1 pin should be NC:", p, pin_net[f"U1.{p}"])
nets = {}
for k, v in pin_net.items(): nets.setdefault(v, []).append(k)
single = [n for n, ps in nets.items() if len(ps) < 2 and not n.startswith("unconnected")]
print("single-pin nets:", single)
print(f"checked {len(exp)} pins, {len(bad)} mismatches, {len(nc_bad)} NC errors, {len(nets)} nets")
sys.exit(1 if bad or nc_bad or single else 0)
