"""Query the JLCPCB parts API: python jlc_search.py "keyword" ["keyword" ...]
Prints LCSC code, model, brand, package, stock, library type (basic/expand), description."""
import json, sys, urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(kw, n=8):
    body = json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    return (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []

for kw in sys.argv[1:]:
    print(f"## {kw}")
    try:
        rows = search(kw)
    except Exception as e:
        print("  ERROR", e); continue
    for c in rows:
        if c["componentCode"].startswith("C99"):  # JLC internal placeholder rows
            continue
        print(f"  {c['componentCode']:>10} | {c['componentModelEn'][:34]:34} | {(c.get('componentBrandEn') or '')[:16]:16} | "
              f"{(c.get('componentSpecificationEn') or '')[:18]:18} | stk {c['stockCount']:>7} | {c['componentLibraryType']:6} | "
              f"{(c.get('describe') or c.get('componentName') or '')[:70]}")
