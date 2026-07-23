import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { motion } from "framer-motion";
import { Loader2, ArrowUpRight, ArrowDownRight, Minus, TrendingUp } from "lucide-react";

const INF = {
  positiva: { color: "#10B981", Icon: ArrowUpRight },
  negativa: { color: "#EF4444", Icon: ArrowDownRight },
  neutra: { color: "#A1A1AA", Icon: Minus },
};

export default function Valor() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/valuation").then(({ data }) => setData(data)); }, []);
  if (!data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;
  const sym = data.currency_symbol;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[980px] mx-auto">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Valor da Empresa</p>
      <div className="mb-14">
        <div className="font-serif-lux text-6xl md:text-7xl text-[#D4AF37]" data-testid="valuation-value">{sym}{Number(data.company_value).toLocaleString("pt-PT")}</div>
        <p className="text-muted-foreground mt-3">Valor atual estimado · {data.progress}% do teu objetivo de {sym}{Number(data.goal_value).toLocaleString("pt-PT")}</p>
      </div>

      <h2 className="font-serif-lux text-3xl mb-2">Como chegámos a este valor?</h2>
      <p className="text-muted-foreground mb-8">Cada fator influencia o valuation, para cima ou para baixo.</p>
      <div className="space-y-3 mb-16">
        {data.factors.map((f, i) => {
          const cfg = INF[f.influence] || INF.neutra;
          return (
            <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
              className="surface rounded-2xl p-5 flex items-center gap-4" data-testid={`factor-${i}`}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${cfg.color}18`, color: cfg.color }}>
                <cfg.Icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium">{f.name}</div>
                <div className="text-sm text-muted-foreground">{f.note}</div>
              </div>
              <div className="font-serif-lux text-xl shrink-0" style={{ color: cfg.color }}>{f.weight}</div>
            </motion.div>
          );
        })}
      </div>

      <h2 className="font-serif-lux text-3xl mb-2">Como aumentar o valor</h2>
      <p className="text-muted-foreground mb-8">Ações concretas e quanto podem acrescentar ao valuation.</p>
      <div className="grid md:grid-cols-2 gap-4">
        {data.actions.map((a, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="surface rounded-2xl p-6" data-testid={`action-${i}`}>
            <div className="flex items-center gap-2 text-[#10B981] mb-2"><TrendingUp className="w-4 h-4" /><span className="font-serif-lux text-2xl">{a.uplift}</span></div>
            <div className="font-medium mb-1">{a.action}</div>
            <div className="text-sm text-muted-foreground">{a.note}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
