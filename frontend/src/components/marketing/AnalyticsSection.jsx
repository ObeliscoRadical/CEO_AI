import { BarChart3, Lightbulb, TrendingUp } from "lucide-react";

const SummaryCard = ({ label, value, testId }) => (
  <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
  </div>
);

const RankedBar = ({ label, value, suffix = "", width, testId }) => (
  <div data-testid={testId}>
    <div className="flex items-center justify-between gap-3 text-xs mb-1.5">
      <span className="text-foreground">{label}</span>
      <span className="text-muted-foreground">{value}{suffix}</span>
    </div>
    <div className="h-2 rounded-full bg-white/6 overflow-hidden">
      <div className="h-full rounded-full bg-gradient-to-r from-[#3B82F6] to-[#A78BFA]" style={{ width: `${Math.max(width, 12)}%` }} />
    </div>
  </div>
);

export const AnalyticsSection = ({ analytics }) => {
  if (!analytics) return null;
  const summary = analytics.summary || {};
  const bestFormats = analytics.best_formats || [];
  const bestWeekdays = analytics.best_weekdays || [];
  const topPosts = analytics.top_posts || [];

  return (
    <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-analytics-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <h2 className="font-serif-lux text-xl flex items-center gap-2"><BarChart3 className="w-5 h-5 text-[#3B82F6]" /> Social Media Agent · Analytics editoriais</h2>
          <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-analytics-description">{analytics.mocked ? <>Painel de aprendizagem das redes sociais. As métricas estão <strong>MOCKED</strong> até a Meta validar permissões de insights.</> : <>Painel de aprendizagem das redes sociais com sinais reais da Meta sempre que disponíveis.</>}</p>
        </div>
        {analytics.mocked ? <span className="text-[11px] px-3 py-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 text-amber-300" data-testid="mkt-analytics-mocked">Métricas <strong>MOCKED</strong></span> : <span className="text-[11px] px-3 py-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 text-emerald-300" data-testid="mkt-analytics-live">Métricas reais</span>}
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <SummaryCard label="Posts publicados" value={summary.published_posts || 0} testId="mkt-analytics-published" />
        <SummaryCard label="Reach total" value={summary.reach || 0} testId="mkt-analytics-reach" />
        <SummaryCard label="Impressões" value={summary.impressions || 0} testId="mkt-analytics-impressions" />
        <SummaryCard label="Engagement médio" value={`${summary.avg_engagement_rate || 0}%`} testId="mkt-analytics-engagement" />
      </div>

      <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-5 mb-6">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-analytics-breakdown">
          <div className="flex items-center gap-2 mb-4"><TrendingUp className="w-4 h-4 text-[#A78BFA]" /><h3 className="font-medium">Melhores formatos e dias</h3></div>
          <div className="space-y-5">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Formatos</p>
              <div className="space-y-3">
                {bestFormats.length === 0 ? <p className="text-sm text-muted-foreground">Sem histórico suficiente.</p> : bestFormats.slice(0, 4).map((item, index) => (
                  <RankedBar key={`${item.label}-${index}`} label={item.label} value={item.avg_engagement_rate} suffix="%" width={Math.min(item.avg_engagement_rate * 10, 100)} testId={`mkt-best-format-${index}`} />
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Dias</p>
              <div className="space-y-3">
                {bestWeekdays.length === 0 ? <p className="text-sm text-muted-foreground">Sem histórico suficiente.</p> : bestWeekdays.slice(0, 4).map((item, index) => (
                  <RankedBar key={`${item.label}-${index}`} label={item.label} value={item.clicks} suffix=" clicks" width={Math.min((item.clicks / Math.max(bestWeekdays[0]?.clicks || 1, 1)) * 100, 100)} testId={`mkt-best-weekday-${index}`} />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-analytics-learning-loop">
          <div className="flex items-center gap-2 mb-4"><Lightbulb className="w-4 h-4 text-[#F59E0B]" /><h3 className="font-medium">Loop de aprendizagem</h3></div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Insights</p>
              <ul className="space-y-2 text-sm text-foreground">
                {(analytics.insights || []).map((item, index) => <li key={index} data-testid={`mkt-analytics-insight-${index}`}>• {item}</li>)}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Ações recomendadas</p>
              <ul className="space-y-2 text-sm text-foreground">
                {(analytics.recommended_actions || []).map((item, index) => <li key={index} data-testid={`mkt-analytics-action-${index}`}>• {item}</li>)}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid="mkt-top-posts">
        <h3 className="font-medium mb-4">Top conteúdos recentes</h3>
        {topPosts.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ainda não existem publicações para ranking.</p>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {topPosts.map((item, index) => (
              <div key={`${item.post_id || index}-${index}`} className="rounded-2xl border border-white/8 bg-black/10 p-4" data-testid={`mkt-top-post-${index}`}>
                <p className="font-medium line-clamp-2" data-testid={`mkt-top-post-title-${index}`}>{item.title}</p>
                <p className="text-xs text-muted-foreground mt-2" data-testid={`mkt-top-post-meta-${index}`}>{item.format} · {item.theme}</p>
                <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
                  <SummaryCard label="Engagement" value={`${item.engagement_rate}%`} testId={`mkt-top-post-engagement-${index}`} />
                  <SummaryCard label="Clicks" value={item.clicks} testId={`mkt-top-post-clicks-${index}`} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};