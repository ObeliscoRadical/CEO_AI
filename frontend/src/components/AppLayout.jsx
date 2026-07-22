import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { LayoutDashboard, MessageSquare, Wallet, Trophy, TrendingUp, Settings as SettingsIcon, LogOut, Sun, Moon } from "lucide-react";
import { motion } from "framer-motion";

const NAV = [
  { to: "/", label: "Empresa Viva", icon: LayoutDashboard, end: true, testid: "nav-dashboard" },
  { to: "/ceo", label: "CEO AI", icon: MessageSquare, testid: "nav-ceo" },
  { to: "/financas", label: "Finanças", icon: Wallet, testid: "nav-financas" },
  { to: "/futuro", label: "Motor de Futuro", icon: TrendingUp, testid: "nav-futuro" },
  { to: "/score", label: "CEO Score", icon: Trophy, testid: "nav-score" },
  { to: "/definicoes", label: "Personalização", icon: SettingsIcon, testid: "nav-definicoes" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-background text-foreground relative z-10">
      <aside className="w-[260px] hidden md:flex flex-col fixed h-screen border-r border-border bg-[hsl(var(--card))] p-6">
        <div className="mb-10">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#D4AF37] shadow-[0_0_12px_#D4AF37]" />
            <span className="font-serif-lux text-2xl tracking-tight">CEO AI</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 tracking-[0.15em] uppercase">Executivo Digital</p>
        </div>
        <nav className="flex-1 flex flex-col gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-colors duration-200 ${
                  isActive ? "bg-[#D4AF37]/12 text-[#D4AF37]" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <n.icon className="w-[18px] h-[18px]" />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-6 pt-6 border-t border-border">
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
      </aside>
      <main className="flex-1 md:ml-[260px] min-h-screen">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <Outlet />
        </motion.div>
      </main>
    </div>
  );
}
