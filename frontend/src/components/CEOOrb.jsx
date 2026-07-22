import { motion } from "framer-motion";

const COLORS = {
  gold: "#D4AF37",
  emerald: "#10B981",
  amber: "#F59E0B",
  ruby: "#EF4444",
};

export function CEOOrb({ size = 160, mood = "gold", className = "" }) {
  const color = COLORS[mood] || COLORS.gold;
  return (
    <div className={`relative flex items-center justify-center ${className}`} style={{ width: size, height: size }} data-testid="ceo-orb">
      <motion.div
        className="absolute rounded-full"
        style={{
          width: size, height: size,
          background: `radial-gradient(circle at 35% 30%, ${color}ee, ${color}55 45%, transparent 70%)`,
          filter: "blur(2px)",
        }}
        animate={{ scale: [1, 1.06, 1], opacity: [0.85, 1, 0.85] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute rounded-full"
        style={{ width: size * 1.5, height: size * 1.5, background: `radial-gradient(circle, ${color}22, transparent 65%)` }}
        animate={{ scale: [1, 1.15, 1] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute rounded-full border"
        style={{ width: size * 0.7, height: size * 0.7, borderColor: `${color}66` }}
        animate={{ rotate: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      />
      <div
        className="absolute rounded-full"
        style={{ width: size * 0.34, height: size * 0.34, background: `radial-gradient(circle at 40% 35%, #fff, ${color})`, boxShadow: `0 0 30px ${color}` }}
      />
    </div>
  );
}
