"""Generate the JLCPCB fabrication + assembly package into fab/ (system Python).
  python scripts/make_fab.py
Outputs: gerbers + drill (zipped), JLC BOM, JLC CPL, schematic PDF, assembly PDF, STEP."""
import csv
import shutil
import subprocess
import zipfile
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
PCB = str(ROOT / "smart-bookmark-esp32s3.kicad_pcb")
SCH = str(ROOT / "smart-bookmark-esp32s3.kicad_sch")
FAB = ROOT / "fab"
GERB = FAB / "gerbers"


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    if GERB.exists():
        shutil.rmtree(GERB)
    GERB.mkdir(parents=True)
    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    run("pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask",
        "--use-drill-file-origin", "--check-zones", "-o", str(GERB) + "\\", PCB)
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--drill-origin", "plot",
        "--excellon-units", "mm", "--generate-map", "--map-format", "gerberx2",
        "-o", str(GERB) + "\\", PCB)
    zpath = FAB / "smart-bookmark-esp32s3_gerbers_JLCPCB.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(GERB.iterdir()):
            z.write(f, f.name)

    # ---- BOM (JLCPCB format: Comment, Designator, Footprint, LCSC Part #) + full BOM with MPN
    raw = FAB / "_bom_raw.csv"
    run("sch", "export", "bom", "--fields", "Reference,Value,Footprint,MPN,LCSC,${DNP},${EXCLUDE_FROM_BOM}",
        "--labels", "Reference,Value,Footprint,MPN,LCSC,DNP,EXCLUDE", "--group-by", "",
        "--exclude-dnp", "-o", str(raw), SCH)
    groups = OrderedDict()
    with raw.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("EXCLUDE") or row.get("DNP"):
                continue
            key = (row["Value"], row["Footprint"], row["MPN"], row["LCSC"])
            groups.setdefault(key, []).append(row["Reference"])
    raw.unlink()
    natural = lambda r: (r.rstrip("0123456789"), int("0" + r[len(r.rstrip("0123456789")):]))
    with (FAB / "BOM_JLCPCB.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, mpn, lcsc), refs in groups.items():
            w.writerow([val if val == mpn else f"{val} {mpn}".strip(), ",".join(sorted(refs, key=natural)), fp.split(":")[-1], lcsc])
    with (FAB / "BOM_full.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Qty", "Designators", "Value", "Manufacturer part number", "LCSC", "Footprint"])
        for (val, fp, mpn, lcsc), refs in groups.items():
            w.writerow([len(refs), " ".join(sorted(refs, key=natural)), val, mpn, lcsc, fp])

    # ---- CPL (JLCPCB format: Designator, Mid X, Mid Y, Layer, Rotation)
    pos = FAB / "_pos_raw.csv"
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
        "--exclude-dnp", "--use-drill-file-origin", "-o", str(pos), PCB)
    bom_refs = {r for refs in groups.values() for r in refs}
    with pos.open(encoding="utf-8") as fh, (FAB / "CPL_JLCPCB.csv").open("w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(fh):
            if row["Ref"] not in bom_refs:
                continue
            w.writerow([row["Ref"], f'{float(row["PosX"]):.3f}mm', f'{float(row["PosY"]):.3f}mm',
                        "Top" if row["Side"] == "top" else "Bottom", f'{float(row["Rot"]):.1f}'])
    pos.unlink()

    # ---- documents
    run("sch", "export", "pdf", "-o", str(FAB / "smart-bookmark-esp32s3_schematic.pdf"), SCH)
    run("pcb", "export", "pdf", "--mode-multipage", "--layers", "F.Fab,Edge.Cuts,F.SilkS",
        "--cl", "Edge.Cuts", "--include-border-title", "--sp",
        "-o", str(FAB / "smart-bookmark-esp32s3_assembly_top.pdf"), PCB)
    run("pcb", "export", "pdf", "--mode-single", "--mirror", "--layers", "B.Fab,B.SilkS,Edge.Cuts",
        "--include-border-title", "--sp", "-o", str(FAB / "smart-bookmark-esp32s3_assembly_bottom.pdf"), PCB)
    run("pcb", "export", "step", "--subst-models", "--force", "-o", str(FAB / "smart-bookmark-esp32s3.step"), PCB)
    for f in sorted(FAB.iterdir()):
        print(f.name, f.stat().st_size if f.is_file() else "")


if __name__ == "__main__":
    main()
