export function applyPublicSeo({ title, description, canonicalPath }) {
  if (title) document.title = title;

  const canonicalHref = `${window.location.origin}${canonicalPath || window.location.pathname}`;
  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement("link");
    canonical.setAttribute("rel", "canonical");
    document.head.appendChild(canonical);
  }
  canonical.setAttribute("href", canonicalHref);

  if (description) {
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", "description");
      document.head.appendChild(meta);
    }
    meta.setAttribute("content", description);
  }

  const measurementId = process.env.REACT_APP_GA4_MEASUREMENT_ID;
  if (!measurementId || document.querySelector('script[data-testid="ga4-script"]')) return;
  const firstScript = document.createElement("script");
  firstScript.async = true;
  firstScript.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  firstScript.setAttribute("data-testid", "ga4-script");
  document.head.appendChild(firstScript);

  const secondScript = document.createElement("script");
  secondScript.setAttribute("data-testid", "ga4-config-script");
  secondScript.innerHTML = `window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);} gtag('js', new Date()); gtag('config', '${measurementId}');`;
  document.head.appendChild(secondScript);
}