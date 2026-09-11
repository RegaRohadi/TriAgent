from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"} if raw else default

@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip())
    gemini_model_fallbacks: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_MODEL_FALLBACKS",
            "gemini-3.1-flash-lite,gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash,gemini-3-flash",
        ).strip()
    )

    embedding_backend: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_BACKEND", "sentence-transformers").strip()
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2").strip()
    )

    semantic_precheck_threshold: float = field(default_factory=lambda: _env_float("SEMANTIC_PRECHECK_THRESHOLD", 0.45))
    retrieval_min_score: float = field(default_factory=lambda: _env_float("RETRIEVAL_MIN_SCORE", 0.30))
    retrieval_top_k: int = field(default_factory=lambda: _env_int("RETRIEVAL_TOP_K", 8))
    classification_confidence_threshold: float = field(
        default_factory=lambda: _env_float("CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.6)
    )
    refund_amount_threshold_usd: float = field(default_factory=lambda: _env_float("REFUND_AMOUNT_THRESHOLD_USD", 500))
    refund_age_days_threshold: int = field(default_factory=lambda: _env_int("REFUND_AGE_DAYS_THRESHOLD", 90))
    contact_frequency_threshold: int = field(default_factory=lambda: _env_int("CONTACT_FREQUENCY_THRESHOLD", 3))
    contact_frequency_window_days: int = field(default_factory=lambda: _env_int("CONTACT_FREQUENCY_WINDOW_DAYS", 7))
    max_redraft_attempts: int = field(default_factory=lambda: _env_int("MAX_REDRAFT_ATTEMPTS", 1))
    max_message_attempts: int = field(default_factory=lambda: _env_int("MAX_MESSAGE_ATTEMPTS", 3))
    message_claim_ttl_seconds: int = field(default_factory=lambda: _env_int("MESSAGE_CLAIM_TTL_SECONDS", 600))

    log_json: bool = field(default_factory=lambda: _env_bool("LOG_JSON", False))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO")

    kb_pdf_dir: Path = PROJECT_ROOT / "knowledge_base" / "pdf"
    data_dir: Path = PROJECT_ROOT / "data"
    db_path: Path = PROJECT_ROOT / "data" / "support.db"
    index_cache_dir: Path = PROJECT_ROOT / "data" / "index_cache"
    sample_email_dir: Path = PROJECT_ROOT / "data" / "sample_emails"
    chat_document_path: Path = PROJECT_ROOT / "part3_doc_agent" / "sample_document.md"
    session_dir: Path = PROJECT_ROOT / "data" / "part3_sessions"

    imap_host: str = field(default_factory=lambda: os.getenv("IMAP_HOST", "").strip())
    imap_port: int = field(default_factory=lambda: _env_int("IMAP_PORT", 993))
    imap_user: str = field(default_factory=lambda: os.getenv("IMAP_USER", "").strip())
    imap_password: str = field(default_factory=lambda: os.getenv("IMAP_PASSWORD", "").strip())
    imap_folder: str = field(default_factory=lambda: os.getenv("IMAP_FOLDER", "INBOX").strip())

    scraper_max_bytes: int = field(default_factory=lambda: _env_int("SCRAPER_MAX_BYTES", 5_000_000))
    scraper_connect_timeout: float = field(default_factory=lambda: _env_float("SCRAPER_CONNECT_TIMEOUT", 5))
    scraper_read_timeout: float = field(default_factory=lambda: _env_float("SCRAPER_READ_TIMEOUT", 15))
    scraper_camoufox_enabled: bool = field(default_factory=lambda: _env_bool("SCRAPER_CAMOUFOX_ENABLED", False))
    scraper_camoufox_timeout: float = field(default_factory=lambda: _env_float("SCRAPER_CAMOUFOX_TIMEOUT", 30))
    chunk_max_tokens: int = field(default_factory=lambda: _env_int("CHUNK_MAX_TOKENS", 2000))
    chunk_overlap_tokens: int = field(default_factory=lambda: _env_int("CHUNK_OVERLAP_TOKENS", 150))
    map_workers: int = field(default_factory=lambda: _env_int("MAP_WORKERS", 3))
    summary_max_words: int = field(default_factory=lambda: _env_int("SUMMARY_MAX_WORDS", 100))
    summary_min_words: int = field(default_factory=lambda: _env_int("SUMMARY_MIN_WORDS", 20))

    memory_window_turns: int = field(default_factory=lambda: _env_int("MEMORY_WINDOW_TURNS", 6))
    memory_max_facts: int = field(default_factory=lambda: _env_int("MEMORY_MAX_FACTS", 25))
    chat_retrieval_top_k: int = field(default_factory=lambda: _env_int("CHAT_RETRIEVAL_TOP_K", 6))
    chat_retrieval_min_score: float = field(default_factory=lambda: _env_float("CHAT_RETRIEVAL_MIN_SCORE", 0.25))

    scraper_port: int = field(default_factory=lambda: _env_int("SCRAPER_PORT", 8002))
    chat_port: int = field(default_factory=lambda: _env_int("CHAT_PORT", 8001))

    poll_interval_seconds: float = field(default_factory=lambda: _env_float("POLL_INTERVAL_SECONDS", 60))
    poll_batch_size: int = field(default_factory=lambda: _env_int("POLL_BATCH_SIZE", 10))

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "").strip())
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 587))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", "").strip())
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", "").strip())
    smtp_from_address: str = field(default_factory=lambda: os.getenv("SMTP_FROM_ADDRESS", "").strip())
    smtp_from_name: str = field(default_factory=lambda: os.getenv("SMTP_FROM_NAME", "Rega's Support").strip())

    @property
    def gemini_models(self) -> list[str]:
        names = [self.gemini_model, *(m.strip() for m in self.gemini_model_fallbacks.split(","))]
        seen: set[str] = set()
        return [n for n in names if n and not (n in seen or seen.add(n))]

    @property
    def llm_backend(self) -> str:
        explicit = os.getenv("LLM_BACKEND", "").strip().lower()
        if explicit:
            return explicit
        return "gemini" if self.gemini_api_key else "mock"

    @property
    def imap_enabled(self) -> bool:
        return bool(self.imap_host and self.imap_user and self.imap_password)

    @property
    def poll_enabled(self) -> bool:
        return os.getenv("POLL_ENABLED", "").strip().lower() in {"1", "true", "yes"} and self.imap_enabled

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.smtp_from_address)

settings = Settings()
