import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const LABELS = {
  ativo_total: "Ativo total",
  ativo_nao_corrente: "Ativo não corrente",
  ativo_corrente: "Ativo corrente",
  passivo_total: "Passivo total",
  capital_proprio: "Capital próprio",
  vendas_e_servicos: "Vendas e serviços",
  rendimentos_totais: "Rendimentos totais",
  gastos_totais: "Gastos totais",
  resultado_liquido: "Resultado líquido",
  ebitda: "EBITDA",
};

const fmt = (v, sym) => (v == null ? "—" : `${sym}${Number(v).toLocaleString("pt-PT", { maximumFractionDigits: 0 })}`);

export const ContasEvolucao = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/financial-history").then(({ data }) => setD(data)).catch(() => setD({ years: [] })); }, []);

  if (!d || !d.years?.length) return null;
  const sym = d.currency_symbol || "€";
  const rows = d.keys.filter((k) => d.years.some((y) => y[k] != null));

  return (
    <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="contas-evolucao">
      <h2 className="font-serif-lux text-2xl mb-1">Contas &amp; Evolução</h2>
      <p className="text-muted-foreground text-sm mb-3">Rubricas extraídas dos teus documentos oficiais (SNC), comparadas ano a ano.</p>
      <div className="flex flex-wrap gap-2 mb-5">
        {d.years.map((y) => {
          if (y.reconciled == null) return null;
          const ok = y.reconciled;
          return (
            <span key={y.year} data-testid={`recon-${y.year}`}
              className={`text-xs px-2.5 py-1 rounded-full border ${ok ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : "border-amber-500/40 text-amber-400 bg-amber-500/10"}`}>
              {y.year}: {ok ? "Balanço reconciliado ✓" : `diferença de ${fmt(Math.abs(y.reconciliation_diff || 0), sym)}`}
            </span>
          );
        })}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" data-testid="contas-table">
          <thead>
            <tr className="text-left text-muted-foreground border-b border-border">
              <th className="py-2 pr-4 font-medium">Rubrica</th>
              {d.years.map((y) => <th key={y.year} className="py-2 px-3 text-right font-medium">{y.year}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => (
              <tr key={k} className="border-b border-border/50" data-testid={`row-${k}`}>
                <td className="py-2 pr-4 text-muted-foreground">{LABELS[k] || k}</td>
                {d.years.map((y) => {
                  const neg = typeof y[k] === "number" && y[k] < 0;
                  return <td key={y.year} className={`py-2 px-3 text-right tabular-nums ${neg ? "text-red-400" : ""}`}>{fmt(y[k], sym)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
