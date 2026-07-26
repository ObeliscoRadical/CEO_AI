import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { API, formatApiError } from "@/lib/api";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Users, Crown, TrendingUp, AlertTriangle, Download, Bell, Search, Loader2,
  Building2, CreditCard, XCircle, Power, RefreshCw, FileClock, StickyNote,
  Pencil, Trash2, KeyRound,
} from "lucide-react";

const FILTERS = [
  ["all", "Todos"], ["active", "Ativos"], ["trial", "Em teste"], ["founders", "Fundadoras"],
  ["professional", "Professional"], ["enterprise", "Enterprise"], ["past_due", "Em atraso"], ["cancelled", "Cancelados"],
];
const STATUS_LABEL = { active: "Ativo", trialing: "Em teste", past_due: "Em atraso", canceled: "Cancelado", unpaid: "Não pago", free: "Grátis" };

const fmtDate = (d) => (d ? new Date(d).toLocaleDateString("pt-PT", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—");

export default function Admin() {
  const [tab, setTab] = useState("overview");
  const [ov, setOv] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [positions, setPositions] = useState([]);
  const [notifs, setNotifs] = useState([]);
  const [audit, setAudit] = useState([]);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [noteFor, setNoteFor] = useState(null);
  const [noteText, setNoteText] = useState("");
  const [editFor, setEditFor] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", is_premium: false });
  const [deleteFor, setDeleteFor] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    const [o, c, p, n, a] = await Promise.all([
      api.get("/admin/overview").then((r) => r.data).catch(() => null),
      api.get("/admin/customers", { params: { filter, search } }).then((r) => r.data.customers).catch(() => []),
      api.get("/admin/founders").then((r) => r.data.positions).catch(() => []),
      api.get("/admin/notifications").then((r) => r.data).catch(() => ({ notifications: [], unread: 0 })),
      api.get("/admin/audit").then((r) => r.data.logs).catch(() => []),
    ]);
    setOv(o); setCustomers(c); setPositions(p); setNotifs(n.notifications || []); setAudit(a);
    setLoading(false);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { api.get("/admin/customers", { params: { filter, search } }).then((r) => setCustomers(r.data.customers)).catch(() => {}); }, [filter, search]);

  const toggleCampaign = async () => {
    const next = !ov?.campaign_active;
    await api.post("/admin/campaign/toggle", { active: next });
    toast.success(next ? "Campanha ativada" : "Campanha suspensa");
    load();
  };
  const cancelSub = async (id) => {
    try { await api.post(`/admin/customers/${id}/cancel`); toast.success("Subscrição marcada para cancelar"); load(); }
    catch (e) { toast.error("Não foi possível cancelar"); }
  };
  const resend = async (id) => {
    try { await api.post(`/admin/customers/${id}/resend-notification`); toast.success("Notificação reenviada"); }
    catch (e) { toast.error("Falhou o reenvio"); }
  };
  const resetPwd = async (c) => {
    if (!c.email) return toast.error("Conta sem email associado");
    try { const r = await api.post(`/admin/customers/${c.id}/reset-password`); toast.success(`Email de redefinição enviado para ${r.data.email}`); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const openEdit = (c) => {
    setEditForm({ name: c.name || "", email: c.email || "", is_premium: ["active", "trialing"].includes(c.subscription_status) });
    setEditFor(c.id);
  };
  const saveEdit = async () => {
    setBusy(true);
    try { await api.patch(`/admin/customers/${editFor}`, editForm); toast.success("Conta atualizada"); setEditFor(null); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const doDelete = async () => {
    setBusy(true);
    try { await api.delete(`/admin/customers/${deleteFor.id}`); toast.success("Conta apagada"); setDeleteFor(null); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const saveNote = async () => {
    if (!noteText.trim()) return;
    await api.post(`/admin/customers/${noteFor}/note`, { note: noteText });
    toast.success("Nota adicionada"); setNoteFor(null); setNoteText(""); load();
  };
  const markRead = async () => { await api.post("/admin/notifications/read-all"); load(); };
  const exportCsv = () => { window.open(`${API}/admin/customers/export`, "_blank"); };

  if (loading) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  const unread = notifs.filter((n) => !n.read).length;

  return (
    <div className="px-6 md:px-10 py-10 md:py-14 max-w-[1240px] mx-auto" data-testid="admin-page">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="font-serif-lux text-4xl">Administração</h1>
          <p className="text-muted-foreground text-sm mt-1">Programa Empresas Fundadoras e gestão de clientes.</p>
        </div>
        <button onClick={toggleCampaign} data-testid="toggle-campaign-btn"
          className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-colors ${ov?.campaign_active ? "bg-[#10B981]/15 text-[#10B981] hover:bg-[#10B981]/25" : "bg-[#EF4444]/15 text-[#EF4444] hover:bg-[#EF4444]/25"}`}>
          <Power className="w-4 h-4" /> {ov?.campaign_active ? "Campanha ativa" : "Campanha suspensa"}
        </button>
      </div>

      {/* Founder progress bar */}
      <div className="surface rounded-2xl p-6 mb-6" data-testid="admin-founder-bar">
        <div className="flex items-center justify-between mb-3">
          <span className="flex items-center gap-2 text-sm"><Crown className="w-4 h-4 text-[#3B82F6]" /> Empresas Fundadoras</span>
          <span className="font-medium">{ov?.founders_assigned}/{ov?.founder_limit} · restam {ov?.remaining_slots} vagas históricas</span>
        </div>
        <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-[#3B82F6] to-[#60A5FA]" style={{ width: `${Math.round(((ov?.founders_assigned || 0) / (ov?.founder_limit || 15)) * 100)}%` }} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-border overflow-x-auto">
        {[["overview", "Visão geral"], ["customers", "Clientes"], ["founders", "Fundadoras"], ["notifs", `Notificações${unread ? ` (${unread})` : ""}`], ["audit", "Auditoria"]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} data-testid={`admin-tab-${k}`}
            className={`px-4 py-2.5 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors ${tab === k ? "border-[#3B82F6] text-[#3B82F6]" : "border-transparent text-muted-foreground hover:text-foreground"}`}>{l}</button>
        ))}
      </div>

      {tab === "overview" && ov && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="admin-overview">
          <Metric icon={Building2} label="Empresas registadas" value={ov.total_companies} />
          <Metric icon={CreditCard} label="Subscrições ativas" value={ov.active_subscriptions} />
          <Metric icon={Users} label="Em teste" value={ov.trialing} />
          <Metric icon={Crown} label="Fundadoras ativas" value={ov.founders_active} tone="#3B82F6" />
          <Metric icon={TrendingUp} label="MRR total" value={`${ov.mrr_total} €`} tone="#10B981" />
          <Metric icon={Crown} label="MRR Fundadoras" value={`${ov.mrr_founders} €`} tone="#3B82F6" />
          <Metric icon={TrendingUp} label="MRR outros planos" value={`${ov.mrr_others} €`} />
          <Metric icon={CreditCard} label="Professional" value={ov.professional_count} />
          <Metric icon={Building2} label="Enterprise" value={ov.enterprise_count} />
          <Metric icon={XCircle} label="Cancelamentos (mês)" value={ov.cancellations_month} tone="#EF4444" />
          <Metric icon={AlertTriangle} label="Pagamentos falhados" value={ov.failed_payments} tone="#F59E0B" />
          <Metric icon={Users} label="Novos (7d / 30d)" value={`${ov.new_7d} / ${ov.new_30d}`} />
        </div>
      )}

      {tab === "customers" && (
        <div data-testid="admin-customers">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input data-testid="admin-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Procurar empresa, nome ou email"
                className="w-full pl-9 pr-3 py-2.5 rounded-full bg-transparent border border-border text-sm focus:outline-none focus:border-[#3B82F6]" />
            </div>
            <button onClick={exportCsv} data-testid="export-csv-btn" className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2.5 text-sm hover:bg-accent transition-colors"><Download className="w-4 h-4" /> Exportar CSV</button>
          </div>
          <div className="flex gap-2 mb-4 flex-wrap">
            {FILTERS.map(([k, l]) => (
              <button key={k} onClick={() => setFilter(k)} data-testid={`filter-${k}`}
                className={`px-3 py-1.5 rounded-full text-xs transition-colors ${filter === k ? "bg-[#3B82F6] text-white" : "border border-border text-muted-foreground hover:bg-accent"}`}>{l}</button>
            ))}
          </div>
          <div className="surface rounded-2xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
                <th className="p-3">Empresa</th><th className="p-3">Responsável</th><th className="p-3">Plano</th><th className="p-3">Fundadora</th>
                <th className="p-3">Estado</th><th className="p-3">€/mês</th><th className="p-3">Registo</th><th className="p-3">Ações</th>
              </tr></thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id} className="border-b border-border/50" data-testid={`customer-row-${c.id}`}>
                    <td className="p-3">{c.company || "—"}</td>
                    <td className="p-3">{c.name}<div className="text-xs text-muted-foreground">{c.email}</div></td>
                    <td className="p-3">{c.plan}</td>
                    <td className="p-3">{c.is_founder ? <span className="text-[#3B82F6]">Nº {c.founder_number}{c.founder_price_locked ? "" : " (perdido)"}</span> : "Não"}</td>
                    <td className="p-3"><span className="text-xs px-2 py-0.5 rounded-full bg-white/5">{STATUS_LABEL[c.subscription_status] || c.subscription_status}</span></td>
                    <td className="p-3">{c.monthly || 0} €</td>
                    <td className="p-3 text-muted-foreground">{fmtDate(c.created_at)}</td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <button onClick={() => setNoteFor(c.id)} title="Nota interna" className="text-muted-foreground hover:text-foreground"><StickyNote className="w-4 h-4" /></button>
                        <button onClick={() => openEdit(c)} data-testid={`edit-btn-${c.id}`} title="Editar conta" className="text-muted-foreground hover:text-[#3B82F6]"><Pencil className="w-4 h-4" /></button>
                        <button onClick={() => resetPwd(c)} data-testid={`reset-pwd-btn-${c.id}`} title="Repor senha (envia email ao utilizador)" className="text-muted-foreground hover:text-[#F59E0B]"><KeyRound className="w-4 h-4" /></button>
                        {c.is_founder && <button onClick={() => resend(c.id)} title="Reenviar notificação" className="text-muted-foreground hover:text-[#3B82F6]"><RefreshCw className="w-4 h-4" /></button>}
                        {c.stripe_subscription_id && <button onClick={() => cancelSub(c.id)} title="Cancelar" className="text-muted-foreground hover:text-[#EF4444]"><XCircle className="w-4 h-4" /></button>}
                        <button onClick={() => setDeleteFor(c)} data-testid={`delete-btn-${c.id}`} title="Apagar conta" className="text-muted-foreground hover:text-[#EF4444]"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {customers.length === 0 && <tr><td colSpan={8} className="p-6 text-center text-muted-foreground">Sem clientes para este filtro.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "founders" && (
        <div className="surface rounded-2xl overflow-x-auto" data-testid="admin-founders">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
              <th className="p-3">Posição</th><th className="p-3">Empresa</th><th className="p-3">Responsável</th><th className="p-3">Preço bloqueado</th><th className="p-3">Estado</th><th className="p-3">Ativação</th>
            </tr></thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.founder_number} className="border-b border-border/50">
                  <td className="p-3 text-[#3B82F6] font-medium">Nº {p.founder_number}</td>
                  <td className="p-3">{p.company || "—"}</td>
                  <td className="p-3">{p.name}<div className="text-xs text-muted-foreground">{p.email}</div></td>
                  <td className="p-3">{p.price_locked ? "Sim" : "Não (cancelado)"}</td>
                  <td className="p-3">{STATUS_LABEL[p.status] || p.status || "—"}</td>
                  <td className="p-3 text-muted-foreground">{fmtDate(p.activated_at)}</td>
                </tr>
              ))}
              {positions.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-muted-foreground">Ainda não há Empresas Fundadoras ativadas.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "notifs" && (
        <div data-testid="admin-notifs">
          <div className="flex justify-end mb-3"><button onClick={markRead} className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"><Bell className="w-4 h-4" /> Marcar como lidas</button></div>
          <div className="space-y-2">
            {notifs.map((n) => (
              <div key={n.id} className={`surface rounded-xl p-4 flex items-center gap-3 ${!n.read ? "border border-[#3B82F6]/30" : ""}`}>
                <Crown className="w-4 h-4 text-[#3B82F6] shrink-0" />
                <div className="flex-1 text-sm">
                  {n.type === "founder_activated"
                    ? <span>Nova Empresa Fundadora <b>nº {n.founder_number}</b> — {n.company} ({n.email}). Restam {n.remaining} vagas.</span>
                    : <span>{n.text}</span>}
                  <div className="text-xs text-muted-foreground mt-0.5">{fmtDate(n.created_at)}</div>
                </div>
              </div>
            ))}
            {notifs.length === 0 && <p className="text-center text-muted-foreground py-10">Sem notificações.</p>}
          </div>
        </div>
      )}

      {tab === "audit" && (
        <div className="surface rounded-2xl overflow-x-auto" data-testid="admin-audit">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border"><th className="p-3">Data</th><th className="p-3">Admin</th><th className="p-3">Ação</th><th className="p-3">Alvo</th></tr></thead>
            <tbody>
              {audit.map((l) => (
                <tr key={l.id} className="border-b border-border/50"><td className="p-3 text-muted-foreground">{fmtDate(l.created_at)}</td><td className="p-3">{l.admin}</td><td className="p-3">{l.action}</td><td className="p-3 text-muted-foreground">{l.target || "—"}</td></tr>
              ))}
              {audit.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-muted-foreground"><FileClock className="w-5 h-5 mx-auto mb-2" />Sem registos de auditoria.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* Note modal */}
      {noteFor && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setNoteFor(null)}>
          <div className="surface rounded-2xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-serif-lux text-2xl mb-4">Nota interna</h3>
            <textarea data-testid="note-input" value={noteText} onChange={(e) => setNoteText(e.target.value)} rows={4} className="w-full rounded-xl bg-transparent border border-border p-3 text-sm focus:outline-none focus:border-[#3B82F6]" placeholder="Escreve uma nota..." />
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setNoteFor(null)} className="text-sm text-muted-foreground">Cancelar</button>
              <button onClick={saveNote} data-testid="save-note-btn" className="rounded-full bg-[#3B82F6] text-white px-5 py-2 text-sm font-medium">Guardar</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit account modal */}
      {editFor && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setEditFor(null)}>
          <div className="surface rounded-2xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()} data-testid="edit-modal">
            <h3 className="font-serif-lux text-2xl mb-4">Editar conta</h3>
            <label className="text-sm">Nome</label>
            <input data-testid="edit-name-input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              className="mt-1 mb-3 w-full rounded-lg bg-transparent border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-[#3B82F6]" />
            <label className="text-sm">Email</label>
            <input data-testid="edit-email-input" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              className="mt-1 mb-3 w-full rounded-lg bg-transparent border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-[#3B82F6]" />
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" data-testid="edit-premium-toggle" checked={!!editForm.is_premium} onChange={(e) => setEditForm({ ...editForm, is_premium: e.target.checked })} />
              Acesso Premium manual
            </label>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setEditFor(null)} className="text-sm text-muted-foreground">Cancelar</button>
              <button onClick={saveEdit} disabled={busy} data-testid="save-edit-btn" className="rounded-full bg-[#3B82F6] text-white px-5 py-2 text-sm font-medium disabled:opacity-60">{busy ? "A guardar..." : "Guardar"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm modal */}
      {deleteFor && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setDeleteFor(null)}>
          <div className="surface rounded-2xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()} data-testid="delete-modal">
            <h3 className="font-serif-lux text-2xl mb-2">Apagar conta</h3>
            <p className="text-sm text-muted-foreground mb-5">Tens a certeza que queres apagar <b>{deleteFor.name || deleteFor.email}</b>? Esta ação remove a conta e todos os dados associados e é irreversível.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteFor(null)} className="text-sm text-muted-foreground">Cancelar</button>
              <button onClick={doDelete} disabled={busy} data-testid="confirm-delete-btn" className="rounded-full bg-[#EF4444] text-white px-5 py-2 text-sm font-medium disabled:opacity-60">{busy ? "A apagar..." : "Apagar definitivamente"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ icon: Icon, label, value, tone }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="surface rounded-2xl p-5">
      <Icon className="w-5 h-5 mb-3" style={{ color: tone || "#9ca3af" }} />
      <div className="font-serif-lux text-2xl" style={{ color: tone }}>{value}</div>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </motion.div>
  );
}

