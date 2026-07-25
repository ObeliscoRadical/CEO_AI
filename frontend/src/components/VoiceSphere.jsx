import { motion } from "framer-motion";
import { useRef } from "react";

// Blue energy orb: a glowing plasma core with energy wisps
// continuously erupting outward. Pure CSS/SVG, no external assets.
export function VoiceSphere({ size = 170, className = "", ripple = false }) {
  const id = useRef(`orb-${Math.random().toString(36).slice(2, 8)}`).current;
  const core = size * 0.66;

  const wisps = [0, 45, 90, 135, 180, 225, 270, 315, 25, 200].map((deg, i) => {
    const a = (deg * Math.PI) / 180;
    const dist = size * (0.42 + (i % 3) * 0.12);
    return { dx: Math.cos(a) * dist, dy: Math.sin(a) * dist, dur: 3 + (i % 4) * 0.8, delay: i * 0.35, s: 0.32 + (i % 3) * 0.12 };
  });

  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }} data-testid="voice-sphere">
      {/* breathing corona */}
      <motion.div
        className="absolute rounded-full"
        style={{ inset: -size * 0.3, background: "radial-gradient(circle, rgba(59,130,246,0.45), rgba(37,99,235,0.14) 46%, transparent 70%)", filter: `blur(${size * 0.09}px)` }}
        animate={{ opacity: [0.6, 1, 0.6], scale: [1, 1.1, 1] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* erupting energy wisps */}
      {wisps.map((w, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            width: size * w.s, height: size * w.s,
            background: "radial-gradient(circle, rgba(191,219,254,0.85), rgba(59,130,246,0.4) 45%, transparent 70%)",
            filter: `blur(${size * 0.05}px)`, mixBlendMode: "screen",
          }}
          initial={{ x: 0, y: 0, scale: 0.3, opacity: 0 }}
          animate={{ x: w.dx, y: w.dy, scale: [0.3, 1, 1.5], opacity: [0, 0.85, 0] }}
          transition={{ duration: w.dur, repeat: Infinity, ease: "easeOut", delay: w.delay }}
        />
      ))}

      {/* plasma core with churning energy */}
      <motion.svg
        width={core} height={core} viewBox="0 0 200 200" className="absolute"
        animate={{ rotate: [0, 8, -6, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
        style={{ filter: "drop-shadow(0 0 26px rgba(59,130,246,0.65))" }}
      >
        <defs>
          <radialGradient id={`${id}-g`} cx="50%" cy="40%" r="62%">
            <stop offset="0%" stopColor="#EFF6FF" />
            <stop offset="28%" stopColor="#93C5FD" />
            <stop offset="62%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#1E3A8A" />
          </radialGradient>
          <filter id={`${id}-smoke`} x="-30%" y="-30%" width="160%" height="160%">
            <feTurbulence type="fractalNoise" baseFrequency="0.014 0.02" numOctaves="4" seed="6" result="n">
              <animate attributeName="baseFrequency" dur="13s" repeatCount="indefinite"
                values="0.014 0.02; 0.022 0.012; 0.016 0.024; 0.014 0.02" />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="n" scale="30" xChannelSelector="R" yChannelSelector="G" result="d" />
            <feGaussianBlur in="d" stdDeviation="2.4" />
          </filter>
          <clipPath id={`${id}-c`}><circle cx="100" cy="100" r="96" /></clipPath>
        </defs>
        <g clipPath={`url(#${id}-c)`}>
          <circle cx="100" cy="100" r="96" fill={`url(#${id}-g)`} />
          <g filter={`url(#${id}-smoke)`}>
            <circle cx="72" cy="70" r="48" fill="#DBEAFE" opacity="0.9" />
            <circle cx="134" cy="118" r="52" fill="#3B82F6" opacity="0.75" />
            <circle cx="92" cy="140" r="38" fill="#1E3A8A" opacity="0.7" />
            <circle cx="130" cy="64" r="32" fill="#EFF6FF" opacity="0.85" />
            <circle cx="56" cy="118" r="28" fill="#2563EB" opacity="0.7" />
          </g>
          <motion.circle cx="92" cy="82" r="26" fill="#FFFFFF" initial={{ r: 22, opacity: 0.4 }}
            animate={{ opacity: [0.4, 0.7, 0.4], r: [22, 30, 22] }} transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
            style={{ filter: "blur(7px)" }} />
          <circle cx="100" cy="100" r="96" fill="none" stroke="rgba(30,58,138,0.5)" strokeWidth="12" opacity="0.55" />
        </g>
      </motion.svg>
    </div>
  );
}
