# Testing

## A. Design checks (done on the computer)

| Check | How | Result on 2026-10-05 |
|---|---|---|
| ERC | `kicad-cli sch erc ... --severity-all` | 0 errors, 0 warnings |
| Pin map against datasheets | `scripts/check_netlist.py` (153 pins typed from the datasheet tables) | 0 mismatches, 0 single-pin nets |
| Parts in stock | `scripts/jlc_search.py` | Every BOM line in stock at JLCPCB |
| Placement | `scripts/build_pcb.py place` | 52 footprints, no courtyard overlaps, nothing in the antenna strip |
| Routing, DRC, schematic parity | — | **Not done yet** (waiting for placement review) |
| Fabrication files | — | **Not done yet** |
| Firmware build | `pio run` in `firmware/` (ESP-IDF 6.1.0) | Success: 560 kB image (30 % of the app slot), RAM 8 %, one deprecation warning. Not run on hardware |

## B. First-article bring-up (to do when boards arrive)

Work through in order; stop at the first failure. Bench supply set to 4.0 V, 300 mA limit, on
the battery pads (BT1 +, BT2 −) unless stated. No cell fitted until step 7.

| # | Test | Expect |
|---|---|---|
| 1 | Visual: mic orientation and port hole clear of solder, USB-C seated, module square | — |
| 2 | Resistance BT1 to BT2, and TP1 (3V3) to TP2 (GND), before power | Not shorted |
| 3 | Apply 4.0 V. If the protection IC stays latched off (0 V at TP1), plug in USB once to release it | TP1 = 3.30 V ± 0.07 |
| 4 | Supply current with a blank module | Tens of mA (ROM bootloader running) |
| 5 | Plug USB-C into a PC | A serial/JTAG device enumerates. If not, hold BOOT (TP4) low and re-plug |
| 6 | Flash the firmware over USB; watch the log | Boots, mounts storage, advertises |
| 7 | Charger: USB on, bench supply replaced by the cell | About 100 mA into the cell; STAT low; stops near 4.20 V |
| 8 | Sleep current: USB off, wait for sleep, measure in series with the cell | Target about 14 µA; investigate anything over 30 µA |
| 9 | Record a clip, pull it with nRF Connect or the app | Speech intelligible, no clipping at normal speaking distance |
| 10 | If the clip is silent or pure noise: set `AUDIO_MIC_SLOT_RIGHT` to 0 in `board.h` | (PDM slot selection could not be verified without hardware) |
| 11 | Battery reading against a meter at 3.5 V and 4.1 V | Within 50 mV |
| 12 | Under-voltage: lower the bench supply slowly | Firmware refuses to record below 3.3 V; protection opens near 2.5 V |
| 13 | BLE range in the enclosure, cell fitted | Works across a room; compare with the bare board |
| 14 | Download speed, 60 s clip, iOS and Android | Record kB/s; verify the CRC matches |
| 15 | Start latency: press to LED on | Record the figure; target under 0.5 s |
| 16 | Short BT1 to BT2 briefly with the cell connected | Protection opens; recovers when USB is plugged in |

## C. Items that need the real enclosure

Fit and height at the USB connector, button travel, microphone port alignment and sealing,
LED visibility, antenna performance next to the cell.
