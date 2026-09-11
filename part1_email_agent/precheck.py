from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from core.config import settings
from core.embeddings import Embedder, get_embedder

CRITICAL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "data_loss": [
        re.compile(r"\bdata\s*(loss|lost|corrupt(ed|ion)?)\b", re.I),
        re.compile(r"\b(lost|missing|deleted|disappear(ed|ing)?)\s+(all\s+)?(my|our|the)?\s*(data|records?|files?)\b", re.I),
        re.compile(r"\b(data|records?|files?)\s+(\w+\s+){0,3}(disappear(ed)?|vanished|are\s+gone|were\s+deleted)\b", re.I),
        re.compile(r"\bdata\s*(saya|kami)\s*(hilang|terhapus|rusak)\b", re.I),
        re.compile(r"\b(record|file|dokumen)\s*(saya|kami)?\s*(hilang|terhapus)\b", re.I),
    ],
    "service_outage": [
        re.compile(r"\b(service\s+)?outage\b", re.I),
        re.compile(r"\b(system|service|platform|server)\s+(is\s+)?(down|offline|unavailable)\b", re.I),
        re.compile(r"\bdowntime\b", re.I),
        re.compile(r"\b(sistem|layanan|server)\s*(sedang\s*)?(mati|down|tidak\s*bisa\s*diakses)\b", re.I),
    ],
    "security_breach": [
        re.compile(r"\bsecurity\s+(breach|incident)\b", re.I),
        re.compile(r"\b(hacked|hacker|breached|compromised)\b", re.I),
        re.compile(r"\bunauthori[sz]ed\s+(access|login)\b", re.I),
        re.compile(r"\b(akun|sistem)\s*(saya|kami)?\s*(di)?(bobol|retas|hack)\b", re.I),
    ],
}

SEMANTIC_ANCHORS: dict[str, list[str]] = {
    "data_loss": [
        "I lost all my data after the sync",
        "our records disappeared completely from the system",
        "most of our customer entries are no longer there after the migration",
        "the information we entered last week is simply not in the system anymore",
        "semua data kami tidak ada lagi setelah sinkronisasi",
        "sebagian besar catatan pelanggan kami tidak ditemukan lagi",
        "seluruh riwayat transaksi kami menghilang begitu saja",
    ],
    "service_outage": [
        "the service is completely unavailable right now",
        "nobody on my team can open the application since this morning",
        "the login page just keeps spinning and no one can get in",
        "none of our staff can sign in to the platform and all work has stopped",
        "our entire office is blocked because the system will not load",
        "seluruh tim kami tidak bisa membuka aplikasi sejak tadi pagi",
        "halaman login hanya berputar terus dan tidak ada yang berhasil masuk",
        "tidak ada satu pun karyawan yang bisa masuk ke platform dan pekerjaan berhenti",
    ],
    "security_breach": [
        "someone accessed my account without permission",
        "there are suspicious logins from an unknown location",
        "we see sign-ins from an IP address in a country we do not operate in",
        "ada orang lain yang masuk ke akun kami tanpa izin",
        "sepertinya kredensial perusahaan kami sudah bocor ke pihak luar",
    ],
}

BENIGN_ANCHORS: list[str] = [
    "how do I add or remove users on my account",
    "bagaimana cara menambah user baru di akun saya",
    "please transfer the admin role to our new IT manager",
    "saya ingin menghapus salah satu pengguna dari akun kami",
    "I forgot my password and cannot log in, how do I reset it",
    "saya tidak bisa login ke akun saya, bagaimana cara reset password",
    "the password reset email never arrived",
    "where can I download a copy of my invoice",
    "bagaimana cara mendapatkan faktur tagihan bulan ini",
    "I would like to upgrade our subscription plan",
]

CONTRASTIVE_MARGIN = 0.05

@dataclass
class PrecheckOutcome:
    triggered: bool
    reason: str | None = None
    evidence: str | None = None
    score: float | None = None

class CriticalSignalDetector:
    def __init__(self, embedder: Embedder | None = None, threshold: float | None = None) -> None:
        self._embedder = embedder or get_embedder()
        self._threshold = settings.semantic_precheck_threshold if threshold is None else threshold
        self._anchor_vectors = {
            category: np.asarray(self._embedder.encode(sentences), dtype=np.float32)
            for category, sentences in SEMANTIC_ANCHORS.items()
        }
        self._benign_vectors = np.asarray(self._embedder.encode(BENIGN_ANCHORS), dtype=np.float32)

    @staticmethod
    def match_keywords(text: str) -> tuple[str, str] | None:
        for category, patterns in CRITICAL_PATTERNS.items():
            for pattern in patterns:
                found = pattern.search(text)
                if found:
                    return category, found.group(0)
        return None

    def score_semantic(self, text: str) -> tuple[str | None, float, float]:
        query = np.asarray(self._embedder.encode(text), dtype=np.float32)

        best_category, best_score = None, 0.0
        for category, anchors in self._anchor_vectors.items():
            score = float((anchors @ query).max())
            if score > best_score:
                best_category, best_score = category, score

        benign_score = float((self._benign_vectors @ query).max())
        return best_category, best_score, benign_score

    def match_semantic(self, text: str) -> tuple[str, float] | None:
        category, critical_score, benign_score = self.score_semantic(text)
        if not category or critical_score < self._threshold:
            return None
        if critical_score <= benign_score - CONTRASTIVE_MARGIN:
            return None
        return category, critical_score

    def detect(self, text: str) -> PrecheckOutcome:
        keyword_hit = self.match_keywords(text)
        if keyword_hit:
            category, matched = keyword_hit
            return PrecheckOutcome(True, f"critical_keyword:{category}", evidence=matched)

        semantic_hit = self.match_semantic(text)
        if semantic_hit:
            category, score = semantic_hit
            return PrecheckOutcome(
                True, f"critical_semantic:{category}", evidence=f"cosine={score:.2f}", score=score
            )

        return PrecheckOutcome(False)
