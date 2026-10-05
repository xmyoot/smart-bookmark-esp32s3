"""Print footprint geometry at rotation 0 (courtyard box, pad centres/sizes) for placement planning.
Run with KiCad's Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" scripts/fpinfo.py [lib:name ...]
With no arguments, prints every footprint used in build/bookmark.net (pads summarised for big parts)."""
import re
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
KFP = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")


def load(fpid):
    lib, name = fpid.split(":")
    libdir = ROOT / "lib" / "bookmark.pretty" if lib == "bookmark" else KFP / f"{lib}.pretty"
    return pcbnew.FootprintLoad(str(libdir), name)


def show(fpid, full):
    fp = load(fpid)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    m = pcbnew.ToMM
    print(f"== {fpid}\n   courtyard x {m(bb.GetLeft()):.2f}..{m(bb.GetRight()):.2f}  y {m(bb.GetTop()):.2f}..{m(bb.GetBottom()):.2f}"
          f"  ({m(bb.GetWidth()):.2f} x {m(bb.GetHeight()):.2f})  pads {len(fp.Pads())}")
    pads = list(fp.Pads())
    if not full and len(pads) > 20:
        pads = [p for p in pads if p.GetNumber() in ("1", "2", "3", "4", "14", "15", "25", "26", "39", "40", "41", "45", "61", "65")]
    for p in pads:
        pos, sz = p.GetPosition(), p.GetSize()
        drill = f" drill {m(p.GetDrillSize().x):.2f}" if p.GetDrillSize().x else ""
        print(f"   {p.GetNumber() or '(np)':>6} ({m(pos.x):7.3f},{m(pos.y):7.3f}) {m(sz.x):.2f}x{m(sz.y):.2f}{drill}")


if __name__ == "__main__":
    ids = sys.argv[1:]
    full = bool(ids)
    if not ids:
        t = (ROOT / "build" / "bookmark.net").read_text(encoding="utf-8")
        ids = sorted(set(re.findall(r'\(footprint "([^"]+)"\)', t)))
    for i in ids:
        show(i, full)
