import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { AppDataProvider } from "@/context/AppDataContext";
import { Toaster } from "sonner";
import Login from "@/pages/Login";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Chat from "@/pages/Chat";
import Finances from "@/pages/Finances";
import Score from "@/pages/Score";
import Future from "@/pages/Future";
import InvestmentGrade from "@/pages/InvestmentGrade";
import Settings from "@/pages/Settings";
import Pricing from "@/pages/Pricing";
import Subscription from "@/pages/Subscription";
import PaymentResult from "@/pages/PaymentResult";
import { AppLayout } from "@/components/AppLayout";
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

function App() {
  return (
    <div className="App grain">
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
              <Route path="/payment/success" element={<Protected><AppDataProvider><PaymentResult /></AppDataProvider></Protected>} />
              <Route path="/payment/cancel" element={<Protected><PaymentResult /></Protected>} />
              <Route element={<Protected><AppDataProvider><AppLayout /></AppDataProvider></Protected>}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/ceo" element={<Chat />} />
                <Route path="/financas" element={<Finances />} />
                <Route path="/score" element={<Score />} />
                <Route path="/futuro" element={<Future />} />
                <Route path="/relatorio" element={<InvestmentGrade />} />
                <Route path="/planos" element={<Pricing />} />
                <Route path="/subscricao" element={<Subscription />} />
                <Route path="/definicoes" element={<Settings />} />
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
