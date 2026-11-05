import { apiRequest, postJson } from "./backend.js";

export const api2 = {
  health: () => apiRequest("part2", "/api/health"),
  summarize: (payload) => postJson("part2", "/api/summarize", payload),
  compare: (payload) => postJson("part2", "/api/compare", payload),
};
