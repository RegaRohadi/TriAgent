export const TABS = ["part1", "part2", "part3"];
export const FETCH_POLL_MS = 700;

export const STATUS_LABEL = {
  auto_replied: "auto replied",
  open: "needs a human",
  resolved: "resolved by human",
  ignored: "ignored",
};

export const STATUS_COLOR = {
  auto_replied: "lime",
  auto_reply: "lime",
  open: "rose",
  route_to_human: "rose",
  failed: "rose",
  resolved: "blue",
  ignored: "neutral",
  queued: "neutral",
  skipped: "neutral",
  processing: "yellow",
};

export const NOTE_TONE = {
  ok: "text-status-lime-text",
  err: "text-text-error-primary",
  note: "text-text-secondary",
};

export function validTab(tab) {
  return TABS.includes(tab) ? tab : "part1";
}
