async function request(path, options) {
  const res = await fetch(path, options);
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;
  if (!res.ok) throw new Error(data?.detail || res.statusText);
  return data;
}

export const api = {
  health: () => request("/api/health"),
  samples: () => request("/api/samples"),
  process: (payload) =>
    request("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  fetchNow: () => request("/api/fetch-now", { method: "POST" }),
  fetchStatus: (jobId) => request(`/api/fetch-status/${jobId}`),
  tickets: (status) => request(`/api/tickets${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  ticket: (traceId) => request(`/api/tickets/${encodeURIComponent(traceId)}`),
  replyAsHuman: (traceId, text) =>
    request(`/api/tickets/${encodeURIComponent(traceId)}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
};
