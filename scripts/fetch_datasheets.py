"""Download the datasheets this design cites into datasheets/ and extract text beside them.
Tries each URL in turn and keeps the first response that is really a PDF.
  python scripts/fetch_datasheets.py
"""
import urllib.request
from pathlib import Path

from pypdf import PdfReader

OUT = Path(__file__).resolve().parents[1] / "datasheets"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SHEETS = {
    "esp32-s3-mini-1_datasheet": ["https://www.espressif.com/sites/default/files/documentation/esp32-s3-mini-1_mini-1u_datasheet_en.pdf"],
    "MCP73831": ["https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf"],
    "T3902": ["https://invensense.tdk.com/wp-content/uploads/2020/05/DS-000357-T3902-v1.0.pdf",
              "https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/ds-000357-t3902-v1.1.pdf",
              "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2401291125_TDK-InvenSense-MMICT390200012_C3171752.pdf"],
    "RT9080": ["https://www.richtek.com/assets/product_file/RT9080/DS9080-06.pdf",
               "https://www.richtek.com/assets/product_file/RT9080/DS9080-04.pdf",
               "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2009192305_Richtek-Tech-RT9080-33GJ5_C841192.pdf"],
    "DW01A": ["https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_PUOLOP-DW01A_C351410.pdf"],
    "FS8205A": ["https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2010271837_FUXINSEMI-FS8205A_C908265.pdf"],
    "TS-1088": ["https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_XUNPU-TS-1088-AR02016_C720477.pdf"],
    "TYPE-C-31-M-12": ["https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2205251630_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf"],
    "USBLC6-2": ["https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2410121836_STMicroelectronics-USBLC6-2SC6_C7519.pdf"],
}


def fetch(name, urls):
    pdf = OUT / f"{name}.pdf"
    if not pdf.exists():
        for u in urls:
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
                    data = r.read()
            except Exception as e:
                print(f"  {name}: {u} -> {e}")
                continue
            if data[:4] == b"%PDF":
                pdf.write_bytes(data)
                break
            print(f"  {name}: {u} -> not a PDF ({data[:40]!r})")
        else:
            return print(f"{name:28} FAILED")
    text = "\n".join(f"--- page {i + 1} ---\n{pg.extract_text() or ''}" for i, pg in enumerate(PdfReader(pdf).pages))
    (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
    print(f"{name:28} ok  {pdf.stat().st_size:>8} bytes, {len(text):>7} chars of text")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for n, u in SHEETS.items():
        fetch(n, u)
