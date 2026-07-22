import { useEffect, useRef, useState } from "react";
import { api, streamChat } from "@/lib/api";
import { CEOOrb } from "@/components/CEOOrb";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Send, Loader2 } from "lucide-react";

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
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

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
        (sid) => { if (sid) setSessionId(sid); }
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

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto px-6">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center">
          <CEOOrb size={150} mood="gold" />
          <h1 className="font-serif-lux text-4xl mt-8 mb-3">Fala comigo.</h1>
          <p className="text-muted-foreground mb-10 max-w-md">Pergunta o que quiseres, como falarias com um CEO ao teu lado. Sem termos técnicos.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
            {SUGGESTIONS.map((s, i) => (
              <button key={i} data-testid={`suggestion-${i}`} onClick={() => send(s)}
                className="text-left text-sm p-4 rounded-xl border border-border hover:border-[#D4AF37]/50 hover:bg-accent transition-colors">
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
              {m.role === "assistant" && <div className="w-8 h-8 rounded-full bg-[#D4AF37]/20 shrink-0 mr-3 flex items-center justify-center"><div className="w-3 h-3 rounded-full bg-[#D4AF37]" /></div>}
              <div className={`max-w-[80%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${m.role === "user" ? "bg-[#D4AF37] text-[#0B0C10]" : "surface"}`}>
                {m.content || <Loader2 className="w-4 h-4 animate-spin" />}
              </div>
            </motion.div>
          ))}
          <div ref={endRef} />
        </div>
      )}

      <div className="py-6 sticky bottom-0 bg-background">
        <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-3 glass rounded-full p-2 pl-6 items-center">
          <Input data-testid="chat-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Escreve a tua pergunta..."
            className="border-0 bg-transparent focus-visible:ring-0 shadow-none" />
          <Button data-testid="chat-send-btn" type="submit" disabled={streaming || !input.trim()}
            className="rounded-full w-11 h-11 p-0 bg-[#D4AF37] text-[#0B0C10] hover:bg-[#c9a431]">
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
}
