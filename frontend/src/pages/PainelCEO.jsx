import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { DecisionCard } from "@/components/DecisionCard";
import { motion } from "framer-motion";
import { Loader2, HeartPulse, Coins, TrendingUp, Landmark, Waves, ArrowRight, Sparkles, AlertTriangle, Flag } from "lucide-react";

const STATUS = { green: "#10B981", amber: "#F59E0B", red: "#EF4444", gold: "#D4AF37" };

export default function PainelCEO() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => api.get("/ceo-daily").then(({ data }) => setData(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const act = async (d, status) => {
    setData((p) => ({ ...p, recomendacoes: p.recomendacoes.filter((x) => x.key !== d.key) }));
    api.post("/decisions/act", { key: d.key, title: d.title, status }).catch(() => {});
  };
  const explain = (d) => navigate("/ceo", { state: { ask: `Sobre "${d.title}": ${d.why} — o que me recomendas fazer?` } });

  if (loading || !data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;

  const hour = new Date().getHours();
  const greet = hour < 12 ? "Bom dia" : hour < 20 ? "Boa tarde" : "Boa noite";
  const sym = data.currency_symbol || "€";
  const v = data.vitals;
  const c = data.conclusao || {};
  const health = v?.saude?.value ?? 0;
  const mood = health >= 75 ? "emerald" : health >= 45 ? "gold" : "amber";

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
      <div className="flex items-start gap-5 mb-10">
        <CEOOrb size={72} mood={mood} className="shrink-0 hidden sm:block" />
        <div>
          <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="font-serif-lux text-4xl md:text-5xl leading-tight" data-testid="ceo-greeting">
            {greet}, {data.user_name?.split(" ")[0]}
          </motion.h1>
          <p className="text-muted-foreground mt-2 text-lg">Hoje analisei toda a tua empresa. Aqui está o que importa.</p>
        </div>
      </div>

      {/* Vitals */}
      <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground mb-5">Hoje a tua empresa está assim</p>
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
        <ConclusionCard title="Estado geral" text={c.estado_geral} Icon={Flag} tone="#D4AF37" testid="conc-estado" />
        <ConclusionCard title="Oportunidades" text={c.oportunidades} Icon={Sparkles} tone="#10B981" testid="conc-oportunidades" />
        <ConclusionCard title="Problemas" text={c.problemas} Icon={AlertTriangle} tone="#EF4444" testid="conc-problemas" />
        <ConclusionCard title="Prioridades" text={c.prioridades} Icon={Flag} tone="#F59E0B" testid="conc-prioridades" />
      </div>

      {/* Recommendations */}
      {data.recomendacoes.length > 0 && (
        <>
          <div className="flex items-center gap-3 mb-6">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">O que eu faria hoje</p>
            <ArrowRight className="w-4 h-4 text-[#D4AF37]" />
          </div>
          <div className="space-y-5">
            {data.recomendacoes.map((d, i) => <DecisionCard key={d.key} d={d} index={i} onAct={act} onExplain={explain} />)}
          </div>
        </>
      )}
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
