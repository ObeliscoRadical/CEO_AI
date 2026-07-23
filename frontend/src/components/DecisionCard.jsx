import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { ArrowUpRight, MessageSquare, Check, Clock } from "lucide-react";

const URGENCY = { alta: "#EF4444", media: "#F59E0B", baixa: "#10B981" };

export function DecisionCard({ d, index = 0, onAct, onExplain }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08, duration: 0.4 }}
      className="surface rounded-3xl p-7 md:p-8" data-testid={`decision-${index}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full" style={{ background: URGENCY[d.urgency] || "#F59E0B" }} />
        <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{d.urgency === "alta" ? "Prioridade alta" : d.urgency === "baixa" ? "Quando puderes" : "Esta semana"}</span>
      </div>
      <h3 className="font-serif-lux text-2xl md:text-3xl leading-snug mb-3">{d.title}</h3>
      <p className="text-muted-foreground leading-relaxed mb-4">{d.why}</p>
      {d.impact && (
        <div className="inline-flex items-center gap-1.5 text-sm text-[#10B981] mb-6"><ArrowUpRight className="w-4 h-4" />{d.impact}</div>
      )}
      <div className="flex flex-wrap gap-3">
        <Button data-testid={`decision-do-${index}`} onClick={() => onAct(d, "done")} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">
          <Check className="w-4 h-4 mr-2" /> Fazer isto
        </Button>
        <Button data-testid={`decision-explain-${index}`} variant="outline" onClick={() => onExplain(d)} className="rounded-full">
          <MessageSquare className="w-4 h-4 mr-2" /> Explica-me melhor
        </Button>
        <Button data-testid={`decision-snooze-${index}`} variant="ghost" onClick={() => onAct(d, "snoozed")} className="rounded-full text-muted-foreground">
          <Clock className="w-4 h-4 mr-2" /> Adiar
        </Button>
      </div>
    </motion.div>
  );
}
