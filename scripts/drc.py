"""Run DRC (with zone refill and schematic parity) and print the violations in board-local mm.
  python scripts/drc.py            -> build/drc.rpt"""
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PCB = ROOT / "smart-bookmark-esp32s3.kicad_pcb"
RPT = ROOT / "build" / "drc.rpt"

r = subprocess.run([CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--refill-zones", "--save-board",
                    "-o", str(RPT), str(PCB)], capture_output=True, text=True)
print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if l.startswith("Found")))
text = RPT.read_text(encoding="utf-8")
text = re.sub(r"@\((\d+\.\d+) mm, (\d+\.\d+) mm\)",
              lambda m: f"@({float(m.group(1)) - 100:.2f}, {float(m.group(2)) - 70:.2f})", text)
print(dict(Counter(re.findall(r"^\[(\w+)\]", text, re.M))))
for line in text.splitlines():
    if line.startswith("[") or "@(" in line:
        print(line[:170])
