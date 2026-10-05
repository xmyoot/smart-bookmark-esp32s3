# Build notes

Coordinates: mm from the board's top-left corner, component side, antenna end up.
Placement table: `scripts/build_pcb.py` (`TOP`, `BACK`). Pad positions: `build/placement.json`.

## 1. Stack-up and rules

| Layer | Use |
|---|---|
| F.Cu | All parts, most signals, GND pour |
| In1.Cu | Solid GND |
| In2.Cu | +3V3 plane |
| B.Cu | Battery and test pads, +BATT and VBUS trunks, the few signals that must cross; GND pour |

0.8 mm, 4 layers. Tracks 0.2 mm signal, 0.4 mm +BATT / VBUS; clearance 0.15 mm; vias 0.5 / 0.3 mm
(0.6 / 0.3 where there is room); copper to edge 0.3 mm. No copper on any layer for y < 4.55 mm
(module antenna rule area).

## 2. Why the parts sit where they do

- **U1 at the top, antenna flush with the top edge**: the head sticks out of the book, so that end
  is in free air. The antenna strip is clear across the whole board width.
- **Pins were assigned to match the floorplan** (see `design_spec.md` section 3). Left column of the
  module: 3V3, BOOT, button, LED, battery ADC, flash MISO/CS. Bottom row: flash SCK/MOSI, the three
  power-status signals, USB. Right column: mic, UART, EN.
- **J1 on the right edge, low**: clear of the cell, short USB pair to the module's bottom row.
- **MK1 at the right edge, mid-height**: outside the cell area so the port hole is open at the back,
  and fed straight down from the module's right column.
- **Protection, charger, LDO along the bottom**: next to the battery pads and the USB input.
- **Nothing assembled on the back**: lowest assembly cost and a flat surface for the cell.

## 3. Routing plan (not yet executed)

Top layer, no crossings by construction:

- **Mic** (right strip): module pin 38 → R15 → along y 12.35 → down x 36.0 → MK1 pad 4 from the right.
  Pin 37 → R14 → along y 13.2 → down x 34.04 through C10/C11 pad 1 → MK1 pad 5.
  Pin 36 → along y 14.05 → down x 32.36 → MK1 pad 1. C10/C11 ground via at about (35.1, 23.85).
- **USB**: pins 23 (D−) and 24 (D+) leave downward, 45° to x 22.4 / 23.0, straight down right of
  SW1 to U2 pads 6 / 4. Through U2 under its body to pads 1 / 3, then to J1: D+ pads B6/A6 joined by a
  U on the pad-row's left (x 29.1), D− pads A7/B7 joined by a U on the right (x 31.4).
  CC1 → R1, CC2 → R2 in the 26–29.5 mm channel. VBUS pads → vias at (28.3, 39.05) and (28.3, 43.95).
- **Power status trio** from pins 20, 21, 22 down the left of SW1 at x 14.3 / 14.8 / 15.3:
  BAT_SENSE_EN → Q3 gate and R10; CHG_STAT_N → U3 pad 1 from above; VBUS_DET → under SW1 at y 34 →
  down x 19.6 → R5/R6 junction.
- **Flash** (DNP): pins 16 / 17 down at x 13.0 / 13.5 into U6 pads 6 / 5; pins 14 / 15 left along
  y 17.45 / 18.3, down x 3.8 / 4.4 into U6 pads 2 / 1.
- **Protection**: OD and BAT_N are straight vertical links U4 ↔ Q1; OC goes round the right at x 8.2;
  VM straight to R8; R7/C3 stacked on the left edge.
- **Battery sense**: gate link Q3 → Q2 goes round the left at x 7.7; R11/R12/C6 stacked at x 13.0.
- **+BATT to the LDO**: top-layer track along y 48.7 from C2 to C4.

Bottom layer:

- +BATT: BT1 → via at C2/U3; BT1 → up x 11.5 → Q2 source via, R9/R7 via; TP7.
- VBUS: (28.3, 39.05)–(28.3, 43.95), across y 41.5 to the U2 via, down x 22.0 to y 46.6, left to the
  via at U3 pad 4 / C1.
- BTN (left strip via → SW1), BAT_ADC (left strip via → C6), BOOT (left strip via → along y 8.5
  under the module → TP4), EN / TX / RX (vias beside the module → their test pads).

Back pads must not have a via of another net inside them: BT1 (10.25–12.75, 43.35–45.85),
BT2 (2.25–4.75, 43.0–45.5), test pads 1.5 mm round.

## 4. Things to check on the first board

See `testing.md` section B. Layout-specific: the T3902 land pattern against the datasheet, the
USB-C overhang against the enclosure wall, CPL rotations in JLCPCB's preview (J1, U1, MK1, SW1 and
the SOT-23 parts are the usual suspects).
