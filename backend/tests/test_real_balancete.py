import asyncio, json, sys
sys.path.insert(0, "/app/backend")
from core import extract_financial_document

async def main():
    data = open("/tmp/balancete.pdf", "rb").read()
    res = await extract_financial_document(data, "application/pdf", "BALANCETE_AAR_ANO 2025.pdf")
    print("=== RESULT ===")
    print(json.dumps(res, ensure_ascii=False, indent=2) if res else "None")
    if res:
        print("\n=== TOTALS ===")
        print(json.dumps(res.get("totals"), ensure_ascii=False, indent=2))
        print("year:", res.get("year"), "doc_type:", res.get("doc_type"), "lines:", len(res.get("lines") or []))

asyncio.run(main())
