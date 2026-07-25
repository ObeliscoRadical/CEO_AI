import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { AppDataProvider, useAppData } from "@/context/AppDataContext";
import { Toaster } from "sonner";
import Login from "@/pages/Login";
import Onboarding from "@/pages/Onboarding";
import PainelCEO from "@/pages/PainelCEO";
import Conselhos from "@/pages/Conselhos";
import Saude from "@/pages/Saude";
import Valor from "@/pages/Valor";
import Relatorios from "@/pages/Relatorios";
import Dashboard from "@/pages/Dashboard";
import Chat from "@/pages/Chat";
import Finances from "@/pages/Finances";
import Score from "@/pages/Score";
import Future from "@/pages/Future";
import InvestmentGrade from "@/pages/InvestmentGrade";
import Settings from "@/pages/Settings";
import Pricing from "@/pages/Pricing";
import Admin from "@/pages/Admin";
import Subscription from "@/pages/Subscription";
import PaymentResult from "@/pages/PaymentResult";
import Terms from "@/pages/legal/Terms";
import Privacy from "@/pages/legal/Privacy";
import Contact from "@/pages/legal/Contact";
import { AppLayout } from "@/components/AppLayout";
import { UpgradeWall } from "@/components/Premium";
import { Loader2 } from "lucide-react";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-[#D4AF37]" />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Spinner() {
  return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>;
}

function PremiumRoute({ children }) {
  const { isPremium, isAdmin, subReady } = useAppData();
  if (!subReady) return <Spinner />;
  if (isPremium || isAdmin) return children;
  return <UpgradeWall />;
}

function AdminRoute({ children }) {
  const { isAdmin, subReady } = useAppData();
  if (!subReady) return <Spinner />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <div className="App grain">
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/termos" element={<Terms />} />
              <Route path="/privacidade" element={<Privacy />} />
              <Route path="/contacto" element={<Contact />} />
              <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
              <Route path="/payment/success" element={<Protected><AppDataProvider><PaymentResult /></AppDataProvider></Protected>} />
              <Route path="/payment/cancel" element={<Protected><PaymentResult /></Protected>} />
              <Route element={<Protected><AppDataProvider><AppLayout /></AppDataProvider></Protected>}>
                <Route path="/" element={<PainelCEO />} />
                <Route path="/conselhos" element={<PremiumRoute><Conselhos /></PremiumRoute>} />
                <Route path="/saude" element={<PremiumRoute><Saude /></PremiumRoute>} />
                <Route path="/valor" element={<PremiumRoute><Valor /></PremiumRoute>} />
                <Route path="/relatorios" element={<PremiumRoute><Relatorios /></PremiumRoute>} />
                <Route path="/ceo" element={<PremiumRoute><Chat /></PremiumRoute>} />
                <Route path="/financas" element={<Finances />} />
                <Route path="/futuro" element={<PremiumRoute><Future /></PremiumRoute>} />
                <Route path="/definicoes" element={<Settings />} />
                <Route path="/planos" element={<Pricing />} />
                <Route path="/subscricao" element={<Subscription />} />
                <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
                <Route path="/empresa-viva" element={<PremiumRoute><Dashboard /></PremiumRoute>} />
                <Route path="/score" element={<PremiumRoute><Score /></PremiumRoute>} />
                <Route path="/relatorio" element={<PremiumRoute><InvestmentGrade /></PremiumRoute>} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" theme="dark" richColors />
        </AuthProvider>
      </ThemeProvider>
    </div>
  );
}

export default App;
