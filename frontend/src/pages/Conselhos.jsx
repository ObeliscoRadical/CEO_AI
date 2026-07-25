import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { DecisionCard } from "@/components/DecisionCard";
import { CEOOrb } from "@/components/CEOOrb";
import { Loader2 } from "lucide-react";

export default function Conselhos() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get("/ceo-daily").then(({ data }) => setData(data)).finally(() => setLoading(false)); }, []);

  const act = async (d, status) => {
    setData((p) => ({ ...p, recomendacoes: p.recomendacoes.filter((x) => x.key !== d.key) }));
    api.post("/decisions/act", { key: d.key, title: d.title, status }).catch(() => {});
  };
  const explain = (d) => navigate("/ceo", { state: { ask: `Sobre "${d.title}": ${d.why} — o que me recomendas fazer?` } });

  if (loading || !data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[900px] mx-auto">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Conselhos</p>
      <h1 className="font-serif-lux text-4xl md:text-5xl mb-12">O que o teu CEO recomenda</h1>
      {data.recomendacoes.length === 0 ? (
        <div className="surface rounded-3xl p-12 text-center">
          <div className="flex justify-center mb-6"><CEOOrb size={90} mood="emerald" /></div>
          <p className="text-muted-foreground">Tudo tratado por agora. Volta amanhã para os próximos conselhos.</p>
        </div>
      ) : (
        <div className="space-y-5">
          {data.recomendacoes.map((d, i) => <DecisionCard key={d.key} d={d} index={i} onAct={act} onExplain={explain} />)}
        </div>
      )}
    </div>
  );
}
