import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Loader2, ArrowRight } from "lucide-react";

const MODES = [
  { key: "conservador", label: "Conservador", desc: "Estabilidade e prudência acima de tudo." },
  { key: "crescimento", label: "Crescimento", desc: "Equilíbrio entre oportunidade e risco." },
  { key: "agressivo", label: "Agressivo", desc: "Resultados rápidos, mais risco." },
  { key: "familiar", label: "Familiar", desc: "Qualidade de vida e sustentabilidade." },
  { key: "startup", label: "Startup", desc: "Escala, produto e runway." },
  { key: "investidor", label: "Investidor", desc: "Retorno sobre capital e valor da empresa." },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [company, setCompany] = useState({ name: "", region: "PT", currency: "EUR", sector: "", employees_count: 0, clients_count: 0, bank_balance: 0, monthly_tax_estimate: 0 });
  const [dna, setDna] = useState({ dream: "", target_revenue: 0, work_hours: "", exit_plan: "", five_year_vision: "", ceo_mode: "crescimento" });

  const steps = [
    { title: "Vamos conhecer a sua empresa", key: "company" },
    { title: "Agora, vamos conhecer-te a ti", key: "you" },
    { title: "Onde queres estar em 5 anos?", key: "vision" },
    { title: "Como queres que eu te aconselhe?", key: "mode" },
  ];

  const next = () => setStep((s) => Math.min(s + 1, steps.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const finish = async () => {
    setLoading(true);
    try {
      await api.post("/company", { ...company, employees_count: Number(company.employees_count), clients_count: Number(company.clients_count), bank_balance: Number(company.bank_balance), monthly_tax_estimate: Number(company.monthly_tax_estimate) });
      await api.post("/dna", { ...dna, target_revenue: Number(dna.target_revenue), answers: { ...company, ...dna } });
      toast.success("CEO DNA concluído. O seu executivo já o conhece.");
      navigate("/");
    } catch (e) {
      toast.error("Erro ao guardar. Tente novamente.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground relative z-10 flex flex-col items-center px-6 py-16">
      <div className="absolute inset-0 opacity-[0.08]" style={{ background: "url('https://images.unsplash.com/photo-1747673002516-f11a48cb0ce2?crop=entropy&cs=srgb&fm=jpg&q=85') center/cover" }} />
      <CEOOrb size={110} mood="gold" />
      <div className="w-full max-w-xl mt-8 relative">
        <div className="flex gap-2 mb-8 justify-center">
          {steps.map((_, i) => (
            <div key={i} className={`h-1 rounded-full transition-all duration-300 ${i <= step ? "w-10 bg-[#D4AF37]" : "w-6 bg-border"}`} />
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }}>
            <h1 className="font-serif-lux text-4xl mb-8 text-center">{steps[step].title}</h1>

            {step === 0 && (
              <div className="space-y-5">
                <Field label="Nome da empresa"><Input data-testid="company-name" value={company.name} onChange={(e) => setCompany({ ...company, name: e.target.value })} className="bg-transparent" placeholder="Ex: Silva & Filhos, Lda" /></Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Região">
                    <Select value={company.region} onValueChange={(v) => setCompany({ ...company, region: v, currency: v === "BR" ? "BRL" : "EUR" })}>
                      <SelectTrigger data-testid="company-region" className="bg-transparent"><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="PT">Portugal (€)</SelectItem><SelectItem value="BR">Brasil (R$)</SelectItem></SelectContent>
                    </Select>
                  </Field>
                  <Field label="Setor"><Input data-testid="company-sector" value={company.sector} onChange={(e) => setCompany({ ...company, sector: e.target.value })} className="bg-transparent" placeholder="Ex: Serviços" /></Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Nº de funcionários"><Input data-testid="company-employees" type="number" value={company.employees_count} onChange={(e) => setCompany({ ...company, employees_count: e.target.value })} className="bg-transparent" /></Field>
                  <Field label="Nº de clientes"><Input data-testid="company-clients" type="number" value={company.clients_count} onChange={(e) => setCompany({ ...company, clients_count: e.target.value })} className="bg-transparent" /></Field>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Saldo bancário atual"><Input data-testid="company-bank" type="number" value={company.bank_balance} onChange={(e) => setCompany({ ...company, bank_balance: e.target.value })} className="bg-transparent" /></Field>
                  <Field label="Estimativa fiscal mensal"><Input data-testid="company-tax" type="number" value={company.monthly_tax_estimate} onChange={(e) => setCompany({ ...company, monthly_tax_estimate: e.target.value })} className="bg-transparent" /></Field>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-5">
                <Field label="Qual é o teu sonho com este negócio?"><Textarea data-testid="dna-dream" value={dna.dream} onChange={(e) => setDna({ ...dna, dream: e.target.value })} className="bg-transparent" placeholder="Ex: ter liberdade financeira e uma empresa que funcione sem mim." /></Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Faturação anual desejada"><Input data-testid="dna-revenue" type="number" value={dna.target_revenue} onChange={(e) => setDna({ ...dna, target_revenue: e.target.value })} className="bg-transparent" placeholder="1000000" /></Field>
                  <Field label="Horas de trabalho / semana"><Input data-testid="dna-hours" value={dna.work_hours} onChange={(e) => setDna({ ...dna, work_hours: e.target.value })} className="bg-transparent" placeholder="Ex: 40h" /></Field>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-5">
                <Field label="Onde queres estar em 5 anos?"><Textarea data-testid="dna-vision" value={dna.five_year_vision} onChange={(e) => setDna({ ...dna, five_year_vision: e.target.value })} className="bg-transparent min-h-[120px]" placeholder="Ex: armazém próprio, 2 técnicos contratados, faturar 1M." /></Field>
                <Field label="Plano de longo prazo">
                  <Select value={dna.exit_plan} onValueChange={(v) => setDna({ ...dna, exit_plan: v })}>
                    <SelectTrigger data-testid="dna-exit" className="bg-transparent"><SelectValue placeholder="Escolhe uma opção" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="crescer">Crescer indefinidamente</SelectItem>
                      <SelectItem value="vender">Vender a empresa</SelectItem>
                      <SelectItem value="reformar">Reformar-me e passar a gestão</SelectItem>
                      <SelectItem value="familiar">Passar para a família</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
              </div>
            )}

            {step === 3 && (
              <div className="grid grid-cols-2 gap-3">
                {MODES.map((m) => (
                  <button key={m.key} data-testid={`mode-${m.key}`} onClick={() => setDna({ ...dna, ceo_mode: m.key })}
                    className={`text-left p-4 rounded-xl border transition-colors ${dna.ceo_mode === m.key ? "border-[#D4AF37] bg-[#D4AF37]/10" : "border-border hover:bg-accent"}`}>
                    <div className="font-medium mb-1">{m.label}</div>
                    <div className="text-xs text-muted-foreground">{m.desc}</div>
                  </button>
                ))}
              </div>
            )}

            <div className="flex gap-3 mt-10">
              {step > 0 && <Button data-testid="back-btn" variant="outline" onClick={back} className="rounded-full">Voltar</Button>}
              {step < steps.length - 1 ? (
                <Button data-testid="next-btn" onClick={next} disabled={step === 0 && !company.name} className="flex-1 rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431] font-medium py-6">
                  Continuar <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button data-testid="finish-btn" onClick={finish} disabled={loading} className="flex-1 rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431] font-medium py-6">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Concluir CEO DNA"}
                </Button>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <Label className="text-xs text-muted-foreground mb-1 block">{label}</Label>
      {children}
    </div>
  );
}
