# Reference circuits

The application circuit each IC is built to, where it comes from, and any deviation. Datasheets
(PDF and extracted text) are in `datasheets/`; `scripts/fetch_datasheets.py` re-downloads them.

## U1 ESP32-S3-MINI-1-N8 — `esp32-s3-mini-1_datasheet.pdf`

- Pin numbers: table 3-1 (pp. 11–12). Checked pin by pin in `scripts/check_netlist.py`.
- Supply: 3V3 on pin 3 with bulk plus 0.1 µF (fig. 9-1). Here C7 22 µF and C8 100 nF.
- EN: RC delay R = 10 kΩ, C = 1 µF (section 9 note). Here R13, C9.
- Straps (table 4-1): GPIO0 weak pull-up, GPIO3 floating, GPIO45 and GPIO46 weak pull-down. All
  four are left at their defaults; GPIO0 goes only to test pad TP4.
- USB: GPIO19 = D−, GPIO20 = D+ direct to the connector through U2. No series resistors.
- Antenna: the footprint carries a no-copper rule area on every layer.

## MK1 T3902 — `T3902.pdf`

- Pins (table 9): 1 DATA, 2 SELECT, 3 GND, 4 CLK, 5 VDD.
- 0.1 µF X7R at pin 5 (table 9 note). Here C11 100 nF, plus C10 1 µF.
- SELECT to GND: data on the "DATA 1 (right)" slot.
- Clock 400 kHz–4.8 MHz depending on mode; below 200 kHz the part sleeps at 12 µA (table 1).
- PCB sound hole 0.5–1 mm, never smaller than 0.375 mm; no paste on the hole (p. 18).
- **Deviation:** VDD is fed from GPIO41 through R14 (100 Ω) instead of the 3V3 rail, so the mic
  is fully off in deep sleep. 0.65 mA through 100 Ω drops 65 mV. R15 (33 Ω) is a source
  termination on the clock.
- Footprint: LCSC/EasyEDA land pattern for this exact part number. **Check it against the
  datasheet drawing on the first article**; the datasheet figure is an image and was not
  machine-readable here.

## U3 MCP73832T-2ACI/OT — `MCP73831.pdf`

- Pins: 1 STAT, 2 VSS, 3 VBAT, 4 VDD, 5 PROG.
- Typical application (p. 1): 4.7 µF on VDD and on VBAT, PROG resistor to VSS.
  Here C1 and C2 are 10 µF 0603 (about 4 µF at bias).
- I_REG = 1000 V / R_PROG: 10 kΩ gives 100 mA (table 1: 90–110 mA).
- STAT on the MCP73832 is open-drain (section 3.3): low while charging. Read with the MCU's
  internal pull-up; no external resistor.
- "-2AC" option: 4.20 V, termination at 7.5 % of I_REG.

## U4 DW01A + Q1 FS8205A — `DW01A.pdf`, `FS8205A.pdf`

- Typical application (DW01A p. 3): R1 100 Ω from BATT+ to VCC, C1 0.1 µF from VCC to cell
  negative, R2 1 kΩ from VM to pack negative, OD and OC to the two gates. Here R7, C3, R8.
- DW01A pins: 1 OD, 2 VM, 3 OC, 4 TD (open), 5 VCC, 6 GND (cell negative).
- FS8205A pins: 1 S1, 2 and 5 common drain, 3 S2, 4 G2, 6 G1. S1 and G1 (OD) on the cell side,
  S2 and G2 (OC) on the system-ground side.
- Thresholds: over-charge 4.30 V, over-discharge 2.50 V, release 2.90 V, over-current 150 mV
  across Q1 (several amps with a 25 mΩ pair, so in practice this is short-circuit protection).

## U5 RT9080-33GJ5 — `RT9080.pdf`

- Pins (TSOT-23-5): 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT.
- At least 1 µF effective on input and output. Here C4 and C5, 10 µF 0603.
- EN tied to VIN: always on.

## U2 USBLC6-2SC6 — `USBLC6-2.pdf`

- Pins: 1 and 6 I/O1, 3 and 4 I/O2, 2 GND, 5 VBUS. D− passes through 1/6, D+ through 3/4.

## J1 USB-C

- 5.1 kΩ from each CC pin to GND (R1, R2): identifies a sink to any USB-C source.
- A6/B6 joined as D+, A7/B7 joined as D−, SBU pins open, shell to GND.

## Battery sense (discrete)

- Q2 AO3401A high-side switch, gate held off by R9 (1 MΩ) to +BATT. Q3 2N7002 pulls the gate low
  when BAT_SENSE_EN is high; R10 (100 kΩ) keeps Q3 off while the MCU pin floats in deep sleep.
- R11 / R12 100 kΩ, C6 100 nF: 21 µA only while a reading is taken.
