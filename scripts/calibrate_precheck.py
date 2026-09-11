from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.embeddings import get_embedder
from part1_email_agent.precheck import CriticalSignalDetector

MUST_CATCH = [
    "Semua karyawan di kantor Jakarta melaporkan halaman login hanya berputar terus dan tidak ada "
    "satu pun dari staf kami yang berhasil masuk ke platform sejak pukul tujuh pagi.",
    "Nobody in our office has been able to open the application since this morning.",
    "Our whole team is stuck, the platform will not load for anyone.",
    "Sepertinya ada orang lain yang masuk ke akun perusahaan kami tanpa izin.",
    "There are logins from an IP address in another country that we do not recognise.",
    "半分のデータが消えました",
    "Setelah migrasi kemarin, sebagian besar catatan pelanggan kami tidak ditemukan lagi.",
]

MUST_NOT_CATCH = [
    "Halo, sejak pagi saya tidak bisa masuk ke akun saya. Bagaimana caranya reset password?",
    "Hi, since this morning I cannot get into my account. How do I reset my password?",
    "I forgot my password and the reset email never arrived.",
    "bagaimana cara menambah user di akun saya",
    "How do I add another user to my account?",
    "Tolong hapus satu pengguna dari akun kami karena sudah resign.",
    "Where can I download a copy of my invoice for our finance department?",
    "Could you confirm which day of the month we are normally charged?",
    "Saya ingin menambah lima pengguna baru di paket Google Workspace kami.",
    "It would be great if the dashboard had a dark mode.",
    "Tagihan JumpCloud kami bulan ini naik, bagaimana cara mendapatkan fakturnya?",
    "We subscribed to the annual plan last week and want to know the refund rules.",
    "Please transfer admin rights to our new IT manager.",
    "Halaman dokumentasi API kalian sepertinya perlu contoh yang lebih banyak.",
]

def main() -> None:
    detector = CriticalSignalDetector(embedder=get_embedder(), threshold=0.0)

    def best(text: str) -> tuple[str, float]:
        category, critical, _benign = detector.score_semantic(text)
        return category or "none", critical

    def verdict(text: str) -> str:
        if detector.match_keywords(text):
            return "ESCALATE (keyword)"
        hit = CriticalSignalDetector(embedder=get_embedder()).match_semantic(text)
        return "ESCALATE (semantic)" if hit else "pass"

    print("\nMUST CATCH (critical, paraphrased - keyword layer deliberately bypassed)")
    catch_scores = []
    for text in MUST_CATCH:
        category, score = best(text)
        catch_scores.append(score)
        print(f"  {score:.3f}  {category:<16} {verdict(text):<20} {text[:56]}")

    print("\nMUST NOT CATCH (ordinary support email)")
    ignore_scores = []
    for text in MUST_NOT_CATCH:
        category, score = best(text)
        ignore_scores.append(score)
        print(f"  {score:.3f}  {category:<16} {verdict(text):<20} {text[:56]}")

    missed = [t for t in MUST_CATCH if verdict(t) == "pass"]
    false_alarms = [t for t in MUST_NOT_CATCH if verdict(t) != "pass"]

    print("\n" + "-" * 78)
    print(f"  raw incident score range : critical {min(catch_scores):.3f}-{max(catch_scores):.3f}"
          f"  |  ordinary {min(ignore_scores):.3f}-{max(ignore_scores):.3f}")
    if min(catch_scores) <= max(ignore_scores):
        print("  These overlap, so no single threshold separates them — which is exactly")
        print("  why the detector also scores against BENIGN_ANCHORS and requires the")
        print("  incident side to win. Judge the rows above by their verdict, not their score.")

    print(f"\n  missed incidents      : {len(missed)} of {len(MUST_CATCH)}")
    print(f"  false escalations     : {len(false_alarms)} of {len(MUST_NOT_CATCH)}")
    for text in missed:
        print(f"    MISSED       {text[:66]}")
    for text in false_alarms:
        print(f"    FALSE ALARM  {text[:66]}")
    if not missed and not false_alarms:
        print("\n  Every case decided correctly.")

if __name__ == "__main__":
    main()
