from fastapi import APIRouter, Depends
from core import *
from models import *
import math

router = APIRouter()

def _parse_date(s: str):
    if not s:
        return None
    s = s.strip()
    if len(s) == 7:  # YYYY-MM
        s = s + "-01"
    try:
        return datetime.fromisoformat(s[:10]).replace(tzinfo=timezone.utc)
    except Exception:
        return None

def _verdict(pct_of_pace):
    if pct_of_pace is None:
        return "off"
    if pct_of_pace <= 1.1:
        return "on"
    if pct_of_pace <= 1.6:
        return "tight"
    return "off"

async def _compute_goal(uid: str, cid):
    """Cálculos 100% determinísticos no backend (a IA nunca inventa números)."""
    snap = await build_snapshot(uid)
    sym = snap["currency_symbol"]
    val = snap.get("valuation", {}) or {}
    current_value = float(snap.get("company_value", 0) or 0)
    current_revenue = val.get("annual_revenue")
    g = await db.goals.find_one({"user_id": uid, "company_id": cid}) or {}
    saved = {k: g.get(k) for k in ("target_value", "target_revenue", "deadline_type",
                                   "deadline_years", "deadline_date", "ytd_revenue", "ytd_as_of")}
    base = {"currency_symbol": sym, "current_value": round(current_value, 2),
            "current_revenue": current_revenue, "financials_source": snap.get("financials_source"),
            "value_sources": snap.get("value_sources"), "goal": saved}

    tv = float(g.get("target_value") or 0)
    tr = float(g.get("target_revenue") or 0)
    if not (tv > 0 or tr > 0):
        return {**base, "configured": False}

    now = datetime.now(timezone.utc)
    years_left = None
    if g.get("deadline_type") == "date" and g.get("deadline_date"):
        d = _parse_date(g["deadline_date"])
        if d:
            years_left = max(0.05, (d - now).days / 365.25)
    if years_left is None:
        years_left = max(0.05, float(g.get("deadline_years") or 3))

    ytd = float(g.get("ytd_revenue") or 0)
    aod = _parse_date(g.get("ytd_as_of")) or now
    months_elapsed = max(1, min(12, aod.month))
    annualized_revenue = round(ytd / months_elapsed * 12, 2) if ytd > 0 else float(current_revenue or 0)

    margin = None
    if val.get("annual_revenue") and val.get("annual_profit") is not None and val["annual_revenue"] > 0:
        margin = val["annual_profit"] / val["annual_revenue"]
    elif snap.get("profit_margin"):
        margin = float(snap["profit_margin"]) / 100.0
    annual_profit_proj = round((annualized_revenue * margin) if margin else float(val.get("annual_profit") or 0), 2)

    out = {**base, "configured": True, "years_left": round(years_left, 2),
           "months_elapsed": months_elapsed, "annualized_revenue": annualized_revenue,
           "annual_profit_projected": annual_profit_proj}

    value_block = None
    if tv > 0:
        gap = round(tv - current_value, 2)
        pct = round(min(100, current_value / tv * 100), 1) if tv else 0
        needed_py = round(gap / years_left, 2) if years_left > 0 else gap
        growth = annual_profit_proj if annual_profit_proj > 0 else 0
        years_at_pace = round(gap / growth, 1) if growth > 0 and gap > 0 else (0 if gap <= 0 else None)
        if gap <= 0:
            verdict = "reached"
        elif growth <= 0:
            verdict = "off"
        else:
            verdict = _verdict(years_at_pace / years_left if years_left > 0 else None)
        milestones = []
        n = max(1, math.ceil(years_left))
        for k in range(1, n + 1):
            milestones.append({"year": now.year + k, "target": round(min(tv, current_value + needed_py * k), 2)})
        value_block = {"target": tv, "gap": gap, "pct": pct, "needed_per_year": needed_py,
                       "growth_per_year": round(growth, 2), "years_at_pace": years_at_pace,
                       "verdict": verdict, "milestones": milestones}

    revenue_block = None
    if tr > 0:
        rgap = round(tr - annualized_revenue, 2)
        rpct = round(min(100, annualized_revenue / tr * 100), 1) if tr else 0
        needed_py_rev = round((tr - annualized_revenue) / years_left, 2) if years_left > 0 else rgap
        if annualized_revenue >= tr:
            rverdict = "reached"
        elif rpct >= 70:
            rverdict = "on"
        elif rpct >= 40:
            rverdict = "tight"
        else:
            rverdict = "off"
        revenue_block = {"target": tr, "projected_year_end": annualized_revenue, "gap": rgap,
                         "pct": rpct, "needed_per_year": needed_py_rev, "verdict": rverdict}

    out["value_goal"] = value_block
    out["revenue_goal"] = revenue_block
    return out

@router.get("/goal")
async def get_goal(user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    return await _compute_goal(uid, cid)

@router.post("/goal")
async def save_goal(inp: GoalInput, user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    data = {k: v for k, v in inp.model_dump().items() if v is not None}
    data.update({"user_id": uid, "company_id": cid, "updated_at": datetime.now(timezone.utc).isoformat()})
    await db.goals.update_one({"user_id": uid, "company_id": cid}, {"$set": data}, upsert=True)
    await db.ai_cache.delete_many({"user_id": uid, "kind": "goal_plan"})
    return {"ok": True}

@router.post("/goal/plan")
async def goal_plan(user: dict = Depends(premium_user)):
    """Plano do CEO por IA — gerado só sob pedido (botão), com cache diário."""
    uid = user["id"]; cid = await active_company_id(uid)
    out = await _compute_goal(uid, cid)
    if not out.get("configured"):
        return {"configured": False}
    sym = out["currency_symbol"]
    vg = out.get("value_goal") or {}
    tv = vg.get("target", 0)
    tr = (out.get("revenue_goal") or {}).get("target", 0)
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    prompt = (
        f"O empresário definiu metas para a empresa. Usa SÓ estes números REAIS (nunca inventes):\n"
        f"- Valor atual da empresa: {sym}{round(out['current_value'])}\n"
        f"- Meta de valor: {sym}{round(tv)} · Prazo: {round(out['years_left'], 1)} anos\n"
        f"- Faturação anualizada (ritmo atual, a partir do que já faturou este ano): {sym}{round(out['annualized_revenue'])}\n"
        f"- Meta de faturação anual: {sym}{round(tr)}\n"
        f"- Lucro anual projetado: {sym}{round(out['annual_profit_projected'])}\n"
        f"- Ao ritmo atual o valor cresce ~{sym}{round(vg.get('growth_per_year', 0))}/ano; "
        f"precisa de ~{sym}{round(vg.get('needed_per_year', 0))}/ano para cumprir o prazo.\n"
        "Devolve APENAS JSON: {\"diagnostico\":str,\"veredicto\":str,\"acoes\":[{\"acao\":str,\"impacto\":str}],\"frase\":str}. "
        "'diagnostico': 2-3 frases, dizendo se vai chegar à meta no prazo e porquê, com os números. "
        "'veredicto': 1 frase directa (ex: 'No bom caminho' ou 'Precisas de acelerar'). "
        "'acoes': 3 a 4 ações concretas e priorizadas para fechar a diferença, cada uma com 'impacto' estimado em " + sym + " ou %. "
        "'frase': 1 frase motivadora e realista. Português europeu. Sem texto fora do JSON."
    )
    plan = await cached_ai("goal_plan", uid, cid, sysmsg, prompt) or {}
    return {"configured": True, "ceo_plan": plan}
