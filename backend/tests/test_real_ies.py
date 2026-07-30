import asyncio, json, sys
sys.path.insert(0, "/app/backend")
from core import extract_financial_document

async def main():
    data = open("/tmp/ies2025.pdf", "rb").read()
    res = await extract_financial_document(data, "application/pdf", "ies 2025.pdf")
    if not res:
        print("None"); return
    print("doc_type:", res.get("doc_type"), "year:", res.get("year"),
          "reconciled:", res.get("reconciled"), "diff:", res.get("reconciliation_diff"),
          "lines:", len(res.get("lines") or []))
    print(json.dumps(res.get("totals"), ensure_ascii=False, indent=2))

asyncio.run(main())
