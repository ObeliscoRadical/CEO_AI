import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { api } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

const MAX_POLLS = 6;

export default function PaymentResult() {
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const isCancel = location.pathname.includes("cancel");
  const sessionId = params.get("session_id");
  const [status, setStatus] = useState(isCancel ? "cancel" : "checking");

  const poll = useCallback(async (attempt) => {
    if (attempt >= MAX_POLLS) { setStatus("timeout"); return; }
    try {
      const { data } = await api.get(`/payments/status/${sessionId}`);
      if (data.payment_status === "paid") { setStatus("paid"); return; }
      if (data.status === "expired" || data.payment_status === "failed") { setStatus("failed"); return; }
    } catch {}
    setTimeout(() => poll(attempt + 1), 2000);
  }, [sessionId]);

  useEffect(() => {
    if (!isCancel && sessionId) poll(0);
    else if (!isCancel && !sessionId) setStatus("failed");
  }, [isCancel, sessionId, poll]);

  const cfg = {
    checking: { icon: <Loader2 className="w-10 h-10 animate-spin text-[#D4AF37]" />, title: "A confirmar o pagamento...", sub: "Um instante, estamos a ativar o teu Premium." },
    paid: { icon: <CheckCircle2 className="w-12 h-12 text-[#10B981]" />, title: "Bem-vindo ao Premium!", sub: "O Motor de Futuro está desbloqueado. Vamos olhar para a frente." },
    cancel: { icon: <XCircle className="w-12 h-12 text-muted-foreground" />, title: "Pagamento cancelado", sub: "Sem problema — podes voltar quando quiseres." },
    failed: { icon: <XCircle className="w-12 h-12 text-[#EF4444]" />, title: "Algo correu mal", sub: "O pagamento não foi concluído. Tenta novamente." },
    timeout: { icon: <Loader2 className="w-10 h-10 text-[#F59E0B]" />, title: "A processar...", sub: "Está a demorar mais do que o normal. Verifica daqui a pouco em Definições." },
  }[status];

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground relative z-10 p-8 text-center">
      <CEOOrb size={120} mood={status === "paid" ? "emerald" : "gold"} />
      <div className="mt-8 mb-4">{cfg.icon}</div>
      <h1 className="font-serif-lux text-4xl mb-2" data-testid="payment-title">{cfg.title}</h1>
      <p className="text-muted-foreground mb-8 max-w-md">{cfg.sub}</p>
      <div className="flex gap-3">
        {status === "paid" ? (
          <Button data-testid="go-future-btn" onClick={() => navigate("/futuro")} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431] px-8">Ir para o Motor de Futuro</Button>
        ) : status !== "checking" ? (
          <>
            <Button data-testid="go-plans-btn" onClick={() => navigate("/planos")} variant="outline" className="rounded-full">Ver planos</Button>
            <Button data-testid="go-home-btn" onClick={() => navigate("/")} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">Voltar ao dashboard</Button>
          </>
        ) : null}
      </div>
    </div>
  );
}
