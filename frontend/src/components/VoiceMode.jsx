import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { VoiceSphere } from "@/components/VoiceSphere";
import { api } from "@/lib/api";
import { Mic, X, Loader2 } from "lucide-react";

const STATUS_LABEL = { idle: "Toca para falar", listening: "A ouvir…", thinking: "A pensar…", speaking: "" };

export function VoiceMode({ open, onClose, sessionId, onSession }) {
  const [status, setStatus] = useState("idle");
  const [amp, setAmp] = useState(0);
  const [userText, setUserText] = useState("");
  const [replyText, setReplyText] = useState("");
  const mrRef = useRef(null); const chunksRef = useRef([]); const streamRef = useRef(null);
  const acRef = useRef(null); const analyserRef = useRef(null); const rafRef = useRef(null);
  const audioRef = useRef(null); const sidRef = useRef(sessionId);

  useEffect(() => { sidRef.current = sessionId; }, [sessionId]);
  useEffect(() => { if (!open) cleanup(); return cleanup; /* eslint-disable-next-line */ }, [open]);

  const cleanup = () => {
    cancelAnimationFrame(rafRef.current);
    try { mrRef.current?.state === "recording" && mrRef.current.stop(); } catch {}
    streamRef.current?.getTracks().forEach((t) => t.stop());
    try { audioRef.current?.pause(); } catch {}
    try { acRef.current?.close(); } catch {}
    acRef.current = null; analyserRef.current = null;
    setAmp(0); setStatus("idle");
  };

  const runAmpLoop = () => {
    const a = analyserRef.current; if (!a) return;
    const buf = new Uint8Array(a.fftSize);
    const tick = () => {
      a.getByteTimeDomainData(buf);
      let sum = 0; for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
      setAmp(Math.min(1, Math.sqrt(sum / buf.length) * 3.2));
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  };

  const pickMime = () => ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((m) => window.MediaRecorder?.isTypeSupported?.(m)) || "";

  const startListening = async () => {
    setUserText(""); setReplyText("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      acRef.current = ac;
      const src = ac.createMediaStreamSource(stream);
      const an = ac.createAnalyser(); an.fftSize = 512; src.connect(an);
      analyserRef.current = an; runAmpLoop();
      const mime = pickMime();
      const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      mrRef.current = mr; chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = handleStop;
      mr.start(); setStatus("listening");
    } catch (e) {
      setStatus("idle"); setReplyText("Preciso de acesso ao microfone para conversar por voz.");
    }
  };

  const stopListening = () => {
    cancelAnimationFrame(rafRef.current); setAmp(0);
    try { mrRef.current?.stop(); } catch {}
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setStatus("thinking");
  };

  const handleStop = async () => {
    const blob = new Blob(chunksRef.current, { type: chunksRef.current[0]?.type || "audio/webm" });
    if (blob.size < 800) { setStatus("idle"); return; }
    const ext = blob.type.includes("mp4") ? "mp4" : "webm";
    const fd = new FormData();
    fd.append("file", blob, `voz.${ext}`);
    if (sidRef.current) fd.append("session_id", sidRef.current);
    try {
      const { data } = await api.post("/voice/chat", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setUserText(data.user_text); setReplyText(data.reply_text);
      if (data.session_id) { sidRef.current = data.session_id; onSession?.(data.session_id); }
      if (data.audio_base64) speak(data.audio_base64); else setStatus("idle");
    } catch (e) {
      setReplyText(e?.response?.data?.detail || "Não consegui perceber. Tenta outra vez.");
      setStatus("idle");
    }
  };

  const speak = async (b64) => {
    setStatus("speaking");
    const audio = new Audio(`data:audio/mp3;base64,${b64}`);
    audioRef.current = audio;
    try {
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      acRef.current = ac;
      const src = ac.createMediaElementSource(audio);
      const an = ac.createAnalyser(); an.fftSize = 512;
      src.connect(an); an.connect(ac.destination);
      analyserRef.current = an; runAmpLoop();
    } catch {}
    audio.onended = () => { cancelAnimationFrame(rafRef.current); setAmp(0); setStatus("idle"); };
    try { await audio.play(); } catch { setStatus("idle"); }
  };

  const onMainButton = () => {
    if (status === "idle") startListening();
    else if (status === "listening") stopListening();
    else if (status === "speaking") { try { audioRef.current?.pause(); } catch {} cancelAnimationFrame(rafRef.current); setAmp(0); setStatus("idle"); }
  };

  if (!open) return null;
  const scale = 1 + amp * 0.28;

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex flex-col items-center justify-center"
        style={{ background: "radial-gradient(circle at 50% 40%, #14110A, #08090C 70%)" }}
        data-testid="voice-mode"
      >
        <button onClick={onClose} data-testid="voice-close" className="absolute top-6 right-6 w-11 h-11 rounded-full flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors">
          <X className="w-6 h-6" />
        </button>

        <motion.div animate={{ scale }} transition={{ type: "spring", stiffness: 120, damping: 18 }} className="relative">
          <div className="absolute rounded-full" style={{ inset: -40, background: `radial-gradient(circle, rgba(212,175,55,${0.15 + amp * 0.4}), transparent 70%)`, filter: "blur(20px)" }} />
          <VoiceSphere size={230} />
        </motion.div>

        <p className="mt-12 text-white/50 text-sm tracking-[0.2em] uppercase h-5" data-testid="voice-status">{STATUS_LABEL[status]}</p>

        <div className="mt-6 max-w-xl px-8 text-center min-h-[80px]">
          {userText && <p className="text-white/40 text-sm mb-3" data-testid="voice-user-text">“{userText}”</p>}
          {status === "thinking" ? (
            <Loader2 className="w-5 h-5 animate-spin text-[#D4AF37] mx-auto" />
          ) : (
            replyText && <p className="text-white text-lg leading-relaxed font-serif-lux" data-testid="voice-reply-text">{replyText}</p>
          )}
        </div>

        <button
          onClick={onMainButton} data-testid="voice-mic-button"
          className="mt-12 w-20 h-20 rounded-full flex items-center justify-center transition-all"
          style={{
            background: status === "listening" ? "#EF4444" : "#D4AF37",
            boxShadow: `0 0 ${20 + amp * 40}px ${status === "listening" ? "rgba(239,68,68,0.6)" : "rgba(212,175,55,0.6)"}`,
          }}
        >
          {status === "thinking" ? <Loader2 className="w-8 h-8 animate-spin text-[#0B0C10]" /> : <Mic className="w-8 h-8 text-[#0B0C10]" />}
        </button>
        <p className="mt-4 text-white/30 text-xs">{status === "listening" ? "Toca para enviar" : "Toca no micro e fala"}</p>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
