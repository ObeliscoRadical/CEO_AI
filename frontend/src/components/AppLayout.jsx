import { useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { Home, Lightbulb, HeartPulse, Coins, MessageSquare, Wallet, TrendingUp, FileText, Settings as SettingsIcon, LogOut, Building2, Plus, Crown, Check, Menu, Compass, Lock, Shield, X } from "lucide-react";
import { motion } from "framer-motion";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CEOTour } from "@/components/CEOTour";
import { toast } from "sonner";

const NAV = [
  { to: "/", label: "Painel do CEO", icon: Home, end: true, testid: "nav-painel" },
  { to: "/conselhos", label: "Conselhos", icon: Lightbulb, testid: "nav-conselhos", gated: true },
  { to: "/saude", label: "Saúde Empresarial", icon: HeartPulse, testid: "nav-saude", gated: true },
  { to: "/valor", label: "Valor da Empresa", icon: Coins, testid: "nav-valor", gated: true },
  { to: "/futuro", label: "Futuro", icon: TrendingUp, testid: "nav-futuro", premium: true, gated: true },
  { to: "/ceo", label: "Conversar com o CEO", icon: MessageSquare, testid: "nav-ceo", gated: true },
  { to: "/financas", label: "Finanças", icon: Wallet, testid: "nav-financas" },
  { to: "/relatorios", label: "Relatórios", icon: FileText, testid: "nav-relatorios", gated: true },
  { to: "/definicoes", label: "Empresa", icon: SettingsIcon, testid: "nav-empresa" },
];

const Logo = ({ size = 40 }) => {
  const bars = [0.45, 0.8, 1, 0.65, 0.35];
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }} aria-hidden="true">
      <div className="absolute inset-0 rounded-xl" style={{ background: "radial-gradient(circle at 50% 60%, rgba(59,130,246,0.45), transparent 70%)", filter: "blur(6px)" }} />
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className="relative">
        <defs>
          <linearGradient id="eq-grad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0" stopColor="#1D4ED8" /><stop offset="0.6" stopColor="#3B82F6" /><stop offset="1" stopColor="#93C5FD" />
          </linearGradient>
        </defs>
        {bars.map((h, i) => (
          <motion.rect
            key={i}
            x={7 + i * 8} width="4.5" rx="2.25"
            fill="url(#eq-grad)"
            initial={{ height: 8 * h, y: 24 - 4 * h }}
            animate={{ height: [8 * h, 30 * h, 12 * h, 26 * h, 8 * h], y: [24 - 4 * h, 24 - 15 * h, 24 - 6 * h, 24 - 13 * h, 24 - 4 * h] }}
            transition={{ duration: 1.6 + i * 0.2, repeat: Infinity, ease: "easeInOut", delay: i * 0.12 }}
          />
        ))}
      </svg>
    </div>
  );
};

export function AppLayout() {
  const { user, logout } = useAuth();
  const { companies, activeCompanyId, isPremium, isAdmin, switchCompany, createCompany } = useAppData();
  const navigate = useNavigate();
  const location = useLocation();
  const [newOpen, setNewOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [form, setForm] = useState({ name: "", region: "PT", currency: "EUR", sector: "" });

  const doLogout = async () => { await logout(); navigate("/login"); };
  const active = companies.find((c) => c.id === activeCompanyId);

  const addCompany = async (e) => {
    e.preventDefault();
    await createCompany(form);
    setNewOpen(false);
    setForm({ name: "", region: "PT", currency: "EUR", sector: "" });
    toast.success("Empresa criada e ativada");
    navigate("/");
  };

  const go = (to) => { navigate(to); setMobileOpen(false); };
  const isActive = (n) => (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to));

  // ---- Desktop icon rail ----
  const RailItem = ({ n }) => {
    const locked = n.gated && !isPremium && !isAdmin;
    const activeItem = isActive(n);
    return (
      <button
        data-testid={n.testid}
        title={n.label}
        onClick={() => go(locked ? "/planos" : n.to)}
        className={`relative w-12 h-12 rounded-xl flex items-center justify-center mb-1 transition-colors duration-300 group ${
          activeItem ? "text-blue-400 bg-blue-500/10" : "text-slate-500 hover:text-blue-400 hover:bg-blue-500/10"
        }`}
      >
        {activeItem && <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-blue-500" />}
        <n.icon className="w-[20px] h-[20px]" />
        {locked && <Lock className="w-3 h-3 absolute top-1.5 right-1.5 text-blue-400/80" />}
        {(n.premium && !isPremium && !isAdmin) && !locked && <Crown className="w-3 h-3 absolute top-1.5 right-1.5 text-blue-400/80" />}
        <span className="pointer-events-none absolute left-16 px-2.5 py-1.5 rounded-lg bg-[#0b0c14] border border-white/10 text-xs text-white whitespace-nowrap opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 z-50 shadow-xl">{n.label}</span>
      </button>
    );
  };

  const DesktopRail = (
    <aside className="hidden md:flex w-20 h-screen fixed left-0 top-0 flex-col items-center py-6 border-r border-white/[0.08] bg-[#05050A]/90 backdrop-blur-xl z-40">
      <div className="flex flex-col items-center gap-1.5 mb-10">
        <Logo />
        <span className="text-[9px] font-bold tracking-[0.2em] text-white/70 uppercase">CEO AI</span>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button data-testid="company-selector" title={active?.name || "Empresa"}
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors">
            <Building2 className="w-[18px] h-[18px]" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-[220px]" align="start" side="right">
          {companies.map((c) => (
            <DropdownMenuItem key={c.id} data-testid={`company-option-${c.id}`} onClick={() => switchCompany(c.id).then(() => navigate("/"))} className="cursor-pointer">
              <Check className={`w-4 h-4 mr-2 ${c.id === activeCompanyId ? "opacity-100 text-blue-400" : "opacity-0"}`} />
              <span className="truncate">{c.name}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuItem data-testid="add-company-trigger" onClick={() => setNewOpen(true)} className="cursor-pointer text-blue-400">
            <Plus className="w-4 h-4 mr-2" /> Nova empresa
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <nav className="flex-1 flex flex-col items-center overflow-y-auto no-scrollbar">
        {NAV.map((n) => <RailItem key={n.to} n={n} />)}
        {isAdmin && <RailItem n={{ to: "/admin", label: "Administração", icon: Shield, testid: "nav-admin" }} />}
      </nav>

      <div className="flex flex-col items-center gap-1 mt-4 pt-4 border-t border-white/[0.08] w-12">
        <button data-testid="restart-tour-btn" title="Tour guiado" onClick={() => window.dispatchEvent(new Event("start-ceo-tour"))} className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 transition-colors"><Compass className="w-[18px] h-[18px]" /></button>
        <button data-testid="nav-subscricao" title={isPremium ? "Subscrição" : "Passar a Premium"} onClick={() => go("/subscricao")} className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${isPremium ? "text-blue-400" : "text-slate-500 hover:text-blue-400 hover:bg-blue-500/10"}`}><Crown className="w-[18px] h-[18px]" /></button>
        <button data-testid="logout-btn" title="Sair" onClick={doLogout} className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"><LogOut className="w-[18px] h-[18px]" /></button>
      </div>
    </aside>
  );

  // ---- Mobile labeled drawer ----
  const DrawerNav = () => (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 mb-8">
        <Logo />
        <div><span className="font-serif-lux text-xl">CEO AI</span><p className="text-[10px] text-slate-400 uppercase tracking-[0.15em]">Diretor Executivo Digital</p></div>
      </div>
      <button data-testid="company-selector-mobile" onClick={() => { setNewOpen(true); }} className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl border border-white/10 hover:bg-white/[0.04] transition-colors mb-4 text-left">
        <Building2 className="w-4 h-4 text-blue-400" /><span className="text-sm truncate flex-1">{active?.name || "Empresa"}</span><Plus className="w-4 h-4 text-slate-400" />
      </button>
      <nav className="flex-1 flex flex-col gap-1 overflow-y-auto">
        {NAV.map((n) => {
          const locked = n.gated && !isPremium && !isAdmin;
          return (
            <button key={n.to} data-testid={`${n.testid}-m`} onClick={() => go(locked ? "/planos" : n.to)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors ${isActive(n) ? "bg-blue-500/10 text-blue-400" : "text-slate-400 hover:text-white hover:bg-white/[0.04]"}`}>
              <n.icon className="w-[18px] h-[18px]" />{n.label}{locked && <Lock className="w-3.5 h-3.5 ml-auto text-blue-400" />}
            </button>
          );
        })}
        {isAdmin && <button data-testid="nav-admin-m" onClick={() => go("/admin")} className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-white/[0.04]"><Shield className="w-[18px] h-[18px]" /> Administração</button>}
        {!isPremium && !isAdmin && <button data-testid="nav-planos-m" onClick={() => go("/planos")} className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm mt-1 border border-blue-500/30 text-blue-400"><Crown className="w-[18px] h-[18px]" /> Passar a Premium</button>}
      </nav>
      <div className="pt-4 border-t border-white/10 flex gap-2">
        <button onClick={() => { go("/subscricao"); }} className="flex-1 py-2 rounded-lg border border-white/10 text-xs text-slate-400">{isPremium ? "Subscrição" : "Upgrade"}</button>
        <button onClick={doLogout} data-testid="logout-btn-m" className="py-2 px-3 rounded-lg border border-white/10 text-xs text-slate-400 hover:text-red-400"><LogOut className="w-4 h-4" /></button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      {DesktopRail}

      <header className="md:hidden fixed top-0 left-0 right-0 h-14 z-30 flex items-center justify-between px-4 border-b border-white/[0.08] bg-[#05050A]/90 backdrop-blur-xl">
        <div className="flex items-center gap-2"><Logo /><span className="font-serif-lux text-lg">CEO AI</span></div>
        <button onClick={() => setMobileOpen(true)} data-testid="mobile-menu-btn" className="w-10 h-10 flex items-center justify-center rounded-xl border border-white/10"><Menu className="w-5 h-5" /></button>
      </header>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[288px] p-6 bg-[#07070d] border-white/10 overflow-y-auto">
          <DrawerNav />
        </SheetContent>
      </Sheet>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="surface">
          <DialogHeader><DialogTitle className="font-serif-lux text-2xl">Nova empresa</DialogTitle>
            <DialogDescription className="text-muted-foreground text-sm">Adiciona outra empresa à tua conta. Podes trocar entre elas a qualquer momento.</DialogDescription>
          </DialogHeader>
          <form onSubmit={addCompany} className="space-y-4">
            <div><Label className="text-xs text-muted-foreground">Nome</Label><Input data-testid="new-company-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="mt-1 bg-transparent" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label className="text-xs text-muted-foreground">Região</Label>
                <Select value={form.region} onValueChange={(v) => setForm({ ...form, region: v, currency: v === "BR" ? "BRL" : "EUR" })}>
                  <SelectTrigger data-testid="new-company-region" className="mt-1 bg-transparent"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="PT">Portugal (€)</SelectItem><SelectItem value="BR">Brasil (R$)</SelectItem></SelectContent>
                </Select>
              </div>
              <div><Label className="text-xs text-muted-foreground">Setor</Label><Input data-testid="new-company-sector" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} className="mt-1 bg-transparent" /></div>
            </div>
            <Button data-testid="create-company-btn" type="submit" className="w-full rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB]">Criar empresa</Button>
          </form>
        </DialogContent>
      </Dialog>

      <main className="md:pl-20 min-h-screen pt-14 md:pt-0 relative z-10">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Outlet />
        </motion.div>
      </main>
      <CEOTour />
    </div>
  );
}
