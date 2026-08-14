import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Bot, Globe, Target, PauseCircle, PlayCircle, RefreshCw, CheckCircle2, TrendingUp, BarChart3, FileText, Sparkles, AlertTriangle, Compass } from "lucide-react";

const MetricCard = ({ label, value, helper, testId }) => (
  <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
    {helper && <p className="text-xs text-muted-foreground mt-2">{helper}</p>}
  </div>
);

const StatusBadge = ({ status }) => {
  const map = {
    awaiting_approval: "border-amber-400/20 bg-amber-500/10 text-amber-300",
    running: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    paused: "border-slate-400/20 bg-slate-500/10 text-slate-200",
  };
  const label = {
    awaiting_approval: "À espera de aprovação",
    running: "Modo autônomo ativo",
    paused: "Pausado",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] ${map[status] || map.awaiting_approval}`} data-testid="mkt-organic-status-badge">
      {label[status] || "Estado"}
    </span>
  );
};

const BulletList = ({ items = [], testIdPrefix }) => (
  <ul className="space-y-2 text-sm text-foreground">
    {(items || []).map((item, index) => <li key={`${item}-${index}`} data-testid={`${testIdPrefix}-${index}`}>• {item}</li>)}
  </ul>
);

const ReportPanel = ({ report, prefix }) => {
  if (!report) {
    return <p className="text-sm text-muted-foreground" data-testid={`${prefix}-empty`}>O agente ainda não gerou relatório neste período.</p>;
  }
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid={`${prefix}-card`}>
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{report.reference_key}</p>
          <h4 className="font-serif-lux text-xl mt-1" data-testid={`${prefix}-headline`}>{report.headline}</h4>
        </div>
        <span className="text-xs text-muted-foreground" data-testid={`${prefix}-created-at`}>{new Date(report.created_at).toLocaleString("pt-PT")}</span>
      </div>
      <p className="text-sm text-muted-foreground leading-6 mb-5" data-testid={`${prefix}-summary`}>{report.summary}</p>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Ações executadas</p>
          <BulletList items={report.executed_actions} testIdPrefix={`${prefix}-executed`} />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Resultados</p>
          <BulletList items={report.results} testIdPrefix={`${prefix}-results`} />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Aprendizados</p>
          <BulletList items={report.learnings} testIdPrefix={`${prefix}-learnings`} />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Próximos ajustes</p>
          <BulletList items={report.next_adjustments} testIdPrefix={`${prefix}-adjustments`} />
        </div>
      </div>
      <div className="mt-5">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Recomendações</p>
        <BulletList items={report.recommendations} testIdPrefix={`${prefix}-recommendations`} />
      </div>
    </div>
  );
};

export const OrganicGrowthAgentSection = ({ data, busy, onCreateStrategy, onApprove, onPause, onResume, onReanalyze, onUpdateObjective }) => {
  const agent = data?.agent || null;
  const [domain, setDomain] = useState(agent?.domain || "");
  const [objective, setObjective] = useState(agent?.objective || "Mais leads qualificados com foco em conversão e receita.");

  useEffect(() => {
    setDomain(agent?.domain || "");
    setObjective(agent?.objective || "Mais leads qualificados com foco em conversão e receita.");
  }, [agent?.domain, agent?.objective]);

  const latestReports = useMemo(() => ({
    daily: data?.reports?.daily?.[0] || null,
    weekly: data?.reports?.weekly?.[0] || null,
    monthly: data?.reports?.monthly?.[0] || null,
  }), [data]);

  const submit = async () => {
    await onCreateStrategy({ domain, objective });
  };

  return (
    <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-organic-agent">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Growth Agent · território exclusivo</p>
          <h2 className="font-serif-lux text-xl flex items-center gap-2 mt-2"><Bot className="w-5 h-5 text-[#3B82F6]" /> Estratégia autónoma do site</h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl" data-testid="mkt-organic-description">Este agente pede o domínio, analisa o site, cruza metas dos Diretores Financeiro e Comercial, propõe a estratégia de 90 dias e, após aprovação inicial, entra em modo autónomo para criar, publicar, medir e otimizar apenas o site e o SEO.</p>
        </div>
        {agent && <StatusBadge status={agent.status} />}
      </div>

      <div className="grid xl:grid-cols-[0.9fr_1.1fr] gap-5 mb-6">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-setup-card">
          <div className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-organic-domain-label">Domínio do site</label>
              <Input value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="Ex.: https://empresa.pt" className="mt-2" data-testid="mkt-organic-domain-input" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid="mkt-organic-objective-label">Objetivo do agente</label>
              <Input value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Ex.: Aumentar leads qualificados sem sacrificar margem" className="mt-2" data-testid="mkt-organic-objective-input" />
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button onClick={submit} disabled={busy || !domain.trim()} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]" data-testid="mkt-organic-analyze-btn">
                {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Globe className="w-4 h-4 mr-2" />} {agent ? "Atualizar estratégia" : "Analisar site e gerar estratégia"}
              </Button>
              {agent && (
                <Button onClick={() => onUpdateObjective(objective)} disabled={busy || !objective.trim()} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="mkt-organic-save-objective-btn">
                  {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Target className="w-4 h-4 mr-2" />} Alterar objetivo
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-controls-card">
          <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Painel operacional</p>
              <h3 className="font-medium mt-1" data-testid="mkt-organic-panel-title">Controlos do agente</h3>
            </div>
            {agent?.autonomous_mode && <span className="text-[11px] px-3 py-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 text-emerald-300" data-testid="mkt-organic-autonomous-badge">Modo autônomo</span>}
          </div>
          <div className="flex gap-2 flex-wrap mb-4">
            {agent?.status === "awaiting_approval" && (
              <Button onClick={onApprove} disabled={busy} className="rounded-full bg-[#10B981] text-white hover:bg-[#059669]" data-testid="mkt-organic-approve-btn">
                {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle2 className="w-4 h-4 mr-2" />} Aprovar Estratégia
              </Button>
            )}
            {agent?.status === "running" && (
              <Button onClick={onPause} disabled={busy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="mkt-organic-pause-btn">
                <PauseCircle className="w-4 h-4 mr-2" /> Pausar
              </Button>
            )}
            {agent?.status === "paused" && (
              <Button onClick={onResume} disabled={busy} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]" data-testid="mkt-organic-resume-btn">
                <PlayCircle className="w-4 h-4 mr-2" /> Retomar
              </Button>
            )}
            {agent && (
              <Button onClick={onReanalyze} disabled={busy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="mkt-organic-reanalyze-btn">
                {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />} Reanalisar site
              </Button>
            )}
          </div>
          <div className="grid sm:grid-cols-2 gap-3 text-sm text-muted-foreground">
            <div data-testid="mkt-organic-status-card"><span className="text-foreground">Estado:</span> {agent ? (agent.status === "running" ? "A operar autonomamente" : agent.status === "paused" ? "Pausado" : "À espera da aprovação inicial") : "Ainda não configurado"}</div>
            <div data-testid="mkt-organic-domain-card"><span className="text-foreground">Domínio:</span> {agent?.domain || "—"}</div>
            <div data-testid="mkt-organic-last-analysis-card"><span className="text-foreground">Última análise:</span> {agent?.last_analysis_at ? new Date(agent.last_analysis_at).toLocaleString("pt-PT") : "—"}</div>
            <div data-testid="mkt-organic-last-run-card"><span className="text-foreground">Última execução:</span> {agent?.last_run_at ? new Date(agent.last_run_at).toLocaleString("pt-PT") : "Ainda não arrancou"}</div>
          </div>
        </div>
      </div>

      {agent?.metrics && (
        <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6" data-testid="mkt-organic-metrics-grid">
          <MetricCard label="Tráfego" value={agent.metrics.traffic || 0} helper={agent.metrics.traffic_label} testId="mkt-organic-metric-traffic" />
          <MetricCard label="Leads" value={agent.metrics.leads || 0} helper="Novos leads CRM nos últimos 30 dias" testId="mkt-organic-metric-leads" />
          <MetricCard label="Conversão" value={`${agent.metrics.conversion_rate || 0}%`} helper="Leads / tráfego do site" testId="mkt-organic-metric-conversion" />
          <MetricCard label="Páginas publicadas" value={agent.metrics.published_site_entries || 0} helper="Conteúdo público gerido pelo gateway" testId="mkt-organic-metric-published" />
        </div>
      )}

      {agent?.blockers?.length > 0 && (
        <div className="rounded-3xl border border-amber-400/20 bg-amber-500/10 p-5 mb-6" data-testid="mkt-organic-blockers-card">
          <div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-amber-300" /><h3 className="font-medium">Bloqueios do site e SEO</h3></div>
          <BulletList items={agent.blockers} testIdPrefix="mkt-organic-blocker" />
        </div>
      )}

      {agent && (
        <div className="grid xl:grid-cols-[0.92fr_1.08fr] gap-5 mb-6">
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-site-analysis">
            <div className="flex items-center gap-2 mb-4"><Compass className="w-4 h-4 text-[#A78BFA]" /><h3 className="font-medium">Leitura do site</h3></div>
            <p className="text-sm text-muted-foreground leading-6 mb-4" data-testid="mkt-organic-site-summary">{agent.site_analysis?.website_summary}</p>
            <div className="space-y-4 text-sm">
              <div data-testid="mkt-organic-positioning"><span className="text-foreground">Posicionamento:</span> {agent.site_analysis?.positioning}</div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Serviços / temas principais</p>
                <BulletList items={agent.site_analysis?.primary_services} testIdPrefix="mkt-organic-service" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Oportunidades encontradas</p>
                <div className="space-y-3">
                  {(agent.site_analysis?.opportunities || []).map((item, index) => (
                    <div key={`${item.title}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-organic-opportunity-${index}`}>
                      <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                        <p className="font-medium" data-testid={`mkt-organic-opportunity-title-${index}`}>{item.title}</p>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-[#A78BFA]" data-testid={`mkt-organic-opportunity-priority-${index}`}>{item.priority}</span>
                      </div>
                      <p className="text-sm text-muted-foreground" data-testid={`mkt-organic-opportunity-detail-${index}`}>{item.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-director-alignment">
              <div className="flex items-center gap-2 mb-4"><Sparkles className="w-4 h-4 text-[#3B82F6]" /><h3 className="font-medium">Alinhamento obrigatório com os Diretores</h3></div>
              <div className="grid md:grid-cols-2 gap-4">
                {[
                  { key: "financeiro", label: "Diretor Financeiro" },
                  { key: "comercial", label: "Diretor Comercial" },
                ].map(({ key, label }) => (
                  <div key={key} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-organic-director-${key}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-[#A78BFA] mb-2">{label}</p>
                    <p className="text-sm text-muted-foreground mb-4" data-testid={`mkt-organic-director-summary-${key}`}>{agent.director_alignment?.[key]?.summary}</p>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">Prioridades</p>
                    <BulletList items={agent.director_alignment?.[key]?.priorities} testIdPrefix={`mkt-organic-director-priority-${key}`} />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-strategy-card">
              <div className="flex items-center gap-2 mb-4"><Target className="w-4 h-4 text-[#10B981]" /><h3 className="font-medium">Estratégia de 90 dias</h3></div>
              <p className="text-sm text-muted-foreground leading-6 mb-4" data-testid="mkt-organic-strategy-thesis">{agent.strategy?.thesis}</p>
              <div className="rounded-2xl border border-white/8 bg-black/10 p-4 mb-4" data-testid="mkt-organic-strategy-north-star">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">North Star</p>
                <p className="font-medium">{agent.strategy?.north_star}</p>
              </div>
              <div className="grid md:grid-cols-3 gap-3 mb-4">
                {(agent.strategy?.phase_plan || []).map((phase, index) => (
                  <div key={`${phase.phase}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-organic-phase-${index}`}>
                    <p className="text-xs uppercase tracking-[0.18em] text-[#A78BFA] mb-2" data-testid={`mkt-organic-phase-title-${index}`}>{phase.phase}</p>
                    <p className="font-medium text-sm" data-testid={`mkt-organic-phase-goal-${index}`}>{phase.goal}</p>
                    <div className="mt-3"><BulletList items={phase.actions} testIdPrefix={`mkt-organic-phase-action-${index}`} /></div>
                  </div>
                ))}
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div data-testid="mkt-organic-kpis">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">KPIs do agente</p>
                  <div className="space-y-3">{(agent.strategy?.kpis || []).map((item, index) => <div key={`${item.label}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-organic-kpi-${index}`}><p className="font-medium">{item.label}</p><p className="text-sm text-muted-foreground mt-2">{item.target}</p></div>)}</div>
                </div>
                <div data-testid="mkt-organic-guardrails">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Guardrails estratégicos</p>
                  <BulletList items={agent.strategy?.decision_guardrails} testIdPrefix="mkt-organic-guardrail" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {agent && (
        <div className="grid xl:grid-cols-[1fr_1fr] gap-5">
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-actions-card">
            <div className="flex items-center gap-2 mb-4"><TrendingUp className="w-4 h-4 text-[#A78BFA]" /><h3 className="font-medium">Ações autónomas no site</h3></div>
            {(data?.actions || []).length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="mkt-organic-actions-empty">Depois da aprovação inicial, o Growth Agent começará a criar atualizações do site, publicá-las pelo gateway e reajustá-las aqui.</p>
            ) : (
              <div className="space-y-3">
                {(data?.actions || []).map((item, index) => (
                  <div key={`${item.title}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-organic-action-${index}`}>
                    <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                      <p className="font-medium" data-testid={`mkt-organic-action-title-${index}`}>{item.title}</p>
                      <span className="text-[10px] uppercase tracking-[0.18em] text-[#3B82F6]" data-testid={`mkt-organic-action-status-${index}`}>{item.status}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2" data-testid={`mkt-organic-action-meta-${index}`}>{item.format} · {item.theme}</p>
                    <p className="text-sm text-muted-foreground" data-testid={`mkt-organic-action-why-${index}`}>{item.why_now}</p>
                    {item.public_url && <p className="text-xs text-emerald-300 mt-3" data-testid={`mkt-organic-action-run-at-${index}`}>Publicado em {item.public_url}</p>}
                    {item.note && <p className="text-xs text-amber-300 mt-3" data-testid={`mkt-organic-action-note-${index}`}>{item.note}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-organic-reports-card">
            <div className="flex items-center gap-2 mb-4"><FileText className="w-4 h-4 text-[#F59E0B]" /><h3 className="font-medium">Relatórios automáticos</h3></div>
            <Tabs defaultValue="daily" data-testid="mkt-organic-reports-tabs">
              <TabsList className="bg-white/[0.04] rounded-full p-1 mb-4">
                <TabsTrigger value="daily" data-testid="mkt-organic-report-tab-daily">Diário</TabsTrigger>
                <TabsTrigger value="weekly" data-testid="mkt-organic-report-tab-weekly">Semanal</TabsTrigger>
                <TabsTrigger value="monthly" data-testid="mkt-organic-report-tab-monthly">Mensal</TabsTrigger>
              </TabsList>
              <TabsContent value="daily"><ReportPanel report={latestReports.daily} prefix="mkt-organic-report-daily" /></TabsContent>
              <TabsContent value="weekly"><ReportPanel report={latestReports.weekly} prefix="mkt-organic-report-weekly" /></TabsContent>
              <TabsContent value="monthly"><ReportPanel report={latestReports.monthly} prefix="mkt-organic-report-monthly" /></TabsContent>
            </Tabs>
          </div>
        </div>
      )}

      {!agent && (
        <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.02] p-8 mt-2 text-center" data-testid="mkt-organic-empty-state">
          <BarChart3 className="w-8 h-8 text-[#A78BFA] mx-auto mb-3" />
          <p className="font-medium">Primeira execução: peça o domínio e aprove a estratégia inicial</p>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl mx-auto">Depois disso, o agente entra em modo autónomo, gera ações para o site, publica através do gateway, mede sinais de tráfego/leads/conversão e só interrompe para decisões estratégicas reais.</p>
        </div>
      )}
    </div>
  );
};