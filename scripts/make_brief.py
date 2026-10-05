"""Generate docs/designBrief.html (self-contained, renders embedded).  python scripts/make_brief.py
Run scripts/render3d.py and scripts/review.py first so the pictures in docs/ are current."""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
img = lambda n: "data:image/png;base64," + base64.b64encode((ROOT / "docs" / n).read_bytes()).decode()

rows = lambda data: "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in data)
parts = [
    ("U1", "ESP32-S3-MINI-1-N8", "C2913206", "MCU + BLE, 8 MB flash, PCB antenna, pre-certified. 15.4 &times; 20.5 &times; 2.4 mm"),
    ("MK1", "TDK T3902", "C3171752", "Bottom-port PDM microphone, powered from GPIO41 so it is fully off in sleep"),
    ("U6", "W25Q128JVPIQ", "C190862", "16 MB NOR flash for clips, on SPI2"),
    ("U3", "MCP73832T-2ACI/OT", "C38066", "Li-ion charger, 4.20 V, 100 mA set by R3 (10 k&Omega;)"),
    ("U4 + Q1", "DW01A + FS8205A", "C351410 / C908265", "Cell protection: 4.30 V over-charge, 2.50 V over-discharge, short-circuit"),
    ("U5", "RT9080-33GJ5", "C841192", "3.3 V LDO, 600 mA, 2 &micro;A quiescent"),
    ("J1 + U2", "HRO TYPE-C-31-M-12 + USBLC6-2SC6", "C165948 / C7519", "USB-C: charging, native USB flashing and logs, ESD protection"),
    ("Q2 + Q3", "AO3401A + 2N7002", "C15127 / C8545", "Battery-sense divider switch: no divider current in sleep"),
    ("SW1 / D1", "TS-1088-AR02016 / KT-0603R", "C720477 / C2286", "Record button (2.0 mm tall) and red status LED"),
]
gpio = [
    ("GPIO1", "Record button", "To GND, internal pull-up, wakes the chip. Same pin as the XIAO prototype (D0)"),
    ("GPIO2", "Status LED", "Active high. Same pin as the XIAO prototype (D1)"),
    ("GPIO5", "Battery voltage", "ADC1, half the cell voltage while GPIO16 is high"),
    ("GPIO16 / 17 / 18", "Battery-sense enable / charging / USB present", "USB plug-in can wake the chip"),
    ("GPIO10&ndash;13", "Clip flash U6", "MISO, CS, SCK, MOSI"),
    ("GPIO19 / 20", "USB D&minus; / D+", "Native USB"),
    ("GPIO40 / 41 / 42", "Mic data / mic power / mic clock", ""),
    ("GPIO0, EN, GPIO43 / 44", "BOOT, reset, UART", "Test pads on the back"),
]
power = [
    ("ESP32-S3 module, deep sleep with wake armed", "8 &micro;A"), ("Regulator U5", "2 &micro;A"),
    ("Protection U4", "3 &micro;A"), ("Flash U6 in deep power-down (to be verified)", "about 1 &micro;A"),
    ("Charger leakage, mic, divider, LED", "about 0"), ("<b>Standby total</b>", "<b>about 15 &micro;A</b>"),
    ("Recording (estimate)", "about 40 mA"), ("BLE transfer (estimate)", "about 80 mA"),
]
decisions = [
    ("Module, not bare chip", "The ESP32-S3-MINI-1 keeps the client's S3 firmware base and hardware PDM decoding, is 2.4 mm tall, and brings its radio certification to a 500-unit run. ESP32-C3/C6 cannot decode a PDM microphone in hardware; nRF52840 would mean rewriting working firmware."),
    ("No SD card", "Clips are IMA ADPCM (8 kB/s) on flash. That removes the tallest, most power-hungry prototype part and makes BLE sync four times faster than raw audio."),
    ("No power-path switch", "The load sits on the cell, as on the XIAO. An OR-ing Schottky would leak more in standby than the rest of the board draws. Firmware sleeps when idle on USB so charging can terminate."),
    ("Pins chosen for the layout", "Each signal group leaves the module on the side its parts sit on, so the top layer has no crossings. Only five signals use the back."),
    ("Height, not area, is tight", "0.8 mm board + 2.4 mm module + 2.5 mm cell = 5.7 mm of an assumed 6.0 mm. The USB-C connector is 3.3 mm tall, so the cell is kept clear of it."),
    ("Module sits 0.45 mm lower than its outline suggests", "The real module is 20.5 mm long; KiCad's footprint draws 20.1 mm. Placed so the real part stays on the board."),
    ("Microphone land pattern corrected", "The imported footprint had a plated port hole and an unconnected four-piece ground ring. The hole is non-plated and the ring is tied to ground."),
]
open_items = [
    "Enclosure CAD: every mechanical position (USB-C, button, microphone hole, LED, cell) is an assumption until it arrives.",
    "Firmware does not use the 16 MB flash U6 yet; clips still go to the module's own flash (about 8.5 minutes).",
    "Firmware compiles but has never run on hardware. The microphone's left/right slot setting is the likeliest first fix.",
    "CPL rotations are not checked in JLCPCB's preview; Gerbers were not opened in a viewer.",
    "The microphone 3D model is a same-size stand-in; compare the land pattern with the T3902 datasheet drawing.",
    "Active-current and battery-life figures are estimates to be measured on the first boards.",
]
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Bookmark Design Brief</title><style>
:root{{--bg:#fbfaf7;--fg:#1d2330;--mut:#5b6474;--line:#dcd9d2;--acc:#1f6f5c;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14171c;--fg:#e6e8ec;--mut:#9aa3b2;--line:#2c323b;--acc:#5cc3a6;--card:#1b1f26}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,Segoe UI,sans-serif}}
main{{max-width:1040px;margin:auto;padding:28px 16px 60px}} h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:18px;margin:34px 0 10px;color:var(--acc)}}
.sub{{color:var(--mut)}} table{{width:100%;border-collapse:collapse;background:var(--card);font-size:14px}}
td,th{{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}} th{{color:var(--mut);font-weight:600}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}} .k{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}}
.k b{{display:block;font-size:20px}} img{{width:100%;border-radius:8px;border:1px solid var(--line);background:#fff}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.wrap{{overflow-x:auto}} pre{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;overflow-x:auto;font-size:13px}}
li{{margin:4px 0}} @media (max-width:720px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main>
<h1>Smart Bookmark voice recorder &mdash; rev A</h1>
<div class="sub">Design brief &middot; press a button, speak, clips sync to a phone over BLE &middot; KiCad 10 &middot; JLCPCB 4-layer + assembly &middot; 2026-10-05</div>
<h2>Status</h2><div class="kpi">
<div class="k"><b>0 / 0</b>ERC errors / warnings</div><div class="k"><b>0 / 0 / 0</b>DRC errors / unconnected / parity</div>
<div class="k"><b>153 / 153</b>datasheet pins verified</div><div class="k"><b>37 &times; 52 mm</b>4-layer, 0.8 mm, parts on one side</div>
<div class="k"><b>about 15 &micro;A</b>standby, from datasheet figures</div><div class="k"><b>builds clean</b>firmware, not yet run on hardware</div></div>
<h2>Board</h2><div class="grid"><img src="{img('render_top.png')}" alt="Top render"><img src="{img('render_bot.png')}" alt="Bottom render">
<img src="{img('render_iso.png')}" alt="Angled render"><img src="{img('route_top.png')}" alt="Top copper"></div>
<p class="sub">Back side carries no parts: the cell lies in the outlined area; battery pads and test pads sit outside it.</p>
<h2>Architecture</h2>
<pre>USB-C VBUS --&gt; charger U3 (100 mA) --&gt; +BATT --&gt; regulator U5 --&gt; 3.3 V --&gt; ESP32-S3 module, clip flash U6
                                        |
                        cell + ---------+        cell - --&gt; protection U4/Q1 --&gt; GND

button --&gt; ESP32-S3 &lt;-- PDM microphone (powered from a GPIO)
           ESP32-S3 --&gt; ADPCM clips on flash --&gt; BLE --&gt; phone app</pre>
<p>The device sleeps until the button is pressed or USB is plugged in. Holding the button records; on release the clip is stored and the
bookmark advertises for 30 s so the phone can fetch it. Protocol: <code>docs/ble_protocol.md</code>.</p>
<h2>Key parts</h2><div class="wrap"><table><tr><th>Ref</th><th>Part</th><th>LCSC</th><th>Role</th></tr>{rows(parts)}</table></div>
<h2>Pin map</h2><div class="wrap"><table><tr><th>Pin</th><th>Function</th><th>Note</th></tr>{rows(gpio)}</table></div>
<h2>Power budget</h2><div class="wrap"><table><tr><th>Item</th><th>Current</th></tr>{rows(power)}</table></div>
<p>Ten 20-second clips and one sync a day is roughly 3.5 mAh, so a 150 mAh cell lasts about six weeks of daily use. Standby alone is
limited by the cell's self-discharge, not the board.</p>
<h2>Engineering decisions</h2><div class="wrap"><table><tr><th>Topic</th><th>Decision</th></tr>{rows(decisions)}</table></div>
<h2>Open items</h2><ul>{''.join(f'<li>{o}</li>' for o in open_items)}</ul>
<h2>Deliverables</h2><p>KiCad sources and generator scripts; Gerber zip, JLCPCB BOM and CPL, schematic and assembly PDFs and STEP in <code>fab/</code>;
ESP-IDF firmware in <code>firmware/</code>; BLE protocol, design spec, reference circuits, bring-up checklist and a proposal draft in <code>docs/</code>.</p>
</main></body></html>"""
(ROOT / "docs" / "designBrief.html").write_text(html, encoding="utf-8")
print("docs/designBrief.html", len(html))
