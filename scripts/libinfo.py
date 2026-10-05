"""Print pin tables for symbols: python scripts/libinfo.py [lib:name ...]
With no arguments, lists every symbol in lib/bookmark.kicad_sym with its footprint and pins."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KICAD_SYM = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
PIN = re.compile(r'\(pin (\w+) \w+.*?\(name "([^"]*)".*?\(number "([^"]*)"', re.S)


def blocks(text):
    for m in re.finditer(r'\n\s*\(symbol "([^"]+)"', text):
        if re.search(r"_\d+_\d+$", m.group(1)):
            continue
        start, d = m.start() + text[m.start():].index("("), 0
        for j in range(start, len(text)):
            d += (text[j] == "(") - (text[j] == ")")
            if d == 0:
                yield m.group(1), text[start:j + 1]
                break


def show(name, blk):
    fp = re.search(r'property\s+"Footprint"\s+"([^"]*)"', blk)
    ext = re.search(r'\(extends "([^"]+)"\)', blk)
    print(f"== {name} | fp: {fp.group(1) if fp else ''}{' | extends ' + ext.group(1) if ext else ''}")
    for typ, pname, num in sorted(PIN.findall(blk), key=lambda p: (len(p[2]), p[2])):
        print(f"   {num:>4}  {pname:22} {typ}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        for n, b in blocks((ROOT / "lib" / "bookmark.kicad_sym").read_text(encoding="utf-8")):
            show(n, b)
    for arg in sys.argv[1:]:
        lib, name = arg.split(":")
        path = ROOT / "lib" / "bookmark.kicad_sym" if lib == "bookmark" else KICAD_SYM / f"{lib}.kicad_sym"
        for n, b in blocks(path.read_text(encoding="utf-8")):
            if n == name:
                show(f"{lib}:{n}", b)
