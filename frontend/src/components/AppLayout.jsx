import { useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useAppData } from "@/context/AppDataContext";
import { Home, Lightbulb, HeartPulse, Coins, MessageSquare, Wallet, TrendingUp, FileText, Settings as SettingsIcon, LogOut, Building2, Plus, Crown, Check, Menu, Compass, Lock, Shield, X, ChevronDown } from "lucide-react";
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
  { to: "/", label: "Painel do CEO", short: "Painel", icon: Home, end: true, testid: "nav-painel" },
  { to: "/conselhos", label: "Conselhos", short: "Conselhos", icon: Lightbulb, testid: "nav-conselhos", gated: true },
  { to: "/saude", label: "Saúde Empresarial", short: "Saúde", icon: HeartPulse, testid: "nav-saude", gated: true },
  { to: "/valor", label: "Valor da Empresa", short: "Valor", icon: Coins, testid: "nav-valor", gated: true },
  { to: "/futuro", label: "Futuro", short: "Futuro", icon: TrendingUp, testid: "nav-futuro", premium: true, gated: true },
  { to: "/ceo", label: "Reunião com CEO", short: "CEO", icon: MessageSquare, testid: "nav-ceo", gated: true },
  { to: "/financas", label: "Finanças", short: "Finanças", icon: Wallet, testid: "nav-financas" },
  { to: "/relatorios", label: "Relatórios", short: "Relatórios", icon: FileText, testid: "nav-relatorios", gated: true },
  { to: "/definicoes", label: "Empresa", short: "Definições", icon: SettingsIcon, testid: "nav-empresa" },
];

const Logo = ({ size = 40 }) => (
  <div className="relative flex items-center justify-center" style={{ width: size, height: size }} aria-hidden="true">
    <div className="absolute inset-1 rounded-full" style={{ background: "radial-gradient(circle, rgba(59,130,246,0.4), transparent 70%)", filter: "blur(6px)" }} />
    <img src="/android_cut.png" alt="CEO AI" className="relative w-full h-full object-contain" style={{ filter: "drop-shadow(0 0 6px rgba(59,130,246,0.45))" }} />
  </div>
);

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

  // ---- Desktop sidebar ----
  const SidebarItem = ({ n }) => {
    const locked = n.gated && !isPremium && !isAdmin;
    const activeItem = isActive(n);
    const showCrown = n.premium && !isPremium && !isAdmin && !locked;
    return (
      <button
        data-testid={n.testid}
        onClick={() => go(locked ? "/planos" : n.to)}
        className={`group relative w-full flex items-center gap-3 pl-4 pr-3 py-2.5 rounded-xl text-[13.5px] font-medium transition-all duration-200 ${
          activeItem
            ? "text-white bg-blue-500/[0.14] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
            : "text-slate-400 hover:text-white hover:bg-white/[0.045]"
        }`}
      >
        {activeItem && <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.7)]" />}
        <n.icon className={`w-[18px] h-[18px] shrink-0 transition-colors ${activeItem ? "text-blue-400" : "text-slate-500 group-hover:text-blue-400"}`} />
        <span className="truncate flex-1 text-left">{n.label}</span>
        {locked && <Lock className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400" />}
        {showCrown && <Crown className="w-3.5 h-3.5 text-amber-400/80" />}
      </button>
    );
  };

  const initials = (user?.name || user?.email || "?").trim().slice(0, 2).toUpperCase();

  const DesktopRail = (
    <aside className="hidden md:flex w-64 h-screen fixed left-0 top-0 flex-col border-r border-white/[0.06] bg-gradient-to-b from-[#0a0a13]/95 to-[#05050A]/95 backdrop-blur-2xl z-40">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 pt-6 pb-5">
        <Logo size={38} />
        <div className="leading-tight">
          <div className="font-serif-lux text-lg">CEO AI</div>
          <div className="text-[9.5px] text-slate-500 uppercase tracking-[0.18em]">Diretor Executivo</div>
        </div>
      </div>

      {/* Company switcher */}
      <div className="px-3 mb-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="company-selector"
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.12] transition-colors text-left">
              <div className="w-7 h-7 rounded-lg bg-blue-500/15 flex items-center justify-center shrink-0"><Building2 className="w-4 h-4 text-blue-400" /></div>
              <div className="flex-1 min-w-0">
                <div className="text-[9.5px] text-slate-500 uppercase tracking-wider leading-none mb-1">Empresa ativa</div>
                <div className="text-[13px] font-medium truncate">{active?.name || "Selecionar"}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[236px]" align="start" side="bottom">
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
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto no-scrollbar">
        <div className="px-4 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">Menu</div>
        {NAV.map((n) => <SidebarItem key={n.to} n={n} />)}
        {isAdmin && <SidebarItem n={{ to: "/admin", label: "Administração", icon: Shield, testid: "nav-admin" }} />}
        <div className="px-4 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">Conta</div>
        <button data-testid="restart-tour-btn" onClick={() => window.dispatchEvent(new Event("start-ceo-tour"))} className="group w-full flex items-center gap-3 pl-4 pr-3 py-2.5 rounded-xl text-[13.5px] font-medium text-slate-400 hover:text-white hover:bg-white/[0.045] transition-all"><Compass className="w-[18px] h-[18px] text-slate-500 group-hover:text-blue-400" /> Tour guiado</button>
        <button data-testid="nav-subscricao" onClick={() => go("/subscricao")} className="group w-full flex items-center gap-3 pl-4 pr-3 py-2.5 rounded-xl text-[13.5px] font-medium text-slate-400 hover:text-white hover:bg-white/[0.045] transition-all"><Crown className={`w-[18px] h-[18px] ${isPremium ? "text-amber-400" : "text-slate-500 group-hover:text-blue-400"}`} /> {isPremium ? "A minha subscrição" : "Ver planos"}</button>
      </nav>

      {/* Premium CTA */}
      {!isPremium && !isAdmin && (
        <div className="px-3 pb-3 pt-1">
          <button onClick={() => go("/planos")} data-testid="sidebar-premium-cta"
            className="w-full rounded-xl p-3.5 text-left relative overflow-hidden border border-blue-500/30 bg-gradient-to-br from-blue-600/25 to-blue-900/10 hover:from-blue-600/35 transition-colors">
            <div className="flex items-center gap-2 mb-1"><Crown className="w-4 h-4 text-amber-400" /><span className="text-[13px] font-semibold">Passar a Premium</span></div>
            <p className="text-[11px] text-slate-400 leading-snug">Desbloqueia decisões, saúde e relatórios do teu CEO.</p>
          </button>
        </div>
      )}

      {/* User */}
      <div className="px-3 py-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-[12px] font-bold text-white shrink-0 shadow-[0_0_12px_rgba(59,130,246,0.4)] overflow-hidden">
            {user?.picture ? <img src={user.picture} alt="" className="w-full h-full object-cover" /> : initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-medium truncate">{user?.name || "Utilizador"}</div>
            <div className="text-[11px] text-slate-500 truncate">{user?.email}</div>
          </div>
          <button data-testid="logout-btn" title="Sair" onClick={doLogout} className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"><LogOut className="w-[17px] h-[17px]" /></button>
        </div>
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

      <main className="md:pl-64 min-h-screen pt-14 md:pt-0 relative z-10">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Outlet />
        </motion.div>
      </main>
      <CEOTour />
    </div>
  );
}
