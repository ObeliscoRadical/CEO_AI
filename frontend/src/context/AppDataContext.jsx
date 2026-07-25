import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AppDataContext = createContext(null);
export const useAppData = () => useContext(AppDataContext);

export function AppDataProvider({ children }) {
  const [companies, setCompanies] = useState([]);
  const [activeCompanyId, setActiveCompanyId] = useState(null);
  const [isPremium, setIsPremium] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [subReady, setSubReady] = useState(false);
  const [plans, setPlans] = useState({});
  const [subscription, setSubscription] = useState(null);
  const [hasBilling, setHasBilling] = useState(false);

  const loadCompanies = useCallback(async () => {
    const { data } = await api.get("/companies");
    setCompanies(data.companies);
    setActiveCompanyId(data.active_company_id);
  }, []);

  const loadSubscription = useCallback(async () => {
    const { data } = await api.get("/subscription");
    setIsPremium(data.is_premium);
    setIsAdmin(!!data.is_admin);
    setPlans(data.plans);
    setSubscription(data.subscription);
    setHasBilling(data.has_billing);
    setSubReady(true);
  }, []);

  useEffect(() => {
    loadCompanies();
    loadSubscription();
  }, [loadCompanies, loadSubscription]);

  const switchCompany = async (id) => {
    await api.put("/companies/active", { company_id: id });
    setActiveCompanyId(id);
  };

  const createCompany = async (payload) => {
    const { data } = await api.post("/companies", payload);
    await loadCompanies();
    setActiveCompanyId(data.id);
    return data;
  };

  return (
    <AppDataContext.Provider value={{ companies, activeCompanyId, isPremium, isAdmin, subReady, plans, subscription, hasBilling, loadCompanies, loadSubscription, switchCompany, createCompany }}>
      {children}
    </AppDataContext.Provider>
  );
}
