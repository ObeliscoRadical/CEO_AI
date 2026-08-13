import { API } from "@/lib/api";

async function fetchJson(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`Falha ao carregar ${path}`);
  return res.json();
}

export async function fetchPublicSections(slotKeys = []) {
  if (!slotKeys.length) return {};
  const data = await fetchJson(`/public/site/sections?slots=${encodeURIComponent(slotKeys.join(","))}`);
  return data.sections || {};
}

export async function fetchPublicEntries(kind = "article") {
  const data = await fetchJson(`/public/site/entries?kind=${encodeURIComponent(kind)}`);
  return data.entries || [];
}

export async function fetchPublicArticle(slug) {
  const data = await fetchJson(`/public/site/article/${slug}`);
  return data.entry;
}

export async function fetchPublicPage(slug) {
  const data = await fetchJson(`/public/site/page/${slug}`);
  return data.entry;
}

export async function trackPublicView(kind, slug) {
  await fetch(`${API}/public/site/view/${kind}/${slug}`, { method: "POST" });
}

export async function trackPublicSurface(pageKey, path, title = "") {
  await fetch(`${API}/public/site/track-static`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_key: pageKey, path, title }),
  });
}