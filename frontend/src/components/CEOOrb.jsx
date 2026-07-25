import { motion } from "framer-motion";

const COLORS = {
  gold: "#3B82F6",
  emerald: "#10B981",
  amber: "#F59E0B",
  ruby: "#EF4444",
};

// The CEO's voice signature: an animated sound wave rising out of smoke.
// Shown whenever the CEO "speaks" (tutorial, greeting, cards...).
export function CEOOrb({ size = 160, mood = "gold", className = "" }) {
  const color = COLORS[mood] || COLORS.gold;
  const bars = [0.32, 0.5, 0.68, 0.88, 1, 0.78, 1, 0.86, 0.66, 0.46, 0.3];
  const barW = size * 0.045;
  const gap = size * 0.028;
  const peak = size * 0.52;
  const wisps = [0.16, 0.34, 0.5, 0.66, 0.84];

  return (
    <div className={`relative flex items-center justify-center overflow-hidden ${className}`}
      style={{ width: size, height: size }} data-testid="ceo-orb">
      {/* smoky aura */}
      <motion.div
        className="absolute rounded-full"
        style={{ width: size * 1.1, height: size * 0.8, background: `radial-gradient(circle, ${color}44, transparent 68%)`, filter: `blur(${size * 0.06}px)` }}
        animate={{ scale: [1, 1.12, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* rising smoke wisps */}
      {wisps.map((x, i) => (
        <motion.div
          key={`s${i}`}
          className="absolute rounded-full"
          style={{
            width: size * (0.1 + (i % 3) * 0.04), height: size * (0.1 + (i % 3) * 0.04),
            left: `${x * 100}%`, top: "42%",
            background: `radial-gradient(circle, ${color}66, transparent 70%)`,
            filter: `blur(${size * 0.045}px)`, mixBlendMode: "screen",
          }}
          initial={{ y: size * 0.1, opacity: 0, scale: 0.5 }}
          animate={{ y: -size * (0.35 + (i % 3) * 0.1), opacity: [0, 0.7, 0], scale: [0.5, 1.2, 1.6] }}
          transition={{ duration: 3 + (i % 4) * 0.7, repeat: Infinity, ease: "easeOut", delay: i * 0.5 }}
        />
      ))}

      {/* sound wave bars */}
      <div className="relative flex items-center justify-center" style={{ gap, height: peak }}>
        {bars.map((h, i) => (
          <motion.div
            key={i}
            style={{
              width: barW, borderRadius: barW,
              background: `linear-gradient(to top, ${color}, #ffffff)`,
              boxShadow: `0 0 ${size * 0.06}px ${color}aa`,
            }}
            animate={{ height: [peak * h * 0.55, peak * h, peak * h * 0.4, peak * h * 0.85, peak * h * 0.55] }}
            transition={{ duration: 1.4 + (i % 4) * 0.35, repeat: Infinity, ease: "easeInOut", delay: i * 0.08 }}
          />
        ))}
      </div>
    </div>
  );
}
