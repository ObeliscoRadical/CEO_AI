import { useState } from "react";
import { api } from "@/lib/api";
import { useAppData } from "@/context/AppDataContext";
import { Button } from "@/components/ui/button";
import { CEOOrb } from "@/components/CEOOrb";
import { Crown, Check, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

const FEATURES = [
  "Motor de Futuro: projeções de caixa a 12 meses",
  "Simulador de decisões (contratar, comprar, subir preços)",
  "Avisos antecipados de rutura de caixa",
  "CEO AI com todos os modelos (Claude, GPT, Gemini)",
  "Empresas ilimitadas",
];

export default function Pricing() {
  const { isPremium, plans } = useAppData();
  const [loading, setLoading] = useState(null);

  const checkout = async (lookup_key) => {
    setLoading(lookup_key);
    try {
      const { data } = await api.post("/payments/checkout", { lookup_key, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch {
      toast.error("Não foi possível iniciar o pagamento");
      setLoading(null);
    }
  };

  return (
    <div className="p-6 md:p-10 max-w-[1000px] mx-auto">
      <div className="text-center mb-12">
        <div className="flex justify-center mb-4"><CEOOrb size={100} mood="gold" /></div>
        <h1 className="font-serif-lux text-5xl mb-3">Desbloqueia o Motor de Futuro</h1>
        <p className="text-muted-foreground max-w-xl mx-auto">O passado já aconteceu. A versão Premium mostra-te o que vem a seguir — e o que decidir hoje para lá chegar.</p>
      </div>

      {isPremium ? (
        <div className="surface rounded-3xl p-10 text-center" data-testid="already-premium">
          <Crown className="w-10 h-10 text-[#D4AF37] mx-auto mb-4" />
          <h2 className="font-serif-lux text-3xl mb-2">Já és Premium</h2>
          <p className="text-muted-foreground">Tens acesso completo ao Motor de Futuro e às simulações.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {Object.entries(plans).map(([key, p], i) => (
            <motion.div key={key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className={`rounded-3xl p-8 border ${key === "premium_yearly" ? "border-[#D4AF37] bg-[#D4AF37]/8" : "border-border surface"}`} data-testid={`plan-${key}`}>
              {key === "premium_yearly" && <span className="text-xs uppercase tracking-[0.2em] text-[#D4AF37]">Melhor valor · 2 meses grátis</span>}
              <h3 className="font-serif-lux text-2xl mt-2">{p.label}</h3>
              <div className="flex items-end gap-1 my-4">
                <span className="font-serif-lux text-5xl text-[#D4AF37]">{p.price}</span>
                <span className="text-muted-foreground mb-2">{p.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm"><Check className="w-4 h-4 text-[#10B981] mt-0.5 shrink-0" />{f}</li>
                ))}
              </ul>
              <Button data-testid={`checkout-${key}`} onClick={() => checkout(key)} disabled={loading === key}
                className="w-full rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431] font-medium py-6">
                {loading === key ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Crown className="w-4 h-4 mr-2" /> Escolher {p.label}</>}
              </Button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
