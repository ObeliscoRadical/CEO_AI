import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Megaphone, Sparkles, Copy, Download, RefreshCw, Calendar, Play, Hash } from "lucide-react";

const FORMAT_COLOR = { Post: "#3B82F6", Story: "#A78BFA", Reel: "#F59E0B" };

export default function Marketing() {
  const [content, setContent] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [gen, setGen] = useState(false);

  const load = () => api.get("/marketing/content").then(({ data }) => {
    if (data.content?.content) { setContent(data.content.content); setUpdated(data.content.updated_at); }
    setLoaded(true);
  }).catch(() => setLoaded(true));

  useEffect(() => { load(); }, []);

  const generate = async () => {
    setGen(true);
    try { const { data } = await api.post("/marketing/generate"); setContent(data.content.content); setUpdated(data.content.updated_at); toast.success("Conteúdos gerados pelo Diretor de Marketing."); }
    catch { toast.error("Não foi possível gerar agora."); }
    setGen(false);
  };

  const copyPost = (p) => {
    const txt = `${p.titulo}\n\n${p.legenda}\n\n${(p.hashtags || []).join(" ")}\n\n${p.cta || ""}`;
    navigator.clipboard.writeText(txt).then(() => toast.success("Conteúdo copiado!")).catch(() => {});
  };

  const exportAll = () => {
    if (!content) return;
    let t = `PLANO DE CONTEÚDOS — CEO AI (Diretor de Marketing)\n\n`;
    if (content.brand) t += `Tom da marca: ${content.brand.tom}\nPilares: ${(content.brand.pilares || []).join(", ")}\n\n`;
    t += `=== CONTEÚDOS ===\n\n`;
    (content.posts || []).forEach((p, i) => {
      t += `${i + 1}. [${p.formato}] ${p.titulo} (${p.dia || ""})\n${p.legenda}\n${(p.hashtags || []).join(" ")}\nCTA: ${p.cta || ""}\n\n`;
    });
    t += `=== CALENDÁRIO EDITORIAL ===\n`;
    (content.calendario || []).forEach((c) => { t += `${c.dia}: [${c.formato}] ${c.tema}\n`; });
    const blob = new Blob([t], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "conteudos-ceo-ai.txt"; a.click();
    URL.revokeObjectURL(url);
    toast.success("Ficheiro exportado.");
  };

  if (!loaded) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#A78BFA]" /></div>;

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1100px] mx-auto" data-testid="marketing-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Conselho Executivo · Diretor de Marketing</p>
      <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <h1 className="font-serif-lux text-4xl md:text-5xl text-[#A78BFA] flex items-center gap-3"><Megaphone className="w-8 h-8" /> Conteúdos & Campanhas</h1>
        {content && (
          <div className="flex gap-2">
            <Button data-testid="mkt-export-btn" onClick={exportAll} variant="outline" className="rounded-full border-white/15 hover:bg-white/5"><Download className="w-4 h-4 mr-2" /> Exportar tudo</Button>
            <Button data-testid="mkt-regen-btn" onClick={generate} disabled={gen} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">{gen ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />} Gerar novamente</Button>
          </div>
        )}
      </div>

      {!content ? (
        <div className="surface rounded-3xl p-8 md:p-12 text-center" data-testid="mkt-intro">
          <div className="w-14 h-14 rounded-2xl bg-[#A78BFA]/18 flex items-center justify-center mx-auto mb-6"><Megaphone className="w-7 h-7 text-[#A78BFA]" /></div>
          <h2 className="font-serif-lux text-2xl mb-2">O Diretor de Marketing está pronto</h2>
          <p className="text-muted-foreground max-w-xl mx-auto mb-8">Vou analisar a identidade da sua marca e criar posts, Stories, Reels e um calendário editorial coerente com o seu setor — prontos a copiar e publicar.</p>
          <Button data-testid="mkt-generate-btn" onClick={generate} disabled={gen} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] px-8 h-12 text-base">
            {gen ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> A criar conteúdos…</> : <><Play className="w-5 h-5 mr-2" /> Gerar conteúdos</>}
          </Button>
        </div>
      ) : (
        <>
          {content.brand && (
            <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-brand">
              <h2 className="font-serif-lux text-xl mb-2 flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#A78BFA]" /> Identidade da marca</h2>
              <p className="text-muted-foreground mb-4">{content.brand.tom}</p>
              <div className="flex flex-wrap gap-2">
                {(content.brand.pilares || []).map((p, i) => <span key={i} className="text-xs px-3 py-1.5 rounded-full border border-[#A78BFA]/30 text-[#A78BFA]">{p}</span>)}
              </div>
            </div>
          )}

          <h2 className="font-serif-lux text-2xl mb-4">Conteúdos prontos a publicar</h2>
          <div className="grid md:grid-cols-2 gap-5 mb-10" data-testid="mkt-posts">
            {(content.posts || []).map((p, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} className="surface rounded-3xl p-6 flex flex-col" data-testid={`mkt-post-${i}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full" style={{ color: FORMAT_COLOR[p.formato] || "#94a3b8", background: `${FORMAT_COLOR[p.formato] || "#94a3b8"}18` }}>{p.formato}</span>
                  {p.dia && <span className="text-xs text-muted-foreground">{p.dia}</span>}
                </div>
                <div className="font-medium mb-2">{p.titulo}</div>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap mb-3 flex-1">{p.legenda}</p>
                {p.hashtags?.length > 0 && <div className="text-xs text-[#3B82F6] mb-3 flex items-start gap-1"><Hash className="w-3 h-3 mt-0.5 shrink-0" /><span>{p.hashtags.join(" ")}</span></div>}
                {p.cta && <div className="text-sm font-medium text-[#10B981] mb-4">{p.cta}</div>}
                <Button data-testid={`mkt-copy-${i}`} onClick={() => copyPost(p)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5 self-start mt-auto"><Copy className="w-3.5 h-3.5 mr-1.5" /> Copiar</Button>
              </motion.div>
            ))}
          </div>

          {content.calendario?.length > 0 && (
            <div className="surface rounded-3xl p-6 md:p-8" data-testid="mkt-calendar">
              <h2 className="font-serif-lux text-xl mb-4 flex items-center gap-2"><Calendar className="w-5 h-5 text-[#A78BFA]" /> Calendário editorial</h2>
              <div className="space-y-2">
                {content.calendario.map((c, i) => (
                  <div key={i} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <span className="text-sm font-medium w-28 shrink-0 capitalize">{c.dia}</span>
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0" style={{ color: FORMAT_COLOR[c.formato] || "#94a3b8", background: `${FORMAT_COLOR[c.formato] || "#94a3b8"}18` }}>{c.formato}</span>
                    <span className="text-sm text-muted-foreground">{c.tema}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground mt-8">A publicação automática no Instagram/Facebook/Google Business chega numa próxima fase. Por agora, copie ou exporte os conteúdos e publique manualmente.</p>
        </>
      )}
    </div>
  );
}
