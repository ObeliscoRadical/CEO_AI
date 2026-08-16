import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle2, Facebook, Instagram, Link2, Loader2, RefreshCw, ShieldCheck, Unlink } from "lucide-react";

const STATE_META = {
  not_connected: { label: "Não ligada", tone: "text-slate-200 bg-slate-500/15 border-slate-400/20" },
  pending_selection: { label: "Escolher página", tone: "text-amber-300 bg-amber-500/15 border-amber-400/20" },
  connected: { label: "Ligação pronta", tone: "text-emerald-300 bg-emerald-500/15 border-emerald-400/20" },
  degraded: { label: "Precisa de rever", tone: "text-red-300 bg-red-500/15 border-red-400/20" },
};

const ChannelToggle = ({ channel, Icon, label, enabled, onToggle, testId }) => (
  <button
    type="button"
    data-testid={testId}
    onClick={() => onToggle(channel)}
    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${enabled ? "border-[#A78BFA] text-[#A78BFA] bg-[#A78BFA]/10" : "border-white/15 text-muted-foreground"}`}
  >
    <Icon className="w-3.5 h-3.5" />
    {label}
  </button>
);

export const MetaConnectionSection = ({
  social,
  targets,
  onToggleTarget,
  onConnect,
  onDisconnect,
  onRunDiagnostics,
  onSelectPage,
  diagnosticsBusy,
  selectingPageId,
}) => {
  const data = social || { configured: false, connected: false, checks: [], available_pages: [], missing_config: [] };
  const state = data.connection_state || (data.connected ? "connected" : "not_connected");
  const meta = STATE_META[state] || STATE_META.not_connected;
  const insightsStatus = data.insights_status || (data.live_metrics_ready ? "ready" : data.insights_permissions_ready ? "permission_ready" : "unverified");
  const analyticsCopy = data.live_metrics_ready
    ? { badge: "live", text: "Métricas reais prontas para sincronização a partir da Meta." }
    : insightsStatus === "no_data"
      ? { badge: "waiting-data", text: "Permissões de insights validadas, mas a Meta ainda não devolveu dados suficientes para trocar o painel para real." }
      : insightsStatus === "permission_ready"
        ? { badge: "waiting-probe", text: "Scopes de analytics presentes. Falta apenas a Meta devolver um probe real para sair do modo MOCKED." }
        : insightsStatus === "permission_denied"
          ? { badge: "mocked", text: "A conta está ligada, mas o token desta sessão ainda não tem leitura de insights validada pela Meta." }
          : insightsStatus === "expired"
            ? { badge: "mocked", text: "O token Meta expirou para leitura de insights. É preciso reconectar a conta." }
            : { badge: "mocked", text: "Mantidos em modo MOCKED até a Meta validar permissões de insights." };
  const subtitle = data.connected
    ? `Ligado a ${data.page_name || "Página"}${data.ig_username ? ` · @${data.ig_username}` : " · sem Instagram profissional"}`
    : data.pending_selection
      ? "OAuth concluído. Falta escolher qual Página de Facebook/Instagram pertence a esta empresa ativa."
      : data.configured
        ? "Ligue Facebook + Instagram da empresa ativa e valide a ligação antes de publicar."
        : "O fluxo já está preparado; falta apenas introduzir as credenciais da app Meta para o ativar.";

  return (
    <div className="surface rounded-[22px] p-5 md:p-6 mb-5" data-testid="mkt-social">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div className="space-y-3 max-w-3xl">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="font-serif-lux text-lg" data-testid="mkt-social-title">Meta · Facebook · Instagram</h2>
            <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] ${meta.tone}`} data-testid="mkt-meta-state">
              {meta.label}
            </span>
            {analyticsCopy.badge === "live" ? (
              <span className="text-[11px] px-3 py-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 text-emerald-300" data-testid="mkt-meta-live-badge">
                Analytics reais
              </span>
            ) : analyticsCopy.badge === "waiting-data" ? (
              <span className="text-[11px] px-3 py-1.5 rounded-full border border-sky-400/20 bg-sky-500/10 text-sky-200" data-testid="mkt-meta-permission-badge">
                Permissões OK · a aguardar dados
              </span>
            ) : (
              <span className="text-[11px] px-3 py-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 text-amber-300" data-testid="mkt-meta-mocked-badge">
                Analytics <strong>MOCKED</strong>
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground" data-testid={data.connected ? "mkt-social-connected" : data.configured ? "mkt-social-hint" : "mkt-social-notconfigured"}>{subtitle}</p>
          {!data.connected && (
            <p className="text-[11px] text-muted-foreground break-all" data-testid="mkt-social-redirect-uri">
              Redirect URI: <code className="text-[#A78BFA]">{data.redirect_uri}</code>
            </p>
          )}
        </div>

        <div className="flex gap-2 flex-wrap">
          <Button data-testid="mkt-connect-btn" onClick={onConnect} disabled={!data.configured} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] disabled:opacity-50">
            <Link2 className="w-4 h-4 mr-2" />
            {data.connected || data.pending_selection ? "Reconectar" : "Ligar Meta"}
          </Button>
          <Button data-testid="mkt-meta-diagnostics-btn" onClick={onRunDiagnostics} disabled={diagnosticsBusy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
            {diagnosticsBusy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Validar ligação
          </Button>
          {(data.connected || data.pending_selection) && (
            <Button data-testid="mkt-disconnect-btn" onClick={onDisconnect} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
              <Unlink className="w-4 h-4 mr-2" />
              Desligar
            </Button>
          )}
        </div>
      </div>

      {!data.configured && data.missing_config?.length > 0 && (
        <div className="rounded-3xl border border-amber-400/20 bg-amber-500/10 p-4 mb-5" data-testid="mkt-meta-missing-config">
          <p className="text-sm text-amber-200">Faltam as variáveis <strong>{data.missing_config.join(", ")}</strong> para ativar o OAuth real.</p>
        </div>
      )}

      <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-4 mb-4">
        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="mkt-meta-checks-card">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-[#A78BFA]" />
            <h3 className="font-medium">Checklist da ligação</h3>
          </div>
          <div className="space-y-3">
            {(data.checks || []).map((check, index) => (
              <div key={`${check.id || index}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-meta-check-${index}`}>
                <div className="flex items-center gap-2 mb-2">
                  {check.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-amber-300" />}
                  <p className="font-medium text-sm" data-testid={`mkt-meta-check-label-${index}`}>{check.label}</p>
                </div>
                <p className="text-xs text-muted-foreground" data-testid={`mkt-meta-check-detail-${index}`}>{check.detail}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="mkt-meta-status-card">
          <div className="flex items-center gap-2 mb-4">
            <Facebook className="w-4 h-4 text-[#3B82F6]" />
            <h3 className="font-medium">Estado operacional</h3>
          </div>
          <div className="space-y-4 text-sm">
            <div data-testid="mkt-meta-status-facebook">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Facebook</p>
              <p>{data.has_facebook ? data.page_name || "Página ligada" : "Ainda sem Página validada"}</p>
            </div>
            <div data-testid="mkt-meta-status-instagram">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Instagram</p>
              <p>{data.has_instagram ? `@${data.ig_username || "conta profissional ligada"}` : "Conta profissional ainda em falta"}</p>
            </div>
            <div data-testid="mkt-meta-status-analytics">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Analytics</p>
              <p>{analyticsCopy.text}</p>
              {data.insights_probe_detail && (
                <p className="text-xs text-muted-foreground mt-2" data-testid="mkt-meta-status-analytics-detail">{data.insights_probe_detail}</p>
              )}
              {data.insights_last_checked_at && (
                <p className="text-[11px] text-muted-foreground mt-2" data-testid="mkt-meta-status-analytics-checked-at">
                  Última validação: {new Date(data.insights_last_checked_at).toLocaleString("pt-PT")}
                </p>
              )}
            </div>
          </div>

          {data.connected && (
            <div className="flex items-center gap-2 mt-5 pt-4 border-t border-white/[0.06] flex-wrap" data-testid="mkt-social-targets">
              <span className="text-xs text-muted-foreground mr-1">Publicar em:</span>
              <ChannelToggle channel="instagram" Icon={Instagram} label="Instagram" enabled={targets.instagram} onToggle={onToggleTarget} testId="mkt-social-target-instagram" />
              <ChannelToggle channel="facebook" Icon={Facebook} label="Facebook" enabled={targets.facebook} onToggle={onToggleTarget} testId="mkt-social-target-facebook" />
            </div>
          )}
        </div>
      </div>

      {data.pending_selection && data.available_pages?.length > 0 && (
        <div className="rounded-[20px] border border-[#A78BFA]/20 bg-[#A78BFA]/8 p-4" data-testid="mkt-meta-page-selection">
          <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
            <div>
              <h3 className="font-medium">Escolher Página ativa</h3>
              <p className="text-sm text-muted-foreground mt-1">Selecione a Página Facebook certa para concluir a ligação desta empresa.</p>
            </div>
            <span className="text-xs text-muted-foreground" data-testid="mkt-meta-page-count">{data.available_pages.length} opções</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {data.available_pages.map((page, index) => (
              <div key={page.page_id || index} className="rounded-3xl border border-white/10 bg-black/10 p-5" data-testid={`mkt-meta-page-${index}`}>
                <div className="space-y-2 mb-4">
                  <p className="font-medium" data-testid={`mkt-meta-page-name-${index}`}>{page.page_name}</p>
                  <p className="text-xs text-muted-foreground" data-testid={`mkt-meta-page-ig-${index}`}>
                    {page.has_instagram ? `Instagram ligado: @${page.ig_username || "conta profissional"}` : "Sem Instagram profissional ligado"}
                  </p>
                  <p className="text-xs text-muted-foreground" data-testid={`mkt-meta-page-tasks-${index}`}>Tasks: {(page.tasks || []).join(", ") || "sem tasks visíveis"}</p>
                </div>
                <Button
                  data-testid={`mkt-meta-select-page-${index}`}
                  onClick={() => onSelectPage(page.page_id)}
                  disabled={selectingPageId === page.page_id}
                  className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]"
                >
                  {selectingPageId === page.page_id ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link2 className="w-4 h-4 mr-2" />}
                  Escolher esta página
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};