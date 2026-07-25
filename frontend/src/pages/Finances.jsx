import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Upload, Trash2, Loader2, ArrowUpRight, ArrowDownRight, Landmark } from "lucide-react";
import { motion } from "framer-motion";

export default function Finances() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [form, setForm] = useState({ type: "income", category: "", amount: "", date: new Date().toISOString().slice(0, 10), description: "" });
  const fileRef = useRef();

  const load = () => api.get("/entries").then(({ data }) => setEntries(data)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    try {
      await api.post("/entries", { ...form, amount: Number(form.amount) });
      setOpen(false);
      setForm({ type: "income", category: "", amount: "", date: new Date().toISOString().slice(0, 10), description: "" });
      toast.success("Registo adicionado");
      load();
    } catch { toast.error("Erro ao adicionar"); }
  };

  const del = async (id) => { await api.delete(`/entries/${id}`); load(); };

  const connectBank = async () => {
    setConnecting(true);
    try {
      const { data } = await api.post("/bank/connect");
      toast.success(`Banco ligado (demo) · ${data.imported} movimentos importados`);
      load();
    } catch { toast.error("Não foi possível ligar o banco"); }
    finally { setConnecting(false); }
  };

  const importFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/entries/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`${data.imported} registos importados com IA`);
      load();
    } catch { toast.error("Não foi possível ler o ficheiro"); }
    finally { setImporting(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const income = entries.filter((e) => e.type === "income").reduce((a, b) => a + b.amount, 0);
  const expense = entries.filter((e) => e.type === "expense").reduce((a, b) => a + b.amount, 0);

  return (
    <div className="p-6 md:p-10 max-w-[1200px] mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="font-serif-lux text-4xl">Finanças</h1>
          <p className="text-muted-foreground text-sm mt-1">Liga os teus dados. O CEO AI analisa tudo por ti.</p>
        </div>
        <div className="flex gap-3">
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.txt" onChange={importFile} className="hidden" data-testid="import-input" />
          <Button data-testid="connect-bank-btn" variant="outline" onClick={connectBank} disabled={connecting} className="rounded-full">
            {connecting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Landmark className="w-4 h-4 mr-2" />} Ligar banco (demo)
          </Button>
          <Button data-testid="import-btn" variant="outline" onClick={() => fileRef.current?.click()} disabled={importing} className="rounded-full">
            {importing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />} Importar CSV
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-entry-btn" className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]"><Plus className="w-4 h-4 mr-2" />Novo registo</Button>
            </DialogTrigger>
            <DialogContent className="surface">
              <DialogHeader><DialogTitle className="font-serif-lux text-2xl">Novo registo financeiro</DialogTitle>
                <DialogDescription className="text-muted-foreground text-sm">Regista uma receita ou despesa. O CEO AI usa estes dados para analisar a saúde da empresa.</DialogDescription>
              </DialogHeader>
              <form onSubmit={add} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><Label className="text-xs text-muted-foreground">Tipo</Label>
                    <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                      <SelectTrigger data-testid="entry-type" className="mt-1 bg-transparent"><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="income">Receita</SelectItem><SelectItem value="expense">Despesa</SelectItem></SelectContent>
                    </Select>
                  </div>
                  <div><Label className="text-xs text-muted-foreground">Valor</Label><Input data-testid="entry-amount" type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required className="mt-1 bg-transparent" /></div>
                </div>
                <div><Label className="text-xs text-muted-foreground">Categoria</Label><Input data-testid="entry-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required className="mt-1 bg-transparent" placeholder="Ex: Vendas, Salários, Renda" /></div>
                <div><Label className="text-xs text-muted-foreground">Data</Label><Input data-testid="entry-date" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="mt-1 bg-transparent" /></div>
                <div><Label className="text-xs text-muted-foreground">Descrição</Label><Input data-testid="entry-desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 bg-transparent" /></div>
                <Button data-testid="save-entry-btn" type="submit" className="w-full rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">Guardar</Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="surface rounded-2xl p-6"><p className="text-xs text-muted-foreground mb-2">Receitas</p><div className="font-serif-lux text-3xl text-[#10B981]">€{income.toLocaleString("pt-PT")}</div></div>
        <div className="surface rounded-2xl p-6"><p className="text-xs text-muted-foreground mb-2">Despesas</p><div className="font-serif-lux text-3xl text-[#EF4444]">€{expense.toLocaleString("pt-PT")}</div></div>
        <div className="surface rounded-2xl p-6"><p className="text-xs text-muted-foreground mb-2">Resultado</p><div className="font-serif-lux text-3xl text-[#3B82F6]">€{(income - expense).toLocaleString("pt-PT")}</div></div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-[#3B82F6]" /></div>
      ) : entries.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">Ainda sem registos. Adiciona um ou importa um CSV.</div>
      ) : (
        <div className="surface rounded-2xl overflow-hidden">
          {entries.map((e, i) => (
            <motion.div key={e.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}
              className="flex items-center gap-4 px-6 py-4 border-b border-border last:border-0" data-testid={`entry-${e.id}`}>
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: e.type === "income" ? "#10B98122" : "#EF444422" }}>
                {e.type === "income" ? <ArrowUpRight className="w-4 h-4 text-[#10B981]" /> : <ArrowDownRight className="w-4 h-4 text-[#EF4444]" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{e.category}</div>
                <div className="text-xs text-muted-foreground">{e.date}{e.description ? ` · ${e.description}` : ""}</div>
              </div>
              <div className={`font-medium ${e.type === "income" ? "text-[#10B981]" : "text-[#EF4444]"}`}>
                {e.type === "income" ? "+" : "-"}€{Number(e.amount).toLocaleString("pt-PT")}
              </div>
              <button onClick={() => del(e.id)} data-testid={`delete-${e.id}`} className="text-muted-foreground hover:text-[#EF4444] transition-colors"><Trash2 className="w-4 h-4" /></button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
