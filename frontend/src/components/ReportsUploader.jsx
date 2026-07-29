import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Loader2, FileText, Trash2, Upload, Sparkles, CheckCircle2 } from "lucide-react";

const QUALITY = {
  high: { label: "Muito útil", color: "#10B981" },
  medium: { label: "Útil", color: "#3B82F6" },
  low: { label: "Pouco relevante", color: "#94a3b8" },
};

export const ReportsUploader = ({ compact = false }) => {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [inbox, setInbox] = useState(null);
  const inputRef = useRef(null);

  const load = async () => {
    try { const { data } = await api.get("/documents"); setDocs(data); } catch (e) {}
    try { const { data } = await api.get("/report-inbox"); setInbox(data); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const onFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    setUploading(true);
    for (const f of files) {
      if (f.size > 12 * 1024 * 1024) { toast.error(`"${f.name}" é demasiado grande (máx 12MB).`); continue; }
      try {
        const fd = new FormData();
        fd.append("file", f);
        fd.append("doc_type", "report");
        const { data } = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
        const s = data?.analysis?.summary;
        toast.success(s ? `Li o teu "${data.filename}": ${s}` : `Analisei "${data.filename}".`);
      } catch (err) {
        toast.error(`Não foi possível analisar "${f.name}".`);
      }
    }
    setUploading(false);
    load();
  };

  const remove = async (id) => {
    try {
      await api.delete(`/documents/${id}`);
      setDocs((d) => d.filter((x) => x.id !== id));
      toast.success("Documento removido.");
    } catch (e) {
      toast.error("Não foi possível remover o documento.");
    }
  };

  return (
    <div className="surface rounded-3xl p-6 md:p-8" data-testid="reports-uploader">
      <div className="flex items-start gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-[#3B82F6]/15 flex items-center justify-center shrink-0"><Sparkles className="w-5 h-5 text-[#3B82F6]" /></div>
        <div>
          <h2 className="font-serif-lux text-2xl leading-tight">Já tens algum relatório? Insere e eu analiso.</h2>
          <p className="text-muted-foreground text-sm mt-1">Carrega relatórios do teu Obelisco Manager, extratos, faturação, balancetes ou contratos (PDF, imagem, Excel, CSV). Eu leio, analiso e passo a usar esses dados reais em todas as decisões e no valor da tua empresa.</p>
        </div>
      </div>

      <input ref={inputRef} type="file" multiple accept="image/*,.pdf,.txt,.csv,.docx,.xlsx,.xls" onChange={onFiles} className="hidden" data-testid="reports-file-input" />
      <Button data-testid="reports-upload-btn" onClick={() => inputRef.current?.click()} disabled={uploading}
        className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] mt-4">
        {uploading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
        {uploading ? "A analisar..." : "Inserir relatório para o CEO analisar"}
      </Button>

      {inbox?.address ? (
        <div className="mt-5 p-4 rounded-xl border border-border" data-testid="report-inbox">
          <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground mb-1">Importação automática por email</p>
          <p className="text-sm text-muted-foreground mb-2">Reencaminha os relatórios (ou configura o teu Obelisco Manager para os enviar) para este endereço e eu analiso-os sozinho:</p>
          <div className="flex items-center gap-2">
            <code className="text-sm bg-accent px-3 py-1.5 rounded-lg flex-1 truncate" data-testid="report-inbox-address">{inbox.address}</code>
            <Button variant="outline" className="rounded-full shrink-0" data-testid="copy-inbox-btn"
              onClick={() => { navigator.clipboard?.writeText(inbox.address); toast.success("Endereço copiado"); }}>Copiar</Button>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-xs text-muted-foreground" data-testid="report-inbox-soon">Importação automática por email: fica disponível assim que o domínio de receção for configurado (podes sempre carregar manualmente aqui).</p>
      )}

      {!loading && docs.length > 0 && (
        <div className="mt-6 space-y-2" data-testid="reports-list">
          <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground mb-2">Documentos que o CEO já leu</p>
          {docs.map((d) => {
            const q = QUALITY[d.analysis?.quality] || QUALITY.low;
            return (
              <div key={d.id} data-testid={`report-${d.id}`} className="flex items-start gap-3 p-3.5 rounded-xl border border-border">
                <FileText className="w-4 h-4 text-[#3B82F6] mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium truncate">{d.filename}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: `${q.color}22`, color: q.color }}>{q.label}</span>
                    {d.analysis?.relevant && <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />}
                  </div>
                  {d.analysis?.summary && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{d.analysis.summary}</p>}
                </div>
                <button onClick={() => remove(d.id)} data-testid={`remove-report-${d.id}`} className="text-muted-foreground hover:text-[#EF4444] transition-colors shrink-0"><Trash2 className="w-4 h-4" /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
