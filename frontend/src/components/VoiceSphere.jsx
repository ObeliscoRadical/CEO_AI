import { motion } from "framer-motion";

// Soft, cloud-like gaseous sphere (ChatGPT voice style) in gold/amber tones.
export function VoiceSphere({ size = 160, className = "" }) {
  const blob = (i, color, x, y, s, dur) => (
    <motion.div
      key={i}
      className="absolute rounded-full"
      style={{ width: size * s, height: size * s, background: color, filter: `blur(${size * 0.09}px)`, mixBlendMode: "screen" }}
      initial={{ x: x, y: y }}
      animate={{ x: [x, x + size * 0.12, x - size * 0.08, x], y: [y, y - size * 0.1, y + size * 0.1, y], scale: [1, 1.15, 0.92, 1] }}
      transition={{ duration: dur, repeat: Infinity, ease: "easeInOut" }}
    />
  );

  return (
    <div
      className={`relative ${className}`}
      style={{ width: size, height: size }}
      data-testid="voice-sphere"
    >
      {/* outer glow */}
      <div
        className="absolute rounded-full"
        style={{ inset: -size * 0.18, background: `radial-gradient(circle, rgba(212,175,55,0.35), transparent 68%)`, filter: `blur(${size * 0.06}px)` }}
      />
      {/* sphere body */}
      <motion.div
        className="absolute inset-0 rounded-full overflow-hidden"
        style={{
          background: "radial-gradient(circle at 50% 22%, #FBE9C4 0%, #E9C766 34%, #C9982E 72%, #A8781F 100%)",
          boxShadow: "inset 0 0 40px rgba(255,255,255,0.35), inset 0 -20px 50px rgba(120,80,10,0.45)",
        }}
        animate={{ rotate: [0, 8, -6, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* drifting gaseous clouds */}
        {blob(0, "radial-gradient(circle, rgba(255,246,214,0.9), transparent 60%)", size * 0.12, size * 0.10, 0.7, 9)}
        {blob(1, "radial-gradient(circle, rgba(224,181,74,0.85), transparent 60%)", size * 0.45, size * 0.42, 0.8, 12)}
        {blob(2, "radial-gradient(circle, rgba(255,255,255,0.7), transparent 55%)", size * 0.30, size * 0.55, 0.55, 10)}
        {blob(3, "radial-gradient(circle, rgba(180,130,30,0.7), transparent 60%)", size * 0.05, size * 0.5, 0.65, 14)}
        {blob(4, "radial-gradient(circle, rgba(255,232,170,0.8), transparent 55%)", size * 0.55, size * 0.12, 0.5, 8)}
        {/* top sheen */}
        <div
          className="absolute rounded-full"
          style={{ top: size * 0.08, left: size * 0.18, width: size * 0.5, height: size * 0.32, background: "radial-gradient(circle, rgba(255,255,255,0.65), transparent 70%)", filter: `blur(${size * 0.05}px)` }}
        />
      </motion.div>
    </div>
  );
}
