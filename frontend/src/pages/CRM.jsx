import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  Loader2, Briefcase, Sparkles, Plus, Trash2, Mail, FileText, Copy, Target, X, Send,
} from "lucide-react";

const STAGE_LABEL = {
  novo: "Novo", qualificado: "Qualificado", reuniao: "Reunião",
  proposta: "Proposta", negociacao: "Negociação", ganho: "Ganho", perdido: "Perdido",
};
const SIZES = ["micro", "pequena", "media", "grande"];
const URG = ["baixa", "media", "alta"];
const scoreColor = (s) => (s >= 70 ? "#10B981" : s >= 45 ? "#F59E0B" : "#94A3B8");
const scoreLabel = (s) => (s >= 70 ? "quente" : s >= 45 ? "morno" : "frio");
const emptyLead = { name: "", contact: "", sector: "", size: "", region: "", value: "", urgency: "", stage: "novo", notes: "", source: "" };

export default function CRM() {
  const [icp, setIcp] = useState(null);
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const [savingIcp, setSavingIcp] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [sym, setSym] = useState("€");
  const [leadForm, setLeadForm] = useState(null);   // objeto lead a editar/criar
  const [savingLead, setSavingLead] = useState(false);
  const [draft, setDraft] = useState(null);          // {kind, ...}
  const [draftLoading, setDraftLoading] = useState(false);

  const loadLeads = () => api.get("/crm/leads").then(({ data }) => setData(data)).catch(() => setFailed(true));
  const loadIcp = () => api.get("/crm/icp").then(({ data }) => setIcp(data.icp || {})).catch(() => {});

  useEffect(() => {
    loadIcp(); loadLeads();
    api.get("/goal").then(({ data }) => setSym(data.currency_symbol || "€")).catch(() => {});
  }, []);

  const fmt = (n) => `${sym}${Number(n || 0).toLocaleString(sym === "R$" ? "pt-BR" : "pt-PT", { maximumFractionDigits: 0 })}`;

  const saveIcp = async () => {
    setSavingIcp(true);
    try { await api.post("/crm/icp", { ...icp, ticket_ideal: icp.ticket_ideal ? Number(icp.ticket_ideal) : null }); toast.success("Cliente ideal guardado."); }
    catch { toast.error("Não foi possível guardar."); }
    setSavingIcp(false);
  };
  const suggestIcp = async () => {
    setSuggesting(true);
    try { const { data } = await api.post("/crm/icp/suggest"); setIcp({ ...(icp || {}), ...data.icp }); toast.success("Sugestão do Diretor Comercial pronta — reveja e guarde."); }
    catch { toast.error("Não foi possível sugerir agora."); }
    setSuggesting(false);
  };

  const saveLead = async () => {
    if (!leadForm.name?.trim()) { toast.error("Indique o nome do lead."); return; }
    setSavingLead(true);
    try {
      const payload = { ...leadForm, value: leadForm.value ? Number(leadForm.value) : null };
      await api.post("/crm/leads", payload);
      setLeadForm(null); await loadLeads();
      toast.success("Lead guardado.");
    } catch { toast.error("Não foi possível guardar o lead."); }
    setSavingLead(false);
  };
  const moveStage = async (id, stage) => {
    try { await api.post(`/crm/leads/${id}/stage`, { stage }); await loadLeads(); }
    catch { toast.error("Não foi possível mover."); }
  };
  const removeLead = async (id) => {
    try { await api.delete(`/crm/leads/${id}`); await loadLeads(); toast.success("Lead removido."); }
    catch { toast.error("Não foi possível remover."); }
  };
  const genDraft = async (lead, kind) => {
    setDraft({ kind, lead, loading: true }); setDraftLoading(true);
    try { const { data } = await api.post(`/crm/leads/${lead.id}/draft`, { kind }); setDraft({ kind, lead, ...data.draft }); }
    catch { toast.error("Não foi possível gerar o rascunho."); setDraft(null); }
    setDraftLoading(false);
  };
  const copyDraft = () => {
    const txt = draft.kind === "email" ? `${draft.assunto || ""}\n\n${draft.corpo || ""}` : `${draft.titulo || ""}\n\n${draft.corpo || ""}`;
    navigator.clipboard.writeText(txt).then(() => toast.success("Copiado!")).catch(() => {});
  };
  const sendSim = async (channel) => {
    const message = `${draft.assunto || draft.titulo || ""}\n\n${draft.corpo || ""}`.trim();
    try {
      const { data } = await api.post(`/crm/leads/${draft.lead.id}/send-sim`, { channel, message, subject: draft.assunto || draft.titulo });
      if (channel === "whatsapp" && data.wa_link) { window.open(data.wa_link, "_blank"); toast.success("WhatsApp aberto com a mensagem."); }
      else if (data.ok) toast.success(`Enviado para o seu email (${data.sent_to}).`);
      else toast.error("Não foi possível enviar.");
    } catch { toast.error("Não foi possível enviar."); }
  };

  if (failed) return <div className="text-center py-40 text-muted-foreground" data-testid="crm-error">Não foi possível carregar. Atualiza a página.</div>;
  if (!data || icp === null) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  const stages = data.stages || [];

  return (
    <div className="px-6 md:px-12 py-14 md:py-20 max-w-[1400px] mx-auto" data-testid="crm-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Conselho Executivo · Diretor Comercial</p>
      <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <h1 className="font-serif-lux text-4xl md:text-5xl text-[#3B82F6] flex items-center gap-3"><Briefcase className="w-8 h-8" /> CRM Comercial</h1>
        <div className="text-sm text-muted-foreground">Pipeline: <span className="text-foreground font-medium">{fmt(data.pipeline_value)}</span></div>
      </div>

      {/* Cliente ideal (ICP) */}
      <div className="surface rounded-3xl p-6 md:p-8 mb-10" data-testid="icp-card">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
          <h2 className="font-serif-lux text-2xl flex items-center gap-2"><Target className="w-5 h-5 text-[#3B82F6]" /> Cliente Ideal (ICP)</h2>
          <Button data-testid="icp-suggest-btn" onClick={suggestIcp} disabled={suggesting} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
            {suggesting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />} Sugerir com IA
          </Button>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          <div><Label className="text-xs text-muted-foreground">Setor-alvo</Label><Input data-testid="icp-sector" value={icp.sector || ""} onChange={(e) => setIcp({ ...icp, sector: e.target.value })} className="mt-1 bg-transparent" /></div>
          <div><Label className="text-xs text-muted-foreground">Dimensão</Label>
            <Select value={icp.size || ""} onValueChange={(v) => setIcp({ ...icp, size: v })}>
              <SelectTrigger data-testid="icp-size" className="mt-1 bg-transparent"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>{SIZES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label className="text-xs text-muted-foreground">Região</Label><Input data-testid="icp-region" value={icp.region || ""} onChange={(e) => setIcp({ ...icp, region: e.target.value })} className="mt-1 bg-transparent" /></div>
          <div><Label className="text-xs text-muted-foreground">Decisor</Label><Input value={icp.decisor || ""} onChange={(e) => setIcp({ ...icp, decisor: e.target.value })} className="mt-1 bg-transparent" placeholder="ex: gerente, CEO" /></div>
          <div><Label className="text-xs text-muted-foreground">Ticket ideal ({sym})</Label><Input type="number" value={icp.ticket_ideal || ""} onChange={(e) => setIcp({ ...icp, ticket_ideal: e.target.value })} className="mt-1 bg-transparent" /></div>
          <div><Label className="text-xs text-muted-foreground">Urgência típica</Label>
            <Select value={icp.urgencia || ""} onValueChange={(v) => setIcp({ ...icp, urgencia: v })}>
              <SelectTrigger className="mt-1 bg-transparent"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>{URG.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select></div>
          <div className="md:col-span-3"><Label className="text-xs text-muted-foreground">Dor principal que resolvemos</Label><Input value={icp.dor || ""} onChange={(e) => setIcp({ ...icp, dor: e.target.value })} className="mt-1 bg-transparent" /></div>
          <div className="md:col-span-3"><Label className="text-xs text-muted-foreground">Notas (onde encontrar / como abordar)</Label><Textarea value={icp.notas || ""} onChange={(e) => setIcp({ ...icp, notas: e.target.value })} className="mt-1 bg-transparent" rows={2} /></div>
        </div>
        <Button data-testid="icp-save-btn" onClick={saveIcp} disabled={savingIcp} className="mt-5 rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
          {savingIcp ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Guardar cliente ideal
        </Button>
      </div>

      {/* Pipeline */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif-lux text-2xl">Pipeline de oportunidades</h2>
        <Button data-testid="add-lead-btn" onClick={() => setLeadForm({ ...emptyLead })} className="rounded-full bg-[#10B981] text-white hover:bg-[#059669]"><Plus className="w-4 h-4 mr-1.5" /> Novo lead</Button>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4" data-testid="pipeline-board">
        {stages.map((st) => {
          const items = (data.leads || []).filter((l) => (l.stage || "novo") === st);
          return (
            <div key={st} className="min-w-[260px] w-[260px] shrink-0" data-testid={`column-${st}`}>
              <div className="flex items-center justify-between mb-3 px-1">
                <span className="text-sm font-medium">{STAGE_LABEL[st]}</span>
                <span className="text-xs text-muted-foreground">{items.length}</span>
              </div>
              <div className="space-y-3">
                {items.map((l) => (
                  <div key={l.id} className="surface rounded-2xl p-4" data-testid={`lead-${l.id}`}>
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <button onClick={() => setLeadForm({ ...emptyLead, ...l, value: l.value ?? "" })} className="font-medium text-left hover:text-[#3B82F6]" data-testid={`lead-name-${l.id}`}>{l.name}</button>
                      <span className="text-[10px] px-2 py-0.5 rounded-full shrink-0" style={{ color: scoreColor(l.score), background: `${scoreColor(l.score)}18` }} data-testid={`lead-score-${l.id}`}>{l.score} · {scoreLabel(l.score)}</span>
                    </div>
                    {(l.sector || l.value) && <div className="text-xs text-muted-foreground mb-3">{l.sector || ""}{l.value ? ` · ${fmt(l.value)}` : ""}</div>}
                    <div className="flex items-center gap-2 mb-2">
                      <Select value={l.stage} onValueChange={(v) => moveStage(l.id, v)}>
                        <SelectTrigger className="h-8 text-xs bg-transparent flex-1" data-testid={`lead-stage-${l.id}`}><SelectValue /></SelectTrigger>
                        <SelectContent>{stages.map((s) => <SelectItem key={s} value={s}>{STAGE_LABEL[s]}</SelectItem>)}</SelectContent>
                      </Select>
                      <button onClick={() => removeLead(l.id)} className="text-muted-foreground hover:text-red-400" data-testid={`lead-delete-${l.id}`}><Trash2 className="w-4 h-4" /></button>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => genDraft(l, "email")} className="flex-1 text-[11px] flex items-center justify-center gap-1 py-1.5 rounded-lg border border-white/10 hover:bg-white/5" data-testid={`draft-email-${l.id}`}><Mail className="w-3.5 h-3.5" /> Email</button>
                      <button onClick={() => genDraft(l, "proposal")} className="flex-1 text-[11px] flex items-center justify-center gap-1 py-1.5 rounded-lg border border-white/10 hover:bg-white/5" data-testid={`draft-proposal-${l.id}`}><FileText className="w-3.5 h-3.5" /> Proposta</button>
                    </div>
                  </div>
                ))}
                {items.length === 0 && <div className="text-xs text-muted-foreground/60 px-1 py-4 text-center border border-dashed border-white/[0.06] rounded-2xl">vazio</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Dialog: criar/editar lead */}
      <Dialog open={!!leadForm} onOpenChange={(o) => !o && setLeadForm(null)}>
        <DialogContent className="max-w-lg" data-testid="lead-dialog">
          <DialogHeader><DialogTitle>{leadForm?.id ? "Editar lead" : "Novo lead"}</DialogTitle></DialogHeader>
          {leadForm && (
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2"><Label className="text-xs text-muted-foreground">Nome *</Label><Input data-testid="lead-input-name" value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })} className="mt-1" /></div>
              <div className="col-span-2"><Label className="text-xs text-muted-foreground">Contacto (email/telefone)</Label><Input value={leadForm.contact} onChange={(e) => setLeadForm({ ...leadForm, contact: e.target.value })} className="mt-1" /></div>
              <div><Label className="text-xs text-muted-foreground">Setor</Label><Input value={leadForm.sector} onChange={(e) => setLeadForm({ ...leadForm, sector: e.target.value })} className="mt-1" /></div>
              <div><Label className="text-xs text-muted-foreground">Dimensão</Label>
                <Select value={leadForm.size || ""} onValueChange={(v) => setLeadForm({ ...leadForm, size: v })}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="—" /></SelectTrigger>
                  <SelectContent>{SIZES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select></div>
              <div><Label className="text-xs text-muted-foreground">Valor potencial ({sym})</Label><Input data-testid="lead-input-value" type="number" value={leadForm.value} onChange={(e) => setLeadForm({ ...leadForm, value: e.target.value })} className="mt-1" /></div>
              <div><Label className="text-xs text-muted-foreground">Urgência</Label>
                <Select value={leadForm.urgency || ""} onValueChange={(v) => setLeadForm({ ...leadForm, urgency: v })}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="—" /></SelectTrigger>
                  <SelectContent>{URG.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select></div>
              <div className="col-span-2"><Label className="text-xs text-muted-foreground">Notas</Label><Textarea value={leadForm.notes} onChange={(e) => setLeadForm({ ...leadForm, notes: e.target.value })} className="mt-1" rows={2} /></div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setLeadForm(null)} className="rounded-full">Cancelar</Button>
            <Button data-testid="lead-save-btn" onClick={saveLead} disabled={savingLead} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">{savingLead ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: rascunho IA */}
      <Dialog open={!!draft} onOpenChange={(o) => !o && setDraft(null)}>
        <DialogContent className="max-w-lg" data-testid="draft-dialog">
          <DialogHeader><DialogTitle>{draft?.kind === "email" ? "Rascunho de email" : "Rascunho de proposta"} · {draft?.lead?.name}</DialogTitle></DialogHeader>
          {draftLoading ? (
            <div className="py-12 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>
          ) : draft && (
            <div className="space-y-3">
              <div className="text-sm font-medium text-[#3B82F6]">{draft.assunto || draft.titulo}</div>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap max-h-[46vh] overflow-y-auto" data-testid="draft-body">{draft.corpo}</div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDraft(null)} className="rounded-full">Fechar</Button>
            {!draftLoading && draft && (
              <>
                <Button data-testid="draft-copy-btn" onClick={copyDraft} variant="outline" className="rounded-full border-white/15"><Copy className="w-4 h-4 mr-1.5" /> Copiar</Button>
                <Button data-testid="draft-wa-btn" onClick={() => sendSim("whatsapp")} variant="outline" className="rounded-full border-[#25D366]/40 text-[#25D366] hover:bg-[#25D366]/10"><Send className="w-4 h-4 mr-1.5" /> WhatsApp</Button>
                <Button data-testid="draft-email-self-btn" onClick={() => sendSim("email")} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]"><Mail className="w-4 h-4 mr-1.5" /> Para o meu email</Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
