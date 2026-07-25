import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useAppData } from "@/context/AppDataContext";
import { Home, Lightbulb, HeartPulse, Coins, MessageSquare, Wallet, TrendingUp, FileText, Settings as SettingsIcon, LogOut, Sun, Moon, Building2, Plus, Crown, ChevronsUpDown, Check, Menu, Compass, Lock, Shield } from "lucide-react";
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

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { companies, activeCompanyId, isPremium, isAdmin, switchCompany, createCompany } = useAppData();
  const navigate = useNavigate();
  const [newOpen, setNewOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [form, setForm] = useState({ name: "", region: "PT", currency: "EUR", sector: "" });

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  const active = companies.find((c) => c.id === activeCompanyId);

  const addCompany = async (e) => {
    e.preventDefault();
    await createCompany(form);
    setNewOpen(false);
    setForm({ name: "", region: "PT", currency: "EUR", sector: "" });
    toast.success("Empresa criada e ativada");
    navigate("/");
  };

  const SidebarContent = ({ onNavigate = () => {} }) => (
    <div className="flex flex-col h-full">
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#D4AF37] shadow-[0_0_12px_#D4AF37]" />
          <span className="font-serif-lux text-2xl tracking-tight">CEO AI</span>
          {isPremium && <Crown className="w-4 h-4 text-[#D4AF37] ml-auto" />}
        </div>
        <p className="text-xs text-muted-foreground mt-1 tracking-[0.15em] uppercase">Diretor Executivo Digital</p>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button data-testid="company-selector" className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl border border-border hover:bg-accent transition-colors mb-6 text-left">
            <div className="w-7 h-7 rounded-lg bg-[#D4AF37]/15 flex items-center justify-center text-[#D4AF37] shrink-0"><Building2 className="w-4 h-4" /></div>
            <span className="text-sm truncate flex-1">{active?.name || "Empresa"}</span>
            <ChevronsUpDown className="w-4 h-4 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-[212px]" align="start">
          {companies.map((c) => (
            <DropdownMenuItem key={c.id} data-testid={`company-option-${c.id}`} onClick={() => { switchCompany(c.id).then(() => navigate("/")); onNavigate(); }} className="cursor-pointer">
              <Check className={`w-4 h-4 mr-2 ${c.id === activeCompanyId ? "opacity-100 text-[#D4AF37]" : "opacity-0"}`} />
              <span className="truncate">{c.name}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuItem data-testid="add-company-trigger" onClick={() => { setNewOpen(true); onNavigate(); }} className="cursor-pointer text-[#D4AF37]">
            <Plus className="w-4 h-4 mr-2" /> Nova empresa
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <nav className="flex-1 flex flex-col gap-1 overflow-y-auto">
        {NAV.map((n) => {
          const locked = n.gated && !isPremium && !isAdmin;
          if (locked) {
            return (
              <button key={n.to} data-testid={n.testid} onClick={() => { onNavigate(); navigate("/planos"); }}
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors duration-200">
                <n.icon className="w-[18px] h-[18px]" />
                {n.label}
                <Lock className="w-3.5 h-3.5 ml-auto text-[#D4AF37]" />
              </button>
            );
          }
          return (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              data-testid={n.testid}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors duration-200 ${
                  isActive ? "bg-[#D4AF37]/12 text-[#D4AF37]" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <n.icon className="w-[18px] h-[18px]" />
              {n.label}
              {(n.to === "/futuro" || n.premium) && !isPremium && !isAdmin && <Crown className="w-3.5 h-3.5 ml-auto text-[#D4AF37]" />}
            </NavLink>
          );
        })}
        {isAdmin && (
          <NavLink to="/admin" data-testid="nav-admin" onClick={onNavigate} className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors mt-1 ${isActive ? "bg-[#D4AF37]/12 text-[#D4AF37]" : "text-muted-foreground hover:text-foreground hover:bg-accent"}`}>
            <Shield className="w-[18px] h-[18px]" /> Administração
          </NavLink>
        )}
        {!isPremium && !isAdmin && (
          <NavLink to="/planos" data-testid="nav-planos" onClick={onNavigate} className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors mt-1 border border-[#D4AF37]/30 ${isActive ? "bg-[#D4AF37]/12 text-[#D4AF37]" : "text-[#D4AF37] hover:bg-[#D4AF37]/10"}`}>
            <Crown className="w-[18px] h-[18px]" /> Passar a Premium
          </NavLink>
        )}
      </nav>

      <div className="mt-6 pt-6 border-t border-border">
        <button data-testid="restart-tour-btn" onClick={() => { onNavigate(); window.dispatchEvent(new Event("start-ceo-tour")); }}
          className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl text-xs mb-3 text-muted-foreground hover:bg-accent transition-colors">
          <Compass className="w-4 h-4" /> <span className="flex-1 text-left">Tour guiado do CEO</span>
        </button>
        <NavLink to="/subscricao" data-testid="nav-subscricao" onClick={onNavigate} className={({ isActive }) => `flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs mb-4 transition-colors ${isActive ? "bg-[#D4AF37]/12 text-[#D4AF37]" : "text-muted-foreground hover:bg-accent"}`}>
          <Crown className={`w-4 h-4 ${isPremium ? "text-[#D4AF37]" : ""}`} />
          <span className="flex-1">{isPremium ? "Subscrição Premium" : "Plano Grátis"}</span>
          <span className="text-[10px] uppercase tracking-wider">{isPremium ? "Gerir" : "Upgrade"}</span>
        </NavLink>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-[#D4AF37]/20 flex items-center justify-center text-[#D4AF37] font-medium">
            {(user?.name || "?")[0].toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm truncate">{user?.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={toggle} data-testid="theme-toggle" className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground transition-colors">
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {theme === "dark" ? "Claro" : "Escuro"}
          </button>
          <button onClick={doLogout} data-testid="logout-btn" className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-border text-xs text-muted-foreground hover:text-[#EF4444] transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-background text-foreground relative z-10">
      {/* Desktop sidebar */}
      <aside className="w-[260px] hidden md:flex flex-col fixed h-screen border-r border-border bg-[hsl(var(--card))] p-6">
        <SidebarContent />
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-14 z-30 flex items-center justify-between px-4 border-b border-border bg-[hsl(var(--card))]">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#D4AF37] shadow-[0_0_10px_#D4AF37]" />
          <span className="font-serif-lux text-xl tracking-tight">CEO AI</span>
          {isPremium && <Crown className="w-3.5 h-3.5 text-[#D4AF37]" />}
        </div>
        <button onClick={() => setMobileOpen(true)} data-testid="mobile-menu-btn" className="w-10 h-10 flex items-center justify-center rounded-xl border border-border text-foreground">
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[284px] p-6 bg-[hsl(var(--card))] border-border overflow-y-auto">
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Nova empresa dialog (single instance) */}
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
            <Button data-testid="create-company-btn" type="submit" className="w-full rounded-full bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">Criar empresa</Button>
          </form>
        </DialogContent>
      </Dialog>

      <main className="flex-1 md:ml-[260px] min-h-screen pt-14 md:pt-0">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Outlet />
        </motion.div>
      </main>
      <CEOTour />
    </div>
  );
}
