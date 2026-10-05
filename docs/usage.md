# Working with this project

Tools: KiCad 10 (installed in `C:\Program Files\KiCad\10.0`), system Python 3 with
`easyeda2kicad`, `pypdf`, `pymupdf` (`pip install --user ...`), git.

The schematic and board are **generated**. Edit the scripts, not the KiCad files: a regenerate
overwrites anything changed in the KiCad GUI.

| Step | Command (from the project folder) | Output |
|---|---|---|
| Schematic | `python scripts/gen_schematic.py` | `*.kicad_sch`, `sheets/` |
| ERC | `kicad-cli sch erc smart-bookmark-esp32s3.kicad_sch -o build/erc.rpt --severity-all` | must report 0 |
| Netlist | `kicad-cli sch export netlist smart-bookmark-esp32s3.kicad_sch -o build/bookmark.net` | |
| Pin check | `python scripts/check_netlist.py build/bookmark.net` | must report 0 mismatches |
| Schematic pictures | `python scripts/sch_png.py` | `build/schematic.pdf`, `build/sch_p*.png` |
| Placement | `"C:\Program Files\KiCad\10.0\bin\python.exe" scripts/build_pcb.py place` | `*.kicad_pcb`, `build/placement.json` |
| Routed board | `"C:\Program Files\KiCad\10.0\bin\python.exe" scripts/build_pcb.py route` | placement + tracks + zones |
| DRC | `python scripts/drc.py` | `build/drc.rpt`; refills zones and saves the board |
| Fab package | `python scripts/make_fab.py` | `fab/` |
| 3D pictures | `python scripts/render3d.py` | `build/render_*.png` |
| Board pictures | `python scripts/review.py NAME "F.Cu,F.Fab,Edge.Cuts"` (add `--mirror` for the back) | `build/NAME.png` |

`kicad-cli` is `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`. `build_pcb.py` must run under
KiCad's own Python because it imports `pcbnew`.

Other helpers: `scripts/jlc_search.py "keyword"` (JLCPCB stock and LCSC numbers),
`scripts/fetch_datasheets.py` (re-download datasheets and extract text),
`scripts/libinfo.py` and `scripts/fpinfo.py` (symbol pins, footprint pad geometry).

To add a part from LCSC: `python -m easyeda2kicad --full --lcsc_id=C##### --output lib/bookmark`,
then `kicad-cli sym upgrade lib/bookmark.kicad_sym --force`, and set its pin types (the importer
marks every pin "unspecified", which trips ERC).

Board coordinates in the scripts are millimetres from the top-left corner of the board, seen
from the component side, antenna end at the top.
