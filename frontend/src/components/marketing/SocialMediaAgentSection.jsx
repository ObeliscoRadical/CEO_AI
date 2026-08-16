import { Button } from "@/components/ui/button";
import { Bot, CalendarRange, ImageIcon, Loader2, RefreshCw, Send, ShieldCheck } from "lucide-react";

const StatCard = ({ label, value, helper, testId }) => (
  <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
    {helper && <p className="text-xs text-muted-foreground mt-2">{helper}</p>}
  </div>
);

const BulletColumn = ({ title, items = [], testIdPrefix }) => (
  <div>
    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">{title}</p>
    <ul className="space-y-2 text-sm text-foreground">
      {items.map((item, index) => <li key={`${item}-${index}`} data-testid={`${testIdPrefix}-${index}`}>• {item}</li>)}
    </ul>
  </div>
);

export const SocialMediaAgentSection = ({ data, busy, onRun, onRefresh }) => {
  const summary = data?.summary || {};
  const status = data?.status || {};

  return (
    <section className="surface rounded-[22px] p-5 md:p-6 mb-5" data-testid="social-media-agent-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Agente · Redes Sociais</p>
          <h2 className="font-serif-lux text-lg flex items-center gap-2 mt-2"><Bot className="w-5 h-5 text-[#A78BFA]" /> Automação</h2>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl" data-testid="social-media-agent-description">Coordena calendário, imagens, filas de publicação e analytics sociais.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={onRefresh} disabled={busy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5" data-testid="social-media-agent-refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Atualizar
          </Button>
          <Button onClick={onRun} disabled={busy} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]" data-testid="social-media-agent-run-btn">
            {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />} Executar Social Agent
          </Button>
        </div>
      </div>

      <div className="rounded-[20px] border border-[#A78BFA]/20 bg-[#A78BFA]/8 p-4 mb-5" data-testid="social-media-agent-boundary-card">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-[#A78BFA] mt-0.5" />
          <div className="grid md:grid-cols-2 gap-5 w-full">
            <BulletColumn title="Este agente faz" items={data?.boundary?.owns || []} testIdPrefix="social-media-agent-owns" />
            <BulletColumn title="Este agente nunca faz" items={data?.boundary?.never || []} testIdPrefix="social-media-agent-never" />
          </div>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-5" data-testid="social-media-agent-stats-grid">
        <StatCard label="Prontos a agendar" value={summary.approved_ready || 0} helper="Posts aprovados e livres" testId="social-media-agent-stat-ready" />
        <StatCard label="Em fila" value={summary.queued || 0} helper="Agendamentos ativos" testId="social-media-agent-stat-queued" />
        <StatCard label="Fila autónoma" value={summary.autonomous_queue || 0} helper="Criada pelo agente" testId="social-media-agent-stat-autonomous" />
        <StatCard label="Publicados" value={summary.published || 0} helper={summary.metrics_mocked ? "Analytics sociais MOCKED" : "Analytics reais"} testId="social-media-agent-stat-published" />
      </div>

      <div className="grid xl:grid-cols-[0.95fr_1.05fr] gap-4">
        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="social-media-agent-status-card">
          <div className="flex items-center gap-2 mb-4"><CalendarRange className="w-4 h-4 text-[#3B82F6]" /><h3 className="font-medium">Estado operacional</h3></div>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p data-testid="social-media-agent-connected"><span className="text-foreground">Ligação:</span> {status.connected ? "pronta" : status.connection_state === "pending_selection" ? "à espera de escolha da página" : "ainda não ligada"}</p>
            <p data-testid="social-media-agent-page"><span className="text-foreground">Página:</span> {status.page_name || "—"}</p>
            <p data-testid="social-media-agent-instagram"><span className="text-foreground">Instagram:</span> {status.ig_username ? `@${status.ig_username}` : "—"}</p>
            <p data-testid="social-media-agent-last-activity"><span className="text-foreground">Última atividade:</span> {status.last_activity_at ? new Date(status.last_activity_at).toLocaleString("pt-PT") : "Sem atividade ainda"}</p>
          </div>
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4" data-testid="social-media-agent-blockers-card">
          <div className="flex items-center gap-2 mb-4"><ImageIcon className="w-4 h-4 text-[#F59E0B]" /><h3 className="font-medium">Bloqueios e próximos passos</h3></div>
          {(data?.blockers || []).length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="social-media-agent-blockers-empty">Sem bloqueios. O agente pode continuar a agendar e publicar peças aprovadas.</p>
          ) : (
            <ul className="space-y-2 text-sm text-foreground">
              {data.blockers.map((item, index) => <li key={`${item}-${index}`} data-testid={`social-media-agent-blocker-${index}`}>• {item}</li>)}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
};