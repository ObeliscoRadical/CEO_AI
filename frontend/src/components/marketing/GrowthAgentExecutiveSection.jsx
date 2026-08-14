import { useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Activity, AlertTriangle, BarChart3, Bot, ExternalLink, Loader2, RefreshCw, Search, ShieldCheck, Sparkles } from "lucide-react";

const StatCard = ({ label, value, helper, testId }) => (
  <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
    {helper && <p className="text-xs text-muted-foreground mt-2">{helper}</p>}
  </div>
);

const ReportCard = ({ report, prefix }) => {
  if (!report) return <p className="text-sm text-muted-foreground" data-testid={`${prefix}-empty`}>Ainda sem relatório neste período.</p>;
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid={`${prefix}-card`}>
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{report.reference_key}</p>
          <h4 className="font-serif-lux text-xl mt-1" data-testid={`${prefix}-headline`}>{report.headline}</h4>
        </div>
        <span className="text-xs text-muted-foreground" data-testid={`${prefix}-created-at`}>{new Date(report.created_at).toLocaleString("pt-PT")}</span>
      </div>
      <p className="text-sm text-muted-foreground leading-6 mb-4" data-testid={`${prefix}-summary`}>{report.summary}</p>
      <div className="grid md:grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Ações realizadas</p>
          <ul className="space-y-2">{(report.actions_taken || []).map((item, index) => <li key={`${item}-${index}`} data-testid={`${prefix}-action-${index}`}>• {item}</li>)}</ul>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Impacto</p>
          <ul className="space-y-2">{(report.impact || []).map((item, index) => <li key={`${item}-${index}`} data-testid={`${prefix}-impact-${index}`}>• {item}</li>)}</ul>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Aprendizagens</p>
          <ul className="space-y-2">{(report.learnings || []).map((item, index) => <li key={`${item}-${index}`} data-testid={`${prefix}-learning-${index}`}>• {item}</li>)}</ul>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Próximos passos</p>
          <ul className="space-y-2">{(report.next_steps || []).map((item, index) => <li key={`${item}-${index}`} data-testid={`${prefix}-next-${index}`}>• {item}</li>)}</ul>
        </div>
      </div>
    </div>
  );
};

export const GrowthAgentExecutiveSection = ({ data, busy, onSync, onRun }) => {
  const latestReports = useMemo(() => ({
    daily: data?.reports?.daily?.[0] || null,
    weekly: data?.reports?.weekly?.[0] || null,
    monthly: data?.reports?.monthly?.[0] || null,
  }), [data]);

  return (
    <section className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="growth-agent-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-6">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Growth Agent · observabilidade do site</p>
          <h2 className="font-serif-lux text-xl flex items-center gap-2 mt-2"><Bot className="w-5 h-5 text-[#10B981]" /> SEO, GA4 e Google Search Console</h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl" data-testid="growth-agent-description">Esta camada monitoriza continuamente páginas públicas, desempenho, oportunidades SEO, quedas de tráfego, conteúdos desatualizados e interligações internas — sempre respeitando a regra de nunca tocar nas redes sociais, no design ou na navegação.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={onSync} disabled={!!busy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="growth-agent-sync-btn">
            {busy === "sync" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />} Sync Google
          </Button>
          <Button onClick={onRun} disabled={!!busy} className="rounded-full bg-[#10B981] text-white hover:bg-[#059669]" data-testid="growth-agent-run-btn">
            {busy === "run" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Activity className="w-4 h-4 mr-2" />} Executar ciclo Growth
          </Button>
        </div>
      </div>

      <div className="rounded-3xl border border-emerald-400/20 bg-emerald-500/10 p-5 mb-6" data-testid="growth-agent-hard-rule-card">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-300 mt-0.5" />
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-emerald-300 mb-2">Regra explícita e inviolável</p>
            <p className="text-sm text-emerald-50 leading-6" data-testid="growth-agent-hard-rule-text">{data?.policy?.hard_rule}</p>
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-5 gap-4 mb-6" data-testid="growth-agent-stats-grid">
        <StatCard label="Páginas monitorizadas" value={data?.summary?.pages_monitored || 0} helper="Públicas e geridas pelo gateway" testId="growth-agent-stat-pages" />
        <StatCard label="Quedas de tráfego" value={data?.summary?.drop_alerts || 0} helper="URLs com deterioração relevante" testId="growth-agent-stat-drops" />
        <StatCard label="Oportunidades SEO" value={data?.summary?.seo_opportunities || 0} helper="CTR/posição/impressões a melhorar" testId="growth-agent-stat-opportunities" />
        <StatCard label="Páginas stale" value={data?.summary?.stale_pages || 0} helper="Conteúdo candidato a refresh" testId="growth-agent-stat-stale" />
        <StatCard label="Ações registadas" value={data?.summary?.actions_logged || 0} helper="Feed executivo do agente" testId="growth-agent-stat-actions" />
      </div>

      {(data?.blockers || []).length > 0 && (
        <div className="rounded-3xl border border-amber-400/20 bg-amber-500/10 p-5 mb-6" data-testid="growth-agent-blockers-card">
          <div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-amber-300" /><h3 className="font-medium">Bloqueios ou dados em falta</h3></div>
          <ul className="space-y-2 text-sm text-amber-50">{data.blockers.map((item, index) => <li key={`${item}-${index}`} data-testid={`growth-agent-blocker-${index}`}>• {item}</li>)}</ul>
        </div>
      )}

      <div className="grid xl:grid-cols-[0.9fr_1.1fr] gap-5 mb-6">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="growth-agent-google-card">
          <div className="flex items-center gap-2 mb-4"><Search className="w-4 h-4 text-[#3B82F6]" /><h3 className="font-medium">Estado das fontes Google</h3></div>
          <div className="space-y-4 text-sm text-muted-foreground">
            <div data-testid="growth-agent-google-gsc"><span className="text-foreground">Search Console:</span> {data?.sync_run?.source_status?.gsc?.ok ? "ativo" : "pendente/erro"}</div>
            <div data-testid="growth-agent-google-ga4"><span className="text-foreground">GA4 Data API:</span> {data?.sync_run?.source_status?.ga4?.ok ? "ativo" : "pendente/erro"}</div>
            <div data-testid="growth-agent-google-tag"><span className="text-foreground">Tag GA4 no site:</span> {data?.google?.ga4_measurement_installed ? "instalada" : "ainda não instalada"}</div>
            <div data-testid="growth-agent-google-property"><span className="text-foreground">Property ID:</span> {data?.google?.ga4_property_id || "—"}</div>
            <div data-testid="growth-agent-google-site"><span className="text-foreground">Site GSC:</span> {data?.google?.gsc_site_url || "—"}</div>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="growth-agent-clusters-card">
          <div className="flex items-center gap-2 mb-4"><Sparkles className="w-4 h-4 text-[#A78BFA]" /><h3 className="font-medium">Clusters de keywords</h3></div>
          {(data?.keyword_clusters || []).length === 0 ? <p className="text-sm text-muted-foreground" data-testid="growth-agent-clusters-empty">Sem clusters suficientes ainda.</p> : (
            <div className="space-y-3">
              {data.keyword_clusters.slice(0, 5).map((cluster, index) => (
                <div key={`${cluster.cluster}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`growth-agent-cluster-${index}`}>
                  <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                    <p className="font-medium" data-testid={`growth-agent-cluster-name-${index}`}>{cluster.cluster}</p>
                    {cluster.needs_new_content && <span className="text-[10px] uppercase tracking-[0.18em] text-amber-300" data-testid={`growth-agent-cluster-gap-${index}`}>novo conteúdo</span>}
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid={`growth-agent-cluster-meta-${index}`}>{cluster.impressions} impressões · {cluster.clicks} cliques · cobertura {cluster.coverage}</p>
                  <p className="text-sm text-muted-foreground mt-2" data-testid={`growth-agent-cluster-queries-${index}`}>{(cluster.queries || []).join(", ") || "Sem queries capturadas"}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid xl:grid-cols-[1.06fr_0.94fr] gap-5 mb-6">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="growth-agent-landing-pages-card">
          <div className="flex items-center gap-2 mb-4"><BarChart3 className="w-4 h-4 text-[#F59E0B]" /><h3 className="font-medium">Comparação por URL / landing page</h3></div>
          {(data?.landing_pages || []).length === 0 ? <p className="text-sm text-muted-foreground">Ainda sem páginas monitorizadas.</p> : (
            <div className="space-y-3">
              {data.landing_pages.slice(0, 6).map((page, index) => (
                <div key={`${page.page_path}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`growth-agent-page-${index}`}>
                  <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                    <div>
                      <p className="font-medium" data-testid={`growth-agent-page-title-${index}`}>{page.title}</p>
                      <a href={page.public_url} target="_blank" rel="noreferrer" className="text-xs text-[#3B82F6] hover:underline inline-flex items-center gap-1" data-testid={`growth-agent-page-url-${index}`}>
                        {page.public_url} <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    {page.requires_attention && <span className="text-[10px] uppercase tracking-[0.18em] text-amber-300" data-testid={`growth-agent-page-attention-${index}`}>atenção</span>}
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid={`growth-agent-page-signals-${index}`}>Sinal atual {page.current_signal} · baseline {page.baseline_signal} · views {page.signals?.internal_views_recent || 0} · GSC clicks {page.signals?.gsc_clicks_recent || 0} · GA sessions {page.signals?.ga_sessions_recent || 0}</p>
                  <p className="text-sm text-muted-foreground mt-2" data-testid={`growth-agent-page-flags-${index}`}>{page.traffic_drop ? "Queda de tráfego detetada. " : ""}{page.seo_opportunity ? "Oportunidade SEO ativa. " : ""}{page.stale_content ? "Conteúdo desatualizado." : ""}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="growth-agent-actions-card">
          <div className="flex items-center gap-2 mb-4"><Activity className="w-4 h-4 text-[#10B981]" /><h3 className="font-medium">Feed executivo automático</h3></div>
          {(data?.actions || []).length === 0 ? <p className="text-sm text-muted-foreground" data-testid="growth-agent-actions-empty">O agente ainda não registou ações nesta camada.</p> : (
            <div className="space-y-3">
              {data.actions.slice(0, 6).map((item, index) => (
                <div key={`${item.created_at}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`growth-agent-action-${index}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                    <p className="font-medium" data-testid={`growth-agent-action-title-${index}`}>{item.title}</p>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-slate-300" data-testid={`growth-agent-action-type-${index}`}>{item.action_type}</span>
                  </div>
                  <p className="text-xs text-muted-foreground" data-testid={`growth-agent-action-url-${index}`}>{item.page_url}</p>
                  <p className="text-sm text-muted-foreground mt-2" data-testid={`growth-agent-action-detail-${index}`}>{item.detail}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="growth-agent-reports-card">
        <div className="flex items-center gap-2 mb-4"><Bot className="w-4 h-4 text-[#3B82F6]" /><h3 className="font-medium">Relatórios executivos automáticos</h3></div>
        <Tabs defaultValue="daily" data-testid="growth-agent-reports-tabs">
          <TabsList className="bg-white/[0.04] rounded-full p-1 mb-4">
            <TabsTrigger value="daily" data-testid="growth-agent-tab-daily">Diário</TabsTrigger>
            <TabsTrigger value="weekly" data-testid="growth-agent-tab-weekly">Semanal</TabsTrigger>
            <TabsTrigger value="monthly" data-testid="growth-agent-tab-monthly">Mensal</TabsTrigger>
          </TabsList>
          <TabsContent value="daily"><ReportCard report={latestReports.daily} prefix="growth-agent-report-daily" /></TabsContent>
          <TabsContent value="weekly"><ReportCard report={latestReports.weekly} prefix="growth-agent-report-weekly" /></TabsContent>
          <TabsContent value="monthly"><ReportCard report={latestReports.monthly} prefix="growth-agent-report-monthly" /></TabsContent>
        </Tabs>
      </div>
    </section>
  );
};