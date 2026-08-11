import { useEffect, useMemo, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  Loader2,
  Megaphone,
  Sparkles,
  Copy,
  Download,
  RefreshCw,
  Calendar,
  Play,
  Hash,
  Share2,
  Instagram,
  Facebook,
  Send,
  Clock,
  CheckCircle2,
  XCircle,
  Link2,
  Unlink,
  Image as ImageIcon,
  Upload,
  Trash2,
  ShieldCheck,
  BadgeCheck,
  Library,
  Target,
  BrainCircuit,
} from "lucide-react";

const FORMAT_COLOR = { Post: "#3B82F6", Story: "#A78BFA", Reel: "#F59E0B" };
const STATUS_META = {
  draft: { label: "Rascunho", tone: "text-slate-200 bg-slate-500/15 border-slate-400/20" },
  approved: { label: "Aprovado", tone: "text-emerald-300 bg-emerald-500/15 border-emerald-400/20" },
  scheduled: { label: "Agendado", tone: "text-amber-300 bg-amber-500/15 border-amber-400/20" },
};

const captionOf = (post) => `${post.legenda || ""}\n\n${(post.hashtags || []).join(" ")}\n${post.cta || ""}`.trim();

const WorkflowBadge = ({ status, testId }) => {
  const meta = STATUS_META[status] || STATUS_META.draft;
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] ${meta.tone}`}
    >
      {meta.label}
    </span>
  );
};

const PillList = ({ items = [], color = "#A78BFA", testIdPrefix }) => (
  <div className="flex flex-wrap gap-2">
    {items.map((item, index) => (
      <span
        key={`${item}-${index}`}
        data-testid={testIdPrefix ? `${testIdPrefix}-${index}` : undefined}
        className="text-xs px-3 py-1.5 rounded-full border"
        style={{ color, borderColor: `${color}50`, background: `${color}12` }}
      >
        {item}
      </span>
    ))}
  </div>
);

const TargetToggle = ({ channel, Icon, label, enabled, onToggle }) => (
  <button
    type="button"
    data-testid={`mkt-target-${channel}`}
    onClick={onToggle}
    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${enabled ? "border-[#A78BFA] text-[#A78BFA] bg-[#A78BFA]/10" : "border-white/15 text-muted-foreground"}`}
  >
    <Icon className="w-3.5 h-3.5" />
    {label}
  </button>
);

function Marketing() {
  const [content, setContent] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [gen, setGen] = useState(false);
  const [social, setSocial] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [busy, setBusy] = useState(null);
  const [schedFor, setSchedFor] = useState(null);
  const [schedWhen, setSchedWhen] = useState("");
  const [targets, setTargets] = useState({ instagram: true, facebook: true });
  const [logo, setLogo] = useState(null);
  const [logoBusy, setLogoBusy] = useState(false);
  const [imgBusy, setImgBusy] = useState(null);
  const [workflowBusy, setWorkflowBusy] = useState(null);

  const loadMarketing = async () => {
    try {
      const { data } = await api.get("/marketing/content");
      if (data.content?.content) {
        setContent(data.content.content);
        setUpdated(data.content.updated_at || null);
      } else {
        setContent(null);
        setUpdated(null);
      }
    } catch {
      setContent(null);
      setUpdated(null);
    } finally {
      setLoaded(true);
    }
  };

  const loadSocial = async () => {
    try {
      const { data } = await api.get("/social/status");
      setSocial(data);
    } catch {
      setSocial(null);
    }
  };

  const loadJobs = async () => {
    try {
      const { data } = await api.get("/social/jobs");
      setJobs(data.jobs || []);
    } catch {
      setJobs([]);
    }
  };

  const loadLogo = async () => {
    try {
      const { data } = await api.get("/social/logo");
      setLogo(data.has_logo ? data.preview : null);
    } catch {
      setLogo(null);
    }
  };

  useEffect(() => {
    loadMarketing();
    loadSocial();
    loadJobs();
    loadLogo();
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) {
      toast.success("Redes ligadas com sucesso!");
      window.history.replaceState({}, "", "/marketing");
      loadSocial();
    }
    if (params.get("social_error")) {
      toast.error(`Não foi possível ligar: ${params.get("social_error")}`);
      window.history.replaceState({}, "", "/marketing");
    }
  }, []);

  const workflow = useMemo(() => {
    if (!content?.workflow_summary) return { draft: 0, approved: 0, scheduled: 0, total: 0 };
    return content.workflow_summary;
  }, [content]);

  const setWorkflowStatus = async (postId, status) => {
    setWorkflowBusy(postId);
    try {
      const { data } = await api.post(`/marketing/posts/${postId}/status`, { status });
      setContent(data.content);
      setUpdated(data.updated_at);
      toast.success(status === "approved" ? "Conteúdo aprovado." : "Conteúdo voltou a rascunho.");
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setWorkflowBusy(null);
    }
  };

  const generate = async () => {
    setGen(true);
    try {
      const { data } = await api.post("/marketing/generate");
      setContent(data.content.content);
      setUpdated(data.content.updated_at);
      toast.success("Plano editorial gerado com contexto real do CRM, memórias e ERP.");
    } catch {
      toast.error("Não foi possível gerar agora.");
    } finally {
      setGen(false);
    }
  };

  const copyPost = (post) => {
    const txt = `${post.titulo}\n\n${post.legenda}\n\n${(post.hashtags || []).join(" ")}\n\n${post.cta || ""}`;
    navigator.clipboard.writeText(txt).then(() => toast.success("Conteúdo copiado!")).catch(() => {});
  };

  const exportAll = () => {
    if (!content) return;
    let text = "PLANO EDITORIAL — CEO AI (Diretor de Marketing)\n\n";
    if (content.brand) {
      text += `Tom da marca: ${content.brand.tom}\n`;
      text += `Pilares: ${(content.brand.pilares || []).join(", ")}\n`;
      text += `Proposta de valor: ${content.brand.proposta_valor || ""}\n\n`;
    }
    text += "=== BIBLIOTECA DE CONTEÚDOS ===\n";
    (content.biblioteca || []).forEach((item, index) => {
      text += `${index + 1}. ${item.titulo}\nÂngulo: ${item.angulo}\nObjetivo: ${item.objetivo}\nCTA: ${item.cta}\n\n`;
    });
    text += "=== POSTS ===\n\n";
    (content.posts || []).forEach((post, index) => {
      text += `${index + 1}. [${post.formato}] ${post.titulo} (${post.dia || ""})\n`;
      text += `Estado: ${post.status || "draft"}\n`;
      text += `Tema: ${post.tema || ""}\n${post.legenda}\n`;
      text += `${(post.hashtags || []).join(" ")}\nCTA: ${post.cta || ""}\n\n`;
    });
    text += "=== CALENDÁRIO 30 DIAS ===\n";
    (content.calendario || []).forEach((item) => {
      text += `${item.data || ""} · ${item.dia}: [${item.formato}] ${item.tema} · ${item.objetivo || ""}\n`;
    });
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "plano-marketing-ceo-ai.txt";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Ficheiro exportado.");
  };

  const connect = async () => {
    try {
      const { data } = await api.get("/social/connect");
      window.location.href = data.auth_url;
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const disconnect = async () => {
    await api.post("/social/disconnect");
    toast.success("Redes desligadas.");
    loadSocial();
  };

  const publishNow = async (post, index) => {
    if (!social?.connected) {
      toast.error("Ligue primeiro as suas redes.");
      return;
    }
    if (post.status !== "approved") {
      toast.error("Aprove primeiro este conteúdo antes de publicar.");
      return;
    }
    setBusy(index);
    try {
      const { data } = await api.post("/social/publish", {
        caption: captionOf(post),
        image_url: post.image_url || null,
        image_prompt: `${post.titulo}. ${content?.brand?.tom || ""}`,
        generate_image: !post.image_url,
        post_id: post.id,
        instagram: targets.instagram,
        facebook: targets.facebook,
      });
      const errors = Object.entries(data.results || {})
        .filter(([, value]) => value?.error)
        .map(([channel, value]) => `${channel}: ${value.error}`);
      if (errors.length) toast.warning(`Publicado com avisos — ${errors.join(" · ")}`);
      else toast.success("Publicado nas suas redes! 🎉");
      await loadMarketing();
      await loadJobs();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(`Falha ao publicar: ${detail?.meta_error ? JSON.stringify(detail.meta_error).slice(0, 180) : formatApiError(detail)}`);
    } finally {
      setBusy(null);
    }
  };

  const openSchedule = (post) => {
    if (post.status !== "approved") {
      toast.error("Aprove primeiro este conteúdo antes de o agendar.");
      return;
    }
    setSchedFor(post);
    const dt = new Date(Date.now() + 60 * 60 * 1000);
    dt.setMinutes(dt.getMinutes() - dt.getTimezoneOffset());
    setSchedWhen(dt.toISOString().slice(0, 16));
  };

  const confirmSchedule = async () => {
    if (!schedWhen || !schedFor) return;
    try {
      await api.post("/social/schedule", {
        caption: captionOf(schedFor),
        image_url: schedFor.image_url || null,
        image_prompt: `${schedFor.titulo}. ${content?.brand?.tom || ""}`,
        generate_image: !schedFor.image_url,
        post_id: schedFor.id,
        instagram: targets.instagram,
        facebook: targets.facebook,
        run_at: new Date(schedWhen).toISOString(),
      });
      toast.success("Publicação agendada!");
      setSchedFor(null);
      await loadMarketing();
      await loadJobs();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const cancelJob = async (id) => {
    try {
      await api.delete(`/social/jobs/${id}`);
      toast.success("Agendamento cancelado.");
      await loadJobs();
      await loadMarketing();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    }
  };

  const uploadLogo = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setLogoBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/social/logo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setLogo(data.preview);
      toast.success("Logo carregado! Será aplicado nas imagens geradas.");
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setLogoBusy(false);
      event.target.value = "";
    }
  };

  const removeLogo = async () => {
    await api.delete("/social/logo");
    setLogo(null);
    toast.success("Logo removido.");
  };

  const genImage = async (index) => {
    setImgBusy(index);
    try {
      const { data } = await api.post("/marketing/image", { index });
      setContent((current) => {
        const posts = [...(current?.posts || [])];
        posts[index] = { ...posts[index], image_url: data.image_url };
        return { ...current, posts };
      });
      toast.success("Imagem criada com o seu logo!");
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail));
    } finally {
      setImgBusy(null);
    }
  };

  const downloadImage = async (url, index) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const linkUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = linkUrl;
      a.download = `marketing-post-${index + 1}.png`;
      a.click();
      URL.revokeObjectURL(linkUrl);
      toast.success("Imagem guardada no seu dispositivo!");
    } catch {
      toast.error("Não foi possível guardar a imagem.");
    }
  };

  if (!loaded) {
    return (
      <div className="flex justify-center py-40" data-testid="marketing-loading-state">
        <Loader2 className="w-6 h-6 animate-spin text-[#A78BFA]" />
      </div>
    );
  }

  const brandBrain = content?.brand_brain || {};

  return (
    <div className="px-6 md:px-16 py-14 md:py-20 max-w-[1200px] mx-auto" data-testid="marketing-page">
      <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground mb-3">Conselho Executivo · Diretor de Marketing</p>
      <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
        <div className="space-y-2 max-w-3xl">
          <h1 className="font-serif-lux text-4xl md:text-5xl text-[#A78BFA] flex items-center gap-3" data-testid="marketing-page-title">
            <Megaphone className="w-8 h-8" />
            Conteúdos & Campanhas
          </h1>
          <p className="text-sm md:text-base text-muted-foreground" data-testid="marketing-page-subtitle">
            Agora com linha editorial baseada no CRM, nas memórias estratégicas e no contexto financeiro atual da empresa.
          </p>
          {updated && <p className="text-xs text-muted-foreground" data-testid="mkt-updated-at">Atualizado em {new Date(updated).toLocaleString("pt-PT")}</p>}
        </div>
        {content && (
          <div className="flex gap-2 flex-wrap">
            <Button data-testid="mkt-export-btn" onClick={exportAll} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
              <Download className="w-4 h-4 mr-2" />
              Exportar tudo
            </Button>
            <Button data-testid="mkt-regen-btn" onClick={generate} disabled={gen} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
              {gen ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Gerar novamente
            </Button>
          </div>
        )}
      </div>

      <div className="surface rounded-3xl p-6 md:p-7 mb-8" data-testid="mkt-social">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#A78BFA]/18 flex items-center justify-center shrink-0">
              <Share2 className="w-5 h-5 text-[#A78BFA]" />
            </div>
            <div>
              <h2 className="font-serif-lux text-xl" data-testid="mkt-social-title">Publicação automática nas redes</h2>
              {social?.connected ? (
                <p className="text-sm text-muted-foreground mt-1" data-testid="mkt-social-connected">
                  Ligado a <b className="text-foreground">{social.page_name || "Página"}</b>
                  {social.ig_username ? (
                    <>
                      {" "}· Instagram <b className="text-foreground">@{social.ig_username}</b>
                    </>
                  ) : (
                    <>
                      {" "}· <span className="text-amber-400">sem Instagram ligado</span>
                    </>
                  )}
                </p>
              ) : social?.configured ? (
                <p className="text-sm text-muted-foreground mt-1" data-testid="mkt-social-hint">
                  Ligue o Instagram/Facebook da empresa ativa para publicar e agendar diretamente a partir daqui.
                </p>
              ) : (
                <p className="text-sm text-amber-400 mt-1" data-testid="mkt-social-notconfigured">
                  A integração da Meta ainda não está configurada. Assim que colarmos o App ID/Secret, o botão de ligar fica ativo.
                </p>
              )}
              {social && !social.connected && social.configured && (
                <p className="text-[11px] text-muted-foreground mt-2" data-testid="mkt-social-redirect-uri">
                  URL de redireccionamento: <code className="text-[#A78BFA] break-all">{social.redirect_uri}</code>
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {social?.connected ? (
              <Button data-testid="mkt-disconnect-btn" onClick={disconnect} variant="outline" className="rounded-full border-white/15 hover:bg-white/5">
                <Unlink className="w-4 h-4 mr-2" />
                Desligar
              </Button>
            ) : (
              <Button data-testid="mkt-connect-btn" onClick={connect} disabled={!social?.configured} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] disabled:opacity-50">
                <Link2 className="w-4 h-4 mr-2" />
                Ligar Instagram/Facebook
              </Button>
            )}
          </div>
        </div>
        {social?.connected && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/[0.06] flex-wrap" data-testid="mkt-social-targets">
            <span className="text-xs text-muted-foreground mr-1">Publicar em:</span>
            <TargetToggle channel="instagram" Icon={Instagram} label="Instagram" enabled={targets.instagram} onToggle={() => setTargets((current) => ({ ...current, instagram: !current.instagram }))} />
            <TargetToggle channel="facebook" Icon={Facebook} label="Facebook" enabled={targets.facebook} onToggle={() => setTargets((current) => ({ ...current, facebook: !current.facebook }))} />
          </div>
        )}
      </div>

      <div className="surface rounded-3xl p-6 md:p-7 mb-8" data-testid="mkt-logo-card">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center overflow-hidden shrink-0">
              {logo ? <img src={logo} alt="Logo" className="w-full h-full object-contain p-1.5" data-testid="mkt-logo-preview" /> : <ImageIcon className="w-6 h-6 text-muted-foreground" />}
            </div>
            <div>
              <h2 className="font-serif-lux text-xl" data-testid="mkt-logo-title">Logo da empresa</h2>
              <p className="text-sm text-muted-foreground mt-1 max-w-md" data-testid="mkt-logo-description">
                {logo ? "O seu logo será sobreposto automaticamente em todas as imagens geradas." : "Carregue o seu logo para aparecer nas imagens geradas e nas publicações sociais."}
              </p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <label data-testid="mkt-logo-upload" className="cursor-pointer inline-flex items-center gap-2 text-sm px-4 h-10 rounded-full border border-white/15 hover:bg-white/5 transition-colors">
              {logoBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} {logo ? "Alterar" : "Carregar logo"}
              <input type="file" accept="image/*" className="hidden" onChange={uploadLogo} disabled={logoBusy} />
            </label>
            {logo && (
              <Button data-testid="mkt-logo-remove" onClick={removeLogo} variant="outline" className="rounded-full border-white/15 hover:bg-white/5 h-10">
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {!content ? (
        <div className="surface rounded-3xl p-8 md:p-12 text-center" data-testid="mkt-intro">
          <div className="w-14 h-14 rounded-2xl bg-[#A78BFA]/18 flex items-center justify-center mx-auto mb-6">
            <Megaphone className="w-7 h-7 text-[#A78BFA]" />
          </div>
          <h2 className="font-serif-lux text-2xl mb-2" data-testid="mkt-intro-title">O Diretor de Marketing está pronto</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto mb-8" data-testid="mkt-intro-description">
            Vou cruzar identidade da marca, CRM, memórias estratégicas e contexto ERP para criar campanhas, posts e um calendário editorial de 30 dias pronto a aprovar.
          </p>
          <Button data-testid="mkt-generate-btn" onClick={generate} disabled={gen} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA] px-8 h-12 text-base">
            {gen ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> A criar conteúdos…</> : <><Play className="w-5 h-5 mr-2" /> Gerar conteúdos</>}
          </Button>
        </div>
      ) : (
        <>
          <div className="grid md:grid-cols-3 gap-4 mb-8" data-testid="mkt-workflow-summary">
            {[
              { key: "draft", label: "Rascunhos", value: workflow.draft, icon: ShieldCheck },
              { key: "approved", label: "Aprovados", value: workflow.approved, icon: BadgeCheck },
              { key: "scheduled", label: "Agendados", value: workflow.scheduled, icon: Clock },
            ].map(({ key, label, value, icon: Icon }) => (
              <div key={key} className="surface rounded-3xl p-5" data-testid={`mkt-workflow-${key}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
                    <p className="text-3xl font-semibold mt-3" data-testid={`mkt-workflow-${key}-value`}>{value || 0}</p>
                  </div>
                  <div className="w-11 h-11 rounded-2xl bg-white/5 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-[#A78BFA]" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {content.brand && (
            <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-5 mb-8">
              <div className="surface rounded-3xl p-6 md:p-8" data-testid="mkt-brand">
                <h2 className="font-serif-lux text-xl mb-2 flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#A78BFA]" /> Identidade da marca</h2>
                <p className="text-muted-foreground mb-4" data-testid="mkt-brand-tone">{content.brand.tom}</p>
                <div className="space-y-5">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Pilares</p>
                    <PillList items={content.brand.pilares || []} testIdPrefix="mkt-brand-pillar" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Proposta de valor</p>
                    <p className="text-sm text-foreground" data-testid="mkt-brand-value-proposition">{content.brand.proposta_valor}</p>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div data-testid="mkt-brand-audiences">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Audiências</p>
                      <PillList items={content.brand.audiencias || []} color="#3B82F6" testIdPrefix="mkt-brand-audience" />
                    </div>
                    <div data-testid="mkt-brand-proof">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Provas</p>
                      <PillList items={content.brand.provas || []} color="#10B981" testIdPrefix="mkt-brand-proof-item" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="surface rounded-3xl p-6 md:p-8" data-testid="mkt-brand-brain">
                <h2 className="font-serif-lux text-xl mb-2 flex items-center gap-2"><BrainCircuit className="w-5 h-5 text-[#3B82F6]" /> Brand Brain</h2>
                <p className="text-sm text-muted-foreground mb-5" data-testid="mkt-brand-brain-positioning">{brandBrain.positioning || "Sem posicionamento disponível."}</p>
                <div className="grid grid-cols-2 gap-3 mb-5" data-testid="mkt-brand-brain-sources">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <p className="text-xs text-muted-foreground">Memórias usadas</p>
                    <p className="text-xl font-semibold" data-testid="mkt-brand-brain-memories">{brandBrain.context_sources?.memories || 0}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                    <p className="text-xs text-muted-foreground">Leads no radar</p>
                    <p className="text-xl font-semibold" data-testid="mkt-brand-brain-leads">{brandBrain.context_sources?.crm_leads || 0}</p>
                  </div>
                </div>
                <div className="space-y-4">
                  <div data-testid="mkt-brand-brain-priorities">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Prioridades editoriais</p>
                    <ul className="space-y-2 text-sm text-foreground">
                      {(brandBrain.prioridades || []).map((item, index) => <li key={index} data-testid={`mkt-brand-brain-priority-${index}`}>• {item}</li>)}
                    </ul>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div data-testid="mkt-brand-brain-do-say">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Dizer sempre</p>
                      <PillList items={content.brand.do_say || []} color="#10B981" testIdPrefix="mkt-brand-dosay" />
                    </div>
                    <div data-testid="mkt-brand-brain-avoid">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Evitar</p>
                      <PillList items={content.brand.avoid || []} color="#F59E0B" testIdPrefix="mkt-brand-avoid" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {content.biblioteca?.length > 0 && (
            <div className="surface rounded-3xl p-6 md:p-8 mb-8" data-testid="mkt-library">
              <div className="flex items-end justify-between gap-4 flex-wrap mb-5">
                <div>
                  <h2 className="font-serif-lux text-xl flex items-center gap-2"><Library className="w-5 h-5 text-[#3B82F6]" /> Biblioteca de conteúdos</h2>
                  <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-library-description">Ângulos reutilizáveis para manter consistência editorial durante os próximos 30 dias.</p>
                </div>
                <div className="text-xs text-muted-foreground" data-testid="mkt-library-count">{content.biblioteca.length} ângulos ativos</div>
              </div>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                {content.biblioteca.map((item, index) => (
                  <div key={item.id || index} className="rounded-3xl border border-white/10 bg-white/[0.03] p-5" data-testid={`mkt-library-${index}`}>
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <p className="font-medium text-base" data-testid={`mkt-library-title-${index}`}>{item.titulo}</p>
                      <Target className="w-4 h-4 text-[#A78BFA] shrink-0" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-4" data-testid={`mkt-library-angle-${index}`}>{item.angulo}</p>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <p data-testid={`mkt-library-objective-${index}`}><span className="text-foreground">Objetivo:</span> {item.objetivo}</p>
                      <p data-testid={`mkt-library-pillar-${index}`}><span className="text-foreground">Pilar:</span> {item.pilar}</p>
                      <p data-testid={`mkt-library-formats-${index}`}><span className="text-foreground">Formatos:</span> {(item.formatos || []).join(", ")}</p>
                      <p data-testid={`mkt-library-cta-${index}`}><span className="text-foreground">CTA:</span> {item.cta}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {jobs.length > 0 && (
            <div className="surface rounded-3xl p-6 mb-8" data-testid="mkt-jobs">
              <h2 className="font-serif-lux text-lg mb-4 flex items-center gap-2"><Clock className="w-4 h-4 text-[#A78BFA]" /> Publicações agendadas</h2>
              <div className="space-y-2">
                {jobs.map((job) => (
                  <div key={job.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex-wrap" data-testid={`mkt-job-${job.id}`}>
                    {job.status === "published" ? <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" /> : job.status === "failed" ? <XCircle className="w-4 h-4 text-red-400 shrink-0" /> : <Clock className="w-4 h-4 text-amber-400 shrink-0" />}
                    <span className="text-xs text-muted-foreground w-44 shrink-0" data-testid={`mkt-job-date-${job.id}`}>{new Date(job.run_at).toLocaleString("pt-PT")}</span>
                    <span className="text-sm flex-1 truncate" data-testid={`mkt-job-caption-${job.id}`}>{job.caption}</span>
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground" data-testid={`mkt-job-status-${job.id}`}>{job.status}</span>
                    {job.status === "queued" && (
                      <button onClick={() => cancelJob(job.id)} className="text-xs text-red-400 hover:underline" data-testid={`mkt-job-cancel-${job.id}`}>
                        cancelar
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-end justify-between flex-wrap gap-4 mb-4">
            <div>
              <h2 className="font-serif-lux text-2xl" data-testid="mkt-posts-title">Conteúdos prontos a aprovar</h2>
              <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-posts-description">Aprovar → publicar/agendar. Cada peça já nasce ligada ao plano editorial de 30 dias.</p>
            </div>
            <WorkflowBadge status="approved" testId="mkt-workflow-hint" />
          </div>

          <div className="grid md:grid-cols-2 gap-5 mb-10" data-testid="mkt-posts">
            {(content.posts || []).map((post, index) => (
              <motion.div key={post.id || index} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }} className="surface rounded-3xl p-6 flex flex-col" data-testid={`mkt-post-${index}`}>
                {post.image_url ? (
                  <img src={post.image_url} alt={post.titulo} className="w-full aspect-square object-cover rounded-2xl mb-4" data-testid={`mkt-img-${index}`} />
                ) : (
                  <button
                    onClick={() => genImage(index)}
                    disabled={imgBusy === index}
                    data-testid={`mkt-genimg-${index}`}
                    className="w-full aspect-square rounded-2xl border border-dashed border-white/15 flex flex-col items-center justify-center gap-2 mb-4 hover:bg-white/[0.03] transition-colors disabled:opacity-60"
                  >
                    {imgBusy === index ? (
                      <>
                        <Loader2 className="w-6 h-6 animate-spin text-[#A78BFA]" />
                        <span className="text-xs text-muted-foreground">A criar imagem (~30s)…</span>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="w-6 h-6 text-[#A78BFA]" />
                        <span className="text-xs text-muted-foreground">Gerar imagem (com o seu logo)</span>
                      </>
                    )}
                  </button>
                )}

                <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="text-[10px] uppercase tracking-wider px-2.5 py-1 rounded-full"
                      style={{ color: FORMAT_COLOR[post.formato] || "#94a3b8", background: `${FORMAT_COLOR[post.formato] || "#94a3b8"}18` }}
                      data-testid={`mkt-post-format-${index}`}
                    >
                      {post.formato}
                    </span>
                    <WorkflowBadge status={post.status} testId={`mkt-post-status-${index}`} />
                  </div>
                  {post.dia && <span className="text-xs text-muted-foreground" data-testid={`mkt-post-day-${index}`}>{post.dia}</span>}
                </div>

                <div className="space-y-3 flex-1">
                  <div className="font-medium text-lg" data-testid={`mkt-post-title-${index}`}>{post.titulo}</div>
                  <div className="flex gap-2 flex-wrap text-xs text-muted-foreground">
                    <span className="px-2.5 py-1 rounded-full border border-white/10" data-testid={`mkt-post-theme-${index}`}>Tema: {post.tema}</span>
                    <span className="px-2.5 py-1 rounded-full border border-white/10" data-testid={`mkt-post-goal-${index}`}>Objetivo: {post.objetivo}</span>
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap" data-testid={`mkt-post-caption-${index}`}>{post.legenda}</p>
                  {post.hashtags?.length > 0 && (
                    <div className="text-xs text-[#3B82F6] flex items-start gap-1" data-testid={`mkt-post-hashtags-${index}`}>
                      <Hash className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>{post.hashtags.join(" ")}</span>
                    </div>
                  )}
                  {post.cta && <div className="text-sm font-medium text-[#10B981]" data-testid={`mkt-post-cta-${index}`}>{post.cta}</div>}
                  {post.scheduled_at && <p className="text-xs text-amber-300" data-testid={`mkt-post-scheduled-at-${index}`}>Agendado para {new Date(post.scheduled_at).toLocaleString("pt-PT")}</p>}
                </div>

                <div className="flex flex-wrap gap-2 mt-6">
                  <Button data-testid={`mkt-copy-${index}`} onClick={() => copyPost(post)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5">
                    <Copy className="w-3.5 h-3.5 mr-1.5" />
                    Copiar texto
                  </Button>

                  {post.status === "draft" ? (
                    <Button
                      data-testid={`mkt-approve-${index}`}
                      onClick={() => setWorkflowStatus(post.id, "approved")}
                      disabled={workflowBusy === post.id}
                      size="sm"
                      className="rounded-full bg-emerald-500 text-white hover:bg-emerald-600"
                    >
                      {workflowBusy === post.id ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <BadgeCheck className="w-3.5 h-3.5 mr-1.5" />}
                      Aprovar
                    </Button>
                  ) : post.status === "approved" ? (
                    <Button
                      data-testid={`mkt-reset-${index}`}
                      onClick={() => setWorkflowStatus(post.id, "draft")}
                      disabled={workflowBusy === post.id}
                      variant="outline"
                      size="sm"
                      className="rounded-full border-white/15 hover:bg-white/5"
                    >
                      {workflowBusy === post.id ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />}
                      Voltar a rascunho
                    </Button>
                  ) : (
                    <span className="text-xs text-amber-300 px-3 py-2 rounded-full border border-amber-400/20 bg-amber-500/10" data-testid={`mkt-scheduled-hint-${index}`}>
                      Para retirar do calendário, cancele o agendamento abaixo.
                    </span>
                  )}

                  {post.image_url && (
                    <Button data-testid={`mkt-download-${index}`} onClick={() => downloadImage(post.image_url, index)} size="sm" className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]">
                      <Download className="w-3.5 h-3.5 mr-1.5" />
                      Guardar imagem
                    </Button>
                  )}

                  {social?.connected && post.status === "approved" && (
                    <>
                      <Button data-testid={`mkt-publish-${index}`} onClick={() => publishNow(post, index)} disabled={busy === index} size="sm" className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">
                        {busy === index ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Send className="w-3.5 h-3.5 mr-1.5" />}
                        Publicar
                      </Button>
                      <Button data-testid={`mkt-schedule-${index}`} onClick={() => openSchedule(post)} variant="outline" size="sm" className="rounded-full border-white/15 hover:bg-white/5">
                        <Clock className="w-3.5 h-3.5 mr-1.5" />
                        Agendar
                      </Button>
                    </>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {content.calendario?.length > 0 && (
            <div className="surface rounded-3xl p-6 md:p-8" data-testid="mkt-calendar">
              <div className="flex items-end justify-between gap-4 flex-wrap mb-4">
                <div>
                  <h2 className="font-serif-lux text-xl flex items-center gap-2"><Calendar className="w-5 h-5 text-[#A78BFA]" /> Calendário editorial 30 dias</h2>
                  <p className="text-sm text-muted-foreground mt-2" data-testid="mkt-calendar-description">Planeamento operacional com ligação direta aos conteúdos aprovados.</p>
                </div>
                <div className="text-xs text-muted-foreground" data-testid="mkt-calendar-count">{content.calendario.length} entradas</div>
              </div>
              <div className="grid lg:grid-cols-2 gap-3">
                {content.calendario.map((item, index) => (
                  <div key={`${item.data}-${index}`} className="flex items-start gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06]" data-testid={`mkt-calendar-item-${index}`}>
                    <div className="w-28 shrink-0">
                      <p className="text-sm font-medium capitalize" data-testid={`mkt-calendar-day-${index}`}>{item.dia}</p>
                      <p className="text-xs text-muted-foreground" data-testid={`mkt-calendar-date-${index}`}>{item.data}</p>
                    </div>
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0" style={{ color: FORMAT_COLOR[item.formato] || "#94a3b8", background: `${FORMAT_COLOR[item.formato] || "#94a3b8"}18` }} data-testid={`mkt-calendar-format-${index}`}>{item.formato}</span>
                        <WorkflowBadge status={item.status || "draft"} testId={`mkt-calendar-status-${index}`} />
                      </div>
                      <p className="text-sm text-foreground" data-testid={`mkt-calendar-theme-${index}`}>{item.tema}</p>
                      <p className="text-xs text-muted-foreground" data-testid={`mkt-calendar-goal-${index}`}>{item.objetivo}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground mt-8" data-testid="mkt-footer-note">
            Fluxo recomendado: <b>aprovar</b> → <b>agendar/publicar</b>. Sem ligação às redes, use <b>Gerar imagem</b> → <b>Guardar imagem</b> e <b>Copiar texto</b> para publicação manual.
          </p>
        </>
      )}

      <Dialog open={!!schedFor} onOpenChange={(open) => !open && setSchedFor(null)}>
        <DialogContent data-testid="mkt-schedule-dialog">
          <DialogHeader>
            <DialogTitle>Agendar publicação</DialogTitle>
            <DialogDescription>
              Escolha a data e hora. A publicação será enviada automaticamente às redes selecionadas da empresa ativa.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs text-muted-foreground" data-testid="mkt-schedule-label">Data e hora</label>
            <Input type="datetime-local" data-testid="mkt-schedule-when" value={schedWhen} onChange={(event) => setSchedWhen(event.target.value)} className="mt-1" />
            <div className="flex gap-2 mt-4 flex-wrap" data-testid="mkt-schedule-targets">
              <TargetToggle channel="instagram" Icon={Instagram} label="Instagram" enabled={targets.instagram} onToggle={() => setTargets((current) => ({ ...current, instagram: !current.instagram }))} />
              <TargetToggle channel="facebook" Icon={Facebook} label="Facebook" enabled={targets.facebook} onToggle={() => setTargets((current) => ({ ...current, facebook: !current.facebook }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSchedFor(null)} className="rounded-full" data-testid="mkt-schedule-cancel">Cancelar</Button>
            <Button data-testid="mkt-schedule-confirm" onClick={confirmSchedule} className="rounded-full bg-[#A78BFA] text-white hover:bg-[#9333EA]">Agendar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default Marketing;