import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { VoiceSphere } from "@/components/VoiceSphere";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchPublicSections } from "@/lib/publicSite";
import { applyPublicSeo } from "@/lib/seo";
import { trackPublicSurface } from "@/lib/publicSite";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

const DEFAULT_PUBLIC_COPY = {
  headline: "O CEO que trabalha 24 horas pela sua empresa",
  subtitle: "Não é um ERP nem um software de gestão. É o seu Diretor Executivo Digital — analisa a empresa consigo e decide, lado a lado, o que fazer hoje.",
  primaryCtaLabel: "Entrar no painel",
  primaryCtaUrl: "#login-auth-panel",
  secondaryCtaLabel: "Ver planos",
  secondaryCtaUrl: "/planos",
  socialProofTitle: "Porque líderes usam o CEO AI",
  socialProofItems: [
    "Clareza executiva sem ruído",
    "CRM, finanças e marketing no mesmo cockpit",
    "Próximo passo sempre visível",
  ],
};

export default function Login() {
  const { login, register, googleSession, user } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [publicCopy, setPublicCopy] = useState(DEFAULT_PUBLIC_COPY);

  const routeAfter = async () => {
    try {
      const { data } = await api.get("/dna");
      navigate(data?.completed ? "/" : "/onboarding");
    } catch {
      navigate("/onboarding");
    }
  };

  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes("session_id=")) {
      const sid = new URLSearchParams(hash.replace("#", "")).get("session_id");
      if (sid) {
        setLoading(true);
        googleSession(sid)
          .then(() => {
            window.history.replaceState(null, "", window.location.pathname);
            routeAfter();
          })
          .catch(() => { setLoading(false); toast.error("Falha no login Google"); });
      }
    }
  }, []);

  useEffect(() => {
    if (user) routeAfter();
  }, [user]);

  useEffect(() => {
    applyPublicSeo({
      title: "CEO AI | Login",
      description: publicCopy.subtitle,
      canonicalPath: "/login",
    });
    trackPublicSurface("login", "/login", "Login / Landing").catch(() => {});
  }, [publicCopy.subtitle]);

  useEffect(() => {
    fetchPublicSections([
      "login.hero_headline",
      "login.hero_subtitle",
      "login.hero_primary_cta_label",
      "login.hero_primary_cta_url",
      "login.hero_secondary_cta_label",
      "login.hero_secondary_cta_url",
      "login.social_proof_title",
      "login.social_proof_1",
      "login.social_proof_2",
      "login.social_proof_3",
    ])
      .then((sections) => {
        setPublicCopy((current) => ({
          headline: sections["login.hero_headline"]?.value || current.headline,
          subtitle: sections["login.hero_subtitle"]?.value || current.subtitle,
          primaryCtaLabel: sections["login.hero_primary_cta_label"]?.value || current.primaryCtaLabel,
          primaryCtaUrl: sections["login.hero_primary_cta_url"]?.value || current.primaryCtaUrl,
          secondaryCtaLabel: sections["login.hero_secondary_cta_label"]?.value || current.secondaryCtaLabel,
          secondaryCtaUrl: sections["login.hero_secondary_cta_url"]?.value || current.secondaryCtaUrl,
          socialProofTitle: sections["login.social_proof_title"]?.value || current.socialProofTitle,
          socialProofItems: [
            sections["login.social_proof_1"]?.value || current.socialProofItems[0],
            sections["login.social_proof_2"]?.value || current.socialProofItems[1],
            sections["login.social_proof_3"]?.value || current.socialProofItems[2],
          ],
        }));
      })
      .catch(() => {});
  }, []);

  const openHeroLink = (href) => {
    const target = href || "#login-auth-panel";
    if (target.startsWith("#")) {
      const node = document.querySelector(target);
      if (node) node.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    window.location.href = target;
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form.name, form.email, form.password);
      await routeAfter();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Erro");
      setLoading(false);
    }
  };

  const googleLogin = () => {
    const redirect = `${window.location.origin}/login`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 text-foreground relative z-10 overflow-hidden"
      style={{ background: "radial-gradient(70% 90% at 25% 20%, rgba(59,130,246,0.14), transparent 60%), radial-gradient(60% 80% at 90% 90%, rgba(30,58,138,0.18), transparent 60%), #05050A" }}>
      {/* Left: brand */}
      <div className="hidden lg:flex flex-col justify-center items-center p-16 relative overflow-hidden">
        <div className="absolute inset-0 opacity-[0.08]" style={{ background: "url('https://images.unsplash.com/photo-1747673002516-f11a48cb0ce2?crop=entropy&cs=srgb&fm=jpg&q=85') center/cover" }} />
        <div className="relative flex items-center justify-center" style={{ width: 340, height: 340 }}>
          <div className="absolute inset-10 rounded-full" style={{ background: "radial-gradient(circle, rgba(59,130,246,0.4), transparent 70%)", filter: "blur(36px)" }} />
          <img src="/android_cut.png" alt="CEO AI" className="relative w-full h-full object-contain" style={{ filter: "drop-shadow(0 0 26px rgba(59,130,246,0.5))" }} />
        </div>
        <h1 className="font-serif-lux text-5xl mt-12 text-center leading-tight tracking-tight" data-testid="login-public-headline">
          {publicCopy.headline}
        </h1>
        <p className="text-muted-foreground mt-6 max-w-md text-center" data-testid="login-public-subtitle">
          {publicCopy.subtitle}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 mt-6" data-testid="login-public-ctas">
          <button onClick={() => openHeroLink(publicCopy.primaryCtaUrl)} className="rounded-full bg-[#3B82F6] px-5 py-3 text-sm font-medium text-white hover:bg-[#2563EB] transition-colors" data-testid="login-public-primary-cta">
            {publicCopy.primaryCtaLabel}
          </button>
          <button onClick={() => openHeroLink(publicCopy.secondaryCtaUrl)} className="rounded-full border border-white/12 px-5 py-3 text-sm text-slate-200 hover:bg-white/[0.04] transition-colors" data-testid="login-public-secondary-cta">
            {publicCopy.secondaryCtaLabel}
          </button>
        </div>
        <div className="mt-8 w-full max-w-xl rounded-[24px] border border-white/10 bg-white/[0.04] p-5" data-testid="login-social-proof-block">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400" data-testid="login-social-proof-title">{publicCopy.socialProofTitle}</p>
          <div className="grid grid-cols-3 gap-3 mt-4" data-testid="login-social-proof-items">
            {publicCopy.socialProofItems.map((item, index) => (
              <div key={`${item}-${index}`} className="rounded-[18px] border border-white/10 bg-black/10 p-3 text-sm text-slate-200" data-testid={`login-social-proof-item-${index}`}>
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-8">
        <motion.div id="login-auth-panel" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm" data-testid="login-auth-panel">
          <div className="lg:hidden flex justify-center mb-8">
            <div className="relative flex items-center justify-center" style={{ width: 150, height: 150 }}>
              <div className="absolute inset-6 rounded-full" style={{ background: "radial-gradient(circle, rgba(59,130,246,0.4), transparent 70%)", filter: "blur(18px)" }} />
              <img src="/android_cut.png" alt="CEO AI" className="relative w-full h-full object-contain" style={{ filter: "drop-shadow(0 0 20px rgba(59,130,246,0.5))" }} />
            </div>
          </div>
          <div className="lg:hidden rounded-[22px] border border-white/10 bg-white/[0.03] p-4 mb-6" data-testid="login-mobile-public-copy">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Homepage</p>
            <h1 className="font-serif-lux text-[28px] leading-tight mt-3" data-testid="login-mobile-public-headline">{publicCopy.headline}</h1>
            <p className="text-sm text-muted-foreground mt-3" data-testid="login-mobile-public-subtitle">{publicCopy.subtitle}</p>
            <div className="flex flex-wrap gap-2 mt-4" data-testid="login-mobile-public-ctas">
              <button onClick={() => openHeroLink(publicCopy.primaryCtaUrl)} className="rounded-full bg-[#3B82F6] px-4 py-2.5 text-sm font-medium text-white" data-testid="login-mobile-public-primary-cta">
                {publicCopy.primaryCtaLabel}
              </button>
              <button onClick={() => openHeroLink(publicCopy.secondaryCtaUrl)} className="rounded-full border border-white/12 px-4 py-2.5 text-sm text-slate-200" data-testid="login-mobile-public-secondary-cta">
                {publicCopy.secondaryCtaLabel}
              </button>
            </div>
            <div className="grid gap-2 mt-4" data-testid="login-mobile-social-proof-items">
              {publicCopy.socialProofItems.map((item, index) => (
                <div key={`${item}-mobile-${index}`} className="rounded-[16px] border border-white/10 bg-black/10 p-3 text-sm text-slate-200" data-testid={`login-mobile-social-proof-item-${index}`}>
                  {item}
                </div>
              ))}
            </div>
          </div>
          <h2 className="font-serif-lux text-4xl mb-2">{mode === "login" ? "Bem-vindo de volta" : "Comece agora"}</h2>
          <p className="text-muted-foreground text-sm mb-8">
            {mode === "login" ? "Entre para falar com o seu CEO AI." : "Crie a sua conta e conheça o seu Diretor Executivo Digital."}
          </p>

          <button onClick={googleLogin} data-testid="google-login-btn" disabled={loading}
            className="w-full flex items-center justify-center gap-3 py-3 rounded-full border border-border hover:bg-accent transition-colors mb-5 text-sm font-medium">
            <img src="https://www.google.com/favicon.ico" alt="" className="w-4 h-4" />
            Continuar com Google
          </button>

          <div className="flex items-center gap-3 mb-5">
            <div className="h-px flex-1 bg-border" /><span className="text-xs text-muted-foreground">ou</span><div className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label className="text-xs text-muted-foreground">Nome</Label>
                <Input data-testid="name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="mt-1 bg-transparent" placeholder="O seu nome" />
              </div>
            )}
            <div>
              <Label className="text-xs text-muted-foreground">Email</Label>
              <Input data-testid="email-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className="mt-1 bg-transparent" placeholder="voce@empresa.com" />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Palavra-passe</Label>
              <Input data-testid="password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required className="mt-1 bg-transparent" placeholder="••••••••" />
            </div>
            <Button data-testid="submit-btn" type="submit" disabled={loading}
              className="w-full rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] hover:-translate-y-0.5 transition-transform font-medium py-6">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : mode === "login" ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            {mode === "login" ? "Ainda não tem conta?" : "Já tem conta?"}{" "}
            <button data-testid="toggle-mode-btn" onClick={() => setMode(mode === "login" ? "register" : "login")} className="text-[#3B82F6] hover:underline">
              {mode === "login" ? "Criar conta" : "Entrar"}
            </button>
          </p>
          <div className="flex items-center justify-center gap-4 mt-8 text-xs text-muted-foreground">
            <a href="/termos" data-testid="footer-terms" className="hover:text-[#3B82F6] transition-colors">Termos</a>
            <span>·</span>
            <a href="/privacidade" data-testid="footer-privacy" className="hover:text-[#3B82F6] transition-colors">Privacidade</a>
            <span>·</span>
            <a href="/contacto" data-testid="footer-contact" className="hover:text-[#3B82F6] transition-colors">Contacto</a>
            <span>·</span>
            <a href="/insights" data-testid="footer-insights" className="hover:text-[#3B82F6] transition-colors">Insights</a>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
