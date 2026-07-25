import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAppData } from "@/context/AppDataContext";
import { Button } from "@/components/ui/button";
import { CEOOrb } from "@/components/CEOOrb";
import { toast } from "sonner";
import { Crown, Loader2, ExternalLink, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

export default function Subscription() {
  const { isPremium, subscription, hasBilling, loadSubscription } = useAppData();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(null);

  const openPortal = async () => {
    setLoading("portal");
    try {
      const { data } = await api.post("/payments/portal", { origin_url: window.location.origin });
      window.location.href = data.url;
    } catch {
      toast.error("Portal indisponível de momento");
      setLoading(null);
    }
  };

  const cancel = async () => {
    setLoading("cancel");
    try {
      await api.post("/payments/cancel-subscription");
      await loadSubscription();
      toast.success("Subscrição cancelada — mantém acesso até ao fim do período.");
    } catch {
      toast.error("Não foi possível cancelar");
    } finally {
      setLoading(null);
    }
  };

  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end * 1000).toLocaleDateString("pt-PT", { day: "2-digit", month: "long", year: "numeric" })
    : null;

  return (
    <div className="p-6 md:p-10 max-w-[820px] mx-auto">
      <h1 className="font-serif-lux text-4xl mb-1">A minha subscrição</h1>
      <p className="text-muted-foreground text-sm mb-8">Gere o teu plano, faturação e método de pagamento.</p>

      {isPremium ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-3xl p-8" data-testid="sub-active">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-14 h-14 rounded-2xl bg-[#3B82F6]/15 flex items-center justify-center"><Crown className="w-7 h-7 text-[#3B82F6]" /></div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-serif-lux text-2xl">{subscription?.plan || "CEO AI Premium"}</h2>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#10B981]/15 text-[#10B981]" data-testid="sub-status">
                  {subscription?.cancel_at_period_end ? "Cancela no fim do período" : "Ativa"}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">Tens acesso total ao Motor de Futuro e ao Relatório de Investimento.</p>
            </div>
          </div>

          {periodEnd && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
              {subscription?.cancel_at_period_end ? <AlertCircle className="w-4 h-4 text-[#F59E0B]" /> : <CheckCircle2 className="w-4 h-4 text-[#10B981]" />}
              {subscription?.cancel_at_period_end ? `O acesso termina a ${periodEnd}.` : `Renova a ${periodEnd}.`}
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            {hasBilling && (
              <Button data-testid="portal-btn" onClick={openPortal} disabled={loading === "portal"} variant="outline" className="rounded-full">
                {loading === "portal" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ExternalLink className="w-4 h-4 mr-2" />} Gerir faturação (Stripe)
              </Button>
            )}
            {!subscription?.cancel_at_period_end && (
              <Button data-testid="cancel-btn" onClick={cancel} disabled={loading === "cancel"} variant="outline" className="rounded-full text-[#EF4444] hover:text-[#EF4444]">
                {loading === "cancel" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Cancelar subscrição
              </Button>
            )}
          </div>
        </motion.div>
      ) : (
        <div className="surface rounded-3xl p-10 text-center" data-testid="sub-free">
          <div className="flex justify-center mb-6"><CEOOrb size={100} mood="gold" /></div>
          <span className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground mb-3"><Sparkles className="w-4 h-4" /> Plano Grátis</span>
          <h2 className="font-serif-lux text-3xl mb-2">Estás no plano grátis</h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">Tens o briefing diário, a Empresa Viva, o CEO AI e o CEO Score. Passa a Premium para desbloquear o Motor de Futuro e o Relatório de Investimento.</p>
          <Button data-testid="upgrade-btn" onClick={() => navigate("/planos")} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] px-8 py-6 font-medium">
            <Crown className="w-4 h-4 mr-2" /> Ver planos Premium
          </Button>
        </div>
      )}
    </div>
  );
}
