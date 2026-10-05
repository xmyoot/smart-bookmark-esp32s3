# Design spec — smart bookmark voice recorder (Rev A)

Source of truth for the schematic (`scripts/gen_schematic.py`), the netlist check
(`scripts/check_netlist.py`), the layout (`scripts/build_pcb.py`) and the firmware pin map
(`firmware/main/board.h`). Net names, reference designators and GPIO numbers are identical in all
of them. Tags: **[CLIENT]** from the request, **[DS]** from a datasheet in `datasheets/`,
**[JLC]** from the JLCPCB parts API on 2026-10-05, **[ASSUMED]** our assumption (see
`client_request.md` Q1–Q11).

## 1. Requirements

| Requirement | Design answer |
|---|---|
| Board about 37 x 52 mm in a 40 x 55 x 8 mm head [CLIENT] | 37.0 x 52.0 mm, R2 corners, 0.8 mm, 4 layers |
| ESP32-S3 with BLE [CLIENT] | ESP32-S3-MINI-1-N8 module (8 MB flash, PCB antenna, pre-certified) |
| Button, LED, PDM mic as the prototype [CLIENT] | SW1 on GPIO1, D1 on GPIO2 (same GPIOs as XIAO D0/D1), T3902 PDM mic |
| Storage, SD replaceable by flash [CLIENT] | Module flash, LittleFS partition; optional 16 MB NOR footprint U6 (DNP) |
| Thin LiPo, USB-C charging, battery level [CLIENT] | MCP73832 100 mA charger, DW01A + FS8205A protection, switched divider to ADC1 |
| Deep sleep, weeks of standby [CLIENT] | About 14 µA typical in deep sleep (section 5) |
| JLCPCB assembly [CLIENT] | All parts on the top side, every part in stock at JLCPCB [JLC] |

## 2. Parts

| Ref | Part | LCSC | Package | Why this part |
|---|---|---|---|---|
| U1 | ESP32-S3-MINI-1-N8 | C2913206 | 15.4 x 20.5 x 2.4 mm | Keeps the S3 (hardware PDM-to-PCM, same SDK as the prototype). 2.4 mm tall; WROOM-1 is 3.1 mm. Deep sleep 7–8 µA [DS table 6-7] |
| MK1 | TDK T3902 (MMICT390200012) | C3171752 | 3.5 x 2.65 x 0.98 mm, bottom port | PDM, 1.65–3.63 V, 64 dBA SNR; 0.65 mA active [DS] |
| U3 | MCP73832T-2ACI/OT | C38066 | SOT-23-5 | 4.20 V, current set by one resistor, open-drain STAT [DS 3.3] |
| U4 / Q1 | DW01A / FS8205A | C351410 / C908265 | SOT-23-6 x2 | Over-charge 4.30 V, over-discharge 2.50 V, short-circuit; 3 µA [DS] |
| U5 | RT9080-33GJ5 | C841192 | TSOT-23-5 | 3.3 V, 600 mA, 2 µA quiescent, 0.31 V dropout at 600 mA [DS] |
| J1 | HRO TYPE-C-31-M-12 | C165948 | 16-pin USB-C, 3.26 mm tall | USB 2.0 + charge; stock KiCad footprint |
| U2 | USBLC6-2SC6 | C7519 | SOT-23-6 | ESD on D+/D− and VBUS |
| SW1 | TS-1088-AR02016 | C720477 | 3.9 x 3.0 x 2.0 mm | 1.6 N tactile, JLCPCB basic part |
| D1 | KT-0603R red | C2286 | 0603 | Basic part |
| Q2 / Q3 | AO3401A / 2N7002 | C15127 / C8545 | SOT-23 | Battery-sense switch, basic parts |
| U6 (DNP) | W25Q128JVPIQ | C190862 | WSON-8 6 x 5 mm | Optional 16 MB clip store |
| Passives | 0402 resistors, 0402/0603/0805 capacitors | see BOM | | All JLCPCB basic parts |

Rejected: ESP32-C3/C6 (no hardware PDM-to-PCM filter), nRF52840 (lower power, but a new SDK and a
rewrite of the client's working firmware), bare ESP32-S3 chip (thinner, but loses the module's
radio certification for a 500-unit run), microSD (1.5–2 mm socket, hundreds of µA idle on many
cards), fuel-gauge IC (3–23 µA continuous, more than the rest of the board asleep).

## 3. GPIO map

| GPIO | Module pin | Net | Direction | Notes |
|---|---|---|---|---|
| 0 | 4 | BOOT | in | Strap, internal pull-up; test pad TP4 only |
| 1 | 5 | BTN_N | in | SW1 to GND, internal pull-up, RTC wake (ext0, low). Same as XIAO D0 |
| 2 | 6 | LED | out | Active high, 1 kΩ, about 1.3 mA. Same as XIAO D1 |
| 5 | 9 | BAT_ADC | analog | ADC1_CH4, reads +BATT / 2 while BAT_SENSE_EN is high |
| 10 | 14 | FLASH_MISO | in | Optional U6 |
| 11 | 15 | FLASH_CS | out | Optional U6 |
| 12 | 16 | FLASH_SCK | out | Optional U6 |
| 13 | 17 | FLASH_MOSI | out | Optional U6 |
| 16 | 20 | BAT_SENSE_EN | out | High = divider connected. 100 kΩ pull-down |
| 17 | 21 | CHG_STAT_N | in | Open-drain from U3: low = charging. Use the internal pull-up |
| 18 | 22 | VBUS_DET | in | VBUS / 2. High = USB present. RTC GPIO, can wake (ext1) |
| 19 / 20 | 23 / 24 | USB_DN / USB_DP | USB | Native USB-Serial-JTAG: flashing and logs |
| 40 | 36 | MIC_DATA | in | PDM data |
| 41 | 37 | MIC_PWR | out | Powers the mic through R14 (100 Ω). Low or hi-Z = mic off |
| 42 | 38 | MIC_CLK | out | PDM clock through R15 (33 Ω). Same GPIO as the XIAO Sense mic clock |
| 43 / 44 | 39 / 40 | UART_TX / UART_RX | UART0 | Test pads TP5 / TP6 |
| EN | 45 | EN | — | 10 kΩ to 3V3, 1 µF to GND [DS fig 9-1]; test pad TP3 |

GPIO3, 45 and 46 (straps) and every other pin are left unconnected.

## 4. Power architecture

```
USB-C VBUS ──► U3 MCP73832 (100 mA) ──► +BATT ──► U5 RT9080 ──► +3V3 (module, pull-ups, U6)
                                         │
                       cell + ───────────┘        cell − = BAT_N ──► Q1 (DW01A) ──► GND
```

- The load sits directly on the cell (same as the XIAO). There is no power-path switch: it
  would add a Schottky whose reverse leakage costs more standby current than the whole board.
  Consequence for firmware: when USB is present and nothing is happening, go to sleep, so the
  cell current can fall below the 7.5 mA termination level [DS MCP73831 table 1].
- Charge current 100 mA = 1000 V / R3 (10 kΩ) [DS]. This is 0.5 C for a 200 mAh cell. **Change R3
  if the cell changes**: 20 kΩ for 50 mA, 5.1 kΩ for about 200 mA.
- Battery sense: BAT_SENSE_EN high turns on Q3, which pulls Q2's gate low and connects
  R11/R12 (100 kΩ each). BAT_ADC = +BATT / 2, 1.5–2.1 V over 3.0–4.2 V. Wait 30 ms before sampling (C6 with 50 kΩ is a 5 ms time constant).
- The mic is powered from GPIO41, so its 12 µA sleep current [DS] is avoided completely.
  Drive MIC_CLK low before dropping MIC_PWR so the clock does not back-feed the mic.

## 5. Power budget

| State | Current | Basis |
|---|---|---|
| Deep sleep, RTC wake armed | 8 µA | U1 [DS table 6-7] |
| LDO quiescent | 2 µA | U5 [DS] |
| Protection IC | 3 µA | U4 [DS] |
| Charger reverse leakage | 0.15 µA | U3 [DS] |
| Mic, divider, LED, flash U6 | 0 | Unpowered or not fitted |
| **Standby total** | **about 14 µA** | 150 mAh / 14 µA is over a year on paper; cell self-discharge will dominate |
| Recording | about 40 mA | CPU at 80 MHz, mic, flash writes [DS table 6-6, estimate] |
| BLE transfer | about 80 mA average | Radio duty cycle estimate; to be measured |

Example day: 10 clips of 20 s each (2.2 mAh) plus one sync of all ten (about 1.3 mAh) is about
3.5 mAh per day, so a 150 mAh cell lasts roughly six weeks of daily use. These active figures are
estimates and are first-article measurements in `testing.md`.

## 6. Audio and storage

- 16 kHz, 16-bit mono from the I2S PDM receiver, encoded to IMA ADPCM (4 bits per sample,
  8 kB/s). A 20 s clip is 160 kB.
- Module flash, 8 MB: two 1.75 MB application slots (OTA), 4.4 MB LittleFS. That holds about
  **8.5 minutes** of audio in total. If the client needs more (Q6), fit U6 for about 33 more
  minutes, or drop OTA for 12 minutes.

## 7. Mechanical

| Item | Value |
|---|---|
| Board | 37.0 x 52.0 x 0.8 mm, four R2 corners, no mounting holes [ASSUMED Q1] |
| Tallest top-side part | J1, 3.26 mm. Module 2.4 mm, button 2.0 mm |
| Stack at the module | 0.8 board + 2.4 module + 2.5 cell = 5.7 mm of an assumed 6.0 mm |
| Stack at J1 | 0.8 + 3.26 = 4.06 mm; the cell must not sit behind J1 (it does not) |
| Antenna | Module antenna at the top edge. No copper on any layer for y < 5.0 mm. Keep the cell and any metal at least 5 mm from this end |
| Cell area on the back | x 1.5–26.5, y 10–40 mm [ASSUMED Q5]. No pads or holes under it; vias are tented |
| Mic port | 0.5 mm hole through the board at (33.2, 26.7), outside the cell area |

Coordinates are in mm from the top-left board corner, seen from the component side.
