import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2, AlertTriangle, TrendingUp, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

const SCENARIOS = [
  { key: "contratar", label: "Contratar alguém" },
  { key: "comprar", label: "Fazer uma compra grande" },
  { key: "perder_cliente", label: "Perder um cliente importante" },
  { key: "subir_precos", label: "Subir os preços" },
  { key: "ferias", label: "Tirar férias" },
];

const VERDICT = {
  favoravel: { color: "#10B981", label: "Favorável" },
  cautela: { color: "#F59E0B", label: "Com cautela" },
  desaconselhado: { color: "#EF4444", label: "Desaconselhado" },
};

export default function Future() {
  const [data, setData] = useState(null);
  const [scenario, setScenario] = useState("contratar");
  const [detail, setDetail] = useState("");
  const [simLoading, setSimLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => { api.get("/future").then(({ data }) => setData(data)); }, []);

  const simulate = async () => {
    setSimLoading(true);
    setResult(null);
    try {
      const { data } = await api.post("/future/simulate", { scenario, detail });
      setResult(data);
    } catch { toast.error("Não foi possível simular agora"); }
    finally { setSimLoading(false); }
  };

  const sym = data?.currency_symbol || "€";

  return (
    <div className="p-6 md:p-10 max-w-[1200px] mx-auto">
      <h1 className="font-serif-lux text-4xl mb-1">Motor de Futuro</h1>
      <p className="text-muted-foreground text-sm mb-8">O passado já aconteceu. Vamos olhar para a frente.</p>

      {!data ? (
        <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>
      ) : (
        <>
          {data.warning && (
            <div className="flex items-center gap-3 p-5 rounded-2xl mb-6 border border-[#EF4444]/40 bg-[#EF4444]/10" data-testid="future-warning">
              <AlertTriangle className="w-5 h-5 text-[#EF4444] shrink-0" />
              <p className="text-sm text-[#EF4444]">{data.warning}</p>
            </div>
          )}
          <div className="surface rounded-3xl p-6 mb-8" data-testid="future-chart">
            <p className="text-xs text-muted-foreground uppercase tracking-[0.2em] mb-6">Projeção de Caixa · 12 meses</p>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data.projection}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#D4AF37" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#D4AF37" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => `${sym}${(v / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} formatter={(v) => [`${sym}${Number(v).toLocaleString("pt-PT")}`, "Caixa"]} />
                <Area type="monotone" dataKey="cash" stroke="#D4AF37" strokeWidth={2.5} fill="url(#g)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {/* Simulator */}
      <div className="surface rounded-3xl p-8">
        <div className="flex items-center gap-2 mb-6"><Sparkles className="w-5 h-5 text-[#D4AF37]" /><h2 className="font-serif-lux text-2xl">Simular uma decisão</h2></div>
        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <Select value={scenario} onValueChange={setScenario}>
            <SelectTrigger data-testid="sim-scenario" className="bg-transparent"><SelectValue /></SelectTrigger>
            <SelectContent>{SCENARIOS.map((s) => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}</SelectContent>
          </Select>
          <Textarea data-testid="sim-detail" value={detail} onChange={(e) => setDetail(e.target.value)} placeholder="Detalhe (ex: técnico a 1400€/mês)" className="md:col-span-2 bg-transparent min-h-[44px]" />
        </div>
        <Button data-testid="sim-btn" onClick={simulate} disabled={simLoading} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">
          {simLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <TrendingUp className="w-4 h-4 mr-2" />} Simular impacto
        </Button>

        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-8 space-y-4" data-testid="sim-result">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium" style={{ background: `${VERDICT[result.verdict]?.color}22`, color: VERDICT[result.verdict]?.color }}>
              {VERDICT[result.verdict]?.label || result.verdict}
            </div>
            <p className="text-lg leading-relaxed">{result.summary}</p>
            <div className="grid md:grid-cols-2 gap-4">
              <Info label="Impacto no caixa" value={result.impact_cash} />
              <Info label="Impacto no lucro" value={result.impact_profit} />
              <Info label="Horizonte" value={result.timeline} />
              <Info label="Recomendação" value={result.recommendation} highlight />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

function Info({ label, value, highlight }) {
  return (
    <div className={`rounded-xl p-4 border ${highlight ? "border-[#D4AF37]/40 bg-[#D4AF37]/8" : "border-border"}`}>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-sm">{value}</p>
    </div>
  );
}
