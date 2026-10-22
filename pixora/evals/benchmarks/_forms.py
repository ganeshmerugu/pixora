"""Golden benchmark data — Forms (10 documents: 5 typical, 3 edge, 2 adversarial)."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import FORM_SCHEMA


def get_forms() -> list[dict]:
    """Return 10 form benchmark documents with ground-truth extractions."""
    return [
        # ── TYPICAL 1 — W-9 ──────────────────────────────────────
        {
            "document_id": "bench_form_001",
            "doc_type": "form",
            "filename": "dataflow_w9.pdf",
            "difficulty": "typical",
            "text": (
                "REQUEST FOR TAXPAYER IDENTIFICATION NUMBER AND CERTIFICATION\n"
                "Form W-9 (Rev. October 2018)\n\n"
                "Form Type: W-9\n"
                "Name: DataFlow Analytics, LLC\n"
                "Business Name: DataFlow Analytics\n"
                "Tax Classification: Limited liability company — C\n"
                "Address: 550 Technology Square\n"
                "City State Zip: Cambridge, MA 02139\n\n"
                "Part I — Taxpayer Identification Number (TIN)\n"
                "EIN: 82-4917356\n\n"
                "Part II — Certification\n"
                "Signature: /s/ Michael Park\n"
                "Signature Date: 02/20/2024\n"
            ),
            "expected": {
                "form_type": "W-9",
                "name": "DataFlow Analytics, LLC",
                "business_name": "DataFlow Analytics",
                "tax_classification": "Limited liability company — C",
                "address": "550 Technology Square",
                "city_state_zip": "Cambridge, MA 02139",
                "ein": "82-4917356",
                "signature_date": "02/20/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── TYPICAL 2 — W-9, sole proprietor ──────────────────────
        {
            "document_id": "bench_form_002",
            "doc_type": "form",
            "filename": "martinez_w9.pdf",
            "difficulty": "typical",
            "text": (
                "Form W-9\n"
                "Request for Taxpayer Identification Number and Certification\n\n"
                "Form Type: W-9\n"
                "Name: Carlos A. Martinez\n"
                "Business Name: Martinez Plumbing Services\n"
                "Tax Classification: Sole proprietor\n"
                "Address: 1847 Oak Hill Avenue\n"
                "City State Zip: San Antonio, TX 78201\n\n"
                "EIN: 74-3218905\n\n"
                "Signature: /s/ Carlos A. Martinez\n"
                "Signature Date: 05/10/2024\n"
            ),
            "expected": {
                "form_type": "W-9",
                "name": "Carlos A. Martinez",
                "business_name": "Martinez Plumbing Services",
                "tax_classification": "Sole proprietor",
                "address": "1847 Oak Hill Avenue",
                "city_state_zip": "San Antonio, TX 78201",
                "ein": "74-3218905",
                "signature_date": "05/10/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── TYPICAL 3 — W-4 ──────────────────────────────────────
        {
            "document_id": "bench_form_003",
            "doc_type": "form",
            "filename": "nguyen_w4.pdf",
            "difficulty": "typical",
            "text": (
                "Employee's Withholding Certificate\n"
                "Form W-4 (2024)\n\n"
                "Form Type: W-4\n"
                "Name: Tina Q. Nguyen\n"
                "Address: 4810 Magnolia Boulevard, Apt 7\n"
                "City State Zip: Burbank, CA 91505\n\n"
                "Filing Status: Married filing jointly\n"
                "Tax Classification: Employee\n\n"
                "Step 3 — Claim Dependents: $4,000\n"
                "Step 4(a) — Other income: $0\n"
                "Step 4(b) — Deductions: $0\n"
                "Step 4(c) — Extra withholding: $50\n\n"
                "EIN: 95-1234567\n"
                "Signature Date: 01/15/2024\n"
            ),
            "expected": {
                "form_type": "W-4",
                "name": "Tina Q. Nguyen",
                "address": "4810 Magnolia Boulevard, Apt 7",
                "city_state_zip": "Burbank, CA 91505",
                "tax_classification": "Employee",
                "ein": "95-1234567",
                "signature_date": "01/15/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── TYPICAL 4 — Vendor application form ───────────────────
        {
            "document_id": "bench_form_004",
            "doc_type": "form",
            "filename": "greenleaf_vendor_app.pdf",
            "difficulty": "typical",
            "text": (
                "VENDOR APPLICATION FORM\n"
                "City of Portland — Procurement Division\n\n"
                "Form Type: Vendor Application\n"
                "Name: Greenleaf Landscaping Inc.\n"
                "Business Name: Greenleaf Landscaping Inc.\n"
                "Tax Classification: S Corporation\n"
                "Address: 8920 SE Foster Road\n"
                "City State Zip: Portland, OR 97266\n\n"
                "Federal Tax ID:\n"
                "EIN: 93-2847105\n\n"
                "Primary Contact: Jennifer Oakes, Operations Manager\n"
                "Phone: (503) 555-0147\n"
                "Email: joakes@greenleafpdx.com\n\n"
                "Signature Date: 03/01/2024\n"
                "Certified Small Business: [X] Yes\n"
            ),
            "expected": {
                "form_type": "Vendor Application",
                "name": "Greenleaf Landscaping Inc.",
                "business_name": "Greenleaf Landscaping Inc.",
                "tax_classification": "S Corporation",
                "address": "8920 SE Foster Road",
                "city_state_zip": "Portland, OR 97266",
                "ein": "93-2847105",
                "signature_date": "03/01/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── TYPICAL 5 — Registration form ─────────────────────────
        {
            "document_id": "bench_form_005",
            "doc_type": "form",
            "filename": "summit_conference_reg.pdf",
            "difficulty": "typical",
            "text": (
                "CONFERENCE REGISTRATION FORM\n"
                "2024 National Healthcare IT Summit\n\n"
                "Form Type: Conference Registration\n"
                "Name: Dr. Patricia Owens\n"
                "Business Name: Owens Medical Consulting PLLC\n"
                "Tax Classification: Professional LLC\n"
                "Address: 1200 Main Street, Suite 500\n"
                "City State Zip: Dallas, TX 75202\n\n"
                "EIN: 75-9182034\n\n"
                "Registration Tier: Premium ($2,495)\n"
                "Dietary Requirements: Vegetarian\n"
                "Sessions Selected: Keynote, AI in Diagnostics, Cybersecurity Panel\n\n"
                "Signature Date: 04/15/2024\n"
            ),
            "expected": {
                "form_type": "Conference Registration",
                "name": "Dr. Patricia Owens",
                "business_name": "Owens Medical Consulting PLLC",
                "tax_classification": "Professional LLC",
                "address": "1200 Main Street, Suite 500",
                "city_state_zip": "Dallas, TX 75202",
                "ein": "75-9182034",
                "signature_date": "04/15/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── EDGE 1 — Amended form, checkbox fields ────────────────
        {
            "document_id": "bench_form_006",
            "doc_type": "form",
            "filename": "amended_w9.pdf",
            "difficulty": "edge",
            "text": (
                "*** AMENDED ***\n"
                "Form W-9 (Rev. October 2018)\n"
                "Request for Taxpayer Identification Number and Certification\n\n"
                "Form Type: W-9 (Amended)\n"
                "Name: Quantum Dynamics Research Corp.\n"
                "Business Name: QDR Corp (formerly Quantum Labs Inc.)\n"
                "Tax Classification: C Corporation\n"
                "Address: 2700 Sand Hill Road, Building 4\n"
                "City State Zip: Menlo Park, CA 94025\n\n"
                "Exempt payee code: [X] 5\n"
                "Exemption from FATCA: [X] A\n\n"
                "Previous EIN (void): 94-3001782\n"
                "EIN: 94-3218907\n\n"
                "Reason for amendment: Corporate name change and new EIN\n"
                "Signature Date: 08/22/2024\n"
            ),
            "expected": {
                "form_type": "W-9 (Amended)",
                "name": "Quantum Dynamics Research Corp.",
                "business_name": "QDR Corp (formerly Quantum Labs Inc.)",
                "tax_classification": "C Corporation",
                "address": "2700 Sand Hill Road, Building 4",
                "city_state_zip": "Menlo Park, CA 94025",
                "ein": "94-3218907",
                "signature_date": "08/22/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── EDGE 2 — Incomplete sections, multi-section ───────────
        {
            "document_id": "bench_form_007",
            "doc_type": "form",
            "filename": "incomplete_i9.pdf",
            "difficulty": "edge",
            "text": (
                "Employment Eligibility Verification\n"
                "Form I-9 (Rev. 10/21/2019)\n\n"
                "Form Type: I-9\n\n"
                "Section 1 — Employee Information:\n"
                "Name: Alejandro Reyes-Fuentes\n"
                "Address: 2250 W Roosevelt Rd\n"
                "City State Zip: Chicago, IL 60608\n\n"
                "EIN: 36-7281940\n"
                "Signature Date: 06/03/2024\n\n"
                "Section 2 — Employer Review:\n"
                "Document Title: US Passport\n"
                "Document Number: 538291047\n"
                "Expiration: 11/2029\n\n"
                "Section 3 — Reverification:\n"
                "[NOT COMPLETED]\n"
            ),
            "expected": {
                "form_type": "I-9",
                "name": "Alejandro Reyes-Fuentes",
                "address": "2250 W Roosevelt Rd",
                "city_state_zip": "Chicago, IL 60608",
                "ein": "36-7281940",
                "signature_date": "06/03/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── EDGE 3 — Very long address, European date ─────────────
        {
            "document_id": "bench_form_008",
            "doc_type": "form",
            "filename": "international_vendor_form.pdf",
            "difficulty": "edge",
            "text": (
                "INTERNATIONAL VENDOR REGISTRATION FORM\n"
                "United Nations Office for Project Services (UNOPS)\n\n"
                "Form Type: International Vendor Registration\n"
                "Name: Consolidated Infrastructure Development Partners Ltd.\n"
                "Business Name: CIDP Ltd.\n"
                "Tax Classification: Foreign Corporation\n"
                "Address: Level 28, Three Pacific Place, 1 Queen's Road East, Admiralty\n"
                "City State Zip: Hong Kong SAR, China 999077\n\n"
                "EIN: 98-7654321\n\n"
                "Signature Date: 15.09.2024\n"
                "Authorized Representative: Kwame Asante, Managing Director\n"
            ),
            "expected": {
                "form_type": "International Vendor Registration",
                "name": "Consolidated Infrastructure Development Partners Ltd.",
                "business_name": "CIDP Ltd.",
                "tax_classification": "Foreign Corporation",
                "address": "Level 28, Three Pacific Place, 1 Queen's Road East, Admiralty",
                "city_state_zip": "Hong Kong SAR, China 999077",
                "ein": "98-7654321",
                "signature_date": "15.09.2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── ADVERSARIAL 1 — Invalid EIN, OCR garble ───────────────
        {
            "document_id": "bench_form_009",
            "doc_type": "form",
            "filename": "ocr_garbled_w9.pdf",
            "difficulty": "adversarial",
            "text": (
                "Forrn W-9\n"
                "Request for Taxpayer ldentification Nurnber\n\n"
                "Form Type: W-9\n"
                "Name: Prestige Worldwide Enterprises lnc.\n"
                "Business Name: Prestige Worldwide\n"
                "Tax Classification: C Cornoration\n"
                "Address: l00 Cornrnerce Drive, Bldg 3\n"
                "City State Zip: Starrford, CT O69O2\n\n"
                "EIN: 0B-47S1238\n\n"
                "Note: EIN appears garbled — original document unclear.\n\n"
                "Signature Date: O3/28/2O24\n"
            ),
            "expected": {
                "form_type": "W-9",
                "name": "Prestige Worldwide Enterprises lnc.",
                "business_name": "Prestige Worldwide",
                "tax_classification": "C Cornoration",
                "address": "l00 Cornrnerce Drive, Bldg 3",
                "city_state_zip": "Starrford, CT O69O2",
                "ein": "0B-47S1238",
                "signature_date": "O3/28/2O24",
            },
            "schema_nodes": FORM_SCHEMA,
        },
        # ── ADVERSARIAL 2 — Conflicting names, trap fields ────────
        {
            "document_id": "bench_form_010",
            "doc_type": "form",
            "filename": "conflicting_names_form.pdf",
            "difficulty": "adversarial",
            "text": (
                "Form W-9\n"
                "Request for Taxpayer Identification Number and Certification\n\n"
                "Form Type: W-9\n\n"
                "Prepared By: Janice Wu (assistant — not the taxpayer)\n\n"
                "Name: Sterling & Associates Wealth Management LLC\n"
                "Business Name: Sterling Wealth Mgmt\n"
                "Tax Classification: Partnership\n"
                "Address: 777 Brickell Avenue, PH-1\n"
                "City State Zip: Miami, FL 33131\n\n"
                "Previous EIN (closed account): 59-1111111\n"
                "EIN: 59-8834021\n\n"
                "Contact Name: Richard Sterling III\n"
                "Signature Date: 11/01/2024\n"
                "Signature: /s/ Janice Wu, per authorization\n"
            ),
            "expected": {
                "form_type": "W-9",
                "name": "Sterling & Associates Wealth Management LLC",
                "business_name": "Sterling Wealth Mgmt",
                "tax_classification": "Partnership",
                "address": "777 Brickell Avenue, PH-1",
                "city_state_zip": "Miami, FL 33131",
                "ein": "59-8834021",
                "signature_date": "11/01/2024",
            },
            "schema_nodes": FORM_SCHEMA,
        },
    ]
