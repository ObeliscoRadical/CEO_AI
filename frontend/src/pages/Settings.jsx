import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useTheme } from "@/context/ThemeContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Brain } from "lucide-react";

const MODES = ["conservador", "crescimento", "agressivo", "familiar", "startup", "investidor"];
const MODELS = [
  { key: "claude", label: "Claude Opus 4.7" },
  { key: "gpt", label: "GPT-5.5" },
  { key: "gemini", label: "Gemini 3.1 Pro" },
];
const TONES = ["direto", "caloroso", "analítico", "motivador"];

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [settings, setSettings] = useState(null);
  const [memories, setMemories] = useState([]);
  const [newMem, setNewMem] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/settings").then(({ data }) => setSettings(data));
    api.get("/memories").then(({ data }) => setMemories(data));
  }, []);

  const update = (patch) => setSettings((s) => ({ ...s, ...patch }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/settings", settings);
      if (settings.theme) setTheme(settings.theme);
      toast.success("Personalização guardada");
    } catch { toast.error("Erro ao guardar"); }
    finally { setSaving(false); }
  };

  const addMem = async () => {
    if (!newMem.trim()) return;
    const { data } = await api.post("/memories", { content: newMem, category: "geral" });
    setMemories((m) => [{ id: data.id, content: newMem, category: "geral" }, ...m]);
    setNewMem("");
    toast.success("O CEO AI vai lembrar-se disto.");
  };
  const delMem = async (id) => { await api.delete(`/memories/${id}`); setMemories((m) => m.filter((x) => x.id !== id)); };

  if (!settings) return <div className="flex justify-center py-32"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;

  return (
    <div className="p-6 md:p-10 max-w-[900px] mx-auto">
      <h1 className="font-serif-lux text-4xl mb-1">Personalização</h1>
      <p className="text-muted-foreground text-sm mb-8">Configura o teu CEO AI ao teu gosto.</p>

      <div className="surface rounded-3xl p-8 space-y-6 mb-6">
        <h2 className="font-serif-lux text-2xl">O teu CEO</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <Label className="text-xs text-muted-foreground">Personalidade / Modo</Label>
            <Select value={settings.ceo_mode} onValueChange={(v) => update({ ceo_mode: v })}>
              <SelectTrigger data-testid="set-mode" className="mt-1 bg-transparent capitalize"><SelectValue /></SelectTrigger>
              <SelectContent>{MODES.map((m) => <SelectItem key={m} value={m} className="capitalize">{m}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Modelo de IA</Label>
            <Select value={settings.model} onValueChange={(v) => update({ model: v })}>
              <SelectTrigger data-testid="set-model" className="mt-1 bg-transparent"><SelectValue /></SelectTrigger>
              <SelectContent>{MODELS.map((m) => <SelectItem key={m.key} value={m.key}>{m.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Tom do briefing</Label>
            <Select value={settings.briefing_tone} onValueChange={(v) => update({ briefing_tone: v })}>
              <SelectTrigger data-testid="set-tone" className="mt-1 bg-transparent capitalize"><SelectValue /></SelectTrigger>
              <SelectContent>{TONES.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Assuntos no briefing</Label>
            <Input data-testid="set-count" type="number" min="1" max="8" value={settings.briefing_count} onChange={(e) => update({ briefing_count: Number(e.target.value) })} className="mt-1 bg-transparent" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Tema visual</Label>
            <Select value={settings.theme} onValueChange={(v) => update({ theme: v })}>
              <SelectTrigger data-testid="set-theme" className="mt-1 bg-transparent capitalize"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="dark">Escuro (Obsidiana)</SelectItem><SelectItem value="light">Claro</SelectItem></SelectContent>
            </Select>
          </div>
        </div>
        <Button data-testid="save-settings-btn" onClick={save} disabled={saving} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null} Guardar
        </Button>
      </div>

      <div className="surface rounded-3xl p-8">
        <div className="flex items-center gap-2 mb-2"><Brain className="w-5 h-5 text-[#D4AF37]" /><h2 className="font-serif-lux text-2xl">CEO Memory</h2></div>
        <p className="text-muted-foreground text-sm mb-6">O que queres que o teu CEO nunca esqueça. Cada conselho vai considerar isto.</p>
        <div className="flex gap-3 mb-5">
          <Input data-testid="mem-input" value={newMem} onChange={(e) => setNewMem(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addMem()} placeholder="Ex: odeio empréstimos; quero contratar 2 técnicos" className="bg-transparent" />
          <Button data-testid="add-mem-btn" onClick={addMem} className="rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]"><Plus className="w-4 h-4" /></Button>
        </div>
        <div className="space-y-2">
          {memories.length === 0 && <p className="text-sm text-muted-foreground">Ainda sem memórias.</p>}
          {memories.map((m) => (
            <div key={m.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-border" data-testid={`mem-${m.id}`}>
              <div className="w-2 h-2 rounded-full bg-[#D4AF37]" />
              <span className="flex-1 text-sm">{m.content}</span>
              <button onClick={() => delMem(m.id)} data-testid={`del-mem-${m.id}`} className="text-muted-foreground hover:text-[#EF4444] transition-colors"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
