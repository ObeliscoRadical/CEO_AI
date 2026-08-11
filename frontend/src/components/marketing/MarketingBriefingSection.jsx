import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Loader2, Mail, Sparkles } from "lucide-react";

const BriefList = ({ title, items, testIdPrefix }) => (
  <div>
    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">{title}</p>
    <ul className="space-y-2 text-sm text-foreground">
      {(items || []).map((item, index) => <li key={index} data-testid={`${testIdPrefix}-${index}`}>• {item}</li>)}
    </ul>
  </div>
);

export const MarketingBriefingSection = ({ briefing, briefingBusy, emailSending, autoEmailEnabled, onToggleAutoEmail, onRefresh, onSendEmail }) => {
  if (!briefing) return null;

  return (
    <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-briefing-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <h2 className="font-serif-lux text-xl flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#A78BFA]" /> Briefing autónomo diário</h2>
          <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-briefing-description">Resumo tático diário do Diretor de Marketing — disponível na app e por email.</p>
        </div>
        <div className="flex items-center gap-3 rounded-full border border-white/10 px-4 py-2 bg-white/[0.03]" data-testid="mkt-briefing-toggle-wrap">
          <div>
            <p className="text-sm font-medium">Email diário</p>
            <p className="text-[11px] text-muted-foreground">Empresa ativa · envio automático</p>
          </div>
          <Switch checked={!!autoEmailEnabled} onCheckedChange={onToggleAutoEmail} data-testid="mkt-briefing-email-toggle" />
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 mb-5" data-testid="mkt-briefing-card">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{briefing.company_name}</p>
            <h3 className="font-serif-lux text-2xl mt-1" data-testid="mkt-briefing-headline">{briefing.headline}</h3>
          </div>
          {briefing.mocked_metrics && <span className="text-[11px] px-3 py-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 text-amber-300" data-testid="mkt-briefing-mocked">Métricas <strong>MOCKED</strong></span>}
        </div>
        <p className="text-sm text-muted-foreground leading-6" data-testid="mkt-briefing-summary">{briefing.summary}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-5 mb-5">
        <BriefList title="O que está a resultar" items={briefing.wins} testIdPrefix="mkt-briefing-win" />
        <BriefList title="Riscos / atenção" items={briefing.risks} testIdPrefix="mkt-briefing-risk" />
        <BriefList title="Ações para hoje" items={briefing.actions} testIdPrefix="mkt-briefing-action" />
        <BriefList title="Experiências sugeridas" items={briefing.experiments} testIdPrefix="mkt-briefing-experiment" />
      </div>

      <div className="flex gap-2 flex-wrap">
        <Button data-testid="mkt-briefing-refresh" onClick={onRefresh} disabled={briefingBusy} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]">
          {briefingBusy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />} Atualizar briefing
        </Button>
        <Button data-testid="mkt-briefing-send-email" onClick={onSendEmail} disabled={emailSending} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
          {emailSending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Mail className="w-4 h-4 mr-2" />} Enviar por email
        </Button>
      </div>
    </div>
  );
};