import { motion } from "framer-motion";
import { useRef } from "react";

// Innovative gold "voice" sphere with real flowing smoke (animated SVG turbulence displacement).
export function VoiceSphere({ size = 170, className = "", ripple = false }) {
  const id = useRef(`vs-${Math.random().toString(36).slice(2, 8)}`).current;

  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }} data-testid="voice-sphere">
      {/* Siri-style activation ripples */}
      {ripple && [0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border"
          style={{ width: size, height: size, borderColor: "rgba(212,175,55,0.5)" }}
          initial={{ scale: 0.85, opacity: 0.6 }}
          animate={{ scale: 1.9, opacity: 0 }}
          transition={{ duration: 3.6, repeat: Infinity, ease: "easeOut", delay: i * 1.2 }}
        />
      ))}
      {/* ambient glow */}
      <motion.div
        className="absolute rounded-full"
        style={{ inset: -size * 0.22, background: "radial-gradient(circle, rgba(212,175,55,0.4), transparent 68%)", filter: `blur(${size * 0.07}px)` }}
        animate={{ opacity: [0.7, 1, 0.7], scale: [1, 1.06, 1] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.svg
        width={size} height={size} viewBox="0 0 200 200"
        className="absolute inset-0"
        animate={{ rotate: [0, 6, -5, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
        style={{ filter: "drop-shadow(0 0 24px rgba(201,152,46,0.35))" }}
      >
        <defs>
          <radialGradient id={`${id}-gold`} cx="50%" cy="28%" r="80%">
            <stop offset="0%" stopColor="#FCEEC6" />
            <stop offset="32%" stopColor="#EBC96A" />
            <stop offset="70%" stopColor="#C79A32" />
            <stop offset="100%" stopColor="#9A711F" />
          </radialGradient>

          {/* flowing smoke: animated fractal noise displaces the light gas layer */}
          <filter id={`${id}-smoke`} x="-40%" y="-40%" width="180%" height="180%">
            <feTurbulence type="fractalNoise" baseFrequency="0.011 0.018" numOctaves="4" seed="8" result="noise">
              <animate attributeName="baseFrequency" dur="22s" repeatCount="indefinite"
                values="0.011 0.018; 0.02 0.012; 0.014 0.022; 0.011 0.018" />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="34" xChannelSelector="R" yChannelSelector="G" result="disp" />
            <feGaussianBlur in="disp" stdDeviation="3.2" />
          </filter>

          {/* second, slower smoke layer for depth */}
          <filter id={`${id}-smoke2`} x="-40%" y="-40%" width="180%" height="180%">
            <feTurbulence type="fractalNoise" baseFrequency="0.016 0.01" numOctaves="3" seed="21" result="n2">
              <animate attributeName="baseFrequency" dur="34s" repeatCount="indefinite"
                values="0.016 0.01; 0.009 0.02; 0.016 0.01" />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="n2" scale="26" xChannelSelector="R" yChannelSelector="G" result="d2" />
            <feGaussianBlur in="d2" stdDeviation="4" />
          </filter>

          <clipPath id={`${id}-clip`}><circle cx="100" cy="100" r="98" /></clipPath>
        </defs>

        <g clipPath={`url(#${id}-clip)`}>
          {/* base sphere */}
          <circle cx="100" cy="100" r="98" fill={`url(#${id}-gold)`} />

          {/* deep slow smoke */}
          <g filter={`url(#${id}-smoke2)`} opacity="0.75">
            <circle cx="70" cy="130" r="62" fill="#B4821E" />
            <circle cx="140" cy="80" r="54" fill="#F0D68A" />
            <circle cx="95" cy="60" r="46" fill="#8C6417" />
          </g>

          {/* bright flowing smoke */}
          <g filter={`url(#${id}-smoke)`}>
            <circle cx="72" cy="66" r="52" fill="#FFF6D0" opacity="0.85" />
            <circle cx="132" cy="120" r="58" fill="#E6BE58" opacity="0.7" />
            <circle cx="92" cy="140" r="44" fill="#FFFFFF" opacity="0.55" />
            <circle cx="140" cy="70" r="38" fill="#C99433" opacity="0.6" />
            <circle cx="55" cy="105" r="34" fill="#FFEDB0" opacity="0.6" />
          </g>

          {/* inner shading for volume */}
          <circle cx="100" cy="100" r="98" fill="none" stroke="rgba(120,80,10,0.45)" strokeWidth="14" opacity="0.5" />
          {/* top sheen */}
          <ellipse cx="82" cy="58" rx="46" ry="28" fill="#FFFFFF" opacity="0.4" style={{ filter: "blur(9px)" }} />
        </g>
      </motion.svg>
    </div>
  );
}
