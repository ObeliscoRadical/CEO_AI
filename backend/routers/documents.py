from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *
from core import _growth_score

router = APIRouter()

# ---------------------------------------------------------------- Investment Grade (PREMIUM)
def to_grade(score: float) -> str:
    for th, g in [(95, "A+"), (88, "A"), (82, "A-"), (75, "B+"), (68, "B"), (62, "B-"),
                  (55, "C+"), (48, "C"), (40, "C-"), (30, "D")]:
        if score >= th:
            return g
    return "F"

@router.get("/investment-grade")
async def investment_grade(user: dict = Depends(get_current_user)):
    if not await can_access_premium(user):
        raise HTTPException(status_code=402, detail="premium_required")
    snap = await build_snapshot(user["id"])
    company = await resolve_company(user["id"]) or {}
    cid = str(company["_id"]) if company.get("_id") else None
    entries = await db.entries.find({"user_id": user["id"], "company_id": cid}, {"type": 1, "amount": 1, "date": 1}).to_list(5000) if cid else []
    dna = await db.ceo_dna.find_one({"user_id": user["id"]}) or {}
    docs = await db.documents.find({"user_id": user["id"], "is_deleted": False}).to_list(500)
    doc_types = set(d.get("doc_type", "other") for d in docs)
    n_docs = len(docs)
    # Document AI insights — only count categories the AI actually verified as relevant
    verified_types = set(); figures = {}; insights = []
    for d in docs:
        a = d.get("analysis") or {}
        if a.get("relevant") and a.get("quality") in ("high", "medium"):
            verified_types.add(d.get("doc_type", "other"))
        for k, v in (a.get("figures") or {}).items():
            if isinstance(v, (int, float)) and v and k not in figures:
                figures[k] = v
        if a.get("summary"):
            insights.append({"filename": d.get("original_filename"), "doc_type": d.get("doc_type", "other"),
                             "quality": a.get("quality"), "relevant": bool(a.get("relevant")), "summary": a.get("summary")})

    inc, months_set = {}, set()
    for e in entries:
        mk = str(e.get("date", ""))[:7]
        if len(mk) == 7:
            months_set.add(mk)
            if e["type"] == "income":
                inc[mk] = inc.get(mk, 0) + e["amount"]
    sorted_m = sorted(inc.keys())
    growth_score = 50
    if len(sorted_m) >= 2:
        recent = sum(inc[m] for m in sorted_m[-3:])
        prior = sum(inc[m] for m in sorted_m[-6:-3])
        if prior > 0:
            growth_score = max(5, min(100, int(60 + ((recent - prior) / prior) * 100)))
        elif recent > 0:
            growth_score = 72
    coverage = len(months_set)
    emp = int(company.get("employees_count", 0)); cli = int(company.get("clients_count", 0))
    dependency_score = min(100, 28 + emp * 12 + (12 if cli > 5 else 0))
    liquidity_score = min(100, int(snap["runway"] * 14))
    risk_score = min(100, int(snap["runway"] * 12 + (20 if snap["profit_margin"] > 0 else 0)))
    fin_score = snap["health"]

    dims = [
        {"key": "financeiro", "label": "Financeiro", "score": fin_score},
        {"key": "crescimento", "label": "Crescimento", "score": growth_score},
        {"key": "risco", "label": "Risco", "score": risk_score},
        {"key": "liquidez", "label": "Liquidez", "score": liquidity_score},
        {"key": "dependencia", "label": "Dependência do Fundador", "score": dependency_score},
    ]
    for d in dims:
        d["grade"] = to_grade(d["score"])
    overall_score = round(sum(d["score"] for d in dims) / len(dims))
    overall_grade = to_grade(overall_score)

    checklist = [
        {"item": "Demonstrações financeiras completas", "upload_type": "financials", "done": "financials" in verified_types},
        {"item": "Histórico de EBITDA e fluxo de caixa (6+ meses)", "done": coverage >= 6 or bool(figures.get("ebitda"))},
        {"item": "Composição de ativos e passivos", "upload_type": "assets", "done": "assets" in verified_types or bool(figures.get("assets"))},
        {"item": "Contratos e qualidade da carteira de clientes", "upload_type": "contracts", "done": ("contracts" in verified_types) or cli > 0},
        {"item": "Avaliação de dependência do fundador", "done": bool(dna.get("completed")) and emp > 0},
    ]
    done = sum(1 for c in checklist if c["done"])
    completeness = round(done / len(checklist) * 100)
    has_real_financials = ("financials" in verified_types) and any(figures.get(k) for k in ("revenue", "ebitda", "net_profit"))
    if completeness >= 75 and has_real_financials:
        tier, margin = "Nível Profissional", 0.10
    elif completeness >= 40:
        tier, margin = "Estimativa Fundamentada", 0.20
    else:
        tier, margin = "Estimativa Inteligente", 0.35
    value = snap["company_value"]
    value_range = {"low": round(value * (1 - margin)), "high": round(value * (1 + margin))}
    next_target = round(value * 1.4) if value else snap["goal_value"]
    sym = snap["currency_symbol"]

    sysmsg = await build_system_prompt(user["id"], user.get("name", ""))
    grades_txt = ", ".join(f"{d['label']}: {d['grade']}" for d in dims)
    docs_block = ""
    if insights:
        lines = [f"- {i['filename']} [{i['doc_type']}, qualidade {i['quality']}]: {i['summary']}" for i in insights[:12]]
        docs_block = "\n\nDOCUMENTOS ANALISADOS PELA IA (usa estes dados reais na tua análise):\n" + "\n".join(lines)
        if figures:
            docs_block += "\nNúmeros extraídos dos documentos: " + json.dumps(figures, ensure_ascii=False)
    prompt = (
        f"Estás a produzir um RELATÓRIO DE INVESTIMENTO estilo agência de rating para esta empresa. "
        f"Valor estimado atual: {sym}{value} (intervalo {sym}{value_range['low']}–{sym}{value_range['high']}). "
        f"Rating global: {overall_grade}. Notas: {grades_txt}. "
        f"Nível de confiança dos dados: {tier} ({completeness}% completos).{docs_block} "
        f"Devolve APENAS JSON: {{\"rationale\":str, \"grade_notes\":{{\"financeiro\":str,\"crescimento\":str,\"risco\":str,\"liquidez\":str,\"dependencia\":str}}, "
        f"\"improvement_plan\":[{{\"action\":str,\"impact\":str}}], \"disclaimer\":str}}. "
        f"'rationale': explica em 2-3 frases PORQUE a empresa vale este valor, referindo os números reais dos documentos quando existam. "
        f"'grade_notes': 1 frase curta por dimensão a justificar a nota. "
        f"'improvement_plan': 3-4 ações concretas e priorizadas para subir o valor até {sym}{next_target}, cada uma com o impacto estimado. "
        f"'disclaimer': 1 frase — se o nível for 'Nível Profissional', diz que a avaliação foi fundamentada em documentos financeiros analisados; caso contrário, esclarece que é uma estimativa e não uma avaliação pericial oficial. "
        f"Tudo em português. Sem texto fora do JSON."
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"grade-{uuid.uuid4()}", system_message=sysmsg).with_model("openai", "gpt-5.4")
    ai = {}
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        ai = json.loads(text)
    except Exception as e:
        logger.error(f"grade error: {e}")
    notes = ai.get("grade_notes", {})
    fallback_why = {
        "financeiro": "Baseado na saúde financeira e margem de lucro atuais.",
        "crescimento": "Baseado na tendência de receita e na base de clientes.",
        "risco": "Baseado na autonomia de caixa e na rentabilidade.",
        "liquidez": "Baseado no saldo disponível face às despesas mensais.",
        "dependencia": "Baseado na estrutura de equipa e na maturidade operacional.",
    }
    for d in dims:
        d["why"] = notes.get(d["key"]) or fallback_why.get(d["key"], "")

    return {
        "overall_grade": overall_grade, "overall_score": overall_score,
        "dimensions": dims, "company_value": value, "value_range": value_range,
        "currency_symbol": sym, "next_target": next_target,
        "confidence": {"tier": tier, "score": completeness, "checklist": checklist},
        "documents_analyzed": len(insights),
        "document_insights": insights,
        "extracted_figures": figures,
        "rationale": ai.get("rationale", "Estimativa baseada nos dados financeiros e no perfil da empresa fornecidos."),
        "improvement_plan": ai.get("improvement_plan", []),
        "disclaimer": ai.get("disclaimer", "Esta é uma estimativa fundamentada nos dados fornecidos e nos documentos analisados, não uma avaliação pericial oficial."),
    }

# ---------------------------------------------------------------- docs
@router.post("/upload")
async def upload(file: UploadFile = File(...), doc_type: str = Form("other"), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    analysis = {}
    try:
        text = extract_document_text(data, file.content_type, file.filename)
        analysis = await analyze_document(text, doc_type, file.filename)
    except Exception as e:
        logger.error(f"doc analysis failed: {e}")
    res = await db.documents.insert_one({"user_id": user["id"], "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type, "doc_type": doc_type,
        "analysis": analysis,
        "size": result.get("size", len(data)), "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    await invalidate_ai_cache(user["id"])
    return {"id": str(res.inserted_id), "filename": file.filename, "doc_type": doc_type, "size": result.get("size", len(data)),
            "analysis": {"relevant": analysis.get("relevant"), "quality": analysis.get("quality"), "summary": analysis.get("summary")}}

@router.get("/documents")
async def list_docs(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"user_id": user["id"], "is_deleted": False}).sort("created_at", -1).to_list(500)
    return [{"id": str(d["_id"]), "filename": d.get("original_filename"), "doc_type": d.get("doc_type", "other"),
             "size": d.get("size", 0), "created_at": d.get("created_at"),
             "analysis": {"relevant": (d.get("analysis") or {}).get("relevant"),
                          "quality": (d.get("analysis") or {}).get("quality"),
                          "summary": (d.get("analysis") or {}).get("summary")}} for d in docs]

@router.delete("/documents/{doc_id}")
async def delete_doc(doc_id: str, user: dict = Depends(get_current_user)):
    await db.documents.update_one({"_id": ObjectId(doc_id), "user_id": user["id"]}, {"$set": {"is_deleted": True}})
    return {"ok": True}
