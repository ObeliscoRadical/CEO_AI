import { Globe, Loader2, RefreshCw, RotateCcw, ShieldCheck, Sparkles, Trash2, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SiteChangeHistorySection } from "@/components/marketing/SiteChangeHistorySection";
import { SiteHomepageManagerSection } from "@/components/marketing/SiteHomepageManagerSection";

const StatCard = ({ label, value, helper, testId }) => (
  <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
    {helper && <p className="text-xs text-muted-foreground mt-2">{helper}</p>}
  </div>
);

export const SitePublishingGatewaySection = ({ data, busy, onAuthorize, onRunNow, onRollback, onRemove, onRefresh, onGenerateHomepageProposal, onApplyHomepageProposal }) => {
  const settings = data?.settings || {};
  const summary = data?.summary || {};
  const architecture = data?.architecture || {};
  const entries = data?.entries || [];
  const logs = data?.logs || [];
  const analytics = data?.analytics || {};
  const changeHistory = data?.change_history || null;
  const homepage = data?.homepage || null;

  return (
    <section className="surface rounded-[22px] p-5 md:p-6 mb-5" data-testid="site-publishing-gateway-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Agente · Site</p>
          <h2 className="font-serif-lux text-lg flex items-center gap-2 mt-2"><Globe className="w-5 h-5 text-[#3B82F6]" /> Gateway</h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl" data-testid="site-publishing-description">Publicação direta no site, sem CMS externo, com logs e rollback.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {!settings.authorized ? (
            <Button onClick={onAuthorize} disabled={busy} className="rounded-full bg-[#10B981] text-white hover:bg-[#059669]" data-testid="site-publishing-authorize-btn">
              {busy === "authorize" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ShieldCheck className="w-4 h-4 mr-2" />} Autorizar uma vez
            </Button>
          ) : (
            <Button onClick={onRunNow} disabled={busy} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]" data-testid="site-publishing-run-btn">
              {busy === "run" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Wand2 className="w-4 h-4 mr-2" />} Publicar agora
            </Button>
          )}
          <Button onClick={onRefresh} disabled={busy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="site-publishing-refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Atualizar
          </Button>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-5" data-testid="site-publishing-stats-grid">
        <StatCard label="Autorização" value={settings.authorized ? "Ativa" : "Pendente"} helper={settings.authorization_note} testId="site-publishing-stat-authorized" />
        <StatCard label="Entradas publicadas" value={summary.published_entries || 0} helper="Artigos, páginas e overrides ativos" testId="site-publishing-stat-published" />
        <StatCard label="Falhas monitorizadas" value={summary.failures || 0} helper="Registadas no log interno" testId="site-publishing-stat-failures" />
        <StatCard label="Rollbacks" value={summary.rollbacks || 0} helper="Reversões executadas com histórico" testId="site-publishing-stat-rollbacks" />
      </div>

      <div className="grid xl:grid-cols-[0.92fr_1.08fr] gap-4 mb-5">
        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="site-publishing-architecture-card">
          <div className="flex items-center gap-2 mb-4"><Sparkles className="w-4 h-4 text-[#A78BFA]" /><h3 className="font-medium">Arquitetura real encontrada</h3></div>
          <div className="space-y-4 text-sm text-muted-foreground">
            <p data-testid="site-publishing-frontend-summary"><span className="text-foreground">Frontend:</span> {architecture.frontend?.stack}. Conteúdo público atual: {architecture.frontend?.public_content_storage_today}</p>
            <p data-testid="site-publishing-backend-summary"><span className="text-foreground">Backend:</span> {architecture.backend?.stack} com rotas em {architecture.backend?.api_prefix}.</p>
            <p data-testid="site-publishing-cms-summary"><span className="text-foreground">CMS:</span> {architecture.cms?.exists ? "Existe" : "Não existe"}. {architecture.cms?.details}</p>
            <p data-testid="site-publishing-mechanism-summary"><span className="text-foreground">Mecanismo escolhido:</span> {architecture.chosen_mechanism?.name} — {architecture.chosen_mechanism?.reason}</p>
          </div>
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="site-publishing-analytics-card">
          <h3 className="font-medium mb-4">Aprendizagem do gateway</h3>
          <div className="space-y-4 text-sm text-muted-foreground">
            <div data-testid="site-publishing-campaign-comparison-block">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Analytics comparativos por campanha</p>
              {(analytics.campaign_comparison || []).length === 0 ? <p>Sem campanhas publicadas ainda.</p> : (
                <div className="space-y-2">
                  {analytics.campaign_comparison.slice(0, 3).map((item, index) => (
                    <div key={`${item.campaign_label}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-3" data-testid={`site-publishing-campaign-${index}`}>
                      <p className="text-foreground font-medium">{item.campaign_label}</p>
                      <p>{item.published_count} publicações · {item.total_views} views · score médio {item.avg_editorial_score}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div data-testid="site-publishing-editorial-score-block">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Scoring editorial</p>
              <p>O gateway pontua SEO, estrutura, imagem hero, estado publicado e consumo real para ajudar o agente a aprender.</p>
            </div>
            <div data-testid="site-publishing-creatives-block">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Criativos automáticos</p>
              <p>{settings.auto_generate_hero_images ? "Ativos" : "Desativados"}: o agente pode reutilizar a geração de imagem já existente para artigos e páginas SEO.</p>
            </div>
          </div>
        </div>
      </div>

      <SiteHomepageManagerSection
        homepage={homepage}
        busy={busy}
        authorized={!!settings.authorized}
        onGenerateProposal={onGenerateHomepageProposal}
        onApplyProposal={onApplyHomepageProposal}
      />

      <SiteChangeHistorySection changeHistory={changeHistory} busy={busy} onRollback={onRollback} />

      <div className="grid xl:grid-cols-[1.02fr_0.98fr] gap-4">
        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="site-publishing-entries-card">
          <h3 className="font-medium mb-4">Publicações e páginas geridas</h3>
          {entries.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="site-publishing-entries-empty">Ainda não existem conteúdos públicos no gateway.</p> : (
            <div className="space-y-3">
              {entries.slice(0, 6).map((entry, index) => (
                <div key={entry.id} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`site-publishing-entry-${index}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                    <div>
                      <p className="font-medium text-foreground" data-testid={`site-publishing-entry-title-${index}`}>{entry.title}</p>
                      <a href={entry.public_url} target="_blank" rel="noreferrer" className="text-xs text-[#3B82F6] hover:underline" data-testid={`site-publishing-entry-url-${index}`}>{entry.public_url}</a>
                    </div>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-slate-300" data-testid={`site-publishing-entry-status-${index}`}>{entry.status}</span>
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid={`site-publishing-entry-meta-${index}`}>{entry.kind} · keyword {entry.seo_keyword} · score {entry.editorial_score} · views {entry.metrics?.views || 0}</p>
                  <p className="text-sm text-muted-foreground mt-2" data-testid={`site-publishing-entry-reason-${index}`}>{entry.strategy_reason}</p>
                  <div className="flex gap-2 flex-wrap mt-4">
                    <Button onClick={() => onRollback(entry.id)} size="sm" variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid={`site-publishing-entry-rollback-${index}`}>
                      <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Rollback
                    </Button>
                    <Button onClick={() => onRemove(entry.id)} size="sm" variant="outline" className="rounded-full border-rose-400/20 text-rose-300 hover:bg-rose-500/10" data-testid={`site-publishing-entry-remove-${index}`}>
                      <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Remover
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="site-publishing-logs-card">
          <h3 className="font-medium mb-4">Log e rollback</h3>
          {logs.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="site-publishing-logs-empty">Sem eventos registados ainda.</p> : (
            <div className="space-y-3">
              {logs.slice(0, 6).map((log, index) => (
                <div key={`${log.created_at}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`site-publishing-log-${index}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                    <p className="font-medium text-foreground" data-testid={`site-publishing-log-action-${index}`}>{log.action} · {log.status}</p>
                    <span className="text-xs text-muted-foreground" data-testid={`site-publishing-log-date-${index}`}>{new Date(log.created_at).toLocaleString("pt-PT")}</span>
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid={`site-publishing-log-keyword-${index}`}>URL {log.url || "—"} · keyword {log.seo_keyword || "—"} · objetivo {log.objective || "—"}</p>
                  <p className="text-sm text-muted-foreground mt-2" data-testid={`site-publishing-log-reason-${index}`}>{log.strategy_reason || log.error || "Evento registado."}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};