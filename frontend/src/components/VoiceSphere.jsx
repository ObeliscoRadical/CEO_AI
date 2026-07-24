import { motion } from "framer-motion";
import { useRef } from "react";

// "Living Sun" (NASA-style): boiling orange-red plasma surface with erupting
// magnetic flare loops, prominences and a hot fusion core.
export function VoiceSphere({ size = 170, className = "", ripple = false }) {
  const id = useRef(`sun-${Math.random().toString(36).slice(2, 8)}`).current;
  const R = 60; // core radius in 200x200 viewBox

  // magnetic loop path: two footpoints on the rim, arcing outward to an apex
  const loopPath = (deg, spread, apex) => {
    const a1 = ((deg - spread) * Math.PI) / 180, a2 = ((deg + spread) * Math.PI) / 180, ac = (deg * Math.PI) / 180;
    const x1 = 100 + R * Math.cos(a1), y1 = 100 + R * Math.sin(a1);
    const x2 = 100 + R * Math.cos(a2), y2 = 100 + R * Math.sin(a2);
    const mx = 100 + apex * Math.cos(ac), my = 100 + apex * Math.sin(ac);
    return `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${mx.toFixed(1)} ${my.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const loops = [
    { d: loopPath(-70, 11, 90), dur: 3.4 }, { d: loopPath(-40, 8, 80), dur: 2.6 },
    { d: loopPath(-110, 9, 84), dur: 3.0 }, { d: loopPath(200, 12, 92), dur: 3.8 },
    { d: loopPath(-15, 7, 76), dur: 2.9 }, { d: loopPath(160, 8, 78), dur: 3.3 },
    { d: loopPath(-90, 14, 96), dur: 4.2 },
  ];

  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }} data-testid="voice-sphere">
      {/* radiant heat glow */}
      <motion.div
        className="absolute rounded-full"
        style={{ inset: -size * 0.4, background: "radial-gradient(circle, rgba(255,110,30,0.4), rgba(200,45,10,0.14) 45%, transparent 70%)", filter: `blur(${size * 0.11}px)` }}
        animate={{ opacity: [0.6, 1, 0.6], scale: [1, 1.12, 1] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* energy pulse from the core */}
      <motion.div
        className="absolute rounded-full"
        style={{ width: size * 0.6, height: size * 0.6, boxShadow: "0 0 46px 10px rgba(255,140,40,0.55)" }}
        animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeOut" }}
      />

      <svg width={size} height={size} viewBox="0 0 200 200" className="absolute" style={{ filter: "drop-shadow(0 0 30px rgba(255,120,30,0.6))" }}>
        <defs>
          <radialGradient id={`${id}-core`} cx="48%" cy="42%" r="62%">
            <stop offset="0%" stopColor="#FFFCEF" />
            <stop offset="16%" stopColor="#FFE58A" />
            <stop offset="42%" stopColor="#FF9E2C" />
            <stop offset="70%" stopColor="#F1531A" />
            <stop offset="100%" stopColor="#A81805" />
          </radialGradient>
          <linearGradient id={`${id}-loop`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFF3C0" />
            <stop offset="50%" stopColor="#FF9A2E" />
            <stop offset="100%" stopColor="rgba(255,80,20,0)" />
          </linearGradient>
          {/* boiling plasma displacement */}
          <filter id={`${id}-plasma`} x="-25%" y="-25%" width="150%" height="150%">
            <feTurbulence type="fractalNoise" baseFrequency="0.022 0.03" numOctaves="5" seed="7" result="n">
              <animate attributeName="baseFrequency" dur="11s" repeatCount="indefinite"
                values="0.022 0.03; 0.034 0.02; 0.024 0.036; 0.022 0.03" />
            </feTurbulence>
            <feDisplacementMap in="SourceGraphic" in2="n" scale="26" xChannelSelector="R" yChannelSelector="G" result="d" />
            <feGaussianBlur in="d" stdDeviation="1.1" />
          </filter>
          {/* fine granulation texture */}
          <filter id={`${id}-gran`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" result="g">
              <animate attributeName="seed" dur="6s" values="3;9;3" repeatCount="indefinite" />
            </feTurbulence>
            <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.9 0.6 0.2 0 0" />
          </filter>
          <filter id={`${id}-glow`} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="1.6" />
          </filter>
          <clipPath id={`${id}-clip`}><circle cx="100" cy="100" r={R} /></clipPath>
        </defs>

        {/* erupting magnetic loops (behind + front of the disk edge) */}
        <g filter={`url(#${id}-glow)`}>
          {loops.map((l, i) => (
            <motion.path key={i} d={l.d} fill="none" stroke={`url(#${id}-loop)`} strokeWidth="2.4" strokeLinecap="round"
              animate={{ opacity: [0.25, 0.95, 0.4, 0.8], pathLength: [0.7, 1, 0.85, 1] }}
              transition={{ duration: l.dur, repeat: Infinity, ease: "easeInOut", delay: i * 0.4 }} />
          ))}
        </g>

        {/* plasma disk */}
        <g clipPath={`url(#${id}-clip)`}>
          <circle cx="100" cy="100" r={R} fill={`url(#${id}-core)`} />
          <g filter={`url(#${id}-plasma)`}>
            <circle cx="72" cy="80" r="40" fill="#FFF2C0" opacity="0.9" />
            <circle cx="130" cy="120" r="44" fill="#FF7A1E" opacity="0.8" />
            <circle cx="96" cy="140" r="32" fill="#B72006" opacity="0.75" />
            <circle cx="126" cy="66" r="28" fill="#FFFFFF" opacity="0.85" />
            <circle cx="58" cy="118" r="24" fill="#E24810" opacity="0.8" />
            <circle cx="100" cy="100" r="18" fill="#FFF8E0" opacity="0.7" />
          </g>
          {/* churning granulation */}
          <motion.rect x="0" y="0" width="200" height="200" filter={`url(#${id}-gran)`}
            animate={{ opacity: [0.12, 0.28, 0.12] }} transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }} />
          {/* limb darkening */}
          <circle cx="100" cy="100" r={R} fill="none" stroke="rgba(120,25,4,0.75)" strokeWidth="12" opacity="0.6" />
          {/* bright fusion center */}
          <motion.circle cx="90" cy="84" r="26" fill="#FFFFFF"
            animate={{ opacity: [0.4, 0.65, 0.4], r: [24, 30, 24] }} transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
            style={{ filter: "blur(7px)" }} />
        </g>

        {/* prominences flickering on the rim */}
        {[18, 55, 120, 165, 220, 275, 315].map((deg, i) => {
          const ac = (deg * Math.PI) / 180;
          const x = 100 + (R - 2) * Math.cos(ac), y = 100 + (R - 2) * Math.sin(ac);
          return (
            <motion.ellipse key={i} cx={x} cy={y} rx="4" ry={7 + (i % 3) * 3} fill={`url(#${id}-loop)`}
              transform={`rotate(${deg + 90} ${x} ${y})`}
              animate={{ opacity: [0.3, 0.9, 0.4], ry: [6, 12, 7] }}
              transition={{ duration: 2.4 + (i % 3), repeat: Infinity, ease: "easeInOut", delay: i * 0.3 }} />
          );
        })}
      </svg>
    </div>
  );
}
