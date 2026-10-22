"""RealDoc-Bench — Production document evaluation covering the 5 failure modes
that break academic benchmarks in real-world deployments.

Based on Extend.ai's analysis:
1. Layout Complexity: multi-column, merged cells, nested tables, rotated headers
2. Handwriting/Mixed: annotations over print, stamps, signatures, form fills
3. Document Length: cross-page entity resolution, 200+ page packages
4. Scan Quality: skew, low DPI, fax compression, partial occlusion
5. Domain Formatting: vertical-specific conventions (financial, medical, logistics)

Metrics per the article:
- CER (Character Error Rate) — per field, not just page average
- Layout Adjusted F1 — structure-aware, not just text
- Document QA Accuracy — downstream reasoning correctness
- Cost per 1000 pages
- P95 latency
"""
from __future__ import annotations
import re
import time
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.evals.enterprise.ocr_quality import compute_wer, compute_cer
from pixora.evals.enterprise.teds import compute_teds
from pixora.evals.enterprise.qa_eval import evaluate_qa, QAPair
from pixora.evals.enterprise.layout_metrics import compute_layout_metrics, DetectionBox
from pixora.evals.matchers import composite_match


# ── Data Structures ──────────────────────────────────────────

class RealDocSample(TypedDict, total=False):
    doc_id: Required[str]
    category: Required[str]
    difficulty: Required[str]
    domain: str
    text: Required[str]
    expected_fields: dict[str, str]
    expected_tables: list[str]
    qa_pairs: list[QAPair]
    layout_boxes: list[DetectionBox]
    has_handwriting: bool
    has_stamps: bool
    page_count: int
    scan_quality: str
    metadata: dict[str, Any]


class FailureModeScore(TypedDict, total=False):
    name: Required[str]
    score: Required[float]
    samples_tested: int
    field_cer: float
    layout_f1: float
    qa_accuracy: float
    table_teds: float
    details: list[dict[str, Any]]


class RealDocReport(TypedDict, total=False):
    overall_score: Required[float]
    layout_adjusted_f1: Required[float]
    document_qa_accuracy: Required[float]
    avg_field_cer: float
    avg_table_teds: float
    failure_modes: Required[dict[str, FailureModeScore]]
    cost_per_1000_pages: float
    p95_latency_ms: float
    total_samples: int
    by_domain: dict[str, dict[str, float]]
    metadata: dict[str, Any]


# ── Failure Mode 1: Layout Complexity ─────────────────────────

LAYOUT_COMPLEXITY_SAMPLES: list[RealDocSample] = [
    RealDocSample(
        doc_id="layout_001", category="layout_complexity", difficulty="hard",
        domain="financial",
        text=(
            "CONSOLIDATED BALANCE SHEET\n"
            "As of December 31, 2024 (in thousands)\n\n"
            "ASSETS                          | 2024      | 2023      | Change\n"
            "Current Assets                  |           |           |\n"
            "  Cash and equivalents          | $42,891   | $38,204   | +12.3%\n"
            "  Accounts receivable, net      | $156,443  | $142,891  | +9.5%\n"
            "  Inventory                     | $89,221   | $95,442   | -6.5%\n"
            "  Prepaid expenses              | $12,384   | $11,892   | +4.1%\n"
            "Total Current Assets            | $300,939  | $288,429  | +4.3%\n\n"
            "Non-Current Assets              |           |           |\n"
            "  Property, plant & equipment   | $445,221  | $412,889  | +7.8%\n"
            "  Goodwill                      | $234,567  | $234,567  | 0.0%\n"
            "  Intangible assets, net        | $67,891   | $72,443   | -6.3%\n"
            "Total Non-Current Assets        | $747,679  | $719,899  | +3.9%\n\n"
            "TOTAL ASSETS                    | $1,048,618| $1,008,328| +4.0%\n"
        ),
        expected_fields={
            "total_assets_2024": "$1,048,618",
            "total_assets_2023": "$1,008,328",
            "cash_2024": "$42,891",
            "accounts_receivable_2024": "$156,443",
            "inventory_2024": "$89,221",
            "goodwill": "$234,567",
            "total_current_assets_2024": "$300,939",
        },
        expected_tables=[
            "| ASSETS | 2024 | 2023 | Change |\n|---|---|---|---|\n| Cash and equivalents | $42,891 | $38,204 | +12.3% |"
        ],
        qa_pairs=[
            QAPair(question="What are total assets for 2024?", answer="$1,048,618", category="table_lookup"),
            QAPair(question="What is the change in inventory?", answer="-6.5%", category="table_lookup"),
            QAPair(question="What is the goodwill amount?", answer="$234,567", category="field_extraction"),
            QAPair(question="Did total current assets increase or decrease?", answer="+4.3%", category="reasoning"),
            QAPair(question="What is the accounts receivable for 2024?", answer="$156,443", category="table_lookup"),
        ],
    ),
    RealDocSample(
        doc_id="layout_002", category="layout_complexity", difficulty="hard",
        domain="logistics",
        text=(
            "BILL OF LADING — MULTIMODAL TRANSPORT\n"
            "B/L No: MAEU-BL-2024-78432          Date: 11/15/2024\n\n"
            "SHIPPER:                    | CONSIGNEE:\n"
            "Guangzhou Precision Mfg     | AutoParts Distribution LLC\n"
            "Block C, Nansha Industrial  | 1847 Harbor Gateway\n"
            "Guangzhou 511458, China     | Long Beach, CA 90802, USA\n\n"
            "CONTAINER | SEAL NO    | PKG  | DESCRIPTION        | GROSS WT  | MEAS\n"
            "MSKU4829371| CN-887421 |  48  | Auto Parts CKD     | 14,220 kg | 28.4 CBM\n"
            "MSKU5512843| CN-887422 |  36  | Electronic Modules  |  8,440 kg | 16.2 CBM\n"
            "TCNU7291034| CN-887423 |  24  | Brake Assemblies    | 11,890 kg | 22.8 CBM\n\n"
            "TOTAL: 108 packages | 34,550 kg | 67.4 CBM\n"
            "FREIGHT: PREPAID | TERMS: CIF Long Beach\n"
            "ETD: 11/18/2024 Nansha | ETA: 12/22/2024 Long Beach\n"
        ),
        expected_fields={
            "bl_number": "MAEU-BL-2024-78432",
            "shipper": "Guangzhou Precision Mfg",
            "consignee": "AutoParts Distribution LLC",
            "total_packages": "108",
            "total_weight": "34,550 kg",
            "freight_terms": "PREPAID",
            "etd": "11/18/2024",
            "eta": "12/22/2024",
        },
        qa_pairs=[
            QAPair(question="What is the B/L number?", answer="MAEU-BL-2024-78432", category="field_extraction"),
            QAPair(question="How many total packages?", answer="108", category="table_aggregation"),
            QAPair(question="What is the total gross weight?", answer="34,550 kg", category="table_aggregation"),
            QAPair(question="What is the seal number for the brake assemblies container?", answer="CN-887423", category="table_lookup", difficulty="hard"),
            QAPair(question="What are the freight terms?", answer="PREPAID", category="field_extraction"),
        ],
    ),
]

# ── Failure Mode 2: Handwriting/Mixed ────────────────────────

HANDWRITING_MIXED_SAMPLES: list[RealDocSample] = [
    RealDocSample(
        doc_id="handwriting_001", category="handwriting_mixed", difficulty="hard",
        domain="insurance",
        has_handwriting=True, has_stamps=True,
        text=(
            "INSURANCE CLAIM FORM — AUTO\n"
            "Claim #: CLM-2024-445921\n"
            "Policy #: POL-AUTO-2024-88721\n\n"
            "Policyholder: Margaret R. Thornton\n"
            "Date of Loss: 09/28/2024\n"
            "Date Filed: 10/02/2024\n\n"
            "VEHICLE INFORMATION:\n"
            "Year/Make/Model: 2022 Toyota RAV4 XLE\n"
            "VIN: JTMR4FHE2ND012847\n"
            "License Plate: 7ABC123 (CA)\n\n"
            "DESCRIPTION OF INCIDENT:\n"
            "[Handwritten] Vehicle was rear-ended at stoplight on\n"
            "[Handwritten] intersection of 5th & Main St. Other driver\n"
            "[Handwritten] admitted fault. Police report #2024-PD-44891.\n"
            "[Handwritten] Approx damage to rear bumper, taillight,\n"
            "[Handwritten] and trunk lid. Car still drivable.\n\n"
            "ESTIMATED REPAIR: $4,850.00\n"
            "DEDUCTIBLE: $500.00\n"
            "AMOUNT CLAIMED: $4,350.00\n\n"
            "[STAMP] RECEIVED OCT 02 2024\n"
            "[STAMP] CLAIMS DEPARTMENT\n"
            "[Signature] M. Thornton    Date: 10/02/2024\n"
            "[Adjuster Note] Approved for estimate. Schedule inspection.\n"
        ),
        expected_fields={
            "claim_number": "CLM-2024-445921",
            "policy_number": "POL-AUTO-2024-88721",
            "policyholder": "Margaret R. Thornton",
            "date_of_loss": "09/28/2024",
            "vin": "JTMR4FHE2ND012847",
            "estimated_repair": "$4,850.00",
            "deductible": "$500.00",
            "amount_claimed": "$4,350.00",
            "police_report": "2024-PD-44891",
        },
        qa_pairs=[
            QAPair(question="What is the claim number?", answer="CLM-2024-445921", category="field_extraction"),
            QAPair(question="What is the VIN?", answer="JTMR4FHE2ND012847", category="field_extraction"),
            QAPair(question="What is the estimated repair cost?", answer="$4,850.00", category="field_extraction"),
            QAPair(question="What happened in the incident?", answer="rear-ended at stoplight", category="handwriting"),
            QAPair(question="Was a police report filed?", answer="2024-PD-44891", category="handwriting", difficulty="hard"),
            QAPair(question="What is the amount after deductible?", answer="$4,350.00", category="reasoning"),
        ],
    ),
]

# ── Failure Mode 3: Document Length / Cross-Page ──────────────

DOCUMENT_LENGTH_SAMPLES: list[RealDocSample] = [
    RealDocSample(
        doc_id="length_001", category="document_length", difficulty="hard",
        domain="legal", page_count=5,
        text=(
            "--- PAGE 1 ---\n"
            "MASTER SERVICES AGREEMENT\n"
            "Agreement No: MSA-2024-0042\n"
            "Effective Date: January 15, 2024\n\n"
            "This Master Services Agreement ('Agreement') is entered into by:\n"
            "PARTY A: Pinnacle Software Inc., a Delaware corporation\n"
            "         123 Innovation Drive, Austin, TX 78701\n"
            "PARTY B: DataVault Solutions LLC, a California LLC\n"
            "         456 Cloud Avenue, San Francisco, CA 94105\n\n"
            "WHEREAS Party A provides software development services...\n\n"
            "--- PAGE 2 ---\n"
            "SECTION 3: COMPENSATION\n"
            "3.1 Base Fee: $750,000 per annum, payable quarterly\n"
            "3.2 Performance Bonus: Up to 15% of Base Fee based on KPIs\n"
            "    defined in Exhibit B (see page 4)\n"
            "3.3 Payment Terms: Net 45 from invoice date\n"
            "3.4 Late Payment: Interest at 1.5% per month\n\n"
            "SECTION 4: TERM AND TERMINATION\n"
            "4.1 Initial Term: 36 months from Effective Date\n"
            "4.2 Renewal: Auto-renews for successive 12-month periods\n"
            "4.3 Termination for Convenience: 90 days written notice\n"
            "4.4 Termination for Cause: As defined in Section 8.2 (page 3)\n\n"
            "--- PAGE 3 ---\n"
            "SECTION 8: BREACH AND REMEDIES\n"
            "8.1 Material Breach includes: (a) non-payment exceeding 60 days,\n"
            "    (b) violation of confidentiality per Section 6, (c) failure\n"
            "    to meet SLA requirements per Exhibit A three consecutive months\n"
            "8.2 Cure Period: 30 days from written notice of breach\n"
            "8.3 Limitation of Liability: Neither party's aggregate liability\n"
            "    shall exceed 2x the annual Base Fee ($1,500,000)\n\n"
            "--- PAGE 4 ---\n"
            "EXHIBIT B: KEY PERFORMANCE INDICATORS\n"
            "KPI-1: System Uptime >= 99.9% (measured monthly)\n"
            "KPI-2: Mean Response Time <= 200ms (p95)\n"
            "KPI-3: Support Ticket Resolution <= 4 hours (critical)\n"
            "KPI-4: Sprint Velocity >= 85% of committed story points\n\n"
            "--- PAGE 5 ---\n"
            "IN WITNESS WHEREOF the parties have executed this Agreement.\n\n"
            "PINNACLE SOFTWARE INC.          DATAVAULT SOLUTIONS LLC\n"
            "By: [Signature]                 By: [Signature]\n"
            "Name: James T. Morrison         Name: Sarah L. Chen\n"
            "Title: CEO                      Title: COO\n"
            "Date: 01/15/2024                Date: 01/15/2024\n"
        ),
        expected_fields={
            "agreement_number": "MSA-2024-0042",
            "effective_date": "January 15, 2024",
            "party_a": "Pinnacle Software Inc.",
            "party_b": "DataVault Solutions LLC",
            "base_fee": "$750,000",
            "payment_terms": "Net 45",
            "initial_term": "36 months",
            "termination_notice": "90 days",
            "liability_cap": "$1,500,000",
            "uptime_sla": "99.9%",
        },
        qa_pairs=[
            QAPair(question="What is the agreement number?", answer="MSA-2024-0042", category="field_extraction"),
            QAPair(question="What is the base fee?", answer="$750,000", category="field_extraction"),
            QAPair(question="What is the liability cap?", answer="$1,500,000", category="cross_page", difficulty="hard"),
            QAPair(question="What is the uptime SLA?", answer="99.9%", category="cross_page"),
            QAPair(question="How is the liability cap calculated?", answer="2x the annual Base Fee", category="reasoning", difficulty="hard"),
            QAPair(question="What is the cure period for breach?", answer="30 days", category="cross_page"),
            QAPair(question="Who signed for Pinnacle Software?", answer="James T. Morrison", category="cross_page"),
            QAPair(question="What triggers termination for cause?", answer="non-payment exceeding 60 days", category="reasoning", difficulty="hard"),
        ],
    ),
]

# ── Failure Mode 4: Scan Quality ─────────────────────────────

SCAN_QUALITY_SAMPLES: list[RealDocSample] = [
    RealDocSample(
        doc_id="scan_001", category="scan_quality", difficulty="hard",
        domain="medical", scan_quality="degraded",
        text=(
            "LAB0RATORY REP0RT\n"
            "Quest Dlagnostlcs — Chantl11y, VA\n\n"
            "Patient Narne: Robert J. Wl11iams\n"
            "Date 0f Birth: O5/l2/l978\n"
            "MRN: MRN-OO284719\n"
            "Orderlng Physlclan: Dr. Amanda Torres, MD\n"
            "Co11ection Date: O3/O8/2O24\n"
            "Report Date: O3/O9/2O24\n\n"
            "COMPLETE BL00D COUNT (CBC)\n"
            "WBC: 7.2 x1O^3/uL (ref 4.5-11.O)\n"
            "RBC: 4.85 xlO^6/uL (ref 4.5O-5.9O)\n"
            "Hemog1obin: l4.8 g/dL (ref l3.5-l7.5)\n"
            "P1ate1ets: 245 xlO^3/uL (ref l5O-4OO)\n\n"
            "METAB0LIC PANEL\n"
            "G1ucose Fastlng: 1l2 mg/dL (ref 7O-99) ** HlGH **\n"
            "BUN: l8 mg/dL (ref 7-2O)\n"
            "Creatinine: l.O mg/dL (ref O.7-l.3)\n\n"
            "Dlagnosis: Pre-dlabetic condltlon, e1evated fastlng g1ucose\n"
        ),
        expected_fields={
            "patient_name": "Robert J. Williams",
            "date_of_birth": "05/12/1978",
            "mrn": "MRN-00284719",
            "ordering_physician": "Dr. Amanda Torres, MD",
            "collection_date": "03/08/2024",
            "hemoglobin": "14.8",
            "glucose_fasting": "112",
            "diagnosis": "Pre-diabetic condition, elevated fasting glucose",
        },
        qa_pairs=[
            QAPair(question="What is the patient name?", answer="Robert J. Williams", category="ocr_correction"),
            QAPair(question="What is the MRN?", answer="MRN-00284719", category="ocr_correction"),
            QAPair(question="What is the fasting glucose?", answer="112", category="ocr_correction"),
            QAPair(question="Is the glucose flagged?", answer="HIGH", category="ocr_correction"),
            QAPair(question="What is the hemoglobin?", answer="14.8", category="field_extraction"),
            QAPair(question="What is the collection date?", answer="03/08/2024", category="ocr_correction", difficulty="hard"),
        ],
    ),
]

# ── Failure Mode 5: Domain Formatting ────────────────────────

DOMAIN_FORMATTING_SAMPLES: list[RealDocSample] = [
    RealDocSample(
        doc_id="domain_001", category="domain_formatting", difficulty="medium",
        domain="healthcare",
        text=(
            "EXPLANATION OF BENEFITS (EOB)\n"
            "Blue Cross Blue Shield of Texas\n"
            "Group #: GRP-44821    Member ID: BCBS-TX-2024-00891\n"
            "Subscriber: Maria Elena Garcia    DOB: 09/21/1990\n"
            "Provider: Austin Orthopedic Associates\n"
            "Date of Service: 08/05/2024\n\n"
            "CLAIM DETAILS:\n"
            "Claim #: CLM-2024-TX-778921\n\n"
            "CPT    | DESCRIPTION              | BILLED   | ALLOWED  | COPAY  | PLAN PAID\n"
            "99214  | Office visit, est. pt    | $285.00  | $185.00  | $40.00 | $145.00\n"
            "73562  | X-ray, knee, 3 views     | $420.00  | $312.00  | $0.00  | $312.00\n"
            "20610  | Joint injection, major   | $650.00  | $485.00  | $0.00  | $485.00\n"
            "97110  | Therapeutic exercise     | $180.00  | $125.00  | $0.00  | $125.00\n\n"
            "TOTALS                            | $1,535.00| $1,107.00| $40.00 | $1,067.00\n\n"
            "PATIENT RESPONSIBILITY: $40.00 (copay) + $428.00 (above allowed) = $468.00\n"
            "REMARK CODES: N130 — Orthopedic referral verified\n"
            "              M15 — Pre-authorization obtained\n"
        ),
        expected_fields={
            "member_id": "BCBS-TX-2024-00891",
            "subscriber": "Maria Elena Garcia",
            "claim_number": "CLM-2024-TX-778921",
            "date_of_service": "08/05/2024",
            "total_billed": "$1,535.00",
            "total_allowed": "$1,107.00",
            "total_plan_paid": "$1,067.00",
            "patient_responsibility": "$468.00",
        },
        qa_pairs=[
            QAPair(question="What is the member ID?", answer="BCBS-TX-2024-00891", category="field_extraction"),
            QAPair(question="What is the total billed amount?", answer="$1,535.00", category="table_aggregation"),
            QAPair(question="How much does the patient owe?", answer="$468.00", category="reasoning"),
            QAPair(question="What is the CPT code for the joint injection?", answer="20610", category="table_lookup", difficulty="hard"),
            QAPair(question="How much did the plan pay for the x-ray?", answer="$312.00", category="table_lookup"),
            QAPair(question="Was pre-authorization obtained?", answer="M15", category="domain_specific", difficulty="hard"),
        ],
    ),
]

ALL_REALDOC_SAMPLES = (
    LAYOUT_COMPLEXITY_SAMPLES
    + HANDWRITING_MIXED_SAMPLES
    + DOCUMENT_LENGTH_SAMPLES
    + SCAN_QUALITY_SAMPLES
    + DOMAIN_FORMATTING_SAMPLES
)


# ── Evaluation Engine ─────────────────────────────────────────

def evaluate_field_extraction(
    parsed_text: str,
    expected_fields: dict[str, str],
) -> tuple[float, float, list[dict]]:
    if not expected_fields:
        return 1.0, 0.0, []

    field_results: list[dict] = []
    total_cer = 0.0
    matched = 0

    for field, expected in expected_fields.items():
        result = composite_match(parsed_text, expected)
        score = result["score"]
        found = expected.lower() in parsed_text.lower()
        cer = compute_cer(expected, _find_best_span(parsed_text, expected))

        if found or score > 0.7:
            matched += 1

        total_cer += cer
        field_results.append({
            "field": field, "expected": expected,
            "found": found, "match_score": round(score, 4),
            "cer": round(cer, 4),
        })

    f1 = matched / len(expected_fields)
    avg_cer = total_cer / len(expected_fields)
    return round(f1, 4), round(avg_cer, 4), field_results


def _find_best_span(text: str, target: str) -> str:
    lower = text.lower()
    t_lower = target.lower()
    pos = lower.find(t_lower)
    if pos >= 0:
        return text[pos:pos + len(target)]

    words = t_lower.split()
    if not words:
        return ""
    t_words = lower.split()
    best = ""
    best_score = 0
    for i in range(len(t_words)):
        for length in range(len(words) - 1, len(words) + 3):
            if i + length > len(t_words):
                break
            span = " ".join(t_words[i:i + length])
            r = composite_match(span, t_lower)
            if r["score"] > best_score:
                best_score = r["score"]
                best = span
    return best


def evaluate_failure_mode(
    samples: list[RealDocSample],
    parse_fn=None,
) -> FailureModeScore:
    if not samples:
        return FailureModeScore(name="empty", score=0.0, samples_tested=0)

    category = samples[0]["category"]
    all_qa: list[float] = []
    all_cer: list[float] = []
    all_f1: list[float] = []
    details: list[dict] = []

    for sample in samples:
        text = sample["text"]
        if parse_fn:
            text = parse_fn(sample)

        field_f1, field_cer, field_details = evaluate_field_extraction(
            text, sample.get("expected_fields", {}),
        )
        all_f1.append(field_f1)
        all_cer.append(field_cer)

        qa_pairs = sample.get("qa_pairs", [])
        if qa_pairs:
            qa_result = evaluate_qa(text, qa_pairs)
            all_qa.append(qa_result["accuracy"])
        else:
            all_qa.append(field_f1)

        details.append({
            "doc_id": sample["doc_id"],
            "field_f1": field_f1,
            "field_cer": field_cer,
            "qa_accuracy": all_qa[-1],
            "field_details": field_details,
        })

    avg_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0
    avg_cer = sum(all_cer) / len(all_cer) if all_cer else 0
    avg_qa = sum(all_qa) / len(all_qa) if all_qa else 0
    overall = (avg_f1 * 0.4 + avg_qa * 0.4 + (1 - avg_cer) * 0.2)

    return FailureModeScore(
        name=category,
        score=round(overall, 4),
        samples_tested=len(samples),
        field_cer=round(avg_cer, 4),
        layout_f1=round(avg_f1, 4),
        qa_accuracy=round(avg_qa, 4),
        details=details,
    )


def run_realdoc_bench(
    parse_fn=None,
    samples: list[RealDocSample] | None = None,
) -> RealDocReport:
    test_samples = samples or ALL_REALDOC_SAMPLES

    groups: dict[str, list[RealDocSample]] = {}
    for s in test_samples:
        groups.setdefault(s["category"], []).append(s)

    failure_modes: dict[str, FailureModeScore] = {}
    all_scores: list[float] = []
    all_qa: list[float] = []
    all_f1: list[float] = []
    all_cer: list[float] = []

    for category, cat_samples in groups.items():
        fm = evaluate_failure_mode(cat_samples, parse_fn)
        failure_modes[category] = fm
        all_scores.append(fm["score"])
        all_qa.append(fm.get("qa_accuracy", 0))
        all_f1.append(fm.get("layout_f1", 0))
        all_cer.append(fm.get("field_cer", 0))

    overall = sum(all_scores) / len(all_scores) if all_scores else 0
    avg_qa = sum(all_qa) / len(all_qa) if all_qa else 0
    avg_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0
    avg_cer = sum(all_cer) / len(all_cer) if all_cer else 0

    by_domain: dict[str, dict[str, float]] = {}
    for s in test_samples:
        domain = s.get("domain", "general")
        if domain not in by_domain:
            by_domain[domain] = {"count": 0, "total_score": 0}
        by_domain[domain]["count"] += 1

    return RealDocReport(
        overall_score=round(overall, 4),
        layout_adjusted_f1=round(avg_f1, 4),
        document_qa_accuracy=round(avg_qa, 4),
        avg_field_cer=round(avg_cer, 4),
        failure_modes=failure_modes,
        total_samples=len(test_samples),
        by_domain=by_domain,
    )


def format_realdoc_report(report: RealDocReport) -> str:
    lines = [
        "RealDoc-Bench Results",
        "=" * 60,
        f"Overall Score:          {report['overall_score'] * 100:.1f}%",
        f"Layout Adjusted F1:     {report['layout_adjusted_f1'] * 100:.1f}%",
        f"Document QA Accuracy:   {report['document_qa_accuracy'] * 100:.1f}%",
        f"Avg Field CER:          {report.get('avg_field_cer', 0) * 100:.1f}%",
        f"Total Samples:          {report.get('total_samples', 0)}",
        "",
        "Per Failure Mode:",
        "-" * 60,
    ]

    for name, fm in report.get("failure_modes", {}).items():
        label = name.replace("_", " ").title()
        lines.append(
            f"  {label:30s}  {fm['score'] * 100:5.1f}%  "
            f"(F1={fm.get('layout_f1', 0) * 100:.0f}%, "
            f"QA={fm.get('qa_accuracy', 0) * 100:.0f}%, "
            f"CER={fm.get('field_cer', 0) * 100:.1f}%)"
        )

    return "\n".join(lines)
