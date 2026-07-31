import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Target, TrendingUp, Flag, Sparkles, CheckCircle2, AlertTriangle, Clock } from "lucide-react";

const VERDICT = {
  reached: { label: "Meta atingida", color: "#10B981", Icon: CheckCircle2 },
  on: { label: "No bom caminho", color: "#10B981", Icon: CheckCircle2 },
  tight: { label: "Justo — dá para acelerar", color: "#F59E0B", Icon: Clock },
  off: { label: "Precisas de acelerar", color: "#EF4444", Icon: AlertTriangle },
};

const fmt = (sym, n) => `${sym}${Number(n || 0).toLocaleString("pt-PT", { maximumFractionDigits: 0 })}`;

function VerdictBadge({ v, testid }) {
  const c = VERDICT[v] || VERDICT.off;
  return (
    <span data-testid={testid} className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full border"
      style={{ color: c.color, borderColor: `${c.color}55`, background: `${c.color}12` }}>
      <c.Icon className="w-3.5 h-3.5" /> {c.label}
    </span>
  );
}

function ProgressBar({ pct, color }) {
  return (
    <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, pct || 0)}%`, background: color }} />
    </div>
  );
}

export default function Metas() {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [planLoading, setPlanLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [form, setForm] = useState({
    target_value: "", target_revenue: "", ytd_revenue: "", ytd_as_of: "",
    deadline_type: "years", deadline_years: "3", deadline_date: "",
  });

  const load = () => api.get("/goal").then(({ data }) => {
    setData(data);
    const g = data.goal || {};
    setForm((f) => ({
      target_value: g.target_value ?? "",
      target_revenue: g.target_revenue ?? "",
      ytd_revenue: g.ytd_revenue ?? "",
      ytd_as_of: (g.ytd_as_of || "").slice(0, 7),
      deadline_type: g.deadline_type || "years",
      deadline_years: g.deadline_years != null ? String(g.deadline_years) : "3",
      deadline_date: (g.deadline_date || "").slice(0, 7),
    }));
  }).catch(() => setFailed(true));

  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        target_value: form.target_value ? Number(form.target_value) : null,
        target_revenue: form.target_revenue ? Number(form.target_revenue) : null,
        ytd_revenue: form.ytd_revenue ? Number(form.ytd_revenue) : null,
        ytd_as_of: form.ytd_as_of || null,
        deadline_type: form.deadline_type,
        deadline_years: form.deadline_type === "years" && form.deadline_years ? Number(form.deadline_years) : null,
        deadline_date: form.deadline_type === "date" && form.deadline_date ? form.deadline_date : null,
      };
      if (!payload.target_value && !payload.target_revenue) {
        toast.error("Define pelo menos uma meta (valor ou faturação).");
        setSaving(false); return;
      }
      await api.post("/goal", payload);
      setPlan(null);
      await load();
      toast.success("Meta guardada. Já calculei o teu ritmo.");
    } catch { toast.error("Não foi possível guardar a meta."); }
    setSaving(false);
  };

  const generatePlan = async () => {
    setPlanLoading(true);
    try {
      const { data } = await api.post("/goal/plan");
      setPlan(data.ceo_plan || {});
    } catch { toast.error("Não foi possível gerar o plano agora."); }
    setPlanLoading(false);
  };

  if (failed) return <div className="text-center py-40 text-muted-foreground" data-testid="meta-error">Não foi possível carregar as tuas metas. Atualiza a página.</div>;
  if (!data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  const sym = data.currency_symbol;
  const vg = data.value_goal, rg = data.revenue_goal;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[980px] mx-auto" data-testid="metas-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">A Minha Meta</p>
      <div className="mb-10">
        <h1 className="font-serif-lux text-4xl md:text-5xl text-[#3B82F6] flex items-center gap-3"><Target className="w-8 h-8" /> Aonde queres chegar</h1>
        <p className="text-muted-foreground mt-3">Define o valor e a faturação que queres atingir, diz-me quanto já faturaste este ano, e eu calculo o ritmo necessário e o que fazer.</p>
      </div>

      {/* Formulário */}
      <div className="surface rounded-3xl p-6 md:p-8 mb-10" data-testid="meta-form">
        <h2 className="font-serif-lux text-2xl mb-6">As tuas metas</h2>
        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <Label className="text-sm text-muted-foreground">Meta de valor da empresa ({sym})</Label>
            <Input data-testid="input-target-value" type="number" value={form.target_value} onChange={set("target_value")} placeholder="ex: 1000000" className="mt-1.5" />
          </div>
          <div>
            <Label className="text-sm text-muted-foreground">Meta de faturação anual ({sym})</Label>
            <Input data-testid="input-target-revenue" type="number" value={form.target_revenue} onChange={set("target_revenue")} placeholder="ex: 500000" className="mt-1.5" />
          </div>
          <div>
            <Label className="text-sm text-muted-foreground">Faturação já feita este ano ({sym})</Label>
            <Input data-testid="input-ytd-revenue" type="number" value={form.ytd_revenue} onChange={set("ytd_revenue")} placeholder="acumulado até à data" className="mt-1.5" />
          </div>
          <div>
            <Label className="text-sm text-muted-foreground">Até que mês se refere</Label>
            <Input data-testid="input-ytd-asof" type="month" value={form.ytd_as_of} onChange={set("ytd_as_of")} className="mt-1.5" />
          </div>
        </div>

        <div className="mt-6">
          <Label className="text-sm text-muted-foreground">Prazo</Label>
          <div className="flex gap-2 mt-1.5 mb-3">
            <button data-testid="deadline-type-years" onClick={() => setForm((f) => ({ ...f, deadline_type: "years" }))}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${form.deadline_type === "years" ? "bg-[#3B82F6] text-white border-transparent" : "border-white/10 text-muted-foreground hover:text-white"}`}>Por nº de anos</button>
            <button data-testid="deadline-type-date" onClick={() => setForm((f) => ({ ...f, deadline_type: "date" }))}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${form.deadline_type === "date" ? "bg-[#3B82F6] text-white border-transparent" : "border-white/10 text-muted-foreground hover:text-white"}`}>Por data alvo</button>
          </div>
          {form.deadline_type === "years" ? (
            <Input data-testid="input-deadline-years" type="number" min="0.5" step="0.5" value={form.deadline_years} onChange={set("deadline_years")} placeholder="ex: 3" className="max-w-[220px]" />
          ) : (
            <Input data-testid="input-deadline-date" type="month" value={form.deadline_date} onChange={set("deadline_date")} className="max-w-[220px]" />
          )}
        </div>

        <Button data-testid="save-meta-btn" onClick={save} disabled={saving} className="mt-7 rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Guardar meta e calcular
        </Button>
      </div>

      {!data.configured ? (
        <div className="surface rounded-3xl p-8 text-center text-muted-foreground" data-testid="meta-empty">
          Define pelo menos uma meta acima e eu mostro-te quanto falta, o ritmo necessário e um plano concreto.
        </div>
      ) : (
        <>
          {/* Ponto de partida */}
          <div className="grid md:grid-cols-3 gap-4 mb-10" data-testid="meta-snapshot">
            <div className="surface rounded-2xl p-5">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Valor atual</div>
              <div className="font-serif-lux text-2xl text-[#3B82F6]" data-testid="meta-current-value">{fmt(sym, data.current_value)}</div>
              {data.value_sources?.patrimonio && <div className="text-[11px] text-muted-foreground mt-1">fonte: {data.value_sources.patrimonio}</div>}
            </div>
            <div className="surface rounded-2xl p-5">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Faturação ao ritmo atual</div>
              <div className="font-serif-lux text-2xl" data-testid="meta-annualized-revenue">{fmt(sym, data.annualized_revenue)}</div>
              <div className="text-[11px] text-muted-foreground mt-1">projeção anual a partir do que já faturaste ({data.months_elapsed} {data.months_elapsed === 1 ? "mês" : "meses"})</div>
            </div>
            <div className="surface rounded-2xl p-5">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Prazo</div>
              <div className="font-serif-lux text-2xl" data-testid="meta-years-left">{data.years_left} anos</div>
              <div className="text-[11px] text-muted-foreground mt-1">lucro anual projetado: {fmt(sym, data.annual_profit_projected)}</div>
            </div>
          </div>

          {/* Meta de valor */}
          {vg && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-3xl p-6 md:p-8 mb-6" data-testid="value-goal-card">
              <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
                <h3 className="font-serif-lux text-2xl flex items-center gap-2"><Flag className="w-5 h-5 text-[#3B82F6]" /> Meta de valor: {fmt(sym, vg.target)}</h3>
                <VerdictBadge v={vg.verdict} testid="value-goal-verdict" />
              </div>
              <ProgressBar pct={vg.pct} color="#3B82F6" />
              <div className="flex justify-between text-sm text-muted-foreground mt-2 mb-6">
                <span>{vg.pct}% do caminho</span>
                <span data-testid="value-goal-gap">Falta {fmt(sym, Math.max(0, vg.gap))}</span>
              </div>
              <div className="grid sm:grid-cols-3 gap-4 text-sm">
                <div><div className="text-muted-foreground">Ritmo necessário</div><div className="font-medium text-foreground" data-testid="value-needed-per-year">{fmt(sym, vg.needed_per_year)}/ano</div></div>
                <div><div className="text-muted-foreground">Ritmo atual (crescimento)</div><div className="font-medium text-foreground">{fmt(sym, vg.growth_per_year)}/ano</div></div>
                <div><div className="text-muted-foreground">Ao ritmo atual chegas em</div><div className="font-medium text-foreground">{vg.verdict === "reached" ? "Já atingiste" : vg.years_at_pace != null ? `${vg.years_at_pace} anos` : "não estás a crescer"}</div></div>
              </div>
              {vg.milestones?.length > 0 && (
                <div className="mt-6">
                  <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Trajetória necessária</div>
                  <div className="flex flex-wrap gap-2" data-testid="value-milestones">
                    {vg.milestones.map((m, i) => (
                      <div key={i} className="px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm">
                        <span className="text-muted-foreground">{m.year}:</span> <span className="font-medium">{fmt(sym, m.target)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Meta de faturação */}
          {rg && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-3xl p-6 md:p-8 mb-10" data-testid="revenue-goal-card">
              <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
                <h3 className="font-serif-lux text-2xl flex items-center gap-2"><TrendingUp className="w-5 h-5 text-[#10B981]" /> Meta de faturação: {fmt(sym, rg.target)}/ano</h3>
                <VerdictBadge v={rg.verdict} testid="revenue-goal-verdict" />
              </div>
              <ProgressBar pct={rg.pct} color="#10B981" />
              <div className="flex justify-between text-sm text-muted-foreground mt-2 mb-6">
                <span>{rg.pct}% da meta (projeção deste ano: {fmt(sym, rg.projected_year_end)})</span>
                <span data-testid="revenue-goal-gap">Falta {fmt(sym, Math.max(0, rg.gap))}</span>
              </div>
              <div className="text-sm"><span className="text-muted-foreground">Precisas de crescer a faturação em </span><span className="font-medium">{fmt(sym, rg.needed_per_year)}/ano</span><span className="text-muted-foreground"> para cumprir o prazo.</span></div>
            </motion.div>
          )}

          {/* Plano do CEO (sob pedido) */}
          <div className="surface rounded-3xl p-6 md:p-8" data-testid="ceo-plan-section">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
              <h3 className="font-serif-lux text-2xl flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#3B82F6]" /> Plano do CEO para atingir a meta</h3>
              <Button data-testid="generate-plan-btn" onClick={generatePlan} disabled={planLoading} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
                {planLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
                {plan ? "Gerar de novo" : "Gerar plano do CEO"}
              </Button>
            </div>
            {!plan && !planLoading && <p className="text-muted-foreground text-sm">Carrega no botão e eu analiso os teus números e digo-te exatamente o que fazer para chegar à meta no prazo.</p>}
            {plan && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5 mt-2" data-testid="ceo-plan">
                {plan.veredicto && <div className="text-lg font-medium text-[#3B82F6]" data-testid="plan-verdict">{plan.veredicto}</div>}
                {plan.diagnostico && <p className="text-muted-foreground" data-testid="plan-diagnostic">{plan.diagnostico}</p>}
                {Array.isArray(plan.acoes) && (
                  <div className="space-y-3">
                    {plan.acoes.map((a, i) => (
                      <div key={i} className="flex items-start gap-3 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06]" data-testid={`plan-action-${i}`}>
                        <div className="w-6 h-6 rounded-lg bg-[#3B82F6]/15 text-[#3B82F6] flex items-center justify-center text-sm font-semibold shrink-0">{i + 1}</div>
                        <div className="flex-1">
                          <div className="font-medium">{a.acao}</div>
                          {a.impacto && <div className="text-sm text-[#10B981] mt-0.5">Impacto: {a.impacto}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {plan.frase && <p className="italic text-foreground/80 border-l-2 border-[#3B82F6] pl-4" data-testid="plan-phrase">{plan.frase}</p>}
              </motion.div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
