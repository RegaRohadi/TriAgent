const FALLBACK_PORTS = { part1: 8000, part2: 8002, part3: 8001 };

function meta(name) {
  if (typeof document === "undefined") return null;
  const value = document.querySelector(`meta[name="${name}"]`)?.getAttribute("content");
  return value && !value.startsWith("__") ? value : null;
}

export const PORTS = (() => {
  try {
    return { ...FALLBACK_PORTS, ...JSON.parse(meta("triagent-ports") || "{}") };
  } catch {
    return FALLBACK_PORTS;
  }
})();

export const DEFAULT_TAB = meta("triagent-default-tab") || "part1";

export function apiBase(part) {
  const port = PORTS[part];
  if (!port) return "";
  return `${window.location.protocol}//${window.location.hostname}:${port}`;
}

function describeDetail(detail, fallback) {
  if (Array.isArray(detail)) return detail.map((item) => item.msg || String(item)).join("; ");
  return detail || fallback;
}

export async function apiRequest(part, path, options) {
  let response;
  try {
    response = await fetch(`${apiBase(part)}${path}`, options);
  } catch {
    throw new Error(
      `Cannot reach ${part} at ${apiBase(part)} — is that service running?`,
    );
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : null;
  if (!response.ok) throw new Error(describeDetail(data?.detail, response.statusText));
  return data;
}

export function postJson(part, path, payload) {
  return apiRequest(part, path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
