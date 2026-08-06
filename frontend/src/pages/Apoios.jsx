import { useEffect, useRef, useState } from "react";
import { api, API, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Loader2, Landmark, Sparkles, ExternalLink, ShieldCheck, ShieldAlert, CheckCircle2,
  AlertTriangle, FileText, Building2, Target, ListChecks, Trash2, Info, ClipboardList, Clock, Paperclip, Download, Upload,
} from "lucide-react";

const INTERESTS = [
  { key: "fundo", label: "Incentivos / Fundos" },
  { key: "fiscal", label: "Incentivos Fiscais" },
  { key: "financiamento", label: "Financiamento" },
  { key: "emprego", label: "Apoio ao Emprego" },
  { key: "inovacao", label: "Inovação / Capacitação" },
  { key: "europeu", label: "Fundos Europeus" },
];

const ELIG_STYLE = {
  elegivel: { bg: "rgba(16,185,129,0.14)", color: "#10B981", Icon: ShieldCheck },
  possivel: { bg: "rgba(59,130,246,0.14)", color: "#3B82F6", Icon: ShieldCheck },
  confirmar: { bg: "rgba(245,158,11,0.14)", color: "#F59E0B", Icon: ShieldAlert },
};

function deadlineLabel(dl) {
  if (dl === "continuo") return "Candidaturas em contínuo";
  if (dl === "consultar_aviso") return "Depende de aviso oficial";
  return `Prazo: ${dl}`;
}

function OpportunityCard({ o, analysis, onTrack, tracking }) {
  const [open, setOpen] = useState(false);
  const st = ELIG_STYLE[o.eligibility] || ELIG_STYLE.confirmar;
  const ai = analysis?.oportunidades?.find((x) => x.id === o.id);
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="surface rounded-3xl p-6" data-testid={`apoios-opp-${o.id}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300">{o.type_label}</span>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-semibold"
              style={{ background: st.bg, color: st.color }} data-testid={`apoios-elig-${o.id}`}>
              <st.Icon className="w-3 h-3 inline mr-1 -mt-0.5" />{o.eligibility_label}
            </span>
          </div>
          <h3 className="font-serif-lux text-lg leading-tight">{o.title}</h3>
          <div className="text-xs text-muted-foreground mt-0.5">{o.entity}</div>
        </div>
      </div>

      <p className="text-sm text-muted-foreground mb-3">{o.summary}</p>

      <div className="grid sm:grid-cols-2 gap-2 mb-3">
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Montante / Taxa</div>
          <div className="text-sm mt-0.5">{o.amount}</div>
        </div>
        <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Prazo</div>
          <div className="text-sm mt-0.5 flex items-center gap-1.5"><Clock className="w-3.5 h-3.5 text-slate-400" />{deadlineLabel(o.deadline)}</div>
        </div>
      </div>

      {o.match_reasons?.length > 0 && (
        <ul className="space-y-1 mb-2">
          {o.match_reasons.map((r, i) => (
            <li key={i} className="text-xs flex gap-2 text-emerald-300/90"><CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>{r}</span></li>
          ))}
        </ul>
      )}
      {o.warnings?.length > 0 && (
        <ul className="space-y-1 mb-2">
          {o.warnings.map((r, i) => (
            <li key={i} className="text-xs flex gap-2 text-amber-300/90"><AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>{r}</span></li>
          ))}
        </ul>
      )}

      <button onClick={() => setOpen((v) => !v)} className="text-xs text-blue-400 hover:text-blue-300 mt-1" data-testid={`apoios-details-${o.id}`}>
        {open ? "Ocultar detalhes" : "Ver documentos e passos"}
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">Despesas elegíveis</div>
            <p className="text-sm text-slate-300">{o.expenses}</p>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">Documentos normalmente exigidos</div>
            <ul className="space-y-1">
              {o.documents.map((d, i) => (
                <li key={i} className="text-sm flex gap-2 text-slate-300"><FileText className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-500" />{d}</li>
              ))}
            </ul>
          </div>
          {ai && (
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/[0.06] p-3.5">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-blue-300 mb-2"><Sparkles className="w-3.5 h-3.5" /> Análise do Diretor de Apoios</div>
              <p className="text-sm text-slate-200 mb-2">{ai.porque_encaixa}</p>
              {ai.passos?.length > 0 && (
                <ol className="space-y-1 mb-2 list-decimal list-inside">
                  {ai.passos.map((p, i) => <li key={i} className="text-sm text-slate-300">{p}</li>)}
                </ol>
              )}
              {ai.onde_tratar && <div className="text-xs text-slate-400">Onde tratar: {ai.onde_tratar}</div>}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/[0.06] flex-wrap">
        <a href={o.url} target="_blank" rel="noreferrer" data-testid={`apoios-link-${o.id}`}
          className="text-xs inline-flex items-center gap-1.5 px-3 py-2 rounded-full border border-white/10 text-slate-300 hover:text-white hover:border-white/20 transition-colors">
          <ExternalLink className="w-3.5 h-3.5" /> Site oficial
        </a>
        {o.tracked ? (
          <span className="text-xs inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-emerald-500/10 text-emerald-400" data-testid={`apoios-tracked-${o.id}`}>
            <CheckCircle2 className="w-3.5 h-3.5" /> A acompanhar
          </span>
        ) : (
          <Button size="sm" data-testid={`apoios-track-${o.id}`} onClick={() => onTrack(o.id)} disabled={tracking === o.id}
            className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] text-xs h-9">
            {tracking === o.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <><ClipboardList className="w-3.5 h-3.5 mr-1.5" /> Acompanhar candidatura</>}
          </Button>
        )}
        <span className="text-[10px] text-slate-500 ml-auto">Fonte verificada a {o.verified_at}</span>
      </div>
    </motion.div>
  );
}

function fmtBytes(n) {
  if (!n) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function ApplicationCard({ a, statuses, onUpdate, onToggle, onDelete, onUpload, onDeleteFile }) {
  const [notes, setNotes] = useState(a.notes || "");
  const [uploadBusy, setUploadBusy] = useState(false);
  const fileRef = useRef(null);
  const done = (arr) => (arr || []).filter((x) => x.done).length;
  const total = (a.checklist?.length || 0) + (a.steps?.length || 0);
  const completed = done(a.checklist) + done(a.steps);
  const files = a.files || [];
  const pick = () => fileRef.current?.click();
  const onFile = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setUploadBusy(true);
    await onUpload(a.id, f);
    setUploadBusy(false);
  };
  return (
    <div className="surface rounded-3xl p-6" data-testid={`apoios-app-${a.id}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300">{a.type_label}</span>
          <h3 className="font-serif-lux text-lg leading-tight mt-1.5">{a.title}</h3>
          <div className="text-xs text-muted-foreground">{a.entity}</div>
        </div>
        <button onClick={() => onDelete(a.id)} data-testid={`apoios-app-delete-${a.id}`}
          className="text-slate-500 hover:text-red-400 shrink-0"><Trash2 className="w-4 h-4" /></button>
      </div>

      <div className="grid sm:grid-cols-2 gap-3 mb-4">
        <div>
          <Label className="text-[11px] text-muted-foreground">Estado</Label>
          <Select value={a.status} onValueChange={(v) => onUpdate(a.id, { status: v })}>
            <SelectTrigger data-testid={`apoios-app-status-${a.id}`} className="mt-1 bg-transparent h-9"><SelectValue /></SelectTrigger>
            <SelectContent>{statuses.map((s) => <SelectItem key={s.code} value={s.code}>{s.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-[11px] text-muted-foreground">Prazo de submissão</Label>
          <Input type="date" data-testid={`apoios-app-deadline-${a.id}`} defaultValue={a.deadline || ""}
            onBlur={(e) => e.target.value !== (a.deadline || "") && onUpdate(a.id, { deadline: e.target.value })}
            className="mt-1 bg-transparent h-9" />
        </div>
      </div>

      <div className="mb-1.5 flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground">Progresso da candidatura</div>
        <div className="text-xs text-slate-400">{completed}/{total}</div>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-4">
        <div className="h-full bg-[#3B82F6]" style={{ width: total ? `${(completed / total) * 100}%` : "0%" }} />
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5"><ListChecks className="w-3.5 h-3.5" /> Passos</div>
          <ul className="space-y-1.5">
            {a.steps.map((s, i) => (
              <li key={i}>
                <button data-testid={`apoios-app-step-${a.id}-${i}`} onClick={() => onToggle(a.id, "steps", i)}
                  className="flex gap-2 text-left text-sm text-slate-300 hover:text-white">
                  <CheckCircle2 className={`w-4 h-4 shrink-0 mt-0.5 ${s.done ? "text-emerald-400" : "text-slate-600"}`} />
                  <span className={s.done ? "line-through text-slate-500" : ""}>{s.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> Documentos</div>
          <ul className="space-y-1.5">
            {a.checklist.map((s, i) => (
              <li key={i}>
                <button data-testid={`apoios-app-doc-${a.id}-${i}`} onClick={() => onToggle(a.id, "checklist", i)}
                  className="flex gap-2 text-left text-sm text-slate-300 hover:text-white">
                  <CheckCircle2 className={`w-4 h-4 shrink-0 mt-0.5 ${s.done ? "text-emerald-400" : "text-slate-600"}`} />
                  <span className={s.done ? "line-through text-slate-500" : ""}>{s.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4">
        <Label className="text-[11px] text-muted-foreground">Notas</Label>
        <Textarea data-testid={`apoios-app-notes-${a.id}`} value={notes} onChange={(e) => setNotes(e.target.value)}
          onBlur={() => notes !== (a.notes || "") && onUpdate(a.id, { notes })}
          placeholder="Anotações, contactos, referências do aviso..." className="mt-1 bg-transparent min-h-[64px] text-sm" />
      </div>

      {/* Documentos anexados */}
      <div className="mt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Paperclip className="w-3.5 h-3.5" /> Documentos anexados{files.length ? ` (${files.length})` : ""}</div>
          <input ref={fileRef} type="file" className="hidden" data-testid={`apoios-app-fileinput-${a.id}`}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp,.csv,.txt" onChange={onFile} />
          <Button size="sm" variant="outline" data-testid={`apoios-app-upload-${a.id}`} onClick={pick} disabled={uploadBusy}
            className="rounded-full h-8 text-xs">
            {uploadBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <><Upload className="w-3.5 h-3.5 mr-1.5" /> Anexar</>}
          </Button>
        </div>
        {files.length === 0 ? (
          <p className="text-xs text-muted-foreground">Carrega aqui os documentos desta candidatura (PDF, imagem, folha de cálculo…). Máx. 10 MB.</p>
        ) : (
          <ul className="space-y-1.5">
            {files.map((f) => (
              <li key={f.id} className="flex items-center gap-2 rounded-xl bg-white/[0.03] border border-white/[0.06] px-3 py-2" data-testid={`apoios-app-file-${a.id}-${f.id}`}>
                <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                <span className="text-sm truncate flex-1">{f.filename}</span>
                <span className="text-[11px] text-slate-500 shrink-0">{fmtBytes(f.size)}</span>
                <a href={`${API}/grants/applications/${a.id}/documents/${f.id}`} target="_blank" rel="noreferrer"
                  data-testid={`apoios-app-file-dl-${a.id}-${f.id}`} className="text-slate-400 hover:text-blue-400 shrink-0" title="Abrir / transferir">
                  <Download className="w-4 h-4" />
                </a>
                <button onClick={() => onDeleteFile(a.id, f.id)} data-testid={`apoios-app-file-del-${a.id}-${f.id}`}
                  className="text-slate-500 hover:text-red-400 shrink-0" title="Remover"><Trash2 className="w-4 h-4" /></button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-white/[0.06]">
        <a href={a.url} target="_blank" rel="noreferrer"
          className="text-xs inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300"><ExternalLink className="w-3.5 h-3.5" /> Abrir portal oficial</a>
      </div>
    </div>
  );
}

export default function Apoios() {
  const [tab, setTab] = useState("opps");
  const [country, setCountry] = useState("PT");
  const [countries, setCountries] = useState([{ code: "PT", label: "Portugal" }, { code: "BR", label: "Brasil" }]);
  const [profile, setProfile] = useState(null);
  const [opps, setOpps] = useState([]);
  const [verifiedAt, setVerifiedAt] = useState("");
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [apps, setApps] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [tracking, setTracking] = useState(null);
  // perfil extra
  const [invest, setInvest] = useState("");
  const [projectType, setProjectType] = useState("");
  const [interests, setInterests] = useState([]);
  const [savingProfile, setSavingProfile] = useState(false);

  const loadOpps = (c) => {
    setLoading(true);
    return api.get(`/grants/opportunities?country=${c}`).then(({ data }) => {
      setOpps(data.opportunities || []); setProfile(data.profile); setVerifiedAt(data.verified_at);
      setInvest(data.profile?.investment_amount || "");
      setProjectType(data.profile?.project_type || "");
      setInterests(data.profile?.interests || []);
    }).catch((e) => toast.error(formatApiError(e.response?.data?.detail))).finally(() => setLoading(false));
  };

  const loadApps = () => api.get("/grants/applications").then(({ data }) => { setApps(data.applications || []); setStatuses(data.statuses || []); }).catch(() => {});

  useEffect(() => {
    api.get("/grants/profile").then(({ data }) => {
      setCountries(data.countries || countries);
      const c = data.profile?.country || "PT";
      setCountry(c);
      loadOpps(c);
    }).catch(() => loadOpps("PT"));
    loadApps();
    // eslint-disable-next-line
  }, []);

  const changeCountry = (c) => { setCountry(c); setAnalysis(null); loadOpps(c); };

  const toggleInterest = (k) => setInterests((prev) => prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]);

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      const { data } = await api.post("/grants/profile", {
        focus_country: country,
        investment_amount: invest ? Number(invest) : null,
        project_type: projectType || null,
        interests,
      });
      setProfile(data.profile);
      toast.success("Perfil atualizado — apoios recalculados.");
      await loadOpps(country);
      setAnalysis(null);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setSavingProfile(false);
  };

  const analyze = async () => {
    setAnalyzing(true);
    try {
      const { data } = await api.post("/grants/analyze", { country }, { timeout: 120000 });
      if (!data.analysis) { toast.error("Sem oportunidades para analisar. Ajusta o perfil."); }
      else { setAnalysis(data.analysis); toast.success("Análise do Diretor de Apoios pronta."); }
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setAnalyzing(false);
  };

  const track = async (grantId) => {
    setTracking(grantId);
    try {
      const { data } = await api.post("/grants/applications", { grant_id: grantId });
      toast.success(data.already ? "Já estavas a acompanhar este apoio." : "Candidatura adicionada. Vê 'As minhas candidaturas'.");
      setOpps((prev) => prev.map((o) => o.id === grantId ? { ...o, tracked: true } : o));
      loadApps();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setTracking(null);
  };

  const updateApp = async (id, patch) => {
    try {
      const { data } = await api.patch(`/grants/applications/${id}`, patch);
      setApps((prev) => prev.map((a) => a.id === id ? data.application : a));
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const toggleItem = async (id, kind, index) => {
    try {
      const { data } = await api.post(`/grants/applications/${id}/toggle`, { kind, index });
      setApps((prev) => prev.map((a) => a.id === id ? data.application : a));
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const deleteApp = async (id) => {
    try { await api.delete(`/grants/applications/${id}`); setApps((prev) => prev.filter((a) => a.id !== id));
      setOpps((prev) => prev.map((o) => { const gid = apps.find((a) => a.id === id)?.grant_id; return o.id === gid ? { ...o, tracked: false } : o; }));
      toast.success("Candidatura removida.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const uploadFile = async (id, file) => {
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`/grants/applications/${id}/documents`, fd, {
        headers: { "Content-Type": "multipart/form-data" }, timeout: 120000,
      });
      setApps((prev) => prev.map((a) => a.id === id ? data.application : a));
      toast.success("Documento anexado.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const deleteFile = async (id, fid) => {
    try {
      const { data } = await api.delete(`/grants/applications/${id}/documents/${fid}`);
      setApps((prev) => prev.map((a) => a.id === id ? (data.application || a) : a));
      toast.success("Documento removido.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10" data-testid="apoios-page">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-blue-500/15 flex items-center justify-center"><Landmark className="w-6 h-6 text-blue-400" /></div>
          <div>
            <h1 className="font-serif-lux text-3xl sm:text-4xl">Apoios & Incentivos</h1>
            <p className="text-sm text-muted-foreground">Apoios públicos, incentivos fiscais e financiamento para a tua empresa.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Foco</Label>
          <Select value={country} onValueChange={changeCountry}>
            <SelectTrigger data-testid="apoios-country" className="w-36 bg-transparent h-9"><SelectValue /></SelectTrigger>
            <SelectContent>{countries.map((c) => <SelectItem key={c.code} value={c.code}>{c.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-full bg-white/[0.04] border border-white/[0.06] w-fit mb-6">
        <button data-testid="apoios-tab-opps" onClick={() => setTab("opps")}
          className={`px-4 py-1.5 rounded-full text-sm transition-colors ${tab === "opps" ? "bg-[#3B82F6] text-white" : "text-slate-400 hover:text-white"}`}>Oportunidades</button>
        <button data-testid="apoios-tab-apps" onClick={() => setTab("apps")}
          className={`px-4 py-1.5 rounded-full text-sm transition-colors ${tab === "apps" ? "bg-[#3B82F6] text-white" : "text-slate-400 hover:text-white"}`}>As minhas candidaturas{apps.length ? ` (${apps.length})` : ""}</button>
      </div>

      {tab === "opps" && (
        <>
          {/* Perfil de elegibilidade */}
          <div className="surface rounded-3xl p-6 mb-6" data-testid="apoios-profile">
            <div className="flex items-center gap-2 mb-4"><Building2 className="w-4 h-4 text-blue-400" /><h2 className="text-lg font-medium">Perfil de elegibilidade</h2></div>
            {profile && (
              <div className="grid sm:grid-cols-4 gap-3 mb-4">
                {[["Setor", profile.sector || "Por indicar"], ["Dimensão", profile.size_label || "Por confirmar"],
                  ["Trabalhadores", profile.employees ?? "—"], ["Faturação anual", profile.annual_revenue ? `${profile.currency_symbol}${Math.round(profile.annual_revenue).toLocaleString()}` : "Por indicar"]].map(([k, v], i) => (
                  <div key={i} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{k}</div>
                    <div className="text-sm mt-0.5">{v}</div>
                  </div>
                ))}
              </div>
            )}
            {profile?.missing?.length > 0 && (
              <div className="flex items-start gap-2 text-xs text-amber-300/90 mb-4">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>Para melhores resultados, completa: {profile.missing.map((m) => m.label).join(", ")}. Setor e dimensão vêm da área <b>Empresa</b>/<b>Finanças</b>.</span>
              </div>
            )}
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Investimento pretendido ({profile?.currency_symbol || "€"})</Label>
                <Input data-testid="apoios-invest" type="number" value={invest} onChange={(e) => setInvest(e.target.value)} placeholder="ex.: 25000" className="mt-1 bg-transparent" />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Tipo de projeto</Label>
                <Input data-testid="apoios-project" value={projectType} onChange={(e) => setProjectType(e.target.value)} placeholder="ex.: digitalização, contratação, expansão" className="mt-1 bg-transparent" />
              </div>
            </div>
            <div className="mt-4">
              <Label className="text-xs text-muted-foreground mb-2 block">Que tipo de apoio te interessa?</Label>
              <div className="flex flex-wrap gap-2">
                {INTERESTS.map((it) => (
                  <button key={it.key} data-testid={`apoios-interest-${it.key}`} onClick={() => toggleInterest(it.key)}
                    className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${interests.includes(it.key) ? "bg-[#3B82F6] text-white border-transparent" : "border-white/10 text-slate-400 hover:text-white"}`}>
                    {it.label}
                  </button>
                ))}
              </div>
            </div>
            <Button data-testid="apoios-profile-save" onClick={saveProfile} disabled={savingProfile}
              className="mt-4 rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
              {savingProfile ? <Loader2 className="w-4 h-4 animate-spin" /> : "Guardar e recalcular apoios"}
            </Button>
          </div>

          {/* Diretor de Apoios (IA) */}
          <div className="surface rounded-3xl p-6 mb-6" data-testid="apoios-director">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-blue-400" /><h2 className="text-lg font-medium">Diretor de Apoios</h2></div>
              <Button data-testid="apoios-analyze-btn" onClick={analyze} disabled={analyzing || loading}
                className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
                {analyzing ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> A analisar…</> : "Analisar com o Diretor de Apoios"}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground mt-2">A IA analisa os apoios elegíveis e traça a estratégia de candidatura, citando as fontes. Só corre quando pedes (poupa créditos).</p>
            {analysis && (
              <div className="mt-4 space-y-3" data-testid="apoios-analysis">
                <p className="text-sm text-slate-200">{analysis.resumo}</p>
                {analysis.prioridade && <div className="rounded-xl bg-blue-500/[0.08] border border-blue-500/20 p-3.5"><div className="text-[11px] uppercase tracking-wider text-blue-300 mb-1">Prioridade</div><p className="text-sm text-slate-200">{analysis.prioridade}</p></div>}
                {analysis.lacunas?.length > 0 && (
                  <div><div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">Como reforçar as candidaturas</div>
                    <ul className="space-y-1">{analysis.lacunas.map((l, i) => <li key={i} className="text-sm flex gap-2 text-slate-300"><Target className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />{l}</li>)}</ul></div>
                )}
                {analysis.proximo_passo && <div className="text-sm text-slate-200"><b>Próximo passo:</b> {analysis.proximo_passo}</div>}
                {analysis.aviso && <div className="flex items-start gap-2 text-xs text-slate-500"><Info className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span>{analysis.aviso}</span></div>}
              </div>
            )}
          </div>

          {/* Oportunidades */}
          {loading ? (
            <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-blue-400" /></div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-medium">{opps.length} oportunidades para o teu perfil</h2>
              </div>
              <div className="grid md:grid-cols-2 gap-5">
                {opps.map((o) => <OpportunityCard key={o.id} o={o} analysis={analysis} onTrack={track} tracking={tracking} />)}
              </div>
              <div className="flex items-start gap-2 text-xs text-slate-500 mt-6 max-w-3xl">
                <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                <span>A elegibilidade é uma <b>estimativa</b> com base no teu perfil e não garante aprovação. Base curada verificada a {verifiedAt}. Confirma sempre requisitos, montantes e prazos na fonte oficial. Isto não é aconselhamento legal nem fiscal.</span>
              </div>
            </>
          )}
        </>
      )}

      {tab === "apps" && (
        <div className="space-y-5">
          {apps.length === 0 ? (
            <div className="surface rounded-3xl p-10 text-center">
              <ClipboardList className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-muted-foreground">Ainda não estás a acompanhar nenhuma candidatura. Vai a <b>Oportunidades</b> e clica em "Acompanhar candidatura".</p>
            </div>
          ) : apps.map((a) => (
            <ApplicationCard key={a.id} a={a} statuses={statuses} onUpdate={updateApp} onToggle={toggleItem} onDelete={deleteApp} onUpload={uploadFile} onDeleteFile={deleteFile} />
          ))}
        </div>
      )}
    </div>
  );
}
