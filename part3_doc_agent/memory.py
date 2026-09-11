from __future__ import annotations

import json
import re
from pathlib import Path

from core.config import settings
from core.logging_config import get_logger
from part3_doc_agent.models import MemoryFact, Turn

log = get_logger(__name__)

MAX_KEY_CHARS = 40
MAX_VALUE_CHARS = 200
SAFE_SESSION_ID = re.compile(r"[^A-Za-z0-9_-]+")
KEY_NORMALISE = re.compile(r"[^a-z0-9]+")

def normalise_session_id(raw: str) -> str:
    cleaned = SAFE_SESSION_ID.sub("-", (raw or "").strip()).strip("-")
    return cleaned[:64] or "default"

def _normalise_key(raw: str) -> str:
    key = KEY_NORMALISE.sub("_", (raw or "").strip().lower()).strip("_")
    key = key.removeprefix("user_").removeprefix("the_")
    return key[:MAX_KEY_CHARS]

class ConversationMemory:
    def __init__(
        self,
        session_id: str = "default",
        window_turns: int | None = None,
        max_facts: int | None = None,
        session_dir: Path | None = None,
    ) -> None:
        self.session_id = normalise_session_id(session_id)
        self.window_turns = window_turns or settings.memory_window_turns
        self.max_facts = max_facts or settings.memory_max_facts
        self.session_dir = session_dir or settings.session_dir
        self.turns: list[Turn] = []
        self.profile: dict[str, str] = {}

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content.strip()))
        overflow = len(self.turns) - self.window_turns * 2
        if overflow > 0:
            del self.turns[:overflow]

    def remember(self, facts: list[MemoryFact]) -> list[str]:
        changed: list[str] = []
        for fact in facts:
            key = _normalise_key(fact.key)
            value = (fact.value or "").strip()[:MAX_VALUE_CHARS]
            if not key or not value:
                continue
            if self.profile.get(key) == value:
                continue
            if key not in self.profile and len(self.profile) >= self.max_facts:
                log.warning("memory_full", session=self.session_id, dropped_key=key, limit=self.max_facts)
                continue
            self.profile[key] = value
            changed.append(key)

        if changed:
            log.info("memory_updated", session=self.session_id, keys=changed)
        return changed

    def clear(self) -> None:
        self.turns.clear()
        self.profile.clear()

    def recall(self, key: str) -> str | None:
        return self.profile.get(_normalise_key(key))

    def as_prompt_context(self) -> str:
        if not self.profile and not self.turns:
            return "This is the first turn. You have not been told anything about this user yet."

        blocks: list[str] = []
        if self.profile:
            facts = "\n".join(f"- {key}: {value}" for key, value in self.profile.items())
            blocks.append(f"What the user has told you about themselves:\n{facts}")
        else:
            blocks.append("The user has not told you anything about themselves yet.")

        if self.turns:
            history = "\n".join(f"{'User' if t.role == 'user' else 'Agent'}: {t.content}" for t in self.turns)
            blocks.append(f"Recent conversation (oldest first):\n{history}")

        return "\n\n".join(blocks)

    @property
    def path(self) -> Path:
        return self.session_dir / f"{self.session_id}.json"

    def save(self) -> Path:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": self.session_id,
            "profile": self.profile,
            "turns": [t.model_dump() for t in self.turns],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.path

    @classmethod
    def load(cls, session_id: str = "default", **kwargs) -> "ConversationMemory":
        memory = cls(session_id, **kwargs)
        if not memory.path.exists():
            return memory
        try:
            payload = json.loads(memory.path.read_text(encoding="utf-8"))
            memory.profile = {str(k): str(v) for k, v in dict(payload.get("profile", {})).items()}
            memory.turns = [Turn(**t) for t in payload.get("turns", [])]
            log.info("memory_loaded", session=memory.session_id, facts=len(memory.profile), turns=len(memory.turns))
        except Exception as exc:
            log.warning("memory_load_failed", session=memory.session_id, error=f"{type(exc).__name__}: {exc}")
            memory.clear()
        return memory
