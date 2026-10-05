"""Export the schematic to build/schematic.pdf and one PNG per page (build/sch_pN.png) for review.
  python scripts/sch_png.py [dpi]"""
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PROJ = "smart-bookmark-esp32s3"

pdf = ROOT / "build" / "schematic.pdf"
pdf.parent.mkdir(exist_ok=True)
subprocess.run([CLI, "sch", "export", "pdf", "-o", str(pdf), str(ROOT / f"{PROJ}.kicad_sch")], check=True, capture_output=True)
dpi = int(sys.argv[1]) if len(sys.argv) > 1 else 110
for i, page in enumerate(pymupdf.open(pdf)):
    out = ROOT / "build" / f"sch_p{i + 1}.png"
    page.get_pixmap(dpi=dpi).save(out)
    print(out)
