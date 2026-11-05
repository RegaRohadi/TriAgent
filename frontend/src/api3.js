import { apiRequest, postJson } from "./backend.js";

export const api3 = {
  health: () => apiRequest("part3", "/api/health"),
  session: (sessionId) => apiRequest("part3", `/api/session/${encodeURIComponent(sessionId)}`),
  clearSession: (sessionId) =>
    apiRequest("part3", `/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),
  chat: (message, sessionId) => postJson("part3", "/api/chat", { message, session_id: sessionId }),
};
