import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2, Megaphone, Sparkles, Copy, Download, RefreshCw, Calendar, Play, Hash, Share2, Instagram, Facebook, Send, Clock, CheckCircle2, XCircle, Link2, Unlink, Image as ImageIcon, Upload, Trash2 } from "lucide-react";

const FORMAT_COLOR = { Post: "#3B82F6", Story: "#A78BFA", Reel: "#F59E0B" };
const captionOf = (p) => `${p.legenda || ""}\n\n${(p.hashtags || []).join(" ")}\n${p.cta || ""}`.trim();

export default function Marketing() {
  const [content, setContent] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [gen, setGen] = useState(false);
  const [social, setSocial] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [busy, setBusy] = useState(null);            // index a publicar
  const [schedFor, setSchedFor] = useState(null);    // post a agendar
  const [schedWhen, setSchedWhen] = useState("");
  const [targets, setTargets] = useState({ instagram: true, facebook: true });
  const [logo, setLogo] = useState(null);
  const [logoBusy, setLogoBusy] = useState(false);
  const [imgBusy, setImgBusy] = useState(null);

  const load = () => api.get("/marketing/content").then(({ data }) => {
    if (data.content?.content) { setContent(data.content.content); setUpdated(data.content.updated_at); }
    setLoaded(true);
  }).catch(() => setLoaded(true));

  const loadSocial = () => api.get("/social/status").then(({ data }) => setSocial(data)).catch(() => {});
  const loadJobs = () => api.get("/social/jobs").then(({ data }) => setJobs(data.jobs || [])).catch(() => {});
  const loadLogo = () => api.get("/social/logo").then(({ data }) => setLogo(data.has_logo ? data.preview : null)).catch(() => {});

  useEffect(() => {
    load(); loadSocial(); loadJobs(); loadLogo();
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) { toast.success("Redes ligadas com sucesso!"); window.history.replaceState({}, "", "/marketing"); loadSocial(); }
    if (params.get("social_error")) { toast.error("Não foi possível ligar: " + params.get("social_error")); window.history.replaceState({}, "", "/marketing"); }
  }, []);

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

  const connect = async () => {
    try { const { data } = await api.get("/social/connect"); window.location.href = data.auth_url; }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const disconnect = async () => {
    await api.post("/social/disconnect"); toast.success("Redes desligadas."); loadSocial();
  };

  const publishNow = async (p, i) => {
    if (!social?.connected) { toast.error("Ligue primeiro as suas redes."); return; }
    setBusy(i);
    try {
      const { data } = await api.post("/social/publish", {
        caption: captionOf(p), image_url: p.image_url || null, image_prompt: `${p.titulo}. ${content?.brand?.tom || ""}`,
        generate_image: !p.image_url, instagram: targets.instagram, facebook: targets.facebook,
      });
      const r = data.results || {};
      const errs = Object.entries(r).filter(([, v]) => v?.error).map(([k, v]) => `${k}: ${v.error}`);
      if (errs.length) toast.warning("Publicado com avisos — " + errs.join(" · "));
      else toast.success("Publicado nas suas redes! 🎉");
    } catch (e) {
      const d = e.response?.data?.detail;
      toast.error("Falha ao publicar: " + (d?.meta_error ? JSON.stringify(d.meta_error).slice(0, 180) : formatApiError(d)));
    }
    setBusy(null); loadJobs();
  };

  const openSchedule = (p) => {
    setSchedFor(p);
    const dt = new Date(Date.now() + 60 * 60 * 1000);
    dt.setMinutes(dt.getMinutes() - dt.getTimezoneOffset());
    setSchedWhen(dt.toISOString().slice(0, 16));
  };

  const confirmSchedule = async () => {
    if (!schedWhen) return;
    const p = schedFor;
    try {
      await api.post("/social/schedule", {
        caption: captionOf(p), image_url: p.image_url || null, image_prompt: `${p.titulo}. ${content?.brand?.tom || ""}`,
        generate_image: !p.image_url, instagram: targets.instagram, facebook: targets.facebook,
        run_at: new Date(schedWhen).toISOString(),
      });
      toast.success("Publicação agendada!"); setSchedFor(null); loadJobs();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const cancelJob = async (id) => { await api.delete(`/social/jobs/${id}`); loadJobs(); };

  const uploadLogo = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/social/logo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setLogo(data.preview); toast.success("Logo carregado! Será aplicado nas imagens geradas.");
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    setLogoBusy(false); e.target.value = "";
  };

  const removeLogo = async () => { await api.delete("/social/logo"); setLogo(null); toast.success("Logo removido."); };

  const genImage = async (i) => {
    setImgBusy(i);
    try {
      const { data } = await api.post("/marketing/image", { index: i });
      setContent((c) => { const posts = [...(c.posts || [])]; posts[i] = { ...posts[i], image_url: data.image_url }; return { ...c, posts }; });
      toast.success("Imagem criada com o seu logo!");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    setImgBusy(null);
  };

  const downloadImage = async (url, i) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const u = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = u; a.download = `obelisco-post-${i + 1}.png`; a.click();
      URL.revokeObjectURL(u);
      toast.success("Imagem guardada no seu dispositivo!");
    } catch { toast.error("Não foi possível guardar a imagem."); }
  };

  if (!loaded) return <div className="flex justify-center py-40"><Loader2 className="w-6 h-6 animate-spin text-[#A78BFA]" /></div>;

  const Target = ({ k, Icon, label }) => (
    <button type="button" data-testid={`mkt-target-${k}`} onClick={() => setTargets((t) => ({ ...t, [k]: !t[k] }))}
      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${targets[k] ? "border-[#A78BFA] text-[#A78BFA] bg-[#A78BFA]/10" : "border-white/15 text-muted-foreground"}`}>
      <Icon className="w-3.5 h-3.5" /> {label}
    </button>
  );

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

      {/* Ligação de redes */}
      <div className="surface rounded-3xl p-6 md:p-7 mb-8" data-testid="mkt-social">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#A78BFA]/18 flex items-center justify-center shrink-0"><Share2 className="w-5 h-5 text-[#A78BFA]" /></div>
            <div>
              <h2 className="font-serif-lux text-xl">Publicação automática nas redes</h2>
              {social?.connected ? (
                <p className="text-sm text-muted-foreground mt-1" data-testid="mkt-social-connected">
                  Ligado a <b className="text-foreground">{social.page_name || "Página"}</b>
                  {social.ig_username ? <> · Instagram <b className="text-foreground">@{social.ig_username}</b></> : <> · <span className="text-amber-400">sem Instagram ligado</span></>}
                </p>
              ) : social?.configured ? (
                <p className="text-sm text-muted-foreground mt-1">Ligue o seu Instagram/Facebook para publicar e agendar diretamente a partir daqui.</p>
              ) : (
                <p className="text-sm text-amber-400 mt-1" data-testid="mkt-social-notconfigured">A integração da Meta ainda não está configurada. Assim que colarmos o App ID/Secret, o botão de ligar fica ativo.</p>
              )}
              {social && !social.connected && social.configured && (
                <p className="text-[11px] text-muted-foreground mt-2">URL de redireccionamento (adicione na app Meta): <code className="text-[#A78BFA] break-all">{social.redirect_uri}</code></p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {social?.connected ? (
              <Button data-testid="mkt-disconnect-btn" onClick={disconnect} variant="outline" className="rounded-full border-white/15 hover:bg-white/5"><Unlink className="w-4 h-4 mr-2" /> Desligar</Button>
            ) : (
              <Button data-testid="mkt-connect-btn" onClick={connect} disabled={!social?.configured} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] disabled:opacity-50"><Link2 className="w-4 h-4 mr-2" /> Ligar Instagram/Facebook</Button>
            )}
          </div>
        </div>
        {social?.connected && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/[0.06]">
            <span className="text-xs text-muted-foreground mr-1">Publicar em:</span>
            <Target k="instagram" Icon={Instagram} label="Instagram" />
            <Target k="facebook" Icon={Facebook} label="Facebook" />
          </div>
        )}
      </div>

      {/* Logo da empresa */}
      <div className="surface rounded-3xl p-6 md:p-7 mb-8" data-testid="mkt-logo-card">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center overflow-hidden shrink-0">
              {logo ? <img src={logo} alt="Logo" className="w-full h-full object-contain p-1.5" data-testid="mkt-logo-preview" /> : <ImageIcon className="w-6 h-6 text-muted-foreground" />}
            </div>
            <div>
              <h2 className="font-serif-lux text-xl">Logo da empresa</h2>
              <p className="text-sm text-muted-foreground mt-1 max-w-md">
                {logo ? "O seu logo será sobreposto automaticamente em todas as imagens geradas." : "Carregue o seu logo (PNG com fundo transparente, de preferência) para aparecer nas imagens geradas."}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <label data-testid="mkt-logo-upload" className="cursor-pointer inline-flex items-center gap-2 text-sm px-4 h-10 rounded-full border border-white/15 hover:bg-white/5 transition-colors">
              {logoBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} {logo ? "Alterar" : "Carregar logo"}
              <input type="file" accept="image/*" className="hidden" onChange={uploadLogo} disabled={logoBusy} />
            </label>
            {logo && <Button data-testid="mkt-logo-remove" onClick={removeLogo} variant="outline" className="rounded-full border-white/15 hover:bg-white/5 h-10"><Trash2 className="w-4 h-4" /></Button>}
          </div>
        </div>
      </div>

      {/* Agendamentos */}
      {jobs.length > 0 && (
        <div className="surface rounded-3xl p-6 mb-8" data-testid="mkt-jobs">
          <h2 className="font-serif-lux text-lg mb-4 flex items-center gap-2"><Clock className="w-4 h-4 text-[#A78BFA]" /> Publicações agendadas</h2>
          <div className="space-y-2">
            {jobs.map((j) => (
              <div key={j.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`mkt-job-${j.id}`}>
                {j.status === "published" ? <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" /> : j.status === "failed" ? <XCircle className="w-4 h-4 text-red-400 shrink-0" /> : <Clock className="w-4 h-4 text-amber-400 shrink-0" />}
                <span className="text-xs text-muted-foreground w-40 shrink-0">{new Date(j.run_at).toLocaleString("pt-PT")}</span>
                <span className="text-sm flex-1 truncate">{j.caption}</span>
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{j.status}</span>
                {j.status === "queued" && <button onClick={() => cancelJob(j.id)} className="text-xs text-red-400 hover:underline" data-testid={`mkt-job-cancel-${j.id}`}>cancelar</button>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!content ? (
        <div className="surface rounded-3xl p-8 md:p-12 text-center" data-testid="mkt-intro">
          <div className="w-14 h-14 rounded-2xl bg-[#A78BFA]/18 flex items-center justify-center mx-auto mb-6"><Megaphone className="w-7 h-7 text-[#A78BFA]" /></div>
          <h2 className="font-serif-lux text-2xl mb-2">O Diretor de Marketing está pronto</h2>
          <p className="text-muted-foreground max-w-xl mx-auto mb-8">Vou analisar a identidade da sua marca e criar posts, Stories, Reels e um calendário editorial coerente com o seu setor — prontos a copiar, publicar ou agendar.</p>
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
                {p.image_url ? (
                  <img src={p.image_url} alt={p.titulo} className="w-full aspect-square object-cover rounded-2xl mb-4" data-testid={`mkt-img-${i}`} />
                ) : (
                  <button onClick={() => genImage(i)} disabled={imgBusy === i} data-testid={`mkt-genimg-${i}`}
                    className="w-full aspect-square rounded-2xl border border-dashed border-white/15 flex flex-col items-center justify-center gap-2 mb-4 hover:bg-white/[0.03] transition-colors disabled:opacity-60">
                    {imgBusy === i
                      ? <><Loader2 className="w-6 h-6 animate-spin text-[#A78BFA]" /><span className="text-xs text-muted-foreground">A criar imagem (~30s)…</span></>
                      : <><ImageIcon className="w-6 h-6 text-[#A78BFA]" /><span className="text-xs text-muted-foreground">Gerar imagem (com o seu logo)</span></>}
                  </button>
                )}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full" style={{ color: FORMAT_COLOR[p.formato] || "#94a3b8", background: `${FORMAT_COLOR[p.formato] || "#94a3b8"}18` }}>{p.formato}</span>
                  {p.dia && <span className="text-xs text-muted-foreground">{p.dia}</span>}
                </div>
                <div className="font-medium mb-2">{p.titulo}</div>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap mb-3 flex-1">{p.legenda}</p>
                {p.hashtags?.length > 0 && <div className="text-xs text-[#3B82F6] mb-3 flex items-start gap-1"><Hash className="w-3 h-3 mt-0.5 shrink-0" /><span>{p.hashtags.join(" ")}</span></div>}
                {p.cta && <div className="text-sm font-medium text-[#10B981] mb-4">{p.cta}</div>}
                <div className="flex flex-wrap gap-2 mt-auto">
                  <Button data-testid={`mkt-copy-${i}`} onClick={() => copyPost(p)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5"><Copy className="w-3.5 h-3.5 mr-1.5" /> Copiar texto</Button>
                  {p.image_url && (
                    <Button data-testid={`mkt-download-${i}`} onClick={() => downloadImage(p.image_url, i)} size="sm" className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]"><Download className="w-3.5 h-3.5 mr-1.5" /> Guardar imagem</Button>
                  )}
                  {social?.connected && (
                    <>
                      <Button data-testid={`mkt-publish-${i}`} onClick={() => publishNow(p, i)} disabled={busy === i} size="sm" className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]">
                        {busy === i ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Send className="w-3.5 h-3.5 mr-1.5" />} Publicar
                      </Button>
                      <Button data-testid={`mkt-schedule-${i}`} onClick={() => openSchedule(p)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5"><Clock className="w-3.5 h-3.5 mr-1.5" /> Agendar</Button>
                    </>
                  )}
                </div>
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

          <p className="text-[11px] text-muted-foreground mt-8">Sem ligação às redes, use <b>Gerar imagem</b> → <b>Guardar imagem</b> e <b>Copiar texto</b> para publicar manualmente no Instagram/Facebook. A imagem inclui o seu logo. Quando ligar a conta Meta, poderá publicar e agendar automaticamente daqui.</p>
        </>
      )}

      {/* Diálogo de agendamento */}
      <Dialog open={!!schedFor} onOpenChange={(o) => !o && setSchedFor(null)}>
        <DialogContent data-testid="mkt-schedule-dialog">
          <DialogHeader>
            <DialogTitle>Agendar publicação</DialogTitle>
            <DialogDescription>Escolha a data e hora. A publicação (com imagem gerada por IA) será enviada automaticamente às redes selecionadas.</DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs text-muted-foreground">Data e hora</label>
            <Input type="datetime-local" data-testid="mkt-schedule-when" value={schedWhen} onChange={(e) => setSchedWhen(e.target.value)} className="mt-1" />
            <div className="flex gap-2 mt-4">
              <Target k="instagram" Icon={Instagram} label="Instagram" />
              <Target k="facebook" Icon={Facebook} label="Facebook" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSchedFor(null)} className="rounded-full">Cancelar</Button>
            <Button data-testid="mkt-schedule-confirm" onClick={confirmSchedule} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]">Agendar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
