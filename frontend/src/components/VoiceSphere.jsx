import { motion } from "framer-motion";
import { useRef } from "react";

// "Living Sun" — a solar plasma core radiating energy: rotating sun rays,
// breathing corona, turbulent molten surface and flickering solar flares.
export function VoiceSphere({ size = 170, className = "", ripple = false }) {
  const id = useRef(`sun-${Math.random().toString(36).slice(2, 8)}`).current;
  const core = size * 0.62;

  const rays = (freq, dur, dir, opacity, blur) => (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: size * 1.9, height: size * 1.9,
        background: `repeating-conic-gradient(from 0deg, transparent 0deg, rgba(245,208,96,${opacity}) ${freq * 0.4}deg, transparent ${freq}deg, transparent ${freq * 2.4}deg)`,
        WebkitMaskImage: "radial-gradient(circle, transparent 26%, #000 40%, transparent 74%)",
        maskImage: "radial-gradient(circle, transparent 26%, #000 40%, transparent 74%)",
        filter: `blur(${blur}px)`,
        mixBlendMode: "screen",
      }}
      animate={{ rotate: dir * 360, opacity: [opacity > 0.2 ? 0.7 : 0.5, 1, 0.7] }}
      transition={{ rotate: { duration: dur, repeat: Infinity, ease: "linear" }, opacity: { duration: 4, repeat: Infinity, ease: "easeInOut" } }}
    />
  );

  const flare = (i, angle, len, w, delay) => (
    <div key={i} className="absolute left-1/2 top-1/2" style={{ transform: `rotate(${angle}deg)` }}>
      <motion.div
        className="absolute"
        style={{
          width: w, height: len, borderRadius: "50%", left: -w / 2, top: core * 0.34,
          background: "radial-gradient(circle at 50% 0%, rgba(255,240,190,0.95), rgba(240,180,70,0.5) 45%, transparent 75%)",
          filter: `blur(${size * 0.02}px)`,
        }}
        animate={{ scaleY: [0.55, 1.25, 0.7, 1], opacity: [0.4, 0.95, 0.5, 0.8] }}
        transition={{ duration: 2.6 + (i % 3), repeat: Infinity, ease: "easeInOut", delay }}
      />
    </div>
  );

  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }} data-testid="voice-sphere">
      {/* outer heat glow */}
      <motion.div
        className="absolute rounded-full"
        style={{ inset: -size * 0.35, background: "radial-gradient(circle, rgba(240,180,70,0.35), rgba(212,140,40,0.12) 45%, transparent 70%)", filter: `blur(${size * 0.1}px)` }}
        animate={{ opacity: [0.6, 1, 0.6], scale: [1, 1.1, 1] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* rotating sun rays (two layers, opposite spin) */}
      {rays(9, 55, 1, 0.28, 2)}
      {rays(4, 38, -1, 0.16, 0.6)}

      {/* solar flares / prominences around the rim */}
      {[0, 40, 78, 130, 175, 210, 255, 300, 335].map((a, i) =>
        flare(i, a, size * (0.16 + (i % 3) * 0.05), size * 0.06, i * 0.3)
      )}

      {/* pulsing energy wave emanating from the core */}
      <motion.div
        className="absolute rounded-full"
        style={{ width: core, height: core, boxShadow: "0 0 40px 8px rgba(245,200,90,0.5)" }}
        animate={{ scale: [1, 1.35, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeOut" }}
      />

      {/* molten plasma core */}
      <motion.svg
        width={core} height={core} viewBox="0 0 200 200" className="absolute"
        animate={{ rotate: [0, 10, -8, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
        style={{ filter: "drop-shadow(0 0 26px rgba(240,180,70,0.55))" }}
      >
        <defs>
          <radialGradient id={`${id}-g`} cx="50%" cy="44%" r="60%">
            <stop offset="0%" stopColor="#FFFDF2" />
            <stop offset="24%" stopColor="#FFE7A0" />
            <stop offset="55%" stopColor="#F1C24E" />
            <stop offset="82%" stopColor="#DB9A2A" />
            <stop offset="100%" stopColor="#B4761B" />
          </radialGradient>
          <filter id={`${id}-plasma`} x="-30%" y="-30%" width="160%" height="160%">
            <feTurbulence type="fractalNoise" baseFrequency="0.018 0.026" numOctaves="4" seed="5" result="n">
              <animate attributeName="baseFrequency" dur="14s" repeatCount="indefinite"
                values="0.018 0.026; 0.03 0.016; 0.02 0.03; 0.018 0.026" />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="n" scale="24" xChannelSelector="R" yChannelSelector="G" result="d" />
            <feGaussianBlur in="d" stdDeviation="1.4" />
          </filter>
          <clipPath id={`${id}-c`}><circle cx="100" cy="100" r="97" /></clipPath>
        </defs>
        <g clipPath={`url(#${id}-c)`}>
          <circle cx="100" cy="100" r="97" fill={`url(#${id}-g)`} />
          {/* churning plasma spots */}
          <g filter={`url(#${id}-plasma)`}>
            <circle cx="70" cy="80" r="42" fill="#FFF4CE" opacity="0.9" />
            <circle cx="132" cy="120" r="46" fill="#E7A93E" opacity="0.75" />
            <circle cx="96" cy="140" r="34" fill="#B4761B" opacity="0.7" />
            <circle cx="128" cy="66" r="30" fill="#FFFBEC" opacity="0.8" />
            <circle cx="58" cy="120" r="26" fill="#D8952A" opacity="0.7" />
          </g>
          {/* bright fusion center */}
          <circle cx="94" cy="86" r="30" fill="#FFFFFF" opacity="0.55" style={{ filter: "blur(8px)" }} />
        </g>
      </motion.svg>
    </div>
  );
}
