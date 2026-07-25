import { useNavigate } from "react-router-dom";
import { Lock, Crown, ArrowRight } from "lucide-react";
import { CEOOrb } from "@/components/CEOOrb";

export function LockedBlock({ title, description }) {
  const navigate = useNavigate();
  return (
    <div data-testid="premium-locked-block" className="surface rounded-2xl p-6 border border-[#3B82F6]/25">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#3B82F6]/15 flex items-center justify-center shrink-0"><Lock className="w-4 h-4 text-[#3B82F6]" /></div>
        <div className="flex-1 min-w-0">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
          <p className="text-sm text-muted-foreground mt-1">{description || "Esta análise faz parte dos planos pagos."}</p>
        </div>
        <button onClick={() => navigate("/planos")} data-testid="unlock-btn"
          className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] px-4 py-2 text-sm font-medium shrink-0 transition-colors inline-flex items-center gap-1">
          <Crown className="w-3.5 h-3.5" /> Desbloquear
        </button>
      </div>
    </div>
  );
}

export function UpgradeWall({ feature }) {
  const navigate = useNavigate();
  return (
    <div className="px-6 md:px-16 py-20 max-w-[720px] mx-auto text-center" data-testid="upgrade-wall">
      <div className="flex justify-center mb-6"><CEOOrb size={96} mood="gold" /></div>
      <span className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-[#3B82F6] mb-4"><Lock className="w-4 h-4" /> Funcionalidade Premium</span>
      <h1 className="font-serif-lux text-4xl mb-3">{feature || "Esta área faz parte dos planos pagos"}</h1>
      <p className="text-muted-foreground max-w-md mx-auto mb-8">O plano grátis é uma demonstração. Torna-te Empresa Fundadora ou Professional para desbloquear o teu Diretor Executivo Digital por completo.</p>
      <button onClick={() => navigate("/planos")} data-testid="upgrade-cta"
        className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] px-8 py-4 font-medium inline-flex items-center gap-2 transition-colors">
        <Crown className="w-4 h-4" /> Ver planos <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
