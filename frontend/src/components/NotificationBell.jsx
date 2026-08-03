import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Bell, Check, Clock, X, Sparkles } from "lucide-react";

export function NotificationBell({ compact = false }) {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  const load = () => api.get("/crm/notifications")
    .then(({ data }) => { setItems(data.notifications || []); setUnread(data.unread || 0); })
    .catch(() => {});

  useEffect(() => {
    load();
    const t = setInterval(load, 45000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const toggle = async () => {
    const willOpen = !open;
    setOpen(willOpen);
    if (willOpen && unread > 0) {
      await Promise.all(items.filter((i) => i.status === "unread").map((i) => api.post(`/crm/notifications/${i.id}/read`).catch(() => {})));
      setUnread(0);
    }
  };

  const act = async (n) => {
    try {
      const { data } = await api.post(`/crm/notifications/${n.id}/act`);
      setOpen(false);
      navigate((data.data && data.data.route) || "/crm");
    } catch { toast.error("Não foi possível abrir."); }
  };
  const snooze = async (n) => { await api.post(`/crm/notifications/${n.id}/snooze`, { days: 1 }); toast.success("Vou lembrar amanhã."); load(); };
  const dismiss = async (n) => { await api.post(`/crm/notifications/${n.id}/dismiss`); load(); };

  return (
    <div className="relative" ref={ref}>
      <button data-testid="notif-bell" onClick={toggle} title="Notificações"
        className={`relative flex items-center justify-center rounded-lg text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors ${compact ? "w-9 h-9" : "w-8 h-8"}`}>
        <Bell className="w-[18px] h-[18px]" />
        {unread > 0 && <span data-testid="notif-badge" className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div data-testid="notif-panel" className="absolute right-0 bottom-full mb-2 md:bottom-auto md:top-full md:mb-0 md:mt-2 w-[340px] max-h-[420px] overflow-y-auto rounded-2xl border border-white/10 bg-[#0a0a13] shadow-2xl z-50 p-2">
          <div className="px-3 py-2 flex items-center gap-2 text-sm font-medium border-b border-white/[0.06] mb-1"><Sparkles className="w-4 h-4 text-blue-400" /> Alertas do CRM</div>
          {items.length === 0 ? (
            <div className="px-3 py-8 text-center text-xs text-slate-500" data-testid="notif-empty">Sem alertas de momento. O CRM avisa quando houver ações a fazer.</div>
          ) : items.map((n) => (
            <div key={n.id} className="p-3 rounded-xl hover:bg-white/[0.03]" data-testid={`notif-item-${n.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="text-[13px] font-medium">{n.title}</div>
                <button onClick={() => dismiss(n)} data-testid={`notif-dismiss-${n.id}`} className="text-slate-600 hover:text-red-400 shrink-0"><X className="w-3.5 h-3.5" /></button>
              </div>
              <p className="text-xs text-slate-400 mt-1 mb-2">{n.body}</p>
              <div className="flex gap-2">
                <button onClick={() => act(n)} data-testid={`notif-act-${n.id}`} className="text-xs px-3 py-1.5 rounded-full bg-blue-500 text-white hover:bg-blue-600 flex items-center gap-1"><Check className="w-3 h-3" /> Sim, preparar</button>
                <button onClick={() => snooze(n)} data-testid={`notif-snooze-${n.id}`} className="text-xs px-3 py-1.5 rounded-full border border-white/10 text-slate-400 hover:bg-white/5 flex items-center gap-1"><Clock className="w-3 h-3" /> Lembrar depois</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
