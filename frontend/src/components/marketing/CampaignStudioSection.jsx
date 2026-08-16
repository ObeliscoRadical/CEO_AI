import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Layers3, Loader2, Sparkles, Target } from "lucide-react";

const OBJECTIVES = [
  { value: "awareness", label: "Awareness" },
  { value: "leads", label: "Leads" },
  { value: "reativacao", label: "Reativação" },
];

const ChannelCard = ({ item, index, cardIndex }) => (
  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-channel-${cardIndex}-${index}`}>
    <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
      <p className="font-medium" data-testid={`mkt-campaign-channel-name-${cardIndex}-${index}`}>{item.channel}</p>
      <span className="text-[10px] uppercase tracking-[0.18em] text-[#A78BFA]" data-testid={`mkt-campaign-channel-format-${cardIndex}-${index}`}>{item.format}</span>
    </div>
    <div className="space-y-2 text-sm text-muted-foreground">
      <p data-testid={`mkt-campaign-channel-purpose-${cardIndex}-${index}`}><span className="text-foreground">Função:</span> {item.purpose}</p>
      <p data-testid={`mkt-campaign-channel-hook-${cardIndex}-${index}`}><span className="text-foreground">Gancho:</span> {item.hook}</p>
      <p data-testid={`mkt-campaign-channel-cta-${cardIndex}-${index}`}><span className="text-foreground">CTA:</span> {item.cta}</p>
      <p data-testid={`mkt-campaign-channel-distribution-${cardIndex}-${index}`}><span className="text-foreground">Distribuição:</span> {item.distribution}</p>
    </div>
  </div>
);

export const CampaignStudioSection = ({ campaigns, generating, onGenerate }) => {
  const [objective, setObjective] = useState("awareness");
  const [name, setName] = useState("");
  const [offer, setOffer] = useState("");
  const [audience, setAudience] = useState("");
  const [notes, setNotes] = useState("");

  const submit = async () => {
    await onGenerate({ objective, name, offer, audience, notes });
  };

  return (
    <div className="surface rounded-[22px] p-5 md:p-6 mb-5" data-testid="mkt-campaign-studio">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-4">
        <div>
          <h2 className="font-serif-lux text-lg flex items-center gap-2"><Layers3 className="w-5 h-5 text-[#A78BFA]" /> Campanhas</h2>
          <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-campaign-description">Crie campanhas sociais por objetivo, já alinhadas com contexto comercial.</p>
        </div>
        <span className="text-xs text-muted-foreground" data-testid="mkt-campaign-count">{(campaigns || []).length} campanhas guardadas</span>
      </div>

      <div className="grid xl:grid-cols-[0.85fr_1.15fr] gap-4">
        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="mkt-campaign-form">
          <div className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-campaign-objective-label">Objetivo</label>
              <Select value={objective} onValueChange={setObjective}>
                <SelectTrigger className="mt-2" data-testid="mkt-campaign-objective-trigger">
                  <SelectValue placeholder="Escolha o objetivo" />
                </SelectTrigger>
                <SelectContent>
                  {OBJECTIVES.map((item) => (
                    <SelectItem key={item.value} value={item.value} data-testid={`mkt-campaign-objective-${item.value}`}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-campaign-name-label">Nome da campanha</label>
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Setembro · Reativar leads mornos" className="mt-2" data-testid="mkt-campaign-name-input" />
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-campaign-offer-label">Oferta / CTA principal</label>
              <Input value={offer} onChange={(event) => setOffer(event.target.value)} placeholder="Ex.: diagnóstico gratuito de 15 minutos" className="mt-2" data-testid="mkt-campaign-offer-input" />
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-campaign-audience-label">Audiência prioritária</label>
              <Input value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Ex.: gestores de obra em Lisboa" className="mt-2" data-testid="mkt-campaign-audience-input" />
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-campaign-notes-label">Notas extra</label>
              <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Contexto, urgência, janela comercial, objeções frequentes…" className="mt-2 min-h-[120px]" data-testid="mkt-campaign-notes-input" />
            </div>

            <Button data-testid="mkt-campaign-generate-btn" onClick={submit} disabled={generating} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] w-full h-11">
              {generating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
              Gerar campanha
            </Button>
          </div>
        </div>

        <div className="space-y-4" data-testid="mkt-campaign-list">
          {(campaigns || []).length === 0 ? (
            <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.02] p-8 text-center" data-testid="mkt-campaign-empty">
              <Target className="w-8 h-8 text-[#A78BFA] mx-auto mb-3" />
              <p className="font-medium">Ainda não existem campanhas guardadas</p>
              <p className="text-sm text-muted-foreground mt-2">Crie a primeira campanha para gerar canais, KPIs, experiências e plano de lançamento.</p>
            </div>
          ) : (
            campaigns.map((campaign, index) => (
              <div key={campaign.id || index} className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid={`mkt-campaign-card-${index}`}>
                <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-[#A78BFA]" data-testid={`mkt-campaign-objective-label-${index}`}>{campaign.objective_label}</p>
                    <h3 className="font-serif-lux text-2xl mt-1" data-testid={`mkt-campaign-name-${index}`}>{campaign.name}</h3>
                  </div>
                  <span className="text-xs text-muted-foreground" data-testid={`mkt-campaign-created-${index}`}>{new Date(campaign.created_at).toLocaleString("pt-PT")}</span>
                </div>

                <div className="grid md:grid-cols-2 gap-4 mb-5 text-sm">
                  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-summary-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Resumo</p>
                    <p>{campaign.summary}</p>
                    <p className="mt-3 text-muted-foreground" data-testid={`mkt-campaign-message-${index}`}><span className="text-foreground">Mensagem central:</span> {campaign.core_message}</p>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-audience-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Audiência & oferta</p>
                    <p><span className="text-foreground">Audiência:</span> {campaign.audience}</p>
                    <p className="mt-3"><span className="text-foreground">Oferta:</span> {campaign.offer}</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4 mb-5">
                  {(campaign.channels || []).map((item, channelIndex) => (
                    <ChannelCard key={`${item.channel}-${channelIndex}`} item={item} index={channelIndex} cardIndex={index} />
                  ))}
                </div>

                <div className="grid lg:grid-cols-3 gap-4 text-sm">
                  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-kpis-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">KPIs</p>
                    <ul className="space-y-2">{(campaign.kpis || []).map((item, kpiIndex) => <li key={kpiIndex} data-testid={`mkt-campaign-kpi-${index}-${kpiIndex}`}>• {item}</li>)}</ul>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-plan-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Plano de lançamento</p>
                    <ul className="space-y-2">{(campaign.launch_plan || []).map((item, planIndex) => <li key={planIndex} data-testid={`mkt-campaign-plan-item-${index}-${planIndex}`}><span className="text-foreground">{item.day}</span> · {item.channel} · {item.action}</li>)}</ul>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-campaign-experiments-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Experiências & próximos passos</p>
                    <ul className="space-y-2 mb-4">{(campaign.experiments || []).map((item, expIndex) => <li key={expIndex} data-testid={`mkt-campaign-experiment-${index}-${expIndex}`}>• {item}</li>)}</ul>
                    <ul className="space-y-2 text-muted-foreground">{(campaign.next_actions || []).map((item, stepIndex) => <li key={stepIndex} data-testid={`mkt-campaign-next-${index}-${stepIndex}`}>→ {item}</li>)}</ul>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};