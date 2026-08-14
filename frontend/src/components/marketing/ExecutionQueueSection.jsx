import { Button } from "@/components/ui/button";
import { CalendarClock, CheckCircle2, Clock, RefreshCw, Send, XCircle } from "lucide-react";

const MetricPill = ({ label, value, testId }) => (
  <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-sm font-medium mt-1">{value}</p>
  </div>
);

export const ExecutionQueueSection = ({ execution, onCancelJob, onRescheduleOpen }) => {
  if (!execution) return null;
  const queued = execution.queued || [];
  const history = execution.history || [];
  const summary = execution.summary || { queued: 0, published: 0, failed: 0 };

  return (
    <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-execution-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <h2 className="font-serif-lux text-xl flex items-center gap-2"><CalendarClock className="w-5 h-5 text-[#A78BFA]" /> Social Media Agent · Fila de execução</h2>
          <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-execution-description">Centro operacional de publicação social com fila viva, histórico recente e re-agendamento por post.</p>
        </div>
        <div className="flex gap-2 flex-wrap" data-testid="mkt-execution-summary">
          <MetricPill label="Em fila" value={summary.queued || 0} testId="mkt-queue-summary-queued" />
          <MetricPill label="Publicados" value={summary.published || 0} testId="mkt-queue-summary-published" />
          <MetricPill label="Falhas" value={summary.failed || 0} testId="mkt-queue-summary-failed" />
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-5">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-queue-list">
          <div className="flex items-center gap-2 mb-4"><Clock className="w-4 h-4 text-amber-300" /><h3 className="font-medium">Agendamentos ativos</h3></div>
          {queued.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="mkt-queue-empty">Ainda não há peças em fila.</p>
          ) : (
            <div className="space-y-3">
              {queued.map((job) => (
                <div key={job.id} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-queue-item-${job.id}`}>
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="min-w-0">
                      <p className="font-medium truncate" data-testid={`mkt-queue-title-${job.id}`}>{job.title}</p>
                      <p className="text-xs text-muted-foreground mt-1" data-testid={`mkt-queue-date-${job.id}`}>{new Date(job.run_at).toLocaleString("pt-PT")}</p>
                      <p className="text-xs text-muted-foreground mt-2 line-clamp-2" data-testid={`mkt-queue-caption-${job.id}`}>{job.caption}</p>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <Button data-testid={`mkt-queue-reschedule-${job.id}`} onClick={() => onRescheduleOpen(job)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5">
                        <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                        Reagendar
                      </Button>
                      <Button data-testid={`mkt-queue-cancel-${job.id}`} onClick={() => onCancelJob(job.id)} variant="outline" size="sm" className="rounded-full border-red-400/20 text-red-300 hover:bg-red-500/10">
                        <XCircle className="w-3.5 h-3.5 mr-1.5" />
                        Cancelar
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-history-list">
          <div className="flex items-center gap-2 mb-4"><Send className="w-4 h-4 text-[#3B82F6]" /><h3 className="font-medium">Histórico recente</h3></div>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="mkt-history-empty">Ainda não há histórico de publicação.</p>
          ) : (
            <div className="space-y-3 max-h-[480px] overflow-auto pr-1">
              {history.map((item) => (
                <div key={`${item.kind}-${item.id}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-history-item-${item.id}`}>
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2 min-w-0">
                      {item.kind === "published" ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
                      <p className="font-medium truncate" data-testid={`mkt-history-title-${item.id}`}>{item.title}</p>
                    </div>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground" data-testid={`mkt-history-kind-${item.id}`}>{item.kind === "published" ? "Publicado" : "Falhou"}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2" data-testid={`mkt-history-date-${item.id}`}>{new Date(item.published_at || item.run_at || Date.now()).toLocaleString("pt-PT")}</p>
                  <p className="text-xs text-muted-foreground mt-2 line-clamp-2" data-testid={`mkt-history-caption-${item.id}`}>{item.caption}</p>
                  {item.kind === "published" && item.metrics ? (
                    <div className="grid grid-cols-2 gap-2 mt-3">
                      <MetricPill label="Reach" value={item.metrics.reach} testId={`mkt-history-reach-${item.id}`} />
                      <MetricPill label="CTR" value={`${item.metrics.clicks} clicks`} testId={`mkt-history-clicks-${item.id}`} />
                      <MetricPill label="Engagement" value={`${item.metrics.engagement_rate}%`} testId={`mkt-history-engagement-${item.id}`} />
                      <MetricPill label="Nota" value={item.metrics.top_signal} testId={`mkt-history-signal-${item.id}`} />
                    </div>
                  ) : null}
                  {item.kind === "published" && item.mocked_metrics && (
                    <p className="text-[11px] text-amber-300 mt-3" data-testid={`mkt-history-mocked-${item.id}`}>Métricas <strong>MOCKED</strong> até ligar a Meta.</p>
                  )}
                  {item.kind === "failed" && item.error && (
                    <p className="text-[11px] text-red-300 mt-3" data-testid={`mkt-history-error-${item.id}`}>{item.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};