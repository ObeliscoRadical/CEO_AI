import { useEffect, useRef, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, streamChat } from "@/lib/api";
import { VoiceSphere } from "@/components/VoiceSphere";
import { VoiceMode } from "@/components/VoiceMode";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Send, Loader2, Plus, MessageSquare, Trash2, Mic } from "lucide-react";

const SUGGESTIONS = [
  "Posso tirar férias este mês?",
  "Posso comprar uma carrinha?",
  "Porque estou sempre sem caixa?",
  "Posso contratar mais um técnico?",
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const endRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  const loadSessions = useCallback(async () => {
    const { data } = await api.get("/chat/sessions");
    setSessions(data);
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const openSession = async (sid) => {
    setSessionId(sid);
    const { data } = await api.get(`/chat/${sid}/messages`);
    setMessages(data);
  };

  const newChat = () => { setSessionId(null); setMessages([]); setInput(""); };

  const removeSession = async (sid, e) => {
    e.stopPropagation();
    await api.delete(`/chat/${sid}`);
    if (sid === sessionId) newChat();
    loadSessions();
  };

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }, { role: "assistant", content: "" }]);
    setStreaming(true);
    try {
      await streamChat(
        { message: msg, session_id: sessionId },
        (delta) => setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = { role: "assistant", content: copy[copy.length - 1].content + delta };
          return copy;
        }),
        (sid) => { if (sid) { setSessionId(sid); loadSessions(); } }
      );
    } catch (e) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: "Desculpa, tive um problema de ligação. Tenta de novo." };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  useEffect(() => {
    const ask = location.state?.ask;
    if (ask) {
      navigate(location.pathname, { replace: true });
      send(ask);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-screen">
      {/* Sessions panel */}
      <div className="w-[240px] hidden lg:flex flex-col border-r border-border p-4">
        <Button data-testid="new-chat-btn" onClick={newChat} className="rounded-full bg-[#3B82F6] text-white hover:bg-[#2563EB] mb-4">
          <Plus className="w-4 h-4 mr-2" /> Nova conversa
        </Button>
        <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] mb-2 px-2">Histórico</p>
        <div className="flex-1 overflow-y-auto space-y-1">
          {sessions.length === 0 && <p className="text-xs text-muted-foreground px-2">Sem conversas ainda.</p>}
          {sessions.map((s) => (
            <div key={s.session_id} onClick={() => openSession(s.session_id)} data-testid={`session-${s.session_id}`}
              className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-colors ${s.session_id === sessionId ? "bg-[#3B82F6]/12 text-[#3B82F6]" : "text-muted-foreground hover:bg-accent"}`}>
              <MessageSquare className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate flex-1">{s.title}</span>
              <button onClick={(e) => removeSession(s.session_id, e)} data-testid={`del-session-${s.session_id}`} className="opacity-0 group-hover:opacity-100 hover:text-[#EF4444] transition-opacity"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col max-w-3xl mx-auto px-6 w-full">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <VoiceSphere size={170} />
            <h1 className="font-serif-lux text-4xl mt-8 mb-3">Fala comigo.</h1>
            <p className="text-muted-foreground mb-8 max-w-md">Pergunta o que quiseres, como falarias com um CEO ao teu lado. Sem termos técnicos.</p>
            <Button data-testid="open-voice-btn" onClick={() => setVoiceOpen(true)}
              className="rounded-full mb-10 h-12 px-7 bg-[#3B82F6] text-white hover:bg-[#2563EB] text-base">
              <Mic className="w-5 h-5 mr-2" /> Falar com o CEO
            </Button>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} data-testid={`suggestion-${i}`} onClick={() => send(s)}
                  className="text-left text-sm p-4 rounded-xl border border-border hover:border-[#3B82F6]/50 hover:bg-accent transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto py-8 space-y-6">
            {messages.map((m, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`} data-testid={`msg-${m.role}-${i}`}>
                {m.role === "assistant" && <div className="w-8 h-8 rounded-full bg-[#3B82F6]/20 shrink-0 mr-3 flex items-center justify-center"><div className="w-3 h-3 rounded-full bg-[#3B82F6]" /></div>}
                <div className={`max-w-[80%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${m.role === "user" ? "bg-[#3B82F6] text-white" : "surface"}`}>
                  {m.content || <Loader2 className="w-4 h-4 animate-spin" />}
                </div>
              </motion.div>
            ))}
            <div ref={endRef} />
          </div>
        )}

        <div className="py-6 sticky bottom-0 bg-background">
          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 glass rounded-full p-2 pl-6 items-center">
            <Input data-testid="chat-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Escreve a tua pergunta..."
              className="border-0 bg-transparent focus-visible:ring-0 shadow-none" />
            <Button data-testid="voice-mic-inline" type="button" onClick={() => setVoiceOpen(true)} variant="ghost"
              className="rounded-full w-11 h-11 p-0 text-[#3B82F6] hover:bg-[#3B82F6]/10" title="Falar com o CEO">
              <Mic className="w-5 h-5" />
            </Button>
            <Button data-testid="chat-send-btn" type="submit" disabled={streaming || !input.trim()}
              className="rounded-full w-11 h-11 p-0 bg-[#3B82F6] text-white hover:bg-[#2563EB]">
              {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </form>
        </div>
      </div>

      <VoiceMode
        open={voiceOpen}
        onClose={() => { setVoiceOpen(false); if (sessionId) openSession(sessionId); loadSessions(); }}
        sessionId={sessionId}
        onSession={setSessionId}
      />
    </div>
  );
}
