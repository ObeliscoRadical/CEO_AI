import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Loader2, Target, TrendingUp, Sparkles, AlertTriangle, MapPin, Flag,
  Gauge, ArrowUpRight, Wallet, Percent, LineChart, CheckCircle2, Clock,
} from "lucide-react";

const fmt = (sym, n) => `${sym}${Number(n || 0).toLocaleString("pt-PT", { maximumFractionDigits: 0 })}`;
const PRESETS = [1, 2, 3, 5, 7, 10];

const VIAB = {
  green: { color: "#10B981", Icon: CheckCircle2 },
  amber: { color: "#F59E0B", Icon: Clock },
  red: { color: "#EF4444", Icon: AlertTriangle },
};

function ProgressBar({ pct, color }) {
  return (
    <div className="h-2.5 rounded-full bg-white/[0.06] overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, pct || 0)}%`, background: color }} />
    </div>
  );
}

function StatCard({ label, value, sub, color, testid, Icon }) {
  return (
    <div className="surface rounded-2xl p-5" data-testid={testid}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground mb-2">
        {Icon && <Icon className="w-3.5 h-3.5" style={{ color }} />} {label}
      </div>
      <div className="font-serif-lux text-2xl md:text-[26px]" style={{ color: color || undefined }}>{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground mt-1.5">{sub}</div>}
    </div>
  );
}

export default function Metas() {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [planLoading, setPlanLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [targetValue, setTargetValue] = useState("");
  const [years, setYears] = useState(5);
  const [custom, setCustom] = useState(false);

  const load = () => api.get("/goal").then(({ data }) => {
    setData(data);
    const g = data.goal || {};
    if (g.target_value != null) setTargetValue(String(g.target_value));
    if (g.deadline_years != null) {
      setYears(Number(g.deadline_years));
      setCustom(!PRESETS.includes(Number(g.deadline_years)));
    }
  }).catch(() => setFailed(true));

  useEffect(() => { load(); }, []);

  const calc = async () => {
    if (!targetValue || Number(targetValue) <= 0) { toast.error("Indique o valor que pretende alcançar."); return; }
    setSaving(true);
    try {
      await api.post("/goal", { target_value: Number(targetValue), deadline_type: "years", deadline_years: Number(years) });
      setPlan(null);
      await load();
      toast.success("Projeção calculada com os seus dados reais.");
    } catch { toast.error("Não foi possível calcular a projeção."); }
    setSaving(false);
  };

  const generatePlan = async () => {
    setPlanLoading(true);
    try {
      const { data } = await api.post("/goal/plan");
      setPlan(data.ceo_plan || {});
    } catch { toast.error("Não foi possível gerar a perspetiva agora."); }
    setPlanLoading(false);
  };

  if (failed) return <div className="text-center py-40 text-muted-foreground" data-testid="meta-error">Não foi possível carregar. Atualiza a página.</div>;
  if (!data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  const sym = data.currency_symbol;
  const cfg = data.configured;
  const req = data.required || {};
  const viab = data.viability ? (VIAB[data.viability.level] || VIAB.amber) : null;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1040px] mx-auto" data-testid="metas-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Metas e Projeções</p>
      <div className="mb-10">
        <h1 className="font-serif-lux text-4xl md:text-5xl text-[#3B82F6] flex items-center gap-3">
          <LineChart className="w-8 h-8" /> Projeção de Valor da Empresa
        </h1>
        <p className="text-muted-foreground mt-3">Planeie o futuro da sua empresa com base nos seus dados reais.</p>
      </div>

      {/* Dados em falta */}
      {data.missing?.length > 0 && (
        <div className="rounded-2xl border border-[#F59E0B]/30 bg-[#F59E0B]/[0.06] p-5 mb-8" data-testid="meta-missing">
          <div className="flex items-center gap-2 text-[#F59E0B] font-medium mb-2"><AlertTriangle className="w-4 h-4" /> Faltam dados para uma projeção fiável</div>
          <ul className="text-sm text-muted-foreground space-y-1">
            {data.missing.map((m, i) => (
              <li key={i}>• <span className="text-foreground">{m.label}</span> — preencha em <span className="text-[#3B82F6]">{m.where}</span></li>
            ))}
          </ul>
        </div>
      )}

      {/* Pergunta ao utilizador */}
      <div className="surface rounded-3xl p-6 md:p-8 mb-10" data-testid="meta-form">
        <h2 className="font-serif-lux text-2xl mb-1">Qual é o valor que pretende alcançar?</h2>
        <p className="text-sm text-muted-foreground mb-5">Esta é uma meta de <span className="text-foreground font-medium">valor da empresa</span> — não de faturação.</p>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <Label className="text-sm text-muted-foreground">Meta de valor da empresa ({sym})</Label>
            <Input data-testid="input-target-value" type="number" value={targetValue} onChange={(e) => setTargetValue(e.target.value)} placeholder="ex: 750000" className="mt-1.5 text-lg" />
          </div>
          <div>
            <Label className="text-sm text-muted-foreground">Em quanto tempo pretende alcançar?</Label>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {PRESETS.map((y) => (
                <button key={y} data-testid={`years-${y}`} onClick={() => { setYears(y); setCustom(false); }}
                  className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${!custom && years === y ? "bg-[#3B82F6] text-white border-transparent" : "border-white/10 text-muted-foreground hover:text-white"}`}>
                  {y} {y === 1 ? "ano" : "anos"}
                </button>
              ))}
              <button data-testid="years-custom" onClick={() => setCustom(true)}
                className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${custom ? "bg-[#3B82F6] text-white border-transparent" : "border-white/10 text-muted-foreground hover:text-white"}`}>
                Personalizado
              </button>
            </div>
            {custom && (
              <Input data-testid="input-custom-years" type="number" min="0.5" step="0.5" value={years} onChange={(e) => setYears(e.target.value)} className="mt-3 max-w-[160px]" placeholder="anos" />
            )}
          </div>
        </div>
        <Button data-testid="calc-projection-btn" onClick={calc} disabled={saving} className="mt-7 rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Gauge className="w-4 h-4 mr-2" />} Calcular Projeção
        </Button>
      </div>

      {/* Património vs Valor */}
      <div className="grid sm:grid-cols-2 gap-4 mb-10" data-testid="meta-value-vs-networth">
        <StatCard testid="meta-networth" Icon={Wallet} label="Património Líquido (ativos − passivos)" color="#A78BFA"
          value={fmt(sym, data.net_worth)} sub="Base contabilística — não é o valor de mercado." />
        <StatCard testid="meta-current-value" Icon={Target} label="Valor Estimado da Empresa" color="#3B82F6"
          value={fmt(sym, data.current_value)}
          sub={data.value_sources?.patrimonio ? `motor de avaliação · fonte: ${data.value_sources.patrimonio}` : "motor de avaliação (património + rendimento)"} />
      </div>

      {!cfg ? (
        <div className="surface rounded-3xl p-8 text-center text-muted-foreground" data-testid="meta-empty">
          Defina o valor que pretende alcançar e o prazo acima, e eu faço a engenharia inversa: quanto precisa de faturar, lucrar e crescer para lá chegar.
        </div>
      ) : (
        <>
          {/* Resumo principal — 3 cartões */}
          <div className="grid md:grid-cols-3 gap-4 mb-6" data-testid="meta-summary">
            <div className="surface rounded-2xl p-5 border border-[#10B981]/25" data-testid="summary-goal">
              <div className="text-xs uppercase tracking-wider text-[#10B981] mb-1">Valor alcançando a meta</div>
              <div className="font-serif-lux text-3xl text-[#10B981]">{fmt(sym, data.target_value)}</div>
              <div className="text-[11px] text-muted-foreground mt-1">em {data.years_left} anos</div>
            </div>
            <div className="surface rounded-2xl p-5" data-testid="summary-pace">
              <div className="text-xs uppercase tracking-wider text-[#F59E0B] mb-1">Mantendo o ritmo atual</div>
              <div className="font-serif-lux text-3xl text-[#F59E0B]">{fmt(sym, data.projected_pace)}</div>
              <div className="text-[11px] text-muted-foreground mt-1">crescimento ~{fmt(sym, data.pace_growth_per_year)}/ano</div>
            </div>
            <div className="surface rounded-2xl p-5" data-testid="summary-difference">
              <div className="text-xs uppercase tracking-wider text-[#3B82F6] mb-1">Diferença — Oportunidade</div>
              <div className="font-serif-lux text-3xl text-[#3B82F6]">{fmt(sym, Math.max(0, data.difference))}</div>
              <div className="text-[11px] text-muted-foreground mt-1">quanto vale acelerar</div>
            </div>
          </div>

          {/* Mensagem dinâmica + viabilidade */}
          <div className="surface rounded-2xl p-5 mb-10 flex items-start gap-4 flex-wrap" data-testid="meta-obstacle">
            <div className="flex-1 min-w-[240px]">
              <div className="text-sm text-foreground">{data.obstacle?.message}</div>
            </div>
            {viab && (
              <span data-testid="meta-viability" className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full border shrink-0"
                style={{ color: viab.color, borderColor: `${viab.color}55`, background: `${viab.color}12` }}>
                <viab.Icon className="w-3.5 h-3.5" /> {data.viability.label}
              </span>
            )}
          </div>

          {/* GPS estratégico */}
          <div className="surface rounded-3xl p-6 md:p-8 mb-10" data-testid="meta-gps">
            <h3 className="font-serif-lux text-2xl flex items-center gap-2 mb-6"><MapPin className="w-5 h-5 text-[#3B82F6]" /> GPS estratégico</h3>
            <div className="grid sm:grid-cols-3 gap-4 mb-6">
              <div><div className="text-xs text-muted-foreground mb-1">Está aqui</div><div className="font-medium text-lg">{fmt(sym, data.current_value)}</div></div>
              <div><div className="text-xs text-muted-foreground mb-1">Se mantiver o ritmo</div><div className="font-medium text-lg text-[#F59E0B]">{fmt(sym, data.projected_pace)}</div></div>
              <div><div className="text-xs text-muted-foreground mb-1">Meta escolhida</div><div className="font-medium text-lg text-[#10B981]">{fmt(sym, data.target_value)}</div></div>
            </div>
            <ProgressBar pct={data.progress} color="#3B82F6" />
            <div className="flex flex-wrap justify-between gap-2 text-sm text-muted-foreground mt-2">
              <span data-testid="gps-progress">{data.progress}% já alcançado</span>
              <span>Falta {fmt(sym, Math.max(0, data.target_value - data.current_value))}</span>
              <span>{data.years_left} anos restantes</span>
            </div>
          </div>

          {/* O que precisa de fazer */}
          <h3 className="font-serif-lux text-2xl mb-4 flex items-center gap-2"><Flag className="w-5 h-5 text-[#3B82F6]" /> O que precisa de fazer para alcançar a meta</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4" data-testid="meta-actions">
            <StatCard testid="action-profit" Icon={TrendingUp} color="#10B981" label="Lucro líquido necessário"
              value={req.required_profit != null ? `${fmt(sym, req.required_profit)}/ano` : "—"} />
            <StatCard testid="action-revenue" Icon={ArrowUpRight} color="#3B82F6" label="Faturação necessária"
              value={req.required_revenue != null ? `${fmt(sym, req.required_revenue)}/ano` : "—"} />
            <StatCard testid="action-monthly" Icon={ArrowUpRight} color="#3B82F6" label="Faturação mensal necessária"
              value={req.required_monthly_revenue != null ? `${fmt(sym, req.required_monthly_revenue)}/mês` : "—"} />
            <StatCard testid="action-growth" Icon={TrendingUp} color="#A78BFA" label="Crescimento necessário"
              value={req.required_growth_total != null ? `+${req.required_growth_total}%` : "—"}
              sub={req.required_growth_annual != null ? `~${req.required_growth_annual}%/ano` : null} />
            <StatCard testid="action-margin" Icon={Percent} color="#F59E0B" label="Margem necessária"
              value={req.assumed_margin != null ? `${req.assumed_margin}%` : "—"}
              sub={req.margin_assumed ? "assumida (falta margem real)" : "manter a margem atual"} />
            <StatCard testid="action-monthly-diff" Icon={ArrowUpRight} color="#3B82F6" label="Diferença mensal"
              value={req.monthly_diff != null ? `${req.monthly_diff >= 0 ? "+" : ""}${fmt(sym, req.monthly_diff)}/mês` : "—"} />
          </div>

          {/* Perspetiva do CEO AI (sob pedido) */}
          <div className="surface rounded-3xl p-6 md:p-8 mt-8" data-testid="ceo-plan-section">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
              <h3 className="font-serif-lux text-2xl flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#3B82F6]" /> Perspetiva do CEO AI</h3>
              <Button data-testid="generate-plan-btn" onClick={generatePlan} disabled={planLoading} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
                {planLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
                {plan ? "Gerar de novo" : "Pedir perspetiva do CEO"}
              </Button>
            </div>
            {!plan && !planLoading && <p className="text-muted-foreground text-sm">Carregue no botão e eu analiso os seus números reais e o seu setor para lhe dizer exatamente o que fazer para chegar à meta no prazo.</p>}
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

          <p className="text-[11px] text-muted-foreground mt-8" data-testid="meta-disclaimer">
            Esta projeção é uma estimativa estratégica baseada nos dados introduzidos e não constitui uma avaliação financeira, contabilística ou jurídica independente.
          </p>
        </>
      )}
    </div>
  );
}
