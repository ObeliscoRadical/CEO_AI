export function Watermark({ text, className = "" }) {
  if (!text) return null;
  return (
    <span aria-hidden="true" className={`watermark text-[20vw] md:text-[11rem] ${className}`}>{text}</span>
  );
}
