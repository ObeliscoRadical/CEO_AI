import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Loader2, ArrowUpRight, ArrowDownRight, Minus, TrendingUp, Gem } from "lucide-react";

const INF = {
  positiva: { color: "#10B981", Icon: ArrowUpRight },
  negativa: { color: "#EF4444", Icon: ArrowDownRight },
  neutra: { color: "#A1A1AA", Icon: Minus },
};

export default function Valor() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/valuation").then(({ data }) => setData(data)); }, []);
  if (!data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;
  const sym = data.currency_symbol;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[980px] mx-auto">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Valor da Empresa</p>
      <div className="mb-14">
        <div className="font-serif-lux text-6xl md:text-7xl text-[#3B82F6]" data-testid="valuation-value">{sym}{Number(data.company_value).toLocaleString("pt-PT")}</div>
        <p className="text-muted-foreground mt-3">Valor atual estimado · {data.progress}% do teu objetivo de {sym}{Number(data.goal_value).toLocaleString("pt-PT")}</p>
        {data.net_worth != null && (
          <p className="text-sm text-muted-foreground mt-1" data-testid="valuation-basis">
            Base patrimonial (ativos − passivos): {sym}{Number(data.net_worth).toLocaleString("pt-PT")} · método: {data.method}
          </p>
        )}
      </div>

      {data.needs_financials ? (
        <div className="surface rounded-3xl p-8 border border-[#3B82F6]/30" data-testid="valuation-needs-financials">
          <h2 className="font-serif-lux text-2xl mb-2">Ainda estou a usar só a tua caixa</h2>
          <p className="text-muted-foreground mb-6">Para calcular o valor <strong>real</strong> da tua empresa preciso dos teus números: faturação mensal, ativos (viatura, ferramentas, equipamentos, stock, clientes a receber) e passivos (dívidas, impostos, fornecedores). Assim que preencheres o Perfil Financeiro, recalculo o valor na hora — e sem gastar créditos de IA.</p>
          <Button data-testid="go-financas-btn" onClick={() => navigate("/financas")} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">Preencher Perfil Financeiro</Button>
        </div>
      ) : (
      <>
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

      <div className="surface rounded-3xl p-8 mt-14 flex flex-col md:flex-row md:items-center gap-6" data-testid="investment-grade-cta">
        <div className="w-12 h-12 rounded-2xl bg-[#3B82F6]/15 flex items-center justify-center text-[#3B82F6] shrink-0"><Gem className="w-6 h-6" /></div>
        <div className="flex-1">
          <h3 className="font-serif-lux text-2xl mb-1">Relatório de Investimento</h3>
          <p className="text-sm text-muted-foreground">Uma avaliação formal, ao nível de investidor, com o grau de confiança da tua empresa. Ideal para investidores, bancos ou uma venda.</p>
        </div>
        <Button data-testid="open-investment-grade" onClick={() => navigate("/relatorio")} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] shrink-0">Ver avaliação formal</Button>
      </div>
      </>
      )}
    </div>
  );
}
