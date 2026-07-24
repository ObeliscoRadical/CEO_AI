import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { VoiceSphere } from "@/components/VoiceSphere";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

export default function Login() {
  const { login, register, googleSession, user } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);

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
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (user) routeAfter();
    // eslint-disable-next-line
  }, [user]);

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
    <div className="min-h-screen grid lg:grid-cols-2 bg-background text-foreground relative z-10">
      {/* Left: brand */}
      <div className="hidden lg:flex flex-col justify-center items-center p-16 relative overflow-hidden border-r border-border">
        <div className="absolute inset-0 opacity-[0.12]" style={{ background: "url('https://images.unsplash.com/photo-1747673002516-f11a48cb0ce2?crop=entropy&cs=srgb&fm=jpg&q=85') center/cover" }} />
        <VoiceSphere size={220} ripple />
        <h1 className="font-serif-lux text-5xl mt-12 text-center leading-tight tracking-tight">
          O CEO que trabalha<br />24 horas pela sua empresa
        </h1>
        <p className="text-muted-foreground mt-6 max-w-md text-center">
          Não é um ERP nem um software de gestão. É o seu Diretor Executivo Digital — analisa a empresa consigo e decide, lado a lado, o que fazer hoje.
        </p>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
          <div className="lg:hidden flex justify-center mb-8"><VoiceSphere size={120} ripple /></div>
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
              className="w-full rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431] hover:-translate-y-0.5 transition-transform font-medium py-6">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : mode === "login" ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            {mode === "login" ? "Ainda não tem conta?" : "Já tem conta?"}{" "}
            <button data-testid="toggle-mode-btn" onClick={() => setMode(mode === "login" ? "register" : "login")} className="text-[#D4AF37] hover:underline">
              {mode === "login" ? "Criar conta" : "Entrar"}
            </button>
          </p>
          <div className="flex items-center justify-center gap-4 mt-8 text-xs text-muted-foreground">
            <a href="/termos" data-testid="footer-terms" className="hover:text-[#D4AF37] transition-colors">Termos</a>
            <span>·</span>
            <a href="/privacidade" data-testid="footer-privacy" className="hover:text-[#D4AF37] transition-colors">Privacidade</a>
            <span>·</span>
            <a href="/contacto" data-testid="footer-contact" className="hover:text-[#D4AF37] transition-colors">Contacto</a>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
