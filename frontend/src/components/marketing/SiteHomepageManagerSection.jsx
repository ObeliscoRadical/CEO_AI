import { Button } from "@/components/ui/button";
import { ExternalLink, Loader2, Sparkles, UploadCloud } from "lucide-react";

const PreviewShell = ({ eyebrow, title, subtitle, primaryCtaLabel, primaryCtaUrl, secondaryCtaLabel, secondaryCtaUrl, proofTitle, proofItems, tone = "live", testIdPrefix }) => {
  const toneClass = tone === "proposal"
    ? "border-[#A78BFA]/18 bg-[#A78BFA]/8"
    : "border-[#3B82F6]/18 bg-[#3B82F6]/8";
  const ctaClass = tone === "proposal"
    ? "bg-[#A78BFA] hover:bg-[#9333EA]"
    : "bg-[#3B82F6] hover:bg-[#2563EB]";

  return (
    <div className={`rounded-[20px] border p-4 md:p-5 ${toneClass}`} data-testid={`${testIdPrefix}-preview`}>
      <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground" data-testid={`${testIdPrefix}-eyebrow`}>{eyebrow}</p>
      <h4 className="font-serif-lux text-[28px] leading-tight mt-3" data-testid={`${testIdPrefix}-headline`}>{title}</h4>
      <p className="text-sm text-muted-foreground mt-3 max-w-2xl" data-testid={`${testIdPrefix}-subtitle`}>{subtitle}</p>
      <div className="flex flex-wrap gap-2 mt-4" data-testid={`${testIdPrefix}-ctas`}>
        <a href={primaryCtaUrl || "#login-auth-panel"} className={`inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium text-white transition-colors ${ctaClass}`} data-testid={`${testIdPrefix}-primary-cta`}>
          {primaryCtaLabel || "Entrar"}
        </a>
        <a href={secondaryCtaUrl || "/planos"} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-black/10 px-4 py-2.5 text-sm text-slate-200 hover:bg-white/[0.04] transition-colors" data-testid={`${testIdPrefix}-secondary-cta`}>
          {secondaryCtaLabel || "Ver planos"}
        </a>
      </div>
      <div className="mt-5 rounded-[18px] border border-white/10 bg-black/15 p-4" data-testid={`${testIdPrefix}-proof-block`}>
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid={`${testIdPrefix}-proof-title`}>{proofTitle}</p>
        <div className="grid sm:grid-cols-3 gap-2 mt-3" data-testid={`${testIdPrefix}-proof-items`}>
          {(proofItems || []).map((item, index) => (
            <div key={`${item}-${index}`} className="rounded-[14px] border border-white/10 bg-white/[0.03] p-3 text-sm text-slate-200" data-testid={`${testIdPrefix}-proof-item-${index}`}>
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const SiteHomepageManagerSection = ({ homepage, busy, onGenerateProposal, onApplyProposal, authorized }) => {
  const state = homepage || {
    live: {
      headline: "Homepage do agente",
      subtitle: "Sem conteúdo carregado.",
      primary_cta_label: "Entrar",
      primary_cta_url: "#login-auth-panel",
      secondary_cta_label: "Ver planos",
      secondary_cta_url: "/planos",
      social_proof_title: "Prova social",
      social_proof_items: ["", "", ""],
    },
    proposal: null,
  };

  return (
    <section className="rounded-[22px] border border-white/10 bg-white/[0.03] p-5 md:p-6 mb-5" data-testid="site-homepage-manager-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Agente · Site</p>
          <h3 className="font-serif-lux text-lg mt-2">Homepage gerida pelo agente</h3>
          <p className="text-sm text-muted-foreground mt-2" data-testid="site-homepage-manager-description">
            O agente pode controlar parcialmente a homepage pública: headline, subtítulo, CTAs e prova social — sem mexer no layout.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={onGenerateProposal} disabled={busy === "homepage-generate"} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="site-homepage-generate-btn">
            {busy === "homepage-generate" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />} Gerar proposta
          </Button>
          <Button onClick={onApplyProposal} disabled={!authorized || busy === "homepage-apply"} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]" data-testid="site-homepage-apply-btn">
            {busy === "homepage-apply" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UploadCloud className="w-4 h-4 mr-2" />} Aplicar na homepage
          </Button>
          <a href="/login" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2.5 text-sm hover:bg-white/[0.04]" data-testid="site-homepage-open-link">
            <ExternalLink className="w-4 h-4" /> Abrir homepage
          </a>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-4" data-testid="site-homepage-preview-grid">
        <div data-testid="site-homepage-live-column">
          <div className="flex items-center justify-between gap-3 mb-3">
            <p className="text-xs uppercase tracking-[0.18em] text-[#93C5FD]">Ao vivo</p>
            <span className="text-[11px] text-muted-foreground" data-testid="site-homepage-live-updated-at">
              {state.updated_at ? `Atualizado em ${new Date(state.updated_at).toLocaleString("pt-PT")}` : "Ainda sem override publicado"}
            </span>
          </div>
          <PreviewShell
            eyebrow="Homepage atual"
            title={state.live?.headline}
            subtitle={state.live?.subtitle}
            primaryCtaLabel={state.live?.primary_cta_label}
            primaryCtaUrl={state.live?.primary_cta_url}
            secondaryCtaLabel={state.live?.secondary_cta_label}
            secondaryCtaUrl={state.live?.secondary_cta_url}
            proofTitle={state.live?.social_proof_title}
            proofItems={state.live?.social_proof_items}
            tone="live"
            testIdPrefix="site-homepage-live"
          />
        </div>

        <div data-testid="site-homepage-proposal-column">
          <div className="flex items-center justify-between gap-3 mb-3">
            <p className="text-xs uppercase tracking-[0.18em] text-[#DDD6FE]">Proposta do agente</p>
            <span className="text-[11px] text-muted-foreground" data-testid="site-homepage-proposal-updated-at">
              {state.last_proposal_at ? `Gerada em ${new Date(state.last_proposal_at).toLocaleString("pt-PT")}` : "Gera uma proposta para começar"}
            </span>
          </div>
          <PreviewShell
            eyebrow="Próxima versão sugerida"
            title={state.proposal?.headline || state.live?.headline}
            subtitle={state.proposal?.subtitle || state.live?.subtitle}
            primaryCtaLabel={state.proposal?.primary_cta_label || state.live?.primary_cta_label}
            primaryCtaUrl={state.proposal?.primary_cta_url || state.live?.primary_cta_url}
            secondaryCtaLabel={state.proposal?.secondary_cta_label || state.live?.secondary_cta_label}
            secondaryCtaUrl={state.proposal?.secondary_cta_url || state.live?.secondary_cta_url}
            proofTitle={state.proposal?.social_proof_title || state.live?.social_proof_title}
            proofItems={state.proposal?.social_proof_items || state.live?.social_proof_items}
            tone="proposal"
            testIdPrefix="site-homepage-proposal"
          />
        </div>
      </div>

      <div className="rounded-[18px] border border-white/10 bg-black/10 p-4 text-sm text-muted-foreground" data-testid="site-homepage-manager-note">
        {authorized
          ? <>Quando aplicares a proposta, o gateway publica overrides seguros na rota <span className="text-slate-100">/login</span> e o histórico aparece automaticamente em <span className="text-slate-100">Alterações do Site</span>.</>
          : <>Para publicar na homepage, autoriza primeiro o gateway. A proposta pode ser gerada já, mas a aplicação fica desbloqueada só depois da autorização.</>}
      </div>
    </section>
  );
};