"""Assemble the client hand-over package: delivery/smart-bookmark-revA/ and the same as a zip.
  python scripts/make_delivery.py
Run make_fab.py and make_brief.py first. Internal working files (proposal, timeline, build
intermediates) are deliberately left out."""
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "smart-bookmark-revA"
OUT = ROOT / "delivery" / NAME
PROJ = "smart-bookmark-esp32s3"

README = """# Smart bookmark voice recorder — design package, Rev A

Everything needed to review, build and continue this design. You own all of it.

## Start here

Open `1_design_brief/designBrief.html` in a browser: one page with pictures of the board, how it
works, the main parts, the power budget and the open items.

## What is in each folder

| Folder | Contents |
|---|---|
| `1_design_brief` | The one-page overview, and renders of the board |
| `2_schematic` | Schematic as a PDF (7 pages) |
| `3_pcb_kicad_project` | Full KiCad 10 project: schematic, board layout, part libraries with 3D models |
| `4_manufacturing_jlcpcb` | Upload-ready files for JLCPCB: Gerber zip, BOM, pick-and-place (CPL), assembly drawings, 3D STEP of the assembled board for your enclosure check |
| `5_firmware` | ESP-IDF firmware source (C). See its `README.md` to build and flash |
| `6_documents` | Design spec, BLE protocol for your app developer, reference circuits, layout notes, bring-up and test checklist, open questions |
| `7_generator_scripts` | The Python scripts that generate the schematic, board and manufacturing files |
| `datasheets` | Datasheets of the main parts |

## Status, stated plainly

| Item | State |
|---|---|
| Schematic | Complete. Electrical rule check: 0 errors, 0 warnings. 153 pins checked against the datasheets |
| Board layout | Complete, 37 x 52 mm, 4 layers. Design rule check: 0 errors, 0 unconnected nets |
| Manufacturing files | Generated. The pick-and-place rotations must still be checked in JLCPCB's preview when ordering |
| Parts | All in stock at JLCPCB on 2026-10-05 |
| Firmware | Compiles cleanly. **It has not run on hardware yet, because no boards have been built** |
| Enclosure fit | **Based on assumptions.** No enclosure CAD was available, so the USB-C, button, microphone, LED and battery positions are our best guess |

## What we need from you

`6_documents/client_request.md` lists eleven questions. The first five (enclosure CAD and interior
height, USB-C position, button position, where sound enters, which battery) can move parts on
the board, so they should be answered before boards are ordered.

## To order boards

1. Upload `4_manufacturing_jlcpcb/smart-bookmark-esp32s3_gerbers_JLCPCB.zip` at jlcpcb.com.
   Choose 4 layers, 0.8 mm thickness.
2. Add PCB assembly, top side, and upload `BOM_JLCPCB.csv` and `CPL_JLCPCB.csv`.
3. Check each part's position and rotation in the preview before paying.
4. The battery is not part of the assembly: it is soldered to the two pads marked BAT+ and BAT-
   on the back.

## App developer

Give them `6_documents/ble_protocol.md`. It has the Bluetooth service and characteristic IDs, the
message formats, the download sequence and the audio file format.
"""

DOCS = ["design_spec.md", "ble_protocol.md", "reference_designs.md", "build_notes.md", "testing.md",
        "usage.md", "client_request.md"]
PICS = ["render_top.png", "render_bot.png", "render_iso.png", "route_top.png", "route_bot.png"]
FW_SKIP = shutil.ignore_patterns(".pio", "build", "managed_components", "sdkconfig", "sdkconfig.old",
                                 "sdkconfig.bookmark", "dependencies.lock", ".gitignore")


def main():
    if OUT.parent.exists():
        shutil.rmtree(OUT.parent)
    OUT.mkdir(parents=True)
    (OUT / "README.md").write_text(README, encoding="utf-8")

    d = OUT / "1_design_brief"; d.mkdir()
    shutil.copy2(ROOT / "docs" / "designBrief.html", d)
    for p in PICS:
        shutil.copy2(ROOT / "docs" / p, d)

    d = OUT / "2_schematic"; d.mkdir()
    shutil.copy2(ROOT / "fab" / f"{PROJ}_schematic.pdf", d)

    d = OUT / "3_pcb_kicad_project"; d.mkdir()
    for f in (f"{PROJ}.kicad_pro", f"{PROJ}.kicad_sch", f"{PROJ}.kicad_pcb", f"{PROJ}.kicad_dru",
              "sym-lib-table", "fp-lib-table"):
        shutil.copy2(ROOT / f, d)
    shutil.copytree(ROOT / "sheets", d / "sheets")
    shutil.copytree(ROOT / "lib", d / "lib", ignore=shutil.ignore_patterns("*.wrl"))

    d = OUT / "4_manufacturing_jlcpcb"; d.mkdir()
    for f in (ROOT / "fab").iterdir():
        if f.is_file() and "schematic" not in f.name:
            shutil.copy2(f, d)

    shutil.copytree(ROOT / "firmware", OUT / "5_firmware", ignore=FW_SKIP)

    d = OUT / "6_documents"; d.mkdir()
    for f in DOCS:
        shutil.copy2(ROOT / "docs" / f, d)

    shutil.copytree(ROOT / "scripts", OUT / "7_generator_scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "make_delivery.py"))

    d = OUT / "datasheets"; d.mkdir()
    for f in (ROOT / "datasheets").glob("*.pdf"):
        shutil.copy2(f, d)

    zpath = OUT.parent / f"{NAME}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                z.write(f, Path(NAME) / f.relative_to(OUT))
    n = sum(1 for f in OUT.rglob("*") if f.is_file())
    print(f"{zpath}  {zpath.stat().st_size / 1e6:.1f} MB, {n} files")
    for sub in sorted(OUT.iterdir()):
        print("  ", sub.name)


if __name__ == "__main__":
    main()
