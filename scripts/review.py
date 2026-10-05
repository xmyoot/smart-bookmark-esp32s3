"""Render board layers to cropped PNGs for review (system Python + pymupdf).
  python scripts/review.py NAME "F.Cu,F.Courtyard,Edge.Cuts" [--mirror] [--dpi 500]
Writes build/NAME.png, cropped to the 37 x 52 mm board (sheet origin 100, 70)."""
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

def render(name, layers, mirror=False, dpi=500, clip=None):
    pdf = ROOT / "build" / f"{name}.pdf"
    cmd = [CLI, "pcb", "export", "pdf", "--mode-single", "--layers", layers, "--sp",
           "--drill-shape-opt", "2", "-o", str(pdf), str(ROOT / "smart-bookmark-esp32s3.kicad_pcb")]
    if mirror:
        cmd.insert(4, "--mirror")
    subprocess.run(cmd, check=True, capture_output=True)
    page = pymupdf.open(pdf)[0]
    k = 72 / 25.4
    pw = page.rect.width / k
    cx0, cy0, cx1, cy1 = clip or (-2.5, -1.5, 39.5, 53.5)     # board-local mm window
    x0, x1 = 100 + cx0, 100 + cx1
    if mirror:
        x0, x1 = pw - x1, pw - x0
    clip = pymupdf.Rect(x0 * k, (70 + cy0) * k, x1 * k, (70 + cy1) * k)
    out = ROOT / "build" / f"{name}.png"
    page.get_pixmap(dpi=dpi, clip=clip).save(out)
    print(out)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 500
    if "--dpi" in sys.argv:
        args.remove(str(dpi))
    clip = None
    if "--clip" in sys.argv:
        i = sys.argv.index("--clip")
        clip = tuple(float(v) for v in sys.argv[i + 1:i + 5])
        for v in sys.argv[i + 1:i + 5]:
            args.remove(v)
    render(args[0], args[1], "--mirror" in sys.argv, dpi, clip)
