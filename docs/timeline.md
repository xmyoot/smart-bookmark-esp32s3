# Timeline — smart-bookmark-esp32s3

## 2026-10-05 — session 1 (Opus 5.5)

Decisions (user): deliver PCB through fab outputs, firmware source, BLE protocol doc and a client
proposal; cell stacked behind a single-sided board; firmware in ESP-IDF; use installed software
(git, KiCad 10.0.5 in Program Files, system Python), not the portable copies.

Done:
- Skeleton and git repo; scripts copied from `hab-pi-zero-hat` and adapted
  (`sch_engine.py` is the HAB schematic writer split out as a module).
- Parts research against the JLCPCB API and datasheets (`datasheets/`, PDF + extracted text).
  All parts in stock. LCSC's `www.lcsc.com/datasheet/` links return HTML through the proxy;
  the `wmsc.lcsc.com` file host works (`scripts/fetch_datasheets.py`).
- Schematic: root + 6 sheets (mcu, usb, power, audio, storage, ui_test), 52 components.
  ERC 0/0. `check_netlist.py`: 153 pins, 0 mismatches.
- Placement on 37 x 52 mm, 4 layers, 0.8 mm. No overlaps. Renders in `docs/placement_*.png`.
- Docs: client_request (Q1–Q11), design_spec, reference_designs, ble_protocol, proposal draft,
  testing, usage.
- Firmware source in `firmware/` (ESP-IDF, NimBLE, LittleFS). Compiles: PlatformIO Core 6.2.0
  (pip, user install), espressif32 7.1.3, ESP-IDF 6.1.0; 560 kB image. The first build took
  22 minutes because PlatformIO's primary mirror fails certificate checks behind the proxy and
  every package falls back to a second mirror.

Design changes made along the way, and why:
1. **No power-path switch.** The load sits on the cell as on the XIAO. A Schottky OR-ing diode's
   reverse leakage would roughly double standby current.
2. **GPIO map changed from the first draft** so every signal group leaves the module on the side
   its parts sit on (no crossings on the top layer): battery sense enable, charger status and USB
   detect on GPIO16/17/18 (bottom row), mic data/power/clock on GPIO40/41/42, flash on
   GPIO10–13 in pad order. Button and LED stay on GPIO1/GPIO2 like the XIAO prototype.
3. **Mic powered from a GPIO** (GPIO41) to remove its 12 µA sleep current.
4. **R4 (charger status pull-up) removed**; the MCU's internal pull-up does the job.
5. **Stock KiCad USB-C symbol and footprint** instead of the EasyEDA import (cleaner pads, 3D model).
6. **Test pads split**: six in the top-right corner of the back (next to the module pins they
   serve), VBAT at the bottom next to the battery pads. All outside the assumed cell area.

Assumptions that drive the layout (all in `client_request.md`): 6 mm interior height, USB-C on the
right long edge, button on the centre line, mic port through the board to the back, 25 x 30 x 2.5 mm
cell at x 1.5–26.5, y 10–40 on the back.

Not verified / open:
- **Routing, DRC, fab outputs: not started.** Waiting for the user's review of the placement.
- Firmware has not run on hardware. PDM slot (left/right) for SELECT = GND is the item most
  likely to need a one-line change on the first article.
- T3902 land pattern is the LCSC/EasyEDA import; compare with the datasheet drawing.
- USB-C shell overhang (1.0 mm) is a guess until the enclosure wall thickness is known.
- Active current figures in the spec are estimates.
- Proposal prices, dates and the answers to client questions 1 and 2 are blanks for the user.

Next:
1. User reviews placement (`docs/placement_top.png`, `docs/placement_back.png`).
2. Routing (`scripts/route_pcb.py`, to be written from the plan in `build_notes.md` section 3),
   zones (In1 GND, In2 +3V3, GND pours top and bottom), DRC to 0.
3. Fab package (`make_fab.py`, still the unadapted HAB copy, untracked), `designBrief.html`.
