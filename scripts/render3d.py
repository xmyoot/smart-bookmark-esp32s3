"""3D renders of the board for review: build/render_top.png, render_bot.png, render_iso.png.
  python scripts/render3d.py [width_px]"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PCB = ROOT / "smart-bookmark-esp32s3.kicad_pcb"
w = sys.argv[1] if len(sys.argv) > 1 else "900"
VIEWS = {
    "top": ["--side", "top"],
    "bot": ["--side", "bottom"],
    "iso": ["--side", "top", "--rotate", "-50,0,-25", "--perspective"],
}
for name, args in VIEWS.items():
    out = ROOT / "build" / f"render_{name}.png"
    r = subprocess.run([CLI, "pcb", "render", "-o", str(out), "-w", w, "-h", str(int(int(w) * 1.35)),
                        "--quality", "basic", *args, str(PCB)], capture_output=True, text=True)
    print(out if r.returncode == 0 else r.stderr.strip() or r.stdout.strip())
