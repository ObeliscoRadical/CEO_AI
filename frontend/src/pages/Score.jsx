import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";
import { CEOOrb } from "@/components/CEOOrb";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export default function Score() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/score").then(({ data }) => setData(data)); }, []);

  if (!data) return <div className="flex justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;

  return (
    <div className="p-6 md:p-10 max-w-[1100px] mx-auto">
      <h1 className="font-serif-lux text-4xl mb-1">CEO Score™</h1>
      <p className="text-muted-foreground text-sm mb-8">A tua empresa avaliada em 8 dimensões — não só dinheiro.</p>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="surface rounded-3xl p-8 flex flex-col items-center justify-center" data-testid="score-overall">
          <CEOOrb size={110} mood={data.overall >= 70 ? "emerald" : data.overall >= 45 ? "gold" : "amber"} />
          <div className="font-serif-lux text-7xl text-[#D4AF37] mt-6">{data.overall}</div>
          <p className="text-muted-foreground text-sm mt-2">Score global</p>
        </div>

        <div className="surface rounded-3xl p-6" data-testid="score-radar">
          <ResponsiveContainer width="100%" height={340}>
            <RadarChart data={data.dimensions} outerRadius="72%">
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="score" stroke="#D4AF37" fill="#D4AF37" fillOpacity={0.35} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {data.dimensions.map((d, i) => (
          <motion.div key={d.dimension} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
            className="surface rounded-2xl p-5" data-testid={`dim-${d.dimension}`}>
            <p className="text-xs text-muted-foreground mb-2">{d.dimension}</p>
            <div className="font-serif-lux text-3xl" style={{ color: d.score >= 70 ? "#10B981" : d.score >= 45 ? "#D4AF37" : "#EF4444" }}>{d.score}</div>
            <div className="h-1.5 rounded-full bg-border mt-3 overflow-hidden">
              <motion.div className="h-full bg-[#D4AF37]" initial={{ width: 0 }} animate={{ width: `${d.score}%` }} transition={{ duration: 0.8, delay: i * 0.04 }} />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
