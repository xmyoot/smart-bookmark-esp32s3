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

Schematic, board layout, manufacturing files, firmware and the documents needed to use them.
You own all of it.

## Folders

| Folder | Contents |
|---|---|
| `1_schematic` | Schematic as a PDF (7 pages) |
| `2_pcb_kicad_project` | Full KiCad 10 project: schematic and board source files, part libraries, 3D models |
| `3_manufacturing_jlcpcb` | Upload-ready files for JLCPCB: Gerber zip, BOM, pick-and-place (CPL), assembly drawings, and a 3D STEP of the assembled board for your enclosure check |
| `4_firmware` | ESP-IDF firmware source (C). See its `README.md` to build and flash |
| `5_documents` | `designBrief.html` (one-page overview with pictures: open this first), design spec, BLE protocol for your app developer, bring-up and test checklist, open questions |

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

`5_documents/client_request.md` lists eleven questions. The first five (enclosure CAD and interior
height, USB-C position, button position, where sound enters, which battery) can move parts on
the board, so they should be answered before boards are ordered.

## To order boards

1. Upload `3_manufacturing_jlcpcb/smart-bookmark-esp32s3_gerbers_JLCPCB.zip` at jlcpcb.com.
   Choose 4 layers, 0.8 mm thickness.
2. Add PCB assembly, top side, and upload `BOM_JLCPCB.csv` and `CPL_JLCPCB.csv`.
3. Check each part's position and rotation in the preview before paying.
4. The battery is not part of the assembly: it is soldered to the two pads marked BAT+ and BAT-
   on the back.

## Notes

- The documents mention files under `scripts/`. Those are the tools the design was generated and
  checked with; they are not needed to open, change or manufacture it.
- Give your app developer `5_documents/ble_protocol.md`: Bluetooth service and characteristic IDs,
  message formats, the download sequence and the audio file format.
"""

DOCS = ["designBrief.html", "design_spec.md", "ble_protocol.md", "testing.md", "client_request.md"]
MODELS_USED = ("BULETM-SMD_ESP32-S3-MINI-1-N8.step", "USB-C_SMD-TYPE-C-31-M-12_1.step", "SW-SMD_L3.9-W2.9-H2.0-LS4.8.step")
FW_SKIP = shutil.ignore_patterns(".pio", "build", "managed_components", "sdkconfig", "sdkconfig.old",
                                 "sdkconfig.bookmark", "dependencies.lock", ".gitignore")


def main():
    if OUT.parent.exists():
        shutil.rmtree(OUT.parent)
    OUT.mkdir(parents=True)
    (OUT / "README.md").write_text(README, encoding="utf-8")

    d = OUT / "1_schematic"; d.mkdir()
    shutil.copy2(ROOT / "fab" / f"{PROJ}_schematic.pdf", d)

    d = OUT / "2_pcb_kicad_project"; d.mkdir()
    for f in (f"{PROJ}.kicad_pro", f"{PROJ}.kicad_sch", f"{PROJ}.kicad_pcb", f"{PROJ}.kicad_dru",
              "sym-lib-table", "fp-lib-table"):
        shutil.copy2(ROOT / f, d)
    shutil.copytree(ROOT / "sheets", d / "sheets")
    keep_model = lambda folder, names: [n for n in names if n.endswith((".step", ".wrl")) and n not in MODELS_USED]
    shutil.copytree(ROOT / "lib", d / "lib", ignore=keep_model)      # only the 3D models the board uses

    d = OUT / "3_manufacturing_jlcpcb"; d.mkdir()
    for f in (ROOT / "fab").iterdir():
        if f.is_file() and "schematic" not in f.name:
            shutil.copy2(f, d)

    shutil.copytree(ROOT / "firmware", OUT / "4_firmware", ignore=FW_SKIP)

    d = OUT / "5_documents"; d.mkdir()
    for f in DOCS:
        shutil.copy2(ROOT / "docs" / f, d)

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
