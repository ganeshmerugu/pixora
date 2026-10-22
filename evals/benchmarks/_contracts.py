"""Golden benchmark data — Contracts (10 documents: 5 typical, 3 edge, 2 adversarial)."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import CONTRACT_SCHEMA


def get_contracts() -> list[dict]:
    """Return 10 contract benchmark documents with ground-truth extractions."""
    return [
        # ── TYPICAL 1 — SaaS Agreement ────────────────────────────
        {
            "document_id": "bench_contract_001",
            "doc_type": "contract",
            "filename": "cloudscale_saas_agreement.pdf",
            "difficulty": "typical",
            "text": (
                "SOFTWARE AS A SERVICE AGREEMENT\n\n"
                "Agreement Type: Software as a Service Agreement\n"
                "Effective Date: January 1, 2024\n\n"
                "Provider Name: CloudScale Inc.\n"
                "Provider Address: 100 Tech Park Way, Wilmington, DE 19801\n\n"
                "Client Name: Pinnacle Financial Services, LLC\n"
                "Client Address: 2200 Broadway, Suite 1800, Denver, CO 80203\n\n"
                "1. SERVICES\n"
                "Provider shall provide Client access to the CloudScale Platform.\n\n"
                "2. TERM\n"
                "Initial Term: 36 months from Effective Date.\n"
                "Renewal: Automatic 12-month renewals unless 90 days written notice.\n\n"
                "3. FEES\n"
                "Annual Fee: $180,000.00\n"
                "Payment: Quarterly in advance ($45,000 per quarter)\n\n"
                "4. LIMITATION OF LIABILITY\n"
                "Liability Cap: $180,000.00\n\n"
                "5. GOVERNING LAW\n"
                "Governing Law: State of Delaware\n\n"
                "IN WITNESS WHEREOF the parties have executed this Agreement.\n"
            ),
            "expected": {
                "agreement_type": "Software as a Service Agreement",
                "effective_date": "January 1, 2024",
                "provider_name": "CloudScale Inc.",
                "provider_address": "100 Tech Park Way, Wilmington, DE 19801",
                "client_name": "Pinnacle Financial Services, LLC",
                "client_address": "2200 Broadway, Suite 1800, Denver, CO 80203",
                "initial_term": "36 months from Effective Date.",
                "annual_fee": "$180,000.00",
                "governing_law": "State of Delaware",
                "liability_cap": "$180,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── TYPICAL 2 — NDA ───────────────────────────────────────
        {
            "document_id": "bench_contract_002",
            "doc_type": "contract",
            "filename": "mutual_nda.pdf",
            "difficulty": "typical",
            "text": (
                "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
                "Agreement Type: Mutual Non-Disclosure Agreement\n"
                "Effective Date: March 15, 2024\n\n"
                "Provider Name: Apex Robotics Corp.\n"
                "Provider Address: 5500 Flatiron Pkwy, Boulder, CO 80301\n\n"
                "Client Name: VentureWorks Capital Partners\n"
                "Client Address: 375 Park Avenue, Suite 3200, New York, NY 10152\n\n"
                "1. PURPOSE\n"
                "The parties wish to explore a potential business relationship\n"
                "and may disclose Confidential Information to each other.\n\n"
                "2. TERM\n"
                "Initial Term: 24 months\n"
                "Survival of obligations: 3 years after termination.\n\n"
                "3. RESTRICTIONS\n"
                "Neither party may reverse-engineer, decompile, or disassemble\n"
                "any Confidential Information.\n\n"
                "Governing Law: State of New York\n"
            ),
            "expected": {
                "agreement_type": "Mutual Non-Disclosure Agreement",
                "effective_date": "March 15, 2024",
                "provider_name": "Apex Robotics Corp.",
                "provider_address": "5500 Flatiron Pkwy, Boulder, CO 80301",
                "client_name": "VentureWorks Capital Partners",
                "client_address": "375 Park Avenue, Suite 3200, New York, NY 10152",
                "initial_term": "24 months",
                "governing_law": "State of New York",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── TYPICAL 3 — Employment Agreement ──────────────────────
        {
            "document_id": "bench_contract_003",
            "doc_type": "contract",
            "filename": "employment_agreement.pdf",
            "difficulty": "typical",
            "text": (
                "EMPLOYMENT AGREEMENT\n\n"
                "Agreement Type: Employment Agreement\n"
                "Effective Date: June 1, 2024\n\n"
                "Provider Name: NovaBridge Technologies Inc.\n"
                "Provider Address: 1 Hacker Way, Building 20, Menlo Park, CA 94025\n\n"
                "Client Name: Dr. Samantha R. Okafor\n"
                "Client Address: 482 Elm Street, Palo Alto, CA 94301\n\n"
                "1. POSITION: Vice President of Engineering\n"
                "2. COMPENSATION\n"
                "   Annual Fee: $425,000.00\n"
                "   Equity: 50,000 stock options, 4-year vest with 1-year cliff\n\n"
                "3. TERM\n"
                "Initial Term: At-will employment\n\n"
                "4. NON-COMPETE\n"
                "Employee agrees not to engage in competing business for 12 months\n"
                "following termination within 50-mile radius.\n\n"
                "5. IP ASSIGNMENT\n"
                "All inventions created during employment are the sole property\n"
                "of the Company.\n\n"
                "Governing Law: State of California\n"
            ),
            "expected": {
                "agreement_type": "Employment Agreement",
                "effective_date": "June 1, 2024",
                "provider_name": "NovaBridge Technologies Inc.",
                "provider_address": "1 Hacker Way, Building 20, Menlo Park, CA 94025",
                "client_name": "Dr. Samantha R. Okafor",
                "client_address": "482 Elm Street, Palo Alto, CA 94301",
                "initial_term": "At-will employment",
                "annual_fee": "$425,000.00",
                "governing_law": "State of California",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── TYPICAL 4 — Consulting Agreement ──────────────────────
        {
            "document_id": "bench_contract_004",
            "doc_type": "contract",
            "filename": "consulting_services_agreement.pdf",
            "difficulty": "typical",
            "text": (
                "CONSULTING SERVICES AGREEMENT\n\n"
                "Agreement Type: Consulting Services Agreement\n"
                "Effective Date: September 1, 2024\n\n"
                "Provider Name: Blackthorn Advisory Group LLC\n"
                "Provider Address: 200 Clarendon Street, 52nd Floor, Boston, MA 02116\n\n"
                "Client Name: Great Lakes Energy Cooperative\n"
                "Client Address: 1400 E Michigan Ave, Lansing, MI 48912\n\n"
                "1. SCOPE\n"
                "Strategic consulting for grid modernization initiative.\n\n"
                "2. FEES\n"
                "Annual Fee: $360,000.00\n"
                "Billed monthly at $30,000 per month.\n\n"
                "3. TERM\n"
                "Initial Term: 12 months\n\n"
                "4. TERMINATION\n"
                "Either party may terminate with 30 days written notice.\n\n"
                "5. LIABILITY\n"
                "Liability Cap: $360,000.00\n\n"
                "Governing Law: Commonwealth of Massachusetts\n"
            ),
            "expected": {
                "agreement_type": "Consulting Services Agreement",
                "effective_date": "September 1, 2024",
                "provider_name": "Blackthorn Advisory Group LLC",
                "provider_address": "200 Clarendon Street, 52nd Floor, Boston, MA 02116",
                "client_name": "Great Lakes Energy Cooperative",
                "client_address": "1400 E Michigan Ave, Lansing, MI 48912",
                "initial_term": "12 months",
                "annual_fee": "$360,000.00",
                "governing_law": "Commonwealth of Massachusetts",
                "liability_cap": "$360,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── TYPICAL 5 — Commercial Lease ──────────────────────────
        {
            "document_id": "bench_contract_005",
            "doc_type": "contract",
            "filename": "office_lease_agreement.pdf",
            "difficulty": "typical",
            "text": (
                "COMMERCIAL OFFICE LEASE AGREEMENT\n\n"
                "Agreement Type: Commercial Office Lease\n"
                "Effective Date: February 1, 2024\n\n"
                "Provider Name: Greystone Property Management Inc.\n"
                "Provider Address: 1700 Market Street, Suite 3400, Philadelphia, PA 19103\n\n"
                "Client Name: Catalyst Digital Marketing Agency\n"
                "Client Address: Same as Premises\n\n"
                "Premises: Suite 800, 1700 Market Street, Philadelphia, PA 19103\n"
                "Square Footage: 4,200 sq ft\n\n"
                "Initial Term: 60 months\n"
                "Annual Fee: $126,000.00\n"
                "Monthly Rent: $10,500.00 per month, due 1st of each month.\n\n"
                "Security Deposit: $21,000.00\n\n"
                "Liability Cap: $500,000.00\n\n"
                "Governing Law: Commonwealth of Pennsylvania\n"
            ),
            "expected": {
                "agreement_type": "Commercial Office Lease",
                "effective_date": "February 1, 2024",
                "provider_name": "Greystone Property Management Inc.",
                "provider_address": "1700 Market Street, Suite 3400, Philadelphia, PA 19103",
                "client_name": "Catalyst Digital Marketing Agency",
                "client_address": "Same as Premises",
                "initial_term": "60 months",
                "annual_fee": "$126,000.00",
                "governing_law": "Commonwealth of Pennsylvania",
                "liability_cap": "$500,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── EDGE 1 — Multi-jurisdiction, European date ────────────
        {
            "document_id": "bench_contract_006",
            "doc_type": "contract",
            "filename": "cross_border_services.pdf",
            "difficulty": "edge",
            "text": (
                "CROSS-BORDER TECHNOLOGY SERVICES AGREEMENT\n\n"
                "Agreement Type: Cross-Border Technology Services Agreement\n"
                "Effective Date: 01.07.2024\n\n"
                "Provider Name: Nordic Data Systems AB\n"
                "Provider Address: Sveavagen 44, 111 34 Stockholm, Sweden\n\n"
                "Client Name: Ashford-Meridian Holdings plc\n"
                "Client Address: 25 Cabot Square, Canary Wharf, London E14 4QA, United Kingdom\n\n"
                "1. SERVICES\n"
                "Cloud infrastructure management across EU/UK data centers.\n\n"
                "2. TERM\n"
                "Initial Term: 24 months with automatic renewal\n\n"
                "3. FEES\n"
                "Annual Fee: EUR 240,000.00\n"
                "Payable semi-annually in advance.\n\n"
                "4. DATA PROTECTION\n"
                "GDPR and UK Data Protection Act 2018 compliance required.\n\n"
                "5. DISPUTE RESOLUTION\n"
                "Arbitration under ICC Rules, seated in Zurich, Switzerland.\n\n"
                "Governing Law: Laws of Sweden with respect to Provider obligations; Laws of England and Wales with respect to Client obligations\n\n"
                "Liability Cap: EUR 480,000.00\n"
            ),
            "expected": {
                "agreement_type": "Cross-Border Technology Services Agreement",
                "effective_date": "01.07.2024",
                "provider_name": "Nordic Data Systems AB",
                "provider_address": "Sveavagen 44, 111 34 Stockholm, Sweden",
                "client_name": "Ashford-Meridian Holdings plc",
                "client_address": "25 Cabot Square, Canary Wharf, London E14 4QA, United Kingdom",
                "initial_term": "24 months with automatic renewal",
                "annual_fee": "EUR 240,000.00",
                "governing_law": "Laws of Sweden with respect to Provider obligations; Laws of England and Wales with respect to Client obligations",
                "liability_cap": "EUR 480,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── EDGE 2 — Ambiguous terms, partial data ────────────────
        {
            "document_id": "bench_contract_007",
            "doc_type": "contract",
            "filename": "vague_partnership_mou.pdf",
            "difficulty": "edge",
            "text": (
                "MEMORANDUM OF UNDERSTANDING\n\n"
                "Agreement Type: Memorandum of Understanding\n"
                "Effective Date: To be determined upon mutual signature\n\n"
                "Provider Name: Sunrise Wellness Partners\n"
                "Provider Address: 300 Biscayne Blvd, Suite 2900, Miami, FL 33131\n\n"
                "Client Name: Harmony Health Systems\n\n"
                "1. PURPOSE\n"
                "The parties intend to explore co-development of telehealth platform.\n\n"
                "2. TERM\n"
                "Initial Term: TBD — subject to board approval\n\n"
                "3. FINANCIAL TERMS\n"
                "Revenue sharing: To be negotiated\n"
                "Annual Fee: Not yet established\n\n"
                "4. NON-BINDING\n"
                "This MOU is non-binding except for Sections 5, 6, and 7.\n\n"
                "Governing Law: State of Florida\n"
            ),
            "expected": {
                "agreement_type": "Memorandum of Understanding",
                "effective_date": "To be determined upon mutual signature",
                "provider_name": "Sunrise Wellness Partners",
                "provider_address": "300 Biscayne Blvd, Suite 2900, Miami, FL 33131",
                "client_name": "Harmony Health Systems",
                "annual_fee": "Not yet established",
                "initial_term": "TBD — subject to board approval",
                "governing_law": "State of Florida",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── EDGE 3 — IP assignment, written-out date ──────────────
        {
            "document_id": "bench_contract_008",
            "doc_type": "contract",
            "filename": "ip_assignment_agreement.pdf",
            "difficulty": "edge",
            "text": (
                "INTELLECTUAL PROPERTY ASSIGNMENT AGREEMENT\n\n"
                "Agreement Type: Intellectual Property Assignment Agreement\n"
                "Effective Date: Twenty-Third of April, Two Thousand Twenty-Four\n\n"
                "Provider Name: Dr. Rajan Mehta (Individual)\n"
                "Provider Address: 1188 Mission Street, Apt 14C, San Francisco, CA 94103\n\n"
                "Client Name: GenomicsAI Inc.\n"
                "Client Address: 4000 Shoreline Court, South San Francisco, CA 94080\n\n"
                "1. ASSIGNMENT\n"
                "Assignor irrevocably assigns all right, title, and interest in\n"
                "Patent Application No. US 2023/0412881 to Assignee.\n\n"
                "2. CONSIDERATION\n"
                "Annual Fee: $75,000.00 plus 2% royalty on net revenue\n\n"
                "3. TERM\n"
                "Initial Term: Perpetual and irrevocable\n\n"
                "Governing Law: State of California\n"
                "Liability Cap: $150,000.00\n"
            ),
            "expected": {
                "agreement_type": "Intellectual Property Assignment Agreement",
                "effective_date": "Twenty-Third of April, Two Thousand Twenty-Four",
                "provider_name": "Dr. Rajan Mehta (Individual)",
                "provider_address": "1188 Mission Street, Apt 14C, San Francisco, CA 94103",
                "client_name": "GenomicsAI Inc.",
                "client_address": "4000 Shoreline Court, South San Francisco, CA 94080",
                "initial_term": "Perpetual and irrevocable",
                "annual_fee": "$75,000.00 plus 2% royalty on net revenue",
                "governing_law": "State of California",
                "liability_cap": "$150,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── ADVERSARIAL 1 — Contradictory dates, OCR garble ──────
        {
            "document_id": "bench_contract_009",
            "doc_type": "contract",
            "filename": "ocr_scanned_contract.pdf",
            "difficulty": "adversarial",
            "text": (
                "MASTER SERVICES AGREERNENT\n\n"
                "Agreement Type: Master Services Agreernent\n"
                "Effective Date: Decernber 1, 2024\n\n"
                "Provider Name: lronclad Solutions lnc.\n"
                "Provider Address: 770 Broadwav, 4th FIoor, New York, NY l0003\n\n"
                "Client Name: Northstar Logistics Group\n"
                "Client Address: 9200 Ward Parkway, Kansas Citv, MO 64ll4\n\n"
                "1. TERM\n"
                "Initial Term: 18 rnonths frorn Effective Date.\n"
                "This agreernent commences on January 15, 2025.\n\n"
                "2. FEES\n"
                "Annual Fee: $216,000.00\n"
                "Monthly retainer: $l8,000.00\n\n"
                "3. LIABILITY\n"
                "Liability Cap: $216,000.00\n\n"
                "Governing Law: State of Missouri\n"
            ),
            "expected": {
                "agreement_type": "Master Services Agreernent",
                "effective_date": "Decernber 1, 2024",
                "provider_name": "lronclad Solutions lnc.",
                "provider_address": "770 Broadwav, 4th FIoor, New York, NY l0003",
                "client_name": "Northstar Logistics Group",
                "client_address": "9200 Ward Parkway, Kansas Citv, MO 64ll4",
                "initial_term": "18 rnonths frorn Effective Date.",
                "annual_fee": "$216,000.00",
                "governing_law": "State of Missouri",
                "liability_cap": "$216,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
        # ── ADVERSARIAL 2 — Missing signatures, near-miss labels ──
        {
            "document_id": "bench_contract_010",
            "doc_type": "contract",
            "filename": "unsigned_draft_contract.pdf",
            "difficulty": "adversarial",
            "text": (
                "DRAFT — FOR DISCUSSION ONLY — NOT EXECUTED\n\n"
                "PROFESSIONAL SERVICES AGREEMENT\n\n"
                "Agreement Type: Professional Services Agreement\n"
                "Effective Date: [DATE]\n\n"
                "Provider Name: Redwood Cybersecurity Partners\n"
                "Provider Address: 2121 N California Blvd, Suite 600, Walnut Creek, CA 94596\n\n"
                "Client Name: [CLIENT NAME TO BE INSERTED]\n"
                "Client Address: [ADDRESS]\n\n"
                "Proposed Annual Fee: $500,000.00\n"
                "Annual Fee: $500,000.00\n\n"
                "Initial Term: 24 months\n"
                "Prior engagement value: $1,200,000  <-- historical, not this contract\n\n"
                "Liability Cap: $1,000,000.00\n\n"
                "Governing Law: State of California\n\n"
                "SIGNATURES:\n"
                "Provider: ___________________________\n"
                "Client:   ___________________________\n"
            ),
            "expected": {
                "agreement_type": "Professional Services Agreement",
                "effective_date": "[DATE]",
                "provider_name": "Redwood Cybersecurity Partners",
                "provider_address": "2121 N California Blvd, Suite 600, Walnut Creek, CA 94596",
                "client_name": "[CLIENT NAME TO BE INSERTED]",
                "client_address": "[ADDRESS]",
                "initial_term": "24 months",
                "annual_fee": "$500,000.00",
                "governing_law": "State of California",
                "liability_cap": "$1,000,000.00",
            },
            "schema_nodes": CONTRACT_SCHEMA,
        },
    ]
