"""
RAG Accuracy Test — Namal University Overview
==============================================
Standalone script (not pytest). Hits the live backend at localhost:8000.

Usage:
    cd backend
    python tests/rag_accuracy_test.py

Output:
    RAG_ACCURACY_REPORT.md  (project root)
    tests/rag_raw_responses.json  (all raw API responses)
"""

import json
import time
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing 'requests'. Run: pip install requests")

BASE_URL = "http://localhost:8000"
PDF_PATH = Path(__file__).parent.parent / "data" / "clients" / "16810180-ad46-42e7-9eb0-e325d3b25886" / "uploads" / "Namal_University_Overview.pdf"
REPORT_PATH = Path(__file__).parent.parent.parent / "RAG_ACCURACY_REPORT.md"
RAW_PATH = Path(__file__).parent / "rag_raw_responses.json"

# ── Test Questions ────────────────────────────────────────────────────────────
#
# Each question has:
#   question       — what is sent to the RAG API
#   expected_kws   — list of keyword groups; PASS requires all groups to match
#                    each group is a list of alternatives (OR), groups are AND-ed
#   should_answer  — True if the doc contains the answer; False = adversarial
#   category       — display grouping
#   difficulty     — Easy / Medium / Hard
#   notes          — ground truth summary for the report

TEST_CASES = [
    # ── Category 1: Simple Factual ────────────────────────────────────────────
    {
        "id": "F1",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "Where is Namal University located?",
        "expected_kws": [["mianwali"], ["punjab", "talagang"]],
        "should_answer": True,
        "notes": "30 km Talagang Road, Mianwali, Punjab 42250",
    },
    {
        "id": "F2",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "Who is the founder of Namal University?",
        "expected_kws": [["imran khan"]],
        "should_answer": True,
        "notes": "Imran Khan conceived the vision in 2005",
    },
    {
        "id": "F3",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "Who is the current Rector of Namal University?",
        "expected_kws": [["najam", "najam ul islam"]],
        "should_answer": True,
        "notes": "Dr. M. Najam ul Islam",
    },
    {
        "id": "F4",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "What year was Namal College established?",
        "expected_kws": [["2008"]],
        "should_answer": True,
        "notes": "Namal College established in 2008",
    },
    {
        "id": "F5",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "What is the minimum eligibility percentage required for admission at Namal University?",
        "expected_kws": [["70%", "70 percent", "70"]],
        "should_answer": True,
        "notes": "At least 70% marks in Intermediate/equivalent",
    },
    {
        "id": "F6",
        "category": "Simple Factual",
        "difficulty": "Easy",
        "question": "What is the contact email address of Namal University?",
        "expected_kws": [["info@namal.edu.pk"]],
        "should_answer": True,
        "notes": "info@namal.edu.pk",
    },
    # ── Category 2: Medium Extraction ─────────────────────────────────────────
    {
        "id": "M1",
        "category": "Medium Extraction",
        "difficulty": "Medium",
        "question": "What undergraduate programs does Namal University offer?",
        "expected_kws": [
            ["electrical engineering", "bs ee", "bsee"],
            ["computer science", "bs cs"],
            ["bba", "business"],
            ["mathematics", "bs math"],
        ],
        "should_answer": True,
        "notes": "BS EE, BS CS, BBA, BS Mathematics",
    },
    {
        "id": "M2",
        "category": "Medium Extraction",
        "difficulty": "Medium",
        "question": "How is the merit/aggregate calculated for admissions at Namal University?",
        "expected_kws": [["43%", "43 percent"], ["intermediate", "entry test"]],
        "should_answer": True,
        "notes": "43% Intermediate marks + 43% Entry Test score",
    },
    {
        "id": "M3",
        "category": "Medium Extraction",
        "difficulty": "Medium",
        "question": "What is the Elite 90 Scholarship at Namal University?",
        "expected_kws": [["100%", "full", "waiver"], ["90%", "90 percent"]],
        "should_answer": True,
        "notes": "100% tuition fee waiver for candidates with 90%+ in Intermediate",
    },
    {
        "id": "M4",
        "category": "Medium Extraction",
        "difficulty": "Medium",
        "question": "What is CAID and who is its director?",
        "expected_kws": [["ai", "big data", "artificial intelligence"], ["tassadaq", "tassadaq hussain"]],
        "should_answer": True,
        "notes": "Centre for AI & Big Data, directed by Dr. Tassadaq Hussain",
    },
    {
        "id": "M5",
        "category": "Medium Extraction",
        "difficulty": "Medium",
        "question": "What is the application fee for admission to Namal University?",
        "expected_kws": [["1,000", "1000", "rs. 1,000"]],
        "should_answer": True,
        "notes": "Rs. 1,000 non-refundable application fee",
    },
    # ── Category 3: Hard / Multi-hop ──────────────────────────────────────────
    {
        "id": "H1",
        "category": "Hard Multi-hop",
        "difficulty": "Hard",
        "question": "How many credit hours does the BS Computer Science program require, and what are its main research areas?",
        "expected_kws": [
            ["133"],
            ["machine learning", "nlp", "deep learning", "computer vision", "ai"],
        ],
        "should_answer": True,
        "notes": "133 credit hours; research in ML, NLP, AI, Deep Learning, Computer Vision, Software Engineering",
    },
    {
        "id": "H2",
        "category": "Hard Multi-hop",
        "difficulty": "Hard",
        "question": "What is the computing performance of CAID's supercomputer and how many GPU units does it have?",
        "expected_kws": [["1.6 petaflop", "petaflops", "1.6"], ["40", "4070ti", "gpu"]],
        "should_answer": True,
        "notes": "1.6 PetaFLOPS peak, 40 × 4070Ti GPUs",
    },
    {
        "id": "H3",
        "category": "Hard Multi-hop",
        "difficulty": "Hard",
        "question": "Which Namal alumni was recognized by the World Economic Forum as a Future Leader?",
        "expected_kws": [["zulqarnain", "zulqarnain haider"]],
        "should_answer": True,
        "notes": "Zulqarnain Haider — WEF Future 50 Leaders",
    },
    {
        "id": "H4",
        "category": "Hard Multi-hop",
        "difficulty": "Hard",
        "question": "Who chairs the Board of Governors at Namal University and name at least three other board members.",
        "expected_kws": [
            ["imran khan"],
            ["dawood", "razak dawood", "sikandar", "aleema", "arif nazir"],
        ],
        "should_answer": True,
        "notes": "Imran Khan chairs; members include Abdul Razak Dawood, Sikandar Mustafa Khan, Aleema Khanum, Dr. Arif Nazir Butt, etc.",
    },
    {
        "id": "H5",
        "category": "Hard Multi-hop",
        "difficulty": "Hard",
        "question": "What is the 2026 admissions deadline and which bank should the application fee be paid to?",
        "expected_kws": [["july 31, 2026", "july 31", "31 july"], ["mcb", "muslim commercial bank"]],
        "should_answer": True,
        "notes": "Deadline: July 31, 2026; Bank: MCB (Muslim Commercial Bank)",
    },
    # ── Category 4: Adversarial / Hallucination Guard ─────────────────────────
    {
        "id": "A1",
        "category": "Adversarial",
        "difficulty": "Medium",
        "question": "Does Namal University offer a BS Pharmacy program?",
        "expected_kws": [["no", "not", "doesn't", "does not", "not mentioned", "not offer",
                          "don't have that information", "i don't have", "not available",
                          "no information", "not in the document", "not listed"]],
        "should_answer": False,
        "notes": "Document only lists EE, CS, BBA, Mathematics — no Pharmacy",
    },
    {
        "id": "A2",
        "category": "Adversarial",
        "difficulty": "Medium",
        "question": "What is the exact annual tuition fee in Pakistani rupees at Namal University?",
        "expected_kws": [["not", "doesn't specify", "not mentioned", "not provided", "no specific",
                          "quarterly", "cannot", "don't have that information", "i don't have",
                          "no information", "not available", "not stated", "not given"]],
        "should_answer": False,
        "notes": "Document only says tuition is quarterly; exact figure not given",
    },
    {
        "id": "A3",
        "category": "Adversarial",
        "difficulty": "Hard",
        "question": "Who is the Vice Chancellor of Namal University?",
        "expected_kws": [["rector", "najam", "no vice chancellor", "not vice chancellor",
                          "position is rector", "don't have that information", "i don't have",
                          "not mentioned", "no information"]],
        "should_answer": False,
        "notes": "Title is Rector (Dr. Najam ul Islam), not Vice Chancellor — ideal response clarifies this",
    },
    {
        "id": "A4",
        "category": "Adversarial",
        "difficulty": "Medium",
        "question": "Does Namal University have a medical school or MBBS program?",
        "expected_kws": [["no", "not", "doesn't", "does not", "not mentioned",
                          "don't have that information", "i don't have", "no information",
                          "not available", "not listed"]],
        "should_answer": False,
        "notes": "No medical school mentioned anywhere in the document",
    },
    {
        "id": "A5",
        "category": "Adversarial",
        "difficulty": "Hard",
        "question": "What is the name of CAID's supercomputer?",
        "expected_kws": [["not mentioned", "not named", "no name", "not provided", "doesn't", "does not specify", "no specific name", "indigenous"]],
        "should_answer": False,
        "notes": "Document describes specs but never gives the supercomputer a proper name",
    },
    # ── Category 5: Cross-Reference / Synthesis ───────────────────────────────
    {
        "id": "X1",
        "category": "Cross-Reference",
        "difficulty": "Hard",
        "question": "What scholarships does Namal University offer to students from Baluchistan or former FATA?",
        "expected_kws": [["100%", "full waiver"], ["admission fee", "security"]],
        "should_answer": True,
        "notes": "EX-FATA / Baluchistan: 100% admission fee + security waiver",
    },
    {
        "id": "X2",
        "category": "Cross-Reference",
        "difficulty": "Hard",
        "question": "Which Namal alumni secured a fully funded Master's scholarship abroad and where?",
        "expected_kws": [["usama", "usama bin sohaib", "tampere", "finland"]],
        "should_answer": True,
        "notes": "Usama Bin Sohaib — 100% scholarship for Master's at Tampere University, Finland",
    },
    {
        "id": "X3",
        "category": "Cross-Reference",
        "difficulty": "Hard",
        "question": "What research projects is CAID currently working on and with which external partners?",
        "expected_kws": [
            ["supercomputing", "rice sorting", "vr", "rehabilitation", "cattle"],
            ["alkaram", "new zealand", "ministry of livestock", "pakistan", "barc"],
        ],
        "should_answer": True,
        "notes": "Projects: Indigenous Supercomputing (BARC), VR Tele-Rehabilitation (NZ Chiropractic), Smart Rice Sorting (Alkaram), Cattle ID (Ministry of Livestock), RISC-V Seed Sorting",
    },
    {
        "id": "X4",
        "category": "Cross-Reference",
        "difficulty": "Medium",
        "question": "What is Namal's Green Namal initiative and what environmental features surround the campus?",
        "expected_kws": [["green namal", "environment", "sustainability"], ["namal lake", "lake", "birds", "migratory"]],
        "should_answer": True,
        "notes": "Environmental sustainability initiative; campus overlooks Namal Lake (5 sq km), migratory birds sanctuary",
    },
    {
        "id": "X5",
        "category": "Cross-Reference",
        "difficulty": "Hard",
        "question": "What was the original university affiliation of Namal College before it became degree-awarding?",
        "expected_kws": [["bradford", "university of bradford", "uk"]],
        "should_answer": True,
        "notes": "Namal College began as an affiliate of University of Bradford, UK",
    },
]


# ── Auth & Upload Helpers ─────────────────────────────────────────────────────

def register_and_login(session: requests.Session) -> str:
    """Register a throwaway account, return access token."""
    email = f"rag_test_{uuid.uuid4().hex[:8]}@test.local"
    password = "TestPass123!"

    r = session.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "company_name": "RAG Accuracy Tester",
        "full_name": "Test Runner",
    })
    if r.status_code not in (200, 201):
        sys.exit(f"[FAIL] Register failed {r.status_code}: {r.text}")

    data = r.json()
    token = data.get("access_token")
    if not token:
        # Try login if register returned no token
        r2 = session.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        if r2.status_code != 200:
            sys.exit(f"[FAIL] Login failed {r2.status_code}: {r2.text}")
        token = r2.json()["access_token"]

    print(f"[OK] Registered & logged in as {email}")
    return token


def upload_pdf(session: requests.Session, token: str) -> int:
    """Upload Namal PDF; return chunk count."""
    if not PDF_PATH.exists():
        sys.exit(f"[FAIL] PDF not found at: {PDF_PATH}")

    headers = {"Authorization": f"Bearer {token}"}
    with PDF_PATH.open("rb") as fh:
        r = session.post(
            f"{BASE_URL}/portal/document/upload",
            headers=headers,
            files={"file": (PDF_PATH.name, fh, "application/pdf")},
            timeout=120,
        )

    if r.status_code != 200:
        sys.exit(f"[FAIL] Upload failed {r.status_code}: {r.text}")

    chunk_count = r.json().get("chunk_count", "?")
    print(f"[OK] PDF uploaded — {chunk_count} chunks indexed")
    return chunk_count


def ask_question(session: requests.Session, token: str, question: str, conv_id: str | None) -> tuple[str, str | None]:
    """Send a question to /portal/chat, return (answer_text, conversation_id)."""
    headers = {"Authorization": f"Bearer {token}"}
    r = session.post(
        f"{BASE_URL}/portal/chat",
        headers=headers,
        json={"question": question, "conversation_id": conv_id},
        timeout=90,
    )
    if r.status_code != 200:
        return f"[HTTP {r.status_code}] {r.text[:200]}", conv_id

    data = r.json()
    answer = data.get("answer", data.get("response", str(data)))
    new_conv_id = data.get("conversation_id", conv_id)
    return answer, new_conv_id


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(response: str, test: dict) -> tuple[str, str]:
    """
    Returns (verdict, reason).
    Verdict: PASS / PARTIAL / FAIL
    """
    text = response.lower()
    matched_groups = []
    missed_groups = []

    for kw_group in test["expected_kws"]:
        hit = any(kw.lower() in text for kw in kw_group)
        if hit:
            matched_groups.append(kw_group)
        else:
            missed_groups.append(kw_group)

    total = len(test["expected_kws"])
    hits = len(matched_groups)

    if not test["should_answer"]:
        # Adversarial: expect the system to decline / say "not in document"
        if hits >= 1:
            return "PASS", "Correctly refused or flagged missing info"
        else:
            return "FAIL", "Hallucinated — gave a confident answer not grounded in document"

    if hits == total:
        return "PASS", f"All {total} keyword groups matched"
    elif hits >= max(1, total // 2):
        return "PARTIAL", f"{hits}/{total} keyword groups matched; missing: {missed_groups}"
    else:
        return "FAIL", f"Only {hits}/{total} keyword groups matched; missing: {missed_groups}"


# ── Report Generator ──────────────────────────────────────────────────────────

def generate_report(results: list[dict], chunk_count, elapsed: float) -> str:
    total = len(results)
    passes = sum(1 for r in results if r["verdict"] == "PASS")
    partials = sum(1 for r in results if r["verdict"] == "PARTIAL")
    fails = sum(1 for r in results if r["verdict"] == "FAIL")
    score_pct = round((passes + 0.5 * partials) / total * 100, 1)

    categories = {}
    for r in results:
        cat = r["category"]
        categories.setdefault(cat, {"PASS": 0, "PARTIAL": 0, "FAIL": 0})
        categories[cat][r["verdict"]] += 1

    lines = [
        "# RAG Accuracy Report — Namal University Overview",
        f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Document:** Namal_University_Overview.pdf (16 pages, {chunk_count} chunks)  ",
        f"**Backend:** DeepSeek-V3 (deepseek-chat) + all-MiniLM-L6-v2 embeddings + BGE reranker  ",
        f"**Total test questions:** {total}  ",
        f"**Total time:** {elapsed:.1f}s  ",
        "",
        "---",
        "",
        "## Overall Score",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Score** | **{score_pct}%** (PASS=1pt, PARTIAL=0.5pt) |",
        f"| PASS | {passes} / {total} |",
        f"| PARTIAL | {partials} / {total} |",
        f"| FAIL | {fails} / {total} |",
        "",
        "---",
        "",
        "## Results by Category",
        "",
        "| Category | PASS | PARTIAL | FAIL | Score |",
        "|----------|------|---------|------|-------|",
    ]

    for cat, counts in categories.items():
        n = counts["PASS"] + counts["PARTIAL"] + counts["FAIL"]
        cat_score = round((counts["PASS"] + 0.5 * counts["PARTIAL"]) / n * 100)
        lines.append(f"| {cat} | {counts['PASS']} | {counts['PARTIAL']} | {counts['FAIL']} | {cat_score}% |")

    lines += ["", "---", "", "## Detailed Results", ""]

    current_cat = None
    for r in results:
        if r["category"] != current_cat:
            current_cat = r["category"]
            lines.append(f"\n### {current_cat}\n")

        verdict_emoji = {"PASS": "✅", "PARTIAL": "⚠️", "FAIL": "❌"}[r["verdict"]]
        lines.append(f"#### [{r['id']}] {r['difficulty']} — {r['verdict']} {verdict_emoji}")
        lines.append(f"**Q:** {r['question']}  ")
        lines.append(f"**Ground truth:** {r['notes']}  ")
        lines.append(f"**Verdict reason:** {r['reason']}  ")
        lines.append(f"\n**RAG Response:**")
        lines.append(f"\n> {r['response'].strip().replace(chr(10), chr(10) + '> ')}  ")
        lines.append("")

    lines += [
        "---",
        "",
        "## Analysis & Recommendations",
        "",
    ]

    if score_pct >= 85:
        lines.append("### System Health: Excellent")
        lines.append(f"The RAG pipeline scores {score_pct}% — well above the 80% production threshold.")
        lines.append("The system reliably retrieves and synthesizes information from the document.")
    elif score_pct >= 65:
        lines.append("### System Health: Good")
        lines.append(f"The RAG pipeline scores {score_pct}% — above the 60% acceptable threshold.")
        lines.append("Most questions are answered correctly; targeted improvements can push this higher.")
    else:
        lines.append("### System Health: Needs Improvement")
        lines.append(f"The RAG pipeline scores {score_pct}% — below the 65% minimum threshold.")
        lines.append("Significant retrieval or generation issues detected.")

    lines.append("")
    lines.append("### Failure Analysis")
    lines.append("")

    failed = [r for r in results if r["verdict"] in ("PARTIAL", "FAIL")]
    if failed:
        for r in failed:
            lines.append(f"- **[{r['id']}]** `{r['verdict']}` — {r['reason']}")
    else:
        lines.append("No failures. All questions passed.")

    lines += [
        "",
        "### Strengths",
        "",
    ]

    pass_cats = {cat: counts for cat, counts in categories.items() if counts["PASS"] >= counts.get("FAIL", 0)}
    if pass_cats:
        for cat in pass_cats:
            lines.append(f"- **{cat}**: Strong retrieval performance")
    else:
        lines.append("- None identified — review all categories")

    lines += [
        "",
        "### Improvement Recommendations",
        "",
        "1. **Tabular data**: The document contains many HTML-encoded tables. Verify table cells are properly tokenized and retrievable.",
        "2. **Adversarial robustness**: Ensure the `NO_CONTEXT_SYSTEM_PROMPT` is triggered when retrieval confidence is low.",
        "3. **Numeric precision**: Facts like percentages and credit hours require exact match — tune chunk overlap if numeric facts are missed.",
        "4. **Multi-hop queries**: For questions requiring synthesis across sections, consider increasing `RETRIEVAL_TOP_K` from 8 to 10.",
        "",
        "---",
        "",
        "*This report was auto-generated by `backend/tests/rag_accuracy_test.py`*",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("RAG ACCURACY TEST — Namal University")
    print("=" * 60)

    # Health check (retry 3x for transient busy state)
    health = None
    for attempt in range(3):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=30)
            if r.status_code == 200:
                health = r.json()
                break
        except (requests.ConnectionError, requests.ReadTimeout):
            if attempt < 2:
                print(f"  Health check attempt {attempt+1} failed, retrying...")
                time.sleep(3)
            else:
                sys.exit(f"[FAIL] Cannot connect to {BASE_URL} after 3 attempts — is the backend running?")
    if not health:
        sys.exit(f"[FAIL] Backend returned non-200 after 3 attempts")
    print(f"[OK] Backend healthy - LLM: {health.get('llm_provider')} / {health.get('llm_model')}")

    session = requests.Session()

    # Auth
    token = register_and_login(session)

    # Upload PDF
    chunk_count = upload_pdf(session, token)
    print("[..] Waiting 3s for index to stabilise…")
    time.sleep(3)

    # Run questions
    results = []
    raw_log = []
    conv_id = None
    start = time.time()

    print(f"\nRunning {len(TEST_CASES)} test questions…\n")
    for i, tc in enumerate(TEST_CASES, 1):
        print(f"  [{i:02d}/{len(TEST_CASES)}] [{tc['id']}] {tc['question'][:70]}…", end=" ", flush=True)
        answer, conv_id = ask_question(session, token, tc["question"], None)  # fresh conv each time
        verdict, reason = evaluate(answer, tc)
        symbol = {"PASS": "OK", "PARTIAL": "~~", "FAIL": "XX"}[verdict]
        print(f"{symbol} {verdict}")

        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "difficulty": tc["difficulty"],
            "question": tc["question"],
            "notes": tc["notes"],
            "response": answer,
            "verdict": verdict,
            "reason": reason,
        })
        raw_log.append({"id": tc["id"], "question": tc["question"], "answer": answer})

        time.sleep(0.8)  # gentle throttle

    elapsed = time.time() - start

    # Save raw responses
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(raw_log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Raw responses saved -> {RAW_PATH}")

    # Generate & save report
    report_md = generate_report(results, chunk_count, elapsed)
    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"[OK] Report saved -> {REPORT_PATH}")

    # Summary
    passes = sum(1 for r in results if r["verdict"] == "PASS")
    partials = sum(1 for r in results if r["verdict"] == "PARTIAL")
    fails = sum(1 for r in results if r["verdict"] == "FAIL")
    score = round((passes + 0.5 * partials) / len(results) * 100, 1)

    print(f"\n{'='*60}")
    print(f"  FINAL SCORE: {score}%  (PASS {passes}  PARTIAL {partials}  FAIL {fails})")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
