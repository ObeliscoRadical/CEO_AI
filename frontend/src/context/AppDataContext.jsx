import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AppDataContext = createContext(null);
export const useAppData = () => useContext(AppDataContext);

export function AppDataProvider({ children }) {
  const [companies, setCompanies] = useState([]);
  const [activeCompanyId, setActiveCompanyId] = useState(null);
  const [isPremium, setIsPremium] = useState(false);
  const [plans, setPlans] = useState({});

  const loadCompanies = useCallback(async () => {
    const { data } = await api.get("/companies");
    setCompanies(data.companies);
    setActiveCompanyId(data.active_company_id);
  }, []);

  const loadSubscription = useCallback(async () => {
    const { data } = await api.get("/subscription");
    setIsPremium(data.is_premium);
    setPlans(data.plans);
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
    <AppDataContext.Provider value={{ companies, activeCompanyId, isPremium, plans, loadCompanies, loadSubscription, switchCompany, createCompany }}>
      {children}
    </AppDataContext.Provider>
  );
}
