import { apiRequest, postJson } from "./backend.js";

const get = (path) => apiRequest("part1", path);

export const api = {
  health: () => get("/api/health"),
  samples: () => get("/api/samples"),
  process: (payload) => postJson("part1", "/api/process", payload),
  fetchNow: () => apiRequest("part1", "/api/fetch-now", { method: "POST" }),
  fetchStatus: (jobId) => get(`/api/fetch-status/${jobId}`),
  tickets: (status) => get(`/api/tickets${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  ticket: (traceId) => get(`/api/tickets/${encodeURIComponent(traceId)}`),
  replyAsHuman: (traceId, text) => postJson("part1", `/api/tickets/${encodeURIComponent(traceId)}/reply`, { text }),
};
