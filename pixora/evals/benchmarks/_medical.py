"""Golden benchmark data — Medical (10 documents: 5 typical, 3 edge, 2 adversarial)."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import MEDICAL_SCHEMA


def get_medical() -> list[dict]:
    """Return 10 medical document benchmarks with ground-truth extractions."""
    return [
        # ── TYPICAL 1 — Lab results (CBC + metabolic) ─────────────
        {
            "document_id": "bench_med_001",
            "doc_type": "medical",
            "filename": "williams_lab_results.pdf",
            "difficulty": "typical",
            "text": (
                "LABORATORY REPORT\n"
                "Quest Diagnostics — Chantilly, VA\n\n"
                "Patient Name: Robert J. Williams\n"
                "Date Of Birth: 05/12/1978\n"
                "MRN: MRN-00284719\n"
                "Ordering Physician: Dr. Amanda Torres, MD\n"
                "Collection Date: 03/08/2024\n"
                "Report Date: 03/09/2024\n\n"
                "COMPLETE BLOOD COUNT (CBC)\n"
                "WBC: 7.2 x10^3/uL (ref 4.5-11.0)\n"
                "RBC: 4.85 x10^6/uL (ref 4.50-5.90)\n"
                "Hemoglobin: 14.8 g/dL (ref 13.5-17.5)\n"
                "Platelets: 245 x10^3/uL (ref 150-400)\n\n"
                "METABOLIC PANEL\n"
                "Glucose Fasting: 112 mg/dL (ref 70-99) ** HIGH **\n"
                "BUN: 18 mg/dL (ref 7-20)\n"
                "Creatinine: 1.0 mg/dL (ref 0.7-1.3)\n\n"
                "Diagnosis: Pre-diabetic condition, elevated fasting glucose\n"
            ),
            "expected": {
                "patient_name": "Robert J. Williams",
                "date_of_birth": "05/12/1978",
                "mrn": "MRN-00284719",
                "ordering_physician": "Dr. Amanda Torres, MD",
                "collection_date": "03/08/2024",
                "report_date": "03/09/2024",
                "diagnosis": "Pre-diabetic condition, elevated fasting glucose",
                "glucose_fasting": "112",
                "hemoglobin": "14.8",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── TYPICAL 2 — Prescription ──────────────────────────────
        {
            "document_id": "bench_med_002",
            "doc_type": "medical",
            "filename": "chen_prescription.pdf",
            "difficulty": "typical",
            "text": (
                "PRESCRIPTION\n"
                "Metropolitan Medical Associates\n"
                "1250 Connecticut Ave NW, Washington, DC 20036\n\n"
                "Patient Name: Linda M. Chen\n"
                "Date Of Birth: 11/03/1965\n"
                "MRN: MRN-00519832\n"
                "Ordering Physician: Dr. James Whitaker, MD\n"
                "Collection Date: 04/22/2024\n"
                "Report Date: 04/22/2024\n\n"
                "Rx 1: Lisinopril 20mg — Take 1 tablet daily\n"
                "      Qty: 90, Refills: 3\n"
                "Rx 2: Atorvastatin 40mg — Take 1 tablet at bedtime\n"
                "      Qty: 90, Refills: 3\n\n"
                "Diagnosis: Essential hypertension, hyperlipidemia\n\n"
                "Glucose Fasting: 94\n"
                "Hemoglobin: 13.1\n"
            ),
            "expected": {
                "patient_name": "Linda M. Chen",
                "date_of_birth": "11/03/1965",
                "mrn": "MRN-00519832",
                "ordering_physician": "Dr. James Whitaker, MD",
                "collection_date": "04/22/2024",
                "report_date": "04/22/2024",
                "diagnosis": "Essential hypertension, hyperlipidemia",
                "glucose_fasting": "94",
                "hemoglobin": "13.1",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── TYPICAL 3 — Discharge summary ─────────────────────────
        {
            "document_id": "bench_med_003",
            "doc_type": "medical",
            "filename": "patel_discharge_summary.pdf",
            "difficulty": "typical",
            "text": (
                "DISCHARGE SUMMARY\n"
                "Johns Hopkins Hospital — Baltimore, MD\n\n"
                "Patient Name: Anil K. Patel\n"
                "Date Of Birth: 07/29/1952\n"
                "MRN: JHH-8827410\n"
                "Ordering Physician: Dr. Catherine Reyes, MD\n"
                "Collection Date: 05/15/2024\n"
                "Report Date: 05/18/2024\n\n"
                "Admission: 05/15/2024 for acute chest pain\n"
                "Discharge: 05/18/2024\n\n"
                "Diagnosis: Non-ST elevation myocardial infarction (NSTEMI)\n\n"
                "Labs at Admission:\n"
                "Glucose Fasting: 145\n"
                "Hemoglobin: 11.9\n"
                "Troponin I: 2.8 ng/mL (ref <0.04) ** CRITICAL **\n\n"
                "Procedures: Cardiac catheterization, drug-eluting stent to LAD\n"
                "Discharge Meds: Aspirin 81mg, Clopidogrel 75mg, Metoprolol 50mg\n"
            ),
            "expected": {
                "patient_name": "Anil K. Patel",
                "date_of_birth": "07/29/1952",
                "mrn": "JHH-8827410",
                "ordering_physician": "Dr. Catherine Reyes, MD",
                "collection_date": "05/15/2024",
                "report_date": "05/18/2024",
                "diagnosis": "Non-ST elevation myocardial infarction (NSTEMI)",
                "glucose_fasting": "145",
                "hemoglobin": "11.9",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── TYPICAL 4 — Radiology report ──────────────────────────
        {
            "document_id": "bench_med_004",
            "doc_type": "medical",
            "filename": "johnson_radiology_report.pdf",
            "difficulty": "typical",
            "text": (
                "RADIOLOGY REPORT\n"
                "Mayo Clinic — Rochester, MN\n\n"
                "Patient Name: Deborah A. Johnson\n"
                "Date Of Birth: 02/14/1980\n"
                "MRN: MC-33918204\n"
                "Ordering Physician: Dr. William Nakamura, MD\n"
                "Collection Date: 06/10/2024\n"
                "Report Date: 06/11/2024\n\n"
                "Exam: CT Chest with Contrast\n"
                "Clinical Indication: Persistent cough, rule out malignancy\n\n"
                "Findings: 8mm ground-glass nodule in the right lower lobe.\n"
                "No mediastinal lymphadenopathy. Heart size normal.\n\n"
                "Diagnosis: Pulmonary nodule, indeterminate, recommend follow-up CT in 3 months\n\n"
                "Glucose Fasting: 88\n"
                "Hemoglobin: 14.2\n"
            ),
            "expected": {
                "patient_name": "Deborah A. Johnson",
                "date_of_birth": "02/14/1980",
                "mrn": "MC-33918204",
                "ordering_physician": "Dr. William Nakamura, MD",
                "collection_date": "06/10/2024",
                "report_date": "06/11/2024",
                "diagnosis": "Pulmonary nodule, indeterminate, recommend follow-up CT in 3 months",
                "glucose_fasting": "88",
                "hemoglobin": "14.2",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── TYPICAL 5 — Referral letter ───────────────────────────
        {
            "document_id": "bench_med_005",
            "doc_type": "medical",
            "filename": "garcia_referral_letter.pdf",
            "difficulty": "typical",
            "text": (
                "REFERRAL LETTER\n"
                "Austin Family Practice\n"
                "3100 Red River St, Austin, TX 78705\n\n"
                "Patient Name: Maria Elena Garcia\n"
                "Date Of Birth: 09/21/1990\n"
                "MRN: AFP-00117294\n"
                "Ordering Physician: Dr. Robert Hernandez, DO\n"
                "Collection Date: 08/05/2024\n"
                "Report Date: 08/05/2024\n\n"
                "Dear Dr. Schwartz,\n\n"
                "I am referring Ms. Garcia for evaluation of persistent\n"
                "bilateral knee pain unresponsive to conservative management.\n\n"
                "Recent Labs:\n"
                "Glucose Fasting: 91\n"
                "Hemoglobin: 12.8\n"
                "ESR: 42 mm/hr (ref <20) ** HIGH **\n"
                "CRP: 3.8 mg/dL (ref <1.0) ** HIGH **\n\n"
                "Diagnosis: Bilateral knee osteoarthritis, suspected inflammatory component\n"
            ),
            "expected": {
                "patient_name": "Maria Elena Garcia",
                "date_of_birth": "09/21/1990",
                "mrn": "AFP-00117294",
                "ordering_physician": "Dr. Robert Hernandez, DO",
                "collection_date": "08/05/2024",
                "report_date": "08/05/2024",
                "diagnosis": "Bilateral knee osteoarthritis, suspected inflammatory component",
                "glucose_fasting": "91",
                "hemoglobin": "12.8",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── EDGE 1 — Multiple test panels, critical flags ─────────
        {
            "document_id": "bench_med_006",
            "doc_type": "medical",
            "filename": "thompson_critical_labs.pdf",
            "difficulty": "edge",
            "text": (
                "*** CRITICAL VALUES — PHYSICIAN NOTIFIED ***\n\n"
                "LabCorp — Comprehensive Panel\n\n"
                "Patient Name: Gerald D. Thompson\n"
                "Date Of Birth: 12.25.1948\n"
                "MRN: LC-99281004\n"
                "Ordering Physician: Dr. Priya Sundaram, MD\n"
                "Collection Date: 09/14/2024\n"
                "Report Date: 09/14/2024\n\n"
                "RENAL PANEL:\n"
                "BUN: 58 mg/dL (ref 7-20) *** CRITICAL HIGH ***\n"
                "Creatinine: 4.2 mg/dL (ref 0.7-1.3) *** CRITICAL HIGH ***\n"
                "eGFR: 14 mL/min (ref >60) *** CRITICAL LOW ***\n"
                "Potassium: 6.1 mEq/L (ref 3.5-5.0) *** CRITICAL HIGH ***\n\n"
                "CBC:\n"
                "Hemoglobin: 9.2\n"
                "Platelets: 98 x10^3/uL (ref 150-400) ** LOW **\n\n"
                "METABOLIC:\n"
                "Glucose Fasting: 287\n"
                "HbA1c: 11.4% (ref <5.7) *** CRITICAL HIGH ***\n\n"
                "Diagnosis: Acute kidney injury, uncontrolled diabetes mellitus, anemia\n"
            ),
            "expected": {
                "patient_name": "Gerald D. Thompson",
                "date_of_birth": "12.25.1948",
                "mrn": "LC-99281004",
                "ordering_physician": "Dr. Priya Sundaram, MD",
                "collection_date": "09/14/2024",
                "report_date": "09/14/2024",
                "diagnosis": "Acute kidney injury, uncontrolled diabetes mellitus, anemia",
                "glucose_fasting": "287",
                "hemoglobin": "9.2",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── EDGE 2 — Handwritten note indicator, partial data ─────
        {
            "document_id": "bench_med_007",
            "doc_type": "medical",
            "filename": "kim_handwritten_notes.pdf",
            "difficulty": "edge",
            "text": (
                "CLINICAL NOTES — Handwritten, transcribed by medical records\n"
                "Southside Community Health Center\n\n"
                "Patient Name: Soon-Yi Kim\n"
                "Date Of Birth: March 3, 1985\n"
                "MRN: SCHC-4102\n"
                "Ordering Physician: Dr. Marcus Washington, MD\n"
                "Collection Date: 10/01/2024\n\n"
                "[Handwritten] Chief Complaint: Fatigue x 3 weeks, weight loss\n"
                "[Handwritten] PE: Thyroid mildly enlarged, nontender\n\n"
                "Labs Ordered:\n"
                "Glucose Fasting: 79\n"
                "Hemoglobin: 10.4\n"
                "TSH: 0.08 mIU/L (ref 0.4-4.0) ** LOW **\n"
                "Free T4: 3.9 ng/dL (ref 0.8-1.8) ** HIGH **\n\n"
                "Diagnosis: Hyperthyroidism, suspected Graves disease\n"
                "[Handwritten] Referral to endocrinology — Dr. Patel\n"
            ),
            "expected": {
                "patient_name": "Soon-Yi Kim",
                "date_of_birth": "March 3, 1985",
                "mrn": "SCHC-4102",
                "ordering_physician": "Dr. Marcus Washington, MD",
                "collection_date": "10/01/2024",
                "diagnosis": "Hyperthyroidism, suspected Graves disease",
                "glucose_fasting": "79",
                "hemoglobin": "10.4",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── EDGE 3 — Pediatric, unusual units ─────────────────────
        {
            "document_id": "bench_med_008",
            "doc_type": "medical",
            "filename": "oconnell_pediatric_labs.pdf",
            "difficulty": "edge",
            "text": (
                "PEDIATRIC LABORATORY REPORT\n"
                "Children's Hospital of Philadelphia\n\n"
                "Patient Name: Liam J. O'Connell\n"
                "Date Of Birth: 04/18/2018\n"
                "MRN: CHOP-002891\n"
                "Ordering Physician: Dr. Elizabeth Fong, MD (Pediatrics)\n"
                "Collection Date: 07/22/2024\n"
                "Report Date: 07/23/2024\n\n"
                "Age at collection: 6 years 3 months\n\n"
                "CBC (Pediatric Ranges):\n"
                "Hemoglobin: 11.5\n"
                "WBC: 8.9 x10^3/uL\n"
                "Platelets: 310 x10^3/uL\n\n"
                "Metabolic:\n"
                "Glucose Fasting: 82\n"
                "Lead (Whole Blood): 3.1 mcg/dL (ref <3.5)\n\n"
                "Diagnosis: Well child check, labs within normal limits\n"
            ),
            "expected": {
                "patient_name": "Liam J. O'Connell",
                "date_of_birth": "04/18/2018",
                "mrn": "CHOP-002891",
                "ordering_physician": "Dr. Elizabeth Fong, MD (Pediatrics)",
                "collection_date": "07/22/2024",
                "report_date": "07/23/2024",
                "diagnosis": "Well child check, labs within normal limits",
                "glucose_fasting": "82",
                "hemoglobin": "11.5",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── ADVERSARIAL 1 — OCR garble, garbled patient ID ────────
        {
            "document_id": "bench_med_009",
            "doc_type": "medical",
            "filename": "ocr_garbled_lab_report.pdf",
            "difficulty": "adversarial",
            "text": (
                "LAB0RATORY REP0RT\n"
                "Centra1 Patho1ogy Associates\n\n"
                "Patient Name: Thornas E. Andersen\n"
                "Date Of Birth: O8/31/l957\n"
                "MRN: CPA-OO4l829l\n"
                "Ordering Physician: Dr. Natalie Forrest, MD\n"
                "Collection Date: ll/20/2024\n"
                "Report Date: ll/21/2024\n\n"
                "CBC:\n"
                "Hemoglobin: 16.1\n"
                "WBC: l2.4 x10^3/uL (ref 4.5-ll.0) ** HlGH **\n\n"
                "Metabolic:\n"
                "Glucose Fasting: l04\n"
                "Creatinine: l.l mg/dL\n\n"
                "PSA: 8.7 ng/rnL (ref <4.0) ** HlGH **\n\n"
                "Diagnosis: Leukocytosis, elevated PSA — urology referral recornrnended\n"
            ),
            "expected": {
                "patient_name": "Thornas E. Andersen",
                "date_of_birth": "O8/31/l957",
                "mrn": "CPA-OO4l829l",
                "ordering_physician": "Dr. Natalie Forrest, MD",
                "collection_date": "ll/20/2024",
                "report_date": "ll/21/2024",
                "diagnosis": "Leukocytosis, elevated PSA — urology referral recornrnended",
                "glucose_fasting": "l04",
                "hemoglobin": "16.1",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
        # ── ADVERSARIAL 2 — Conflicting dates, trap values ────────
        {
            "document_id": "bench_med_010",
            "doc_type": "medical",
            "filename": "conflicting_dates_lab.pdf",
            "difficulty": "adversarial",
            "text": (
                "LABORATORY REPORT\n"
                "Regional Medical Center — Tulsa, OK\n\n"
                "Patient Name: Barbara J. Kowalski\n"
                "Date Of Birth: 06/15/1970\n"
                "MRN: RMC-7718294\n"
                "Ordering Physician: Dr. Samuel Obi, MD\n"
                "Collection Date: 02/28/2024\n"
                "Report Date: 02/27/2024\n\n"
                "NOTE: Report date precedes collection date due to timezone\n"
                "data entry error. Correct report date is 03/01/2024.\n\n"
                "Prior Glucose (ref only): 210 mg/dL  <-- from 01/2023, not current\n\n"
                "Hemoglobin: 13.5\n"
                "Glucose Fasting: 98\n\n"
                "Diagnosis: Diabetes monitoring, fasting glucose within normal limits\n"
            ),
            "expected": {
                "patient_name": "Barbara J. Kowalski",
                "date_of_birth": "06/15/1970",
                "mrn": "RMC-7718294",
                "ordering_physician": "Dr. Samuel Obi, MD",
                "collection_date": "02/28/2024",
                "report_date": "02/27/2024",
                "diagnosis": "Diabetes monitoring, fasting glucose within normal limits",
                "glucose_fasting": "98",
                "hemoglobin": "13.5",
            },
            "schema_nodes": MEDICAL_SCHEMA,
        },
    ]
