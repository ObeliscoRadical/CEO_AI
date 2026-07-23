import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { CEOOrb } from "@/components/CEOOrb";
import { motion } from "framer-motion";
import { Loader2, TrendingUp } from "lucide-react";

const color = (s) => (s >= 70 ? "#10B981" : s >= 45 ? "#D4AF37" : "#EF4444");

export default function Saude() {
  const [data, setData] = useState(null);
  const [active, setActive] = useState(0);

  useEffect(() => { api.get("/health-index").then(({ data }) => setData(data)); }, []);
  if (!data) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;

  const d = data.dimensions[active];

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1080px] mx-auto">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Saúde Empresarial</p>
      <h1 className="font-serif-lux text-4xl md:text-5xl mb-4">A tua empresa está {data.overall >= 70 ? "saudável" : data.overall >= 45 ? "estável" : "frágil"}</h1>
      <p className="text-muted-foreground max-w-2xl mb-12 leading-relaxed">{data.summary}</p>

      <div className="grid lg:grid-cols-2 gap-10 items-center mb-14">
        <div className="surface rounded-3xl p-6 relative">
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center"><div className="font-serif-lux text-6xl text-[#D4AF37]">{data.overall}</div><div className="text-xs text-muted-foreground">/100</div></div>
          </div>
          <ResponsiveContainer width="100%" height={380}>
            <RadarChart data={data.dimensions} outerRadius="70%">
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
              <Radar dataKey="score" stroke="#D4AF37" fill="#D4AF37" fillOpacity={0.28} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div>
          <div className="grid grid-cols-3 gap-2 mb-6">
            {data.dimensions.map((dim, i) => (
              <button key={dim.dimension} onClick={() => setActive(i)} data-testid={`dim-btn-${i}`}
                className={`p-3 rounded-xl border text-left transition-colors ${i === active ? "border-[#D4AF37] bg-[#D4AF37]/8" : "border-border hover:bg-accent"}`}>
                <div className="text-[11px] text-muted-foreground truncate">{dim.dimension}</div>
                <div className="font-serif-lux text-xl" style={{ color: color(dim.score) }}>{dim.score}</div>
              </button>
            ))}
          </div>
          <motion.div key={active} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-3xl p-7" data-testid="dim-detail">
            <h3 className="font-serif-lux text-2xl mb-4">{d.dimension} · <span style={{ color: color(d.score) }}>{d.score}</span></h3>
            <Row label="Porquê esta nota" value={d.why} />
            <Row label="O que melhorar" value={d.improve} />
            <div className="flex items-center gap-2 mt-4 text-sm text-[#10B981]"><TrendingUp className="w-4 h-4" /> Potencial: {d.potential}</div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="mb-3">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">{label}</div>
      <div className="text-sm leading-relaxed">{value}</div>
    </div>
  );
}
