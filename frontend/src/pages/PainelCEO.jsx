import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { DecisionCard } from "@/components/DecisionCard";
import { LockedBlock } from "@/components/Premium";
import { Watermark } from "@/components/Watermark";
import { motion } from "framer-motion";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Loader2, HeartPulse, Coins, TrendingUp, TrendingDown, Landmark, Waves, ArrowRight, Sparkles, AlertTriangle, Flag, AlertOctagon, ShieldAlert, Lightbulb, Target, Info } from "lucide-react";

const STATUS = { green: "#10B981", amber: "#F59E0B", red: "#EF4444", gold: "#3B82F6" };
const fmt = (n) => Number(n || 0).toLocaleString("pt-PT", { useGrouping: "always", maximumFractionDigits: 0 });
const SIGNAL = {
  critical: { Icon: AlertOctagon, color: "#EF4444" },
  attention: { Icon: AlertTriangle, color: "#F59E0B" },
  positive: { Icon: TrendingUp, color: "#10B981" },
  risk: { Icon: ShieldAlert, color: "#F97316" },
  opportunity: { Icon: Lightbulb, color: "#3B82F6" },
};

export default function PainelCEO() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [sig, setSig] = useState(null);
  const [bal, setBal] = useState(null);
  const [hist, setHist] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => Promise.all([
    api.get("/ceo-daily").then(({ data }) => setData(data)).catch(() => {}),
    api.get("/signals").then(({ data }) => setSig(data)).catch(() => {}),
    api.get("/dashboard").then(({ data }) => setBal(data)).catch(() => {}),
    api.get("/equity-history").then(({ data }) => setHist(data)).catch(() => {}),
  ]).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const act = async (d, status) => {
    setData((p) => ({ ...p, recomendacoes: p.recomendacoes.filter((x) => x.key !== d.key) }));
    api.post("/decisions/act", { key: d.key, title: d.title, status }).catch(() => {});
  };
  const explain = (d) => navigate("/ceo", { state: { ask: `Sobre "${d.title}": ${d.why} — o que me recomendas fazer?` } });

  if (loading || !data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  const hour = new Date().getHours();
  const greet = hour < 12 ? "Bom dia" : hour < 20 ? "Boa tarde" : "Boa noite";
  const sym = data.currency_symbol || "€";
  const v = data.vitals;
  const c = data.conclusao || {};
  const health = v?.saude?.value ?? 0;
  const mood = health >= 75 ? "emerald" : health >= 45 ? "gold" : "amber";
  const count = sig?.count || 0;

  const vitalCards = [
    { ...v.saude, Icon: HeartPulse, display: `${v.saude.value}`, suffix: "/100", onClick: () => navigate("/saude") },
    { ...v.valor, Icon: Coins, display: `${sym}${Number(v.valor.value).toLocaleString("pt-PT")}`, suffix: "", onClick: () => navigate("/valor") },
    { ...v.crescimento, Icon: TrendingUp, display: `${v.crescimento.value}`, suffix: "%", onClick: () => navigate("/futuro") },
    { ...v.tesouraria, Icon: Landmark, display: v.tesouraria.value, suffix: "", onClick: () => navigate("/financas") },
    { ...v.fluxo, Icon: Waves, display: v.fluxo.value, suffix: "", onClick: () => navigate("/financas") },
  ];

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1100px] mx-auto">
      {/* Greeting */}
      <div className="relative flex items-start gap-5 mb-14 pt-4">
        <Watermark text={data.company_name} />
        <CEOOrb size={72} mood={mood} className="shrink-0 hidden sm:block relative z-10" />
        <div className="relative z-10">
          <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="font-serif-lux text-4xl md:text-6xl leading-[1.05] tracking-tight" data-testid="ceo-greeting">
            {greet}, {data.user_name?.split(" ")[0]}
          </motion.h1>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-[0.2em] mt-3">
            {new Date().toLocaleDateString("pt-PT", { weekday: "long", day: "numeric", month: "long" })}
          </p>
          <p className="text-muted-foreground mt-2 text-base md:text-lg">
            {count > 0 ? `Hoje tenho ${count} ${count === 1 ? "alerta importante" : "alertas importantes"}.` : "Analisei toda a tua empresa. Aqui está o que importa."}
          </p>
        </div>
      </div>

      {/* Signals — sharp quantified alerts */}
      {sig?.signals?.length > 0 && (
        <div className="mb-16" data-testid="signals-section">
          <div className="space-y-3">
            {sig.signals.map((s, i) => {
              const cfg = SIGNAL[s.type] || SIGNAL.attention;
              return (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                  className="surface rounded-2xl p-5 flex items-start gap-4" data-testid={`signal-${i}`}>
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${cfg.color}1a` }}>
                    <cfg.Icon className="w-5 h-5" style={{ color: cfg.color }} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[15px] md:text-base font-medium leading-snug">{s.text}</p>
                    {s.detail && <p className="text-sm text-muted-foreground mt-1">{s.detail}</p>}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {sig.priority?.text ? (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="rounded-2xl p-6 mt-4 border border-[#3B82F6]/30" style={{ background: "rgba(59,130,246,0.06)" }} data-testid="signal-priority">
              <div className="flex items-center gap-2 text-[#3B82F6] mb-2"><Target className="w-4 h-4" /><span className="text-xs uppercase tracking-[0.18em]">Prioridade máxima de hoje</span></div>
              <p className="text-lg font-medium">{sig.priority.text}</p>
              {sig.priority.why && <p className="text-sm text-muted-foreground mt-1">{sig.priority.why}</p>}
            </motion.div>
          ) : sig?.premium_locked ? (
            <div className="mt-4"><LockedBlock title="Prioridade máxima de hoje" description="A prioridade nº1 do teu dia faz parte dos planos pagos." /></div>
          ) : null}
        </div>
      )}

      {/* Balanço & Património */}
      {bal && (
        <div className="mb-16" data-testid="value-card">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground mb-5">Balanço &amp; Património</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <BalTile label="Caixa disponível" value={`${sym}${fmt(bal.cash_available)}`} color="#3B82F6" testid="bal-cash" />
            <BalTile label="Total de ativos" value={`${sym}${fmt(bal.total_assets)}`} color="#10B981" testid="bal-assets" />
            <BalTile label="Total de passivos" value={`${sym}${fmt(bal.total_liabilities)}`} color="#EF4444" testid="bal-liabilities" />
            <BalTile label="Património líquido" value={`${sym}${fmt(bal.net_worth)}`} color={(bal.net_worth || 0) >= 0 ? "#3B82F6" : "#EF4444"} tip="Corresponde ao total de ativos menos o total de passivos registados." testid="company-value" />
            <BalTile label="Valor estimado da empresa" value={bal.has_balance ? `${sym}${fmt(bal.company_value)}` : "Avaliação ainda não calculada"} small={!bal.has_balance} color="#3B82F6" tip="Estimativa = base patrimonial (ativos − passivos) + valor de rendimento (lucro anual × múltiplo). Não é necessariamente o preço de venda." testid="bal-estimated" />
          </div>
          {hist?.points?.length >= 2 && (
            <div className="mt-5 surface rounded-2xl p-5" data-testid="equity-history">
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Evolução do património líquido</p>
                {hist.delta != null && (
                  <span className={`inline-flex items-center gap-1 text-xs font-medium ${hist.delta >= 0 ? "text-emerald-400" : "text-red-400"}`} data-testid="equity-delta">
                    {hist.delta >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                    {hist.delta >= 0 ? "+" : "−"}{sym}{fmt(Math.abs(hist.delta))} este mês
                  </span>
                )}
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={hist.points} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                  <defs>
                    <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis hide domain={["dataMin", "dataMax"]} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} formatter={(val) => [`${sym}${fmt(val)}`, "Património"]} />
                  <Area type="monotone" dataKey="net_worth" stroke="#3B82F6" strokeWidth={2.5} fill="url(#eq)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          {hist?.points?.length === 1 && bal.has_balance && (
            <p className="text-[11px] text-muted-foreground mt-3" data-testid="equity-hint">A evolução do teu património vai aparecer aqui à medida que os meses passam.</p>
          )}
          {!bal.has_balance && <p className="text-[11px] text-amber-400 mt-3" data-testid="fill-balance-hint">Preenche o Perfil Financeiro em Finanças para veres o valor real da tua empresa →</p>}
          <p className="text-[11px] text-muted-foreground mt-2">O património líquido = total de ativos − total de passivos. Não representa necessariamente o preço de venda da empresa.</p>
        </div>
      )}

      {/* Vitals */}
      <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground mb-5">Hoje a tua empresa está assim</p>
      {!data.has_data && (
        <div className="surface rounded-2xl p-5 mb-5 flex flex-col sm:flex-row sm:items-center gap-4 border border-[#3B82F6]/25" data-testid="no-data-hint">
          <p className="text-sm text-muted-foreground flex-1">Ainda não tenho os teus números. Liga o teu banco ou importa um CSV e eu calculo o valor real da tua empresa e afino as decisões de hoje.</p>
          <button onClick={() => navigate("/financas")} data-testid="add-data-btn" className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] px-5 py-2.5 text-sm font-medium shrink-0 transition-colors">Adicionar dados</button>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-16">
        {vitalCards.map((vc, i) => (
          <motion.button key={i} onClick={vc.onClick} data-testid={`vital-${i}`}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
            className="surface rounded-2xl p-5 text-left hover:-translate-y-0.5 transition-transform">
            <vc.Icon className="w-5 h-5 mb-4" style={{ color: STATUS[vc.status] || STATUS.gold }} />
            <div className="font-serif-lux text-2xl leading-none truncate" style={{ color: vc.status === "gold" ? STATUS.gold : undefined }}>
              {vc.display}<span className="text-sm text-muted-foreground">{vc.suffix}</span>
            </div>
            <p className="text-[12px] text-muted-foreground mt-2 leading-tight">{vc.label}</p>
          </motion.button>
        ))}
      </div>

      {/* Conclusão */}
      <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground mb-5">A minha leitura de hoje</p>
      <div className="grid md:grid-cols-2 gap-4 mb-16">
        <ConclusionCard title="Estado geral" text={c.estado_geral} Icon={Flag} tone="#3B82F6" testid="conc-estado" />
        <ConclusionCard title="Oportunidades" text={c.oportunidades} Icon={Sparkles} tone="#10B981" testid="conc-oportunidades" />
        <ConclusionCard title="Problemas" text={c.problemas} Icon={AlertTriangle} tone="#EF4444" testid="conc-problemas" />
        <ConclusionCard title="Prioridades" text={c.prioridades} Icon={Flag} tone="#F59E0B" testid="conc-prioridades" />
      </div>

      {/* Recommendations */}
      {data.recomendacoes.length > 0 ? (
        <>
          <div className="flex items-center gap-3 mb-6">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">O que eu faria hoje</p>
            <ArrowRight className="w-4 h-4 text-[#3B82F6]" />
          </div>
          <div className="space-y-5">
            {data.recomendacoes.map((d, i) => <DecisionCard key={d.key} d={d} index={i} onAct={act} onExplain={explain} />)}
          </div>
        </>
      ) : data.premium_locked ? (
        <>
          <div className="flex items-center gap-3 mb-6">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">O que eu faria hoje</p>
          </div>
          <LockedBlock title="Recomendações do dia" description="As decisões concretas que eu tomaria hoje fazem parte dos planos pagos." />
        </>
      ) : null}
    </div>
  );
}

function BalTile({ label, value, color, tip, small, testid }) {
  return (
    <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-4" title={tip || ""} data-testid={testid}>
      <p className="text-[11px] text-muted-foreground mb-1.5 flex items-center gap-1">{label}{tip ? <Info className="w-3 h-3 opacity-60" /> : null}</p>
      <div className={`font-serif-lux ${small ? "text-sm leading-snug" : "text-2xl"}`} style={{ color }}>{value}</div>
    </div>
  );
}

function ConclusionCard({ title, text, Icon, tone, testid }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-2xl p-6" data-testid={testid}>
      <div className="flex items-center gap-2 mb-3" style={{ color: tone }}>
        <Icon className="w-4 h-4" /><span className="text-sm font-medium text-foreground">{title}</span>
      </div>
      <p className="text-[15px] leading-relaxed text-muted-foreground">{text || "—"}</p>
    </motion.div>
  );
}
