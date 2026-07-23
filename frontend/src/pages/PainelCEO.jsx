import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { DecisionCard } from "@/components/DecisionCard";
import { motion } from "framer-motion";
import { Loader2, HeartPulse, Coins, ArrowRight } from "lucide-react";

export default function PainelCEO() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => api.get("/decisions").then(({ data }) => setData(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const act = async (d, status) => {
    setData((p) => ({ ...p, decisions: p.decisions.filter((x) => x.key !== d.key) }));
    api.post("/decisions/act", { key: d.key, title: d.title, status }).catch(() => {});
  };
  const explain = (d) => navigate("/ceo", { state: { ask: `Sobre "${d.title}": ${d.why} — o que me recomendas fazer?` } });

  const mood = (h) => (h >= 75 ? "emerald" : h >= 45 ? "gold" : "amber");
  const sym = data?.currency_symbol || "€";

  if (loading) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1080px] mx-auto">
      <div className="flex flex-col items-center text-center mb-16">
        <CEOOrb size={128} mood={mood(data.health)} />
        <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mt-8 mb-4">Painel do CEO · {data.company_name}</p>
        <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="font-serif-lux text-4xl md:text-5xl leading-[1.15] max-w-2xl" data-testid="verdict">
          {data.verdict}
        </motion.h1>
      </div>

      {data.decisions.length > 0 && (
        <>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground mb-6">As decisões de hoje</p>
          <div className="space-y-5 mb-16">
            {data.decisions.map((d, i) => <DecisionCard key={d.key} d={d} index={i} onAct={act} onExplain={explain} />)}
          </div>
        </>
      )}

      <div className="grid sm:grid-cols-2 gap-5">
        <button onClick={() => navigate("/saude")} data-testid="tile-saude" className="surface rounded-3xl p-7 text-left hover:-translate-y-0.5 transition-transform group">
          <div className="flex items-center justify-between mb-6"><HeartPulse className="w-5 h-5 text-[#D4AF37]" /><ArrowRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-1 transition-transform" /></div>
          <div className="font-serif-lux text-5xl">{data.health}<span className="text-2xl text-muted-foreground">/100</span></div>
          <p className="text-sm text-muted-foreground mt-2">Saúde Empresarial</p>
        </button>
        <button onClick={() => navigate("/valor")} data-testid="tile-valor" className="surface rounded-3xl p-7 text-left hover:-translate-y-0.5 transition-transform group">
          <div className="flex items-center justify-between mb-6"><Coins className="w-5 h-5 text-[#D4AF37]" /><ArrowRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-1 transition-transform" /></div>
          <div className="font-serif-lux text-5xl text-[#D4AF37]">{sym}{Number(data.company_value).toLocaleString("pt-PT")}</div>
          <p className="text-sm text-muted-foreground mt-2">Valor da Empresa · {data.progress}% do objetivo</p>
        </button>
      </div>
    </div>
  );
}
