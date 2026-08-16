import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRightLeft, Clock3, Eye, Filter, RotateCcw } from "lucide-react";

const ACTION_STYLES = {
  create: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
  update: "border-sky-400/20 bg-sky-500/10 text-sky-200",
  delete: "border-rose-400/20 bg-rose-500/10 text-rose-200",
  rollback: "border-amber-400/20 bg-amber-500/10 text-amber-200",
};

const DIFF_STYLES = {
  added: "text-emerald-300 border-emerald-400/15 bg-emerald-500/8",
  removed: "text-rose-300 border-rose-400/15 bg-rose-500/8",
  changed: "text-sky-200 border-sky-400/15 bg-sky-500/8",
};

const tokenizeDiffText = (value) => String(value || "").trim().split(/\s+/).filter(Boolean);

const buildInlineDiff = (beforeValue, afterValue) => {
  const beforeWords = tokenizeDiffText(beforeValue);
  const afterWords = tokenizeDiffText(afterValue);

  if (beforeWords.length === 0 && afterWords.length === 0) {
    return { operations: [], counts: { added: 0, removed: 0, changed: 0 } };
  }

  const matrix = Array.from({ length: beforeWords.length + 1 }, () => Array(afterWords.length + 1).fill(0));
  for (let row = 1; row <= beforeWords.length; row += 1) {
    for (let col = 1; col <= afterWords.length; col += 1) {
      if (beforeWords[row - 1] === afterWords[col - 1]) matrix[row][col] = matrix[row - 1][col - 1] + 1;
      else matrix[row][col] = Math.max(matrix[row - 1][col], matrix[row][col - 1]);
    }
  }

  const operations = [];
  let row = beforeWords.length;
  let col = afterWords.length;

  while (row > 0 && col > 0) {
    if (beforeWords[row - 1] === afterWords[col - 1]) {
      operations.push({ type: "same", text: beforeWords[row - 1] });
      row -= 1;
      col -= 1;
    } else if (matrix[row - 1][col] >= matrix[row][col - 1]) {
      operations.push({ type: "removed", text: beforeWords[row - 1] });
      row -= 1;
    } else {
      operations.push({ type: "added", text: afterWords[col - 1] });
      col -= 1;
    }
  }

  while (row > 0) {
    operations.push({ type: "removed", text: beforeWords[row - 1] });
    row -= 1;
  }
  while (col > 0) {
    operations.push({ type: "added", text: afterWords[col - 1] });
    col -= 1;
  }

  operations.reverse();

  const counts = operations.reduce((acc, operation) => {
    if (operation.type === "added") acc.added += 1;
    if (operation.type === "removed") acc.removed += 1;
    return acc;
  }, { added: 0, removed: 0 });

  return {
    operations,
    counts: {
      ...counts,
      changed: counts.added + counts.removed,
    },
  };
};

const InlineDiffText = ({ operations, side, testId }) => {
  const visibleOperations = operations.filter((operation) => operation.type === "same" || (side === "before" ? operation.type === "removed" : operation.type === "added"));

  return (
    <div className="rounded-[14px] border border-white/8 bg-black/20 p-3 leading-6" data-testid={testId}>
      {visibleOperations.length === 0 ? (
        <span className="text-muted-foreground">—</span>
      ) : visibleOperations.map((operation, index) => {
        const tokenClass = operation.type === "same"
          ? "text-slate-200/92"
          : side === "before"
            ? "text-rose-200 bg-rose-500/18 line-through decoration-rose-300/80 rounded px-1 py-0.5"
            : "text-emerald-100 bg-emerald-500/18 rounded px-1 py-0.5";

        return (
          <span key={`${side}-${operation.text}-${index}`} className={tokenClass} data-testid={`${testId}-token-${index}`}>
            {index > 0 ? " " : ""}
            {operation.text}
          </span>
        );
      })}
    </div>
  );
};

const InlineDiffPanel = ({ diff, testIdPrefix }) => {
  const { operations, counts } = useMemo(() => buildInlineDiff(diff.before, diff.after), [diff.after, diff.before]);

  return (
    <div className="space-y-3" data-testid={`${testIdPrefix}-inline-panel`}>
      <div className="flex items-center gap-2 flex-wrap" data-testid={`${testIdPrefix}-inline-summary`}>
        <span className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Destaque inline
        </span>
        <span className="rounded-full border border-emerald-400/18 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-200" data-testid={`${testIdPrefix}-added-count`}>
          +{counts.added} adições
        </span>
        <span className="rounded-full border border-rose-400/18 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-200" data-testid={`${testIdPrefix}-removed-count`}>
          -{counts.removed} remoções
        </span>
      </div>

      <div className="grid lg:grid-cols-2 gap-3 text-sm" data-testid={`${testIdPrefix}-inline-grid`}>
        <div data-testid={`${testIdPrefix}-inline-before-wrap`}>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-2">Antes · com texto removido</p>
          <InlineDiffText operations={operations} side="before" testId={`${testIdPrefix}-inline-before`} />
        </div>
        <div data-testid={`${testIdPrefix}-inline-after-wrap`}>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-2">Depois · com texto adicionado</p>
          <InlineDiffText operations={operations} side="after" testId={`${testIdPrefix}-inline-after`} />
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value, testId }) => (
  <div className="rounded-[18px] border border-white/10 bg-white/[0.03] p-4" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
    <p className="text-2xl font-semibold mt-2">{value}</p>
  </div>
);

const PreviewCard = ({ title, preview, emptyText, testIdPrefix }) => {
  if (!preview) {
    return (
      <div className="rounded-[18px] border border-dashed border-white/10 bg-black/10 p-4" data-testid={`${testIdPrefix}-empty`}>
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-2">{title}</p>
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      </div>
    );
  }

  return (
    <div className="rounded-[18px] border border-white/10 bg-black/10 p-4" data-testid={`${testIdPrefix}-card`}>
      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">{title}</p>
      <div className="space-y-2 text-sm">
        <p className="font-medium" data-testid={`${testIdPrefix}-title`}>{preview.title}</p>
        {preview.excerpt && <p className="text-muted-foreground" data-testid={`${testIdPrefix}-excerpt`}>{preview.excerpt}</p>}
        {preview.cta && <p className="text-xs text-[#BFDBFE]" data-testid={`${testIdPrefix}-cta`}>CTA · {preview.cta}</p>}
        {preview.seo && <p className="text-xs text-muted-foreground" data-testid={`${testIdPrefix}-seo`}>SEO · {preview.seo}</p>}
        {preview.sections?.length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid={`${testIdPrefix}-sections`}>
            {preview.sections.map((item, index) => (
              <span key={`${item}-${index}`} className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-muted-foreground" data-testid={`${testIdPrefix}-section-${index}`}>
                {item}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export const SiteChangeHistorySection = ({ changeHistory, busy, onRollback }) => {
  const history = changeHistory || { summary: {}, filters: { pages: [], types: [], dates: [] }, items: [] };
  const [pageFilter, setPageFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");

  useEffect(() => {
    if (pageFilter !== "all" && !history.filters?.pages?.some((item) => item.value === pageFilter)) setPageFilter("all");
    if (typeFilter !== "all" && !history.filters?.types?.some((item) => item.value === typeFilter)) setTypeFilter("all");
  }, [history.filters, pageFilter, typeFilter]);

  const filteredItems = useMemo(() => {
    return (history.items || []).filter((item) => {
      if (pageFilter !== "all" && item.page_value !== pageFilter) return false;
      if (typeFilter !== "all" && item.action !== typeFilter) return false;
      if (dateFilter && item.date_key !== dateFilter) return false;
      return true;
    });
  }, [history.items, pageFilter, typeFilter, dateFilter]);

  const clearFilters = () => {
    setPageFilter("all");
    setTypeFilter("all");
    setDateFilter("");
  };

  return (
    <section className="rounded-[22px] border border-white/10 bg-white/[0.03] p-5 md:p-6 mb-5" data-testid="site-changes-section">
      <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Agente · Site</p>
          <h3 className="font-serif-lux text-lg mt-2">Alterações do site</h3>
          <p className="text-sm text-muted-foreground mt-2" data-testid="site-changes-description">
            Timeline visual com before/after, motivo da alteração e atalho para rollback do conteúdo gerido pelo agente.
          </p>
        </div>
        <div className="text-xs text-muted-foreground" data-testid="site-changes-total-note">
          {filteredItems.length} de {(history.items || []).length} alterações visíveis
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-5" data-testid="site-changes-summary-grid">
        <StatCard label="Alterações" value={history.summary?.total || 0} testId="site-changes-stat-total" />
        <StatCard label="Updates" value={history.summary?.update || 0} testId="site-changes-stat-update" />
        <StatCard label="Criações" value={history.summary?.create || 0} testId="site-changes-stat-create" />
        <StatCard label="Rollbacks" value={history.summary?.rollback || 0} testId="site-changes-stat-rollback" />
      </div>

      <div className="grid md:grid-cols-[1.2fr_0.9fr_0.8fr_auto] gap-3 mb-5" data-testid="site-changes-filters">
        <label className="space-y-2" data-testid="site-changes-page-filter-wrap">
          <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Página</span>
          <select value={pageFilter} onChange={(event) => setPageFilter(event.target.value)} className="h-11 rounded-[14px] border border-white/10 bg-black/10 px-3 text-sm" data-testid="site-changes-page-filter">
            <option value="all">Todas</option>
            {(history.filters?.pages || []).map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label className="space-y-2" data-testid="site-changes-type-filter-wrap">
          <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tipo</span>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="h-11 rounded-[14px] border border-white/10 bg-black/10 px-3 text-sm" data-testid="site-changes-type-filter">
            <option value="all">Todos</option>
            {(history.filters?.types || []).map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label className="space-y-2" data-testid="site-changes-date-filter-wrap">
          <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Data</span>
          <Input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} data-testid="site-changes-date-filter" className="h-11 rounded-[14px] border-white/10 bg-black/10" />
        </label>
        <div className="flex items-end">
          <Button variant="outline" onClick={clearFilters} className="rounded-full border-white/15 hover:bg-white/5 h-11 w-full md:w-auto" data-testid="site-changes-clear-filters">
            <Filter className="w-4 h-4 mr-2" /> Limpar
          </Button>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="rounded-[20px] border border-dashed border-white/12 bg-black/10 p-6" data-testid="site-changes-empty">
          <p className="font-medium">Ainda não há alterações visíveis com estes filtros.</p>
          <p className="text-sm text-muted-foreground mt-2">Assim que o agente criar, atualizar, remover ou reverter conteúdos do site, elas vão aparecer aqui com before/after.</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="site-changes-list">
          {filteredItems.map((item, index) => (
            <div key={item.id || index} className="grid xl:grid-cols-[180px_1fr] gap-4" data-testid={`site-change-card-${index}`}>
              <div className="rounded-[18px] border border-white/10 bg-black/10 p-4 h-fit" data-testid={`site-change-meta-${index}`}>
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] text-muted-foreground" data-testid={`site-change-date-${index}`}>
                  <Clock3 className="w-3.5 h-3.5" />
                  {item.created_at ? new Date(item.created_at).toLocaleString("pt-PT") : "Sem data"}
                </div>
                <p className="text-xs text-muted-foreground mt-3" data-testid={`site-change-kind-${index}`}>{item.kind_label}</p>
                <p className="font-medium mt-1" data-testid={`site-change-page-${index}`}>{item.page_label}</p>
                {item.url && <p className="text-xs text-[#93C5FD] mt-2 break-all" data-testid={`site-change-url-${index}`}>{item.url}</p>}
              </div>

              <div className="rounded-[20px] border border-white/10 bg-white/[0.02] p-4 md:p-5" data-testid={`site-change-content-${index}`}>
                <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <span className={`inline-flex rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em] ${ACTION_STYLES[item.action] || ACTION_STYLES.update}`} data-testid={`site-change-action-${index}`}>
                        {item.action_label}
                      </span>
                      {item.diff_summary?.map((label, diffIndex) => (
                        <span key={`${label}-${diffIndex}`} className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-muted-foreground" data-testid={`site-change-highlight-${index}-${diffIndex}`}>
                          {label}
                        </span>
                      ))}
                    </div>
                    <h4 className="font-serif-lux text-xl" data-testid={`site-change-title-${index}`}>{item.title}</h4>
                    <p className="text-sm text-muted-foreground mt-2" data-testid={`site-change-reason-${index}`}>{item.strategy_reason || "Sem motivo registado."}</p>
                  </div>
                  {item.rollback_available && item.rollback_version_id && (
                    <Button
                      onClick={() => onRollback(item.entry_id, item.rollback_version_id)}
                      disabled={busy === `rollback-${item.entry_id}`}
                      variant="outline"
                      className="rounded-full border-white/15 hover:bg-white/5"
                      data-testid={`site-change-rollback-${index}`}
                    >
                      <RotateCcw className="w-4 h-4 mr-2" /> Reverter para antes
                    </Button>
                  )}
                </div>

                <div className="grid lg:grid-cols-2 gap-4 mb-4" data-testid={`site-change-previews-${index}`}>
                  <PreviewCard title="Antes" preview={item.before_preview} emptyText="Esta alteração não tinha uma versão anterior visível." testIdPrefix={`site-change-before-${index}`} />
                  <PreviewCard title="Depois" preview={item.after_preview} emptyText="Sem snapshot final disponível para esta alteração." testIdPrefix={`site-change-after-${index}`} />
                </div>

                <div className="rounded-[18px] border border-white/10 bg-black/10 p-4" data-testid={`site-change-diff-${index}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <ArrowRightLeft className="w-4 h-4 text-[#A78BFA]" />
                    <p className="font-medium">Diff visual</p>
                  </div>
                  {item.diff_items?.length === 0 ? (
                    <p className="text-sm text-muted-foreground" data-testid={`site-change-diff-empty-${index}`}>Sem campos alterados detetados nesta entrada.</p>
                  ) : (
                    <div className="space-y-3" data-testid={`site-change-diff-list-${index}`}>
                      {item.diff_items.map((diff, diffIndex) => (
                        <div key={`${diff.field}-${diffIndex}`} className={`rounded-[16px] border p-3 ${DIFF_STYLES[diff.mode] || DIFF_STYLES.changed}`} data-testid={`site-change-diff-item-${index}-${diffIndex}`}>
                          <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                            <p className="text-xs uppercase tracking-[0.18em]" data-testid={`site-change-diff-label-${index}-${diffIndex}`}>{diff.label}</p>
                            <span className="text-[11px] uppercase tracking-[0.18em]" data-testid={`site-change-diff-mode-${index}-${diffIndex}`}>{diff.mode}</span>
                          </div>
                          <div className="grid lg:grid-cols-2 gap-3 text-sm">
                            <div data-testid={`site-change-diff-before-${index}-${diffIndex}`}>
                              <p className="text-[11px] uppercase tracking-[0.18em] opacity-70 mb-1">Antes</p>
                              <p>{diff.before}</p>
                            </div>
                            <div data-testid={`site-change-diff-after-${index}-${diffIndex}`}>
                              <p className="text-[11px] uppercase tracking-[0.18em] opacity-70 mb-1">Depois</p>
                              <p>{diff.after}</p>
                            </div>
                          </div>

                          <div className="mt-3" data-testid={`site-change-inline-diff-${index}-${diffIndex}`}>
                            <InlineDiffPanel diff={diff} testIdPrefix={`site-change-inline-diff-${index}-${diffIndex}`} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {item.url && (
                  <div className="mt-4">
                    <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-[#93C5FD] hover:underline" data-testid={`site-change-open-url-${index}`}>
                      <Eye className="w-4 h-4" /> Abrir página atual
                    </a>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};