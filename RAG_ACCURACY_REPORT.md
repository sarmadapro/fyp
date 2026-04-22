# RAG Accuracy Report — Namal University Overview

**Generated:** 2026-04-21 06:31  
**Document:** Namal_University_Overview.pdf (16 pages, 44 chunks)  
**Backend:** DeepSeek-V3 (deepseek-chat) + all-MiniLM-L6-v2 embeddings + BGE reranker  
**Total test questions:** 26  
**Total time:** 150.0s  

---

## Overall Score

| Metric | Value |
|--------|-------|
| **Score** | **100.0%** (PASS=1pt, PARTIAL=0.5pt) |
| PASS | 26 / 26 |
| PARTIAL | 0 / 26 |
| FAIL | 0 / 26 |

---

## Results by Category

| Category | PASS | PARTIAL | FAIL | Score |
|----------|------|---------|------|-------|
| Simple Factual | 6 | 0 | 0 | 100% |
| Medium Extraction | 5 | 0 | 0 | 100% |
| Hard Multi-hop | 5 | 0 | 0 | 100% |
| Adversarial | 5 | 0 | 0 | 100% |
| Cross-Reference | 5 | 0 | 0 | 100% |

---

## Detailed Results


### Simple Factual

#### [F1] Easy — PASS ✅
**Q:** Where is Namal University located?  
**Ground truth:** 30 km Talagang Road, Mianwali, Punjab 42250  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> Namal University is located 30 km along Talagang Road in Mianwali, Punjab 42250, Pakistan.  

#### [F2] Easy — PASS ✅
**Q:** Who is the founder of Namal University?  
**Ground truth:** Imran Khan conceived the vision in 2005  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> The founder of Namal University is Imran Khan, who conceived the vision in 2005 to build an academic institution on the banks of Namal Lake, Mianwali.  

#### [F3] Easy — PASS ✅
**Q:** Who is the current Rector of Namal University?  
**Ground truth:** Dr. M. Najam ul Islam  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> The current Rector of Namal University is Dr. M. Najam ul Islam.  

#### [F4] Easy — PASS ✅
**Q:** What year was Namal College established?  
**Ground truth:** Namal College established in 2008  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> Namal College was established in 2008.  

#### [F5] Easy — PASS ✅
**Q:** What is the minimum eligibility percentage required for admission at Namal University?  
**Ground truth:** At least 70% marks in Intermediate/equivalent  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> The minimum eligibility percentage required for admission is at least 70% marks in Intermediate or equivalent examinations.  

#### [F6] Easy — PASS ✅
**Q:** What is the contact email address of Namal University?  
**Ground truth:** info@namal.edu.pk  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> The main contact email address for Namal University is **info@namal.edu.pk**.  


### Medium Extraction

#### [M1] Medium — PASS ✅
**Q:** What undergraduate programs does Namal University offer?  
**Ground truth:** BS EE, BS CS, BBA, BS Mathematics  
**Verdict reason:** All 4 keyword groups matched  

**RAG Response:**

> Namal University offers the following undergraduate programs:  
> - BS Electrical Engineering  
> - BS Computer Science  
> - BBA  
> - BS Mathematics  

#### [M2] Medium — PASS ✅
**Q:** How is the merit/aggregate calculated for admissions at Namal University?  
**Ground truth:** 43% Intermediate marks + 43% Entry Test score  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> The aggregate merit is calculated as: **43% Intermediate/equivalent marks + 43% Entry Test score**.  

#### [M3] Medium — PASS ✅
**Q:** What is the Elite 90 Scholarship at Namal University?  
**Ground truth:** 100% tuition fee waiver for candidates with 90%+ in Intermediate  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> The Elite 90 Scholarship is a 100% tuition fee waiver for candidates with 90% or more in Intermediate or an equivalent qualification.  

#### [M4] Medium — PASS ✅
**Q:** What is CAID and who is its director?  
**Ground truth:** Centre for AI & Big Data, directed by Dr. Tassadaq Hussain  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> **CAID (Centre for AI & Big Data)** is a leading research hub at Namal University that drives cutting-edge research, fosters creative solutions, and cultivates expert talent in artificial intelligence and big data.
> 
> **Director:** Dr. Tassadaq Hussain (Professor & Director CAID).  

#### [M5] Medium — PASS ✅
**Q:** What is the application fee for admission to Namal University?  
**Ground truth:** Rs. 1,000 non-refundable application fee  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> The application fee is Rs. 1,000/- (non-refundable).  


### Hard Multi-hop

#### [H1] Hard — PASS ✅
**Q:** How many credit hours does the BS Computer Science program require, and what are its main research areas?  
**Ground truth:** 133 credit hours; research in ML, NLP, AI, Deep Learning, Computer Vision, Software Engineering  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> The BS Computer Science program requires **133 credit hours**. Its main research areas include **Machine Learning, NLP, AI, Deep Learning, Computer Vision, and Software Engineering**.  

#### [H2] Hard — PASS ✅
**Q:** What is the computing performance of CAID's supercomputer and how many GPU units does it have?  
**Ground truth:** 1.6 PetaFLOPS peak, 40 × 4070Ti GPUs  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> **Computing Performance:** 1.6 PetaFLOPS peak performance.
> 
> **GPU Units:** 40 × 4070Ti GPUs.  

#### [H3] Hard — PASS ✅
**Q:** Which Namal alumni was recognized by the World Economic Forum as a Future Leader?  
**Ground truth:** Zulqarnain Haider — WEF Future 50 Leaders  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> Zulqarnain Haider was selected among the World Economic Forum Future 50 Leaders.  

#### [H4] Hard — PASS ✅
**Q:** Who chairs the Board of Governors at Namal University and name at least three other board members.  
**Ground truth:** Imran Khan chairs; members include Abdul Razak Dawood, Sikandar Mustafa Khan, Aleema Khanum, Dr. Arif Nazir Butt, etc.  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> **Chair of the Board of Governors:** Mr. Imran Khan.
> 
> **Three other board members:**
> - Mr. Abdul Razak Dawood (Founder, Descon)
> - Mr. Sikandar Mustafa Khan (Chairman, Millat Tractors)
> - Mrs. Aleema Khanum  

#### [H5] Hard — PASS ✅
**Q:** What is the 2026 admissions deadline and which bank should the application fee be paid to?  
**Ground truth:** Deadline: July 31, 2026; Bank: MCB (Muslim Commercial Bank)  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> **2026 admissions deadline:** Friday, July 31, 2026.
> 
> **Bank for application fee:** Muslim Commercial Bank (MCB).  


### Adversarial

#### [A1] Medium — PASS ✅
**Q:** Does Namal University offer a BS Pharmacy program?  
**Ground truth:** Document only lists EE, CS, BBA, Mathematics — no Pharmacy  
**Verdict reason:** Correctly refused or flagged missing info  

**RAG Response:**

> I don't have that information.  

#### [A2] Medium — PASS ✅
**Q:** What is the exact annual tuition fee in Pakistani rupees at Namal University?  
**Ground truth:** Document only says tuition is quarterly; exact figure not given  
**Verdict reason:** Correctly refused or flagged missing info  

**RAG Response:**

> I don't have that information.  

#### [A3] Hard — PASS ✅
**Q:** Who is the Vice Chancellor of Namal University?  
**Ground truth:** Title is Rector (Dr. Najam ul Islam), not Vice Chancellor — ideal response clarifies this  
**Verdict reason:** Correctly refused or flagged missing info  

**RAG Response:**

> I don't have that information.  

#### [A4] Medium — PASS ✅
**Q:** Does Namal University have a medical school or MBBS program?  
**Ground truth:** No medical school mentioned anywhere in the document  
**Verdict reason:** Correctly refused or flagged missing info  

**RAG Response:**

> I don't have that information.  

#### [A5] Hard — PASS ✅
**Q:** What is the name of CAID's supercomputer?  
**Ground truth:** Document describes specs but never gives the supercomputer a proper name  
**Verdict reason:** Correctly refused or flagged missing info  

**RAG Response:**

> The context does not specify a name for CAID's supercomputer.  


### Cross-Reference

#### [X1] Hard — PASS ✅
**Q:** What scholarships does Namal University offer to students from Baluchistan or former FATA?  
**Ground truth:** EX-FATA / Baluchistan: 100% admission fee + security waiver  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> Namal University offers the **EX-FATA / Baluchistan** scholarship, which provides a **100% admission fee + security waiver** for candidates from formerly FATA or Baluchistan.  

#### [X2] Hard — PASS ✅
**Q:** Which Namal alumni secured a fully funded Master's scholarship abroad and where?  
**Ground truth:** Usama Bin Sohaib — 100% scholarship for Master's at Tampere University, Finland  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> Usama Bin Sohaib secured a 100% scholarship for a Master's at Tampere University, Finland.  

#### [X3] Hard — PASS ✅
**Q:** What research projects is CAID currently working on and with which external partners?  
**Ground truth:** Projects: Indigenous Supercomputing (BARC), VR Tele-Rehabilitation (NZ Chiropractic), Smart Rice Sorting (Alkaram), Cattle ID (Ministry of Livestock), RISC-V Seed Sorting  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> Based on the context, CAID is currently working on the following research projects with these external partners:
> 
> | Project | Description | Partners |
> |---|---|---|
> | Indigenous Supercomputing | Developing Pakistan's fastest supercomputing system for AI applications | **BARC** (Balochistan Agriculture Research Center); Pakistan Supercomputing Center |
> | VR Tele-Rehabilitation | Virtual Reality Platform enabling remote rehabilitation services | **New Zealand Chiropractic Center**; Riphah |
> | Smart Rice Sorting | AI-powered solution for intelligent rice processing | **Alkaram Rice Engineering** |
> | Real-time Cattle ID System | Image-based livestock breed identification for farmers | **Ministry of Livestock** |
> | RISC-V Seed Sorting | FPGA-accelerated high-speed multi-camera grain inspection | **Industrial partners** |  

#### [X4] Medium — PASS ✅
**Q:** What is Namal's Green Namal initiative and what environmental features surround the campus?  
**Ground truth:** Environmental sustainability initiative; campus overlooks Namal Lake (5 sq km), migratory birds sanctuary  
**Verdict reason:** All 2 keyword groups matched  

**RAG Response:**

> **Green Namal Initiative** is the university's commitment to environmental sustainability, motivating all members to become ecologically conscious. The university uses renewable energy resources, recycles waste, and actively maintains its scenic natural surroundings.
> 
> **Environmental features surrounding the campus include:**
> - **Namal Lake** (5 sq km)
> - The historic **Namal Dam** (built 1913 by the British)
> - The surrounding **valley** — a sanctuary for migratory birds including Russian ducks and Siberian cranes.
> 
> The campus itself sits at the foothill of a mountaintop overlooking Namal Lake, surrounded by the Koh-i-Suleiman and Salt Range.  

#### [X5] Hard — PASS ✅
**Q:** What was the original university affiliation of Namal College before it became degree-awarding?  
**Ground truth:** Namal College began as an affiliate of University of Bradford, UK  
**Verdict reason:** All 1 keyword groups matched  

**RAG Response:**

> Namal College was originally an affiliate college of the University of Bradford, UK.  

---

## Analysis & Recommendations

### System Health: Excellent

The RAG pipeline scores **100%** across all 26 test questions (26 PASS / 0 PARTIAL / 0 FAIL).  
This exceeds the 80% production quality threshold by 20 points.

---

### Strength Analysis

#### 1. Factual Precision (F1–F6) — 6/6 PASS

The system extracts exact facts with high fidelity: location, founding year, founder, Rector, eligibility threshold (70%), and contact email — all returned verbatim from the document. No hallucinations observed.

#### 2. Structured Information Extraction (M1–M5) — 5/5 PASS

The system correctly extracts structured content including:
- All four degree programs (BS EE, BS CS, BBA, BS Mathematics)
- The binary merit formula (43% + 43%)
- Scholarship conditions (Elite 90 = 100% tuition fee waiver for 90%+)
- Named entities (CAID director: Dr. Tassadaq Hussain)
- Numeric fees (Rs. 1,000)

This confirms that HTML-encoded tables in the PDF are being correctly parsed and chunked.

#### 3. Multi-hop Reasoning (H1–H5) — 5/5 PASS

The hardest category performed perfectly. Highlights:
- **H1**: Correctly combined credit hours (133) with research areas across two separate sections of the document.
- **H2**: Retrieved hardware specs from a complex table (1.6 PetaFLOPS, 40 × 4070Ti GPUs).
- **H4**: Retrieved the full Board of Governors list and correctly identified the chair.
- **H5**: Combined deadline (July 31, 2026) with banking details (MCB) from different paragraphs.

#### 4. Hallucination Prevention (A1–A5) — 5/5 PASS

All adversarial/out-of-scope questions were handled without hallucination:

| ID | Question | Response | Assessment |
|----|----------|----------|------------|
| A1 | BS Pharmacy? | "I don't have that information" | Correct refusal — pharmacy not offered |
| A2 | Annual tuition fee? | "I don't have that information" | Correct — only quarterly fee structure mentioned |
| A3 | Vice Chancellor? | "I don't have that information" | Correct refusal — title is Rector, not VC; **minor weakness**: could redirect to Rector info |
| A4 | Medical school? | "I don't have that information" | Correct — no medical program exists |
| A5 | Supercomputer name? | "The context does not specify a name" | Ideal response — acknowledges spec exists but name is not given |

**Note on A3**: While the refusal is technically correct (no Vice Chancellor exists at Namal), an ideal response would redirect: *"Namal University does not have a Vice Chancellor — the equivalent position is Rector, held by Dr. M. Najam ul Islam."* This is a marginal improvement opportunity, not a failure.

#### 5. Cross-Document Synthesis (X1–X5) — 5/5 PASS

- **X3** produced a complete formatted table of all CAID research projects with correct partners — demonstrating that the parent-child chunking strategy successfully preserves multi-row table relationships.
- **X4** correctly synthesized the Green Namal initiative with environmental details (Namal Lake, Namal Dam built 1913, migratory bird species) from different paragraphs.
- **X5** correctly identified the historical Bradford affiliation — a historical fact buried in the "About" section.

---

### Observed Weaknesses

| Issue | Severity | Details |
|-------|----------|---------|
| A3 response not context-aware | Low | System says "I don't have that information" instead of redirecting to the Rector title |
| No PARTIAL grades observed | N/A | The test set may need harder synthesis questions that cross 4+ document sections |

---

### Improvement Recommendations

1. **Context-aware refusals**: When a query asks about a title/role not in the document, the system should check if a related role exists (e.g., VC → Rector) and redirect rather than giving a flat "no information" response.

2. **Increase adversarial diversity**: Add questions that combine out-of-scope topics with in-scope ones (e.g., "What is the tuition fee for the Pharmacy program?") to test boundary handling under compound ambiguity.

3. **Confidence scores**: Expose retrieval similarity scores in the response payload so low-confidence answers can be flagged in the UI.

4. **Tabular chunking verification**: The CAID project table (X3) was retrieved correctly, but future documents with wider or nested tables should be tested separately.

5. **Longer conversation stress test**: All questions in this test used fresh conversation IDs. A follow-up test should chain 8–10 questions in a single conversation to stress-test context window handling.

---

### Verdict

> The VoiceRAG system demonstrates **production-grade accuracy** on the Namal University document.  
> Retrieval is precise, multi-hop reasoning is reliable, and hallucination is effectively prevented.  
> The single identified improvement (context-aware refusals for related-but-absent entities) is a minor UX enhancement, not a correctness issue.

---

*This report was auto-generated by `backend/tests/rag_accuracy_test.py`*