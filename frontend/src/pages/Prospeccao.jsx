import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Target, Search, RefreshCw, Download, Mail, Phone, Globe, MapPin, Building2, Sparkles, Copy, UserPlus, CheckCircle2 } from "lucide-react";

const ICONS = { contratos_mensais: Building2, grandes_obras: Target, reparos: Sparkles };

export default function Prospeccao() {
  const [campaigns, setCampaigns] = useState([]);
  const [configured, setConfigured] = useState(true);
  const [selected, setSelected] = useState(null);
  const [region, setRegion] = useState("");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [msg, setMsg] = useState(null);
  const [msgBusy, setMsgBusy] = useState(false);
  const [crmBusy, setCrmBusy] = useState(false);

  useEffect(() => {
    api.get("/prospecting/campaigns").then(({ data }) => {
      setCampaigns(data.campaigns || []); setConfigured(data.configured);
      if (data.campaigns?.[0]) setSelected(data.campaigns[0].key);
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.get(`/prospecting/list?campaign=${selected}`).then(({ data }) => setRows(data.prospects || [])).catch(() => {});
    setMsg(null);
  }, [selected]);

  const run = async (endpoint, setLoading) => {
    if (!region.trim()) { toast.error("Escreva a região (ex.: Lisboa)."); return; }
    setLoading(true);
    try {
      const { data } = await api.post(endpoint, { campaign: selected, region: region.trim() });
      setRows(data.prospects || []);
      toast.success(endpoint.includes("update") ? `${data.added} nova(s) empresa(s) adicionada(s).` : `${data.added} empresa(s) encontrada(s).`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setLoading(false);
  };

  const exportCsv = () => {
    if (!rows.length) { toast.error("Sem contactos para exportar."); return; }
    const head = ["Nome da Empresa", "Segmento", "E-mail", "Telefone", "Website", "Endereço"];
    const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
    const csv = [head.join(","), ...rows.map((r) => [r.name, r.segment, r.email, r.phone, r.website, r.address].map(esc).join(","))].join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `captacao-${selected}.csv`; a.click();
    URL.revokeObjectURL(url);
    toast.success("Lista exportada (CSV).");
  };

  const genMessage = async () => {
    setMsgBusy(true);
    try { const { data } = await api.post("/prospecting/message", { campaign: selected }); setMsg(data.message); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setMsgBusy(false);
  };

  const sendToCrm = async () => {
    setCrmBusy(true);
    try {
      const { data } = await api.post("/prospecting/to-crm", { campaign: selected });
      toast.success(data.added > 0 ? `${data.added} empresa(s) enviada(s) para o CRM.` : "Nenhuma empresa nova para enviar (já estão no CRM).");
      const { data: l } = await api.get(`/prospecting/list?campaign=${selected}`); setRows(l.prospects || []);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setCrmBusy(false);
  };

  const copyMsg = () => {
    navigator.clipboard.writeText(`${msg?.assunto || ""}\n\n${msg?.corpo || ""}`).then(() => toast.success("Proposta copiada!"));
  };

  if (!loaded) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1200px] mx-auto" data-testid="prospeccao-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Diretor Comercial · Captação</p>
      <h1 className="font-serif-lux text-4xl md:text-5xl text-[#3B82F6] flex items-center gap-3 mb-8"><Target className="w-8 h-8" /> Campanhas de Captação</h1>

      {!configured && (
        <div className="surface rounded-2xl p-4 mb-6 border border-amber-500/30" data-testid="prosp-notconfigured">
          <p className="text-sm text-amber-400">A busca de empresas ainda não está ativa. Assim que colarmos a chave da Google Places API, o robô começa a minerar contactos reais.</p>
        </div>
      )}

      {/* Seletor de campanha */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {campaigns.map((c) => {
          const Icon = ICONS[c.key] || Target;
          const active = selected === c.key;
          return (
            <button key={c.key} data-testid={`prosp-campaign-${c.key}`} onClick={() => setSelected(c.key)}
              className={`text-left surface rounded-3xl p-6 transition-all ${active ? "ring-2 ring-[#3B82F6] bg-[#3B82F6]/5" : "hover:bg-white/[0.03]"}`}>
              <div className={`w-11 h-11 rounded-2xl flex items-center justify-center mb-4 ${active ? "bg-[#3B82F6] text-white" : "bg-[#3B82F6]/15 text-[#3B82F6]"}`}><Icon className="w-5 h-5" /></div>
              <div className="font-medium mb-1">{c.label}</div>
              <p className="text-xs text-muted-foreground mb-3">{c.hint}</p>
              <div className="flex flex-wrap gap-1.5">{c.targets.map((t, i) => <span key={i} className="text-[10px] px-2 py-0.5 rounded-full border border-white/10 text-muted-foreground capitalize">{t}</span>)}</div>
            </button>
          );
        })}
      </div>

      {/* Região + ações */}
      <div className="surface rounded-3xl p-5 md:p-6 mb-8 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[220px]">
          <label className="text-xs text-muted-foreground">Região de busca</label>
          <Input data-testid="prosp-region" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Ex.: Lisboa, Porto, Setúbal…" className="mt-1" />
        </div>
        <Button data-testid="prosp-search-btn" onClick={() => run("/prospecting/search", setBusy)} disabled={busy || updating} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] h-10">
          {busy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />} Procurar empresas
        </Button>
        <Button data-testid="prosp-update-btn" onClick={() => run("/prospecting/update", setUpdating)} disabled={busy || updating} variant="outline" className="rounded-full border-white/15 hover:bg-white/5 h-10">
          {updating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />} Atualizar Clientes
        </Button>
        <Button data-testid="prosp-message-btn" onClick={genMessage} disabled={msgBusy} variant="outline" className="rounded-full border-white/15 hover:bg-white/5 h-10">
          {msgBusy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />} Gerar proposta (IA)
        </Button>
        <Button data-testid="prosp-tocrm-btn" onClick={sendToCrm} disabled={crmBusy} variant="outline" className="rounded-full border-[#3B82F6]/40 text-[#3B82F6] hover:bg-[#3B82F6]/10 h-10">
          {crmBusy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UserPlus className="w-4 h-4 mr-2" />} Enviar ao CRM
        </Button>
        <Button data-testid="prosp-export-btn" onClick={exportCsv} variant="outline" className="rounded-full border-white/15 hover:bg-white/5 h-10"><Download className="w-4 h-4 mr-2" /> Exportar CSV</Button>
      </div>

      {/* Resultados */}
      {rows.length > 0 ? (
        <div className="surface rounded-3xl overflow-hidden" data-testid="prosp-results">
          <div className="px-5 py-3 border-b border-white/[0.06] text-sm text-muted-foreground">{rows.length} empresa(s) na lista</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-muted-foreground border-b border-white/[0.06]">
                <th className="px-5 py-3">Empresa</th><th className="px-3 py-3">Segmento</th><th className="px-3 py-3">E-mail</th><th className="px-3 py-3">Telefone</th><th className="px-3 py-3">Endereço</th>
              </tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={r.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]" data-testid={`prosp-row-${i}`}>
                    <td className="px-5 py-3 font-medium">{r.name || "—"}{r.website && <a href={r.website} target="_blank" rel="noreferrer" className="ml-2 inline-flex text-[#3B82F6]"><Globe className="w-3.5 h-3.5" /></a>}{r.sent_to_crm && <span className="ml-2 inline-flex items-center gap-1 text-[10px] text-[#10B981]" data-testid={`prosp-incrm-${i}`}><CheckCircle2 className="w-3 h-3" />no CRM</span>}</td>
                    <td className="px-3 py-3 text-muted-foreground capitalize">{r.segment || "—"}</td>
                    <td className="px-3 py-3">{r.email ? <a href={`mailto:${r.email}`} className="text-[#3B82F6] flex items-center gap-1"><Mail className="w-3 h-3" />{r.email}</a> : <span className="text-muted-foreground">—</span>}</td>
                    <td className="px-3 py-3">{r.phone ? <span className="flex items-center gap-1"><Phone className="w-3 h-3 text-muted-foreground" />{r.phone}</span> : <span className="text-muted-foreground">—</span>}</td>
                    <td className="px-3 py-3 text-muted-foreground text-xs max-w-[240px]"><span className="flex items-start gap-1"><MapPin className="w-3 h-3 mt-0.5 shrink-0" />{r.address || "—"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="surface rounded-3xl p-10 text-center text-muted-foreground" data-testid="prosp-empty">
          Escolha uma campanha, escreva a região e clique <b className="text-foreground">Procurar empresas</b> para o robô minerar contactos reais.
        </div>
      )}

      {/* Proposta IA */}
      <Dialog open={!!msg} onOpenChange={(o) => !o && setMsg(null)}>
        <DialogContent data-testid="prosp-message-dialog">
          <DialogHeader>
            <DialogTitle>{msg?.assunto || "Proposta comercial"}</DialogTitle>
            <DialogDescription>Proposta gerada para o segmento desta campanha. Reveja e ajuste antes de enviar.</DialogDescription>
          </DialogHeader>
          <div className="whitespace-pre-wrap text-sm text-muted-foreground max-h-[50vh] overflow-y-auto py-2">{msg?.corpo}</div>
          <Button data-testid="prosp-message-copy" onClick={copyMsg} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]"><Copy className="w-4 h-4 mr-2" /> Copiar proposta</Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
