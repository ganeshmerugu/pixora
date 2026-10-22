"""Golden benchmark data — Invoices (10 documents: 5 typical, 3 edge, 2 adversarial)."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import INVOICE_SCHEMA


def get_invoices() -> list[dict]:
    """Return 10 invoice benchmark documents with ground-truth extractions."""
    return [
        # ── TYPICAL 1 ─────────────────────────────────────────────
        {
            "document_id": "bench_inv_001",
            "doc_type": "invoice",
            "filename": "acme_corp_invoice.pdf",
            "difficulty": "typical",
            "text": (
                "INVOICE\n\n"
                "Vendor Name: Acme Corporation\n"
                "Vendor Address: 1234 Innovation Drive, Suite 500, San Francisco, CA 94105\n\n"
                "Invoice Number: INV-2024-00891\n"
                "Invoice Date: 03/15/2024\n"
                "Due Date: 04/14/2024\n"
                "PO Number: PO-7823\n\n"
                "Bill To Name: TechStart Inc.\n"
                "Bill To Address: 456 Market Street, Floor 12, New York, NY 10013\n\n"
                "| Item | Description | Qty | Unit Price | Amount |\n"
                "| SVC-101 | Cloud Infrastructure Setup | 1 | $12,500.00 | $12,500.00 |\n"
                "| SVC-102 | API Integration Services | 40 | $175.00 | $7,000.00 |\n"
                "| SVC-103 | Data Migration (per GB) | 250 | $8.50 | $2,125.00 |\n"
                "| LIC-200 | Enterprise License (Annual) | 1 | $24,000.00 | $24,000.00 |\n\n"
                "Subtotal: $45,625.00\n"
                "Tax: $4,049.22\n"
                "Total Due: $49,674.22\n\n"
                "Payment Terms: Net 30\n"
                "Wire Transfer: Chase Bank, Routing: 021000021, Account: 483927156\n"
            ),
            "expected": {
                "vendor_name": "Acme Corporation",
                "vendor_address": "1234 Innovation Drive, Suite 500, San Francisco, CA 94105",
                "invoice_number": "INV-2024-00891",
                "invoice_date": "03/15/2024",
                "due_date": "04/14/2024",
                "po_number": "PO-7823",
                "bill_to_name": "TechStart Inc.",
                "bill_to_address": "456 Market Street, Floor 12, New York, NY 10013",
                "subtotal": "$45,625.00",
                "tax": "$4,049.22",
                "total_due": "$49,674.22",
                "payment_terms": "Net 30",
                "__line_items": [
                    {"item": "SVC-101", "description": "Cloud Infrastructure Setup", "qty": "1", "unit_price": "$12,500.00", "amount": "$12,500.00"},
                    {"item": "SVC-102", "description": "API Integration Services", "qty": "40", "unit_price": "$175.00", "amount": "$7,000.00"},
                    {"item": "SVC-103", "description": "Data Migration (per GB)", "qty": "250", "unit_price": "$8.50", "amount": "$2,125.00"},
                    {"item": "LIC-200", "description": "Enterprise License (Annual)", "qty": "1", "unit_price": "$24,000.00", "amount": "$24,000.00"},
                ],
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── TYPICAL 2 ─────────────────────────────────────────────
        {
            "document_id": "bench_inv_002",
            "doc_type": "invoice",
            "filename": "meridian_consulting_inv.pdf",
            "difficulty": "typical",
            "text": (
                "Meridian Consulting Group\n"
                "800 Wilshire Blvd, 14th Floor, Los Angeles, CA 90017\n\n"
                "INVOICE\n\n"
                "Vendor Name: Meridian Consulting Group\n"
                "Vendor Address: 800 Wilshire Blvd, 14th Floor, Los Angeles, CA 90017\n"
                "Invoice Number: MCG-10455\n"
                "Invoice Date: 06/01/2024\n"
                "Due Date: 07/01/2024\n"
                "PO Number: REQ-2024-331\n\n"
                "Bill To Name: Riverside Unified School District\n"
                "Bill To Address: 3380 14th Street, Riverside, CA 92501\n\n"
                "Strategic Planning Workshop (3 days) ... $18,000.00\n"
                "Stakeholder Interview Report .......... $7,500.00\n"
                "Travel & Lodging ...................... $2,340.00\n\n"
                "Subtotal: $27,840.00\n"
                "Tax: $0.00\n"
                "Total Due: $27,840.00\n\n"
                "Payment Terms: Net 45\n"
            ),
            "expected": {
                "vendor_name": "Meridian Consulting Group",
                "vendor_address": "800 Wilshire Blvd, 14th Floor, Los Angeles, CA 90017",
                "invoice_number": "MCG-10455",
                "invoice_date": "06/01/2024",
                "due_date": "07/01/2024",
                "po_number": "REQ-2024-331",
                "bill_to_name": "Riverside Unified School District",
                "bill_to_address": "3380 14th Street, Riverside, CA 92501",
                "subtotal": "$27,840.00",
                "tax": "$0.00",
                "total_due": "$27,840.00",
                "payment_terms": "Net 45",
                "__line_items": [
                    {"description": "Strategic Planning Workshop (3 days)", "amount": "$18,000.00"},
                    {"description": "Stakeholder Interview Report", "amount": "$7,500.00"},
                    {"description": "Travel & Lodging", "amount": "$2,340.00"},
                ],
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── TYPICAL 3 ─────────────────────────────────────────────
        {
            "document_id": "bench_inv_003",
            "doc_type": "invoice",
            "filename": "steelworks_mfg_invoice.pdf",
            "difficulty": "typical",
            "text": (
                "ATLAS STEELWORKS MFG.\n"
                "Invoice\n\n"
                "Vendor Name: Atlas Steelworks Mfg.\n"
                "Vendor Address: 4500 Industrial Parkway, Gary, IN 46402\n"
                "Invoice Number: ASM-77210\n"
                "Invoice Date: 09/20/2024\n"
                "Due Date: 10/20/2024\n"
                "PO Number: PO-00992\n\n"
                "Bill To Name: Consolidated Builders LLC\n"
                "Bill To Address: 1100 Construction Ave, Columbus, OH 43215\n\n"
                "Structural I-Beams W12x26, 40ft (qty 120) ... $186,000.00\n"
                "Steel Plate A36, 1in x 4ft x 8ft (qty 50) .. $47,500.00\n"
                "Delivery & Crane Unloading .................. $8,200.00\n\n"
                "Subtotal: $241,700.00\n"
                "Tax: $16,919.00\n"
                "Total Due: $258,619.00\n\n"
                "Payment Terms: Net 30 — 2% discount if paid within 10 days\n"
            ),
            "expected": {
                "vendor_name": "Atlas Steelworks Mfg.",
                "vendor_address": "4500 Industrial Parkway, Gary, IN 46402",
                "invoice_number": "ASM-77210",
                "invoice_date": "09/20/2024",
                "due_date": "10/20/2024",
                "po_number": "PO-00992",
                "bill_to_name": "Consolidated Builders LLC",
                "bill_to_address": "1100 Construction Ave, Columbus, OH 43215",
                "subtotal": "$241,700.00",
                "tax": "$16,919.00",
                "total_due": "$258,619.00",
                "payment_terms": "Net 30 — 2% discount if paid within 10 days",
                "__line_items": [
                    {"description": "Structural I-Beams W12x26, 40ft", "qty": "120", "amount": "$186,000.00"},
                    {"description": "Steel Plate A36, 1in x 4ft x 8ft", "qty": "50", "amount": "$47,500.00"},
                    {"description": "Delivery & Crane Unloading", "amount": "$8,200.00"},
                ],
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── TYPICAL 4 ─────────────────────────────────────────────
        {
            "document_id": "bench_inv_004",
            "doc_type": "invoice",
            "filename": "savory_catering_inv.pdf",
            "difficulty": "typical",
            "text": (
                "Savory Delights Catering\n"
                "INVOICE\n\n"
                "Vendor Name: Savory Delights Catering\n"
                "Vendor Address: 222 Magnolia Lane, Charleston, SC 29401\n"
                "Invoice Number: SDC-2024-0087\n"
                "Invoice Date: 11/05/2024\n"
                "Due Date: 11/19/2024\n\n"
                "Bill To Name: Harper & Associates Law Firm\n"
                "Bill To Address: 55 Broad Street, Suite 400, Charleston, SC 29401\n\n"
                "Corporate Holiday Gala (150 guests)\n"
                "  Hors d'oeuvres platter x 10 .... $1,200.00\n"
                "  Prime rib carving station ....... $3,800.00\n"
                "  Dessert bar .................... $1,600.00\n"
                "  Wait staff (8 hrs, 12 persons) . $2,880.00\n"
                "  Linen & table decor rental ..... $1,450.00\n\n"
                "Subtotal: $10,930.00\n"
                "Tax: $764.10\n"
                "Total Due: $11,694.10\n\n"
                "Payment Terms: Due upon receipt\n"
            ),
            "expected": {
                "vendor_name": "Savory Delights Catering",
                "vendor_address": "222 Magnolia Lane, Charleston, SC 29401",
                "invoice_number": "SDC-2024-0087",
                "invoice_date": "11/05/2024",
                "due_date": "11/19/2024",
                "bill_to_name": "Harper & Associates Law Firm",
                "bill_to_address": "55 Broad Street, Suite 400, Charleston, SC 29401",
                "subtotal": "$10,930.00",
                "tax": "$764.10",
                "total_due": "$11,694.10",
                "payment_terms": "Due upon receipt",
                "__line_items": [
                    {"description": "Hors d'oeuvres platter x 10", "amount": "$1,200.00"},
                    {"description": "Prime rib carving station", "amount": "$3,800.00"},
                    {"description": "Dessert bar", "amount": "$1,600.00"},
                    {"description": "Wait staff (8 hrs, 12 persons)", "amount": "$2,880.00"},
                    {"description": "Linen & table decor rental", "amount": "$1,450.00"},
                ],
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── TYPICAL 5 ─────────────────────────────────────────────
        {
            "document_id": "bench_inv_005",
            "doc_type": "invoice",
            "filename": "whitfield_legal_inv.pdf",
            "difficulty": "typical",
            "text": (
                "WHITFIELD, GRANT & PEARCE LLP\n"
                "Attorneys at Law\n"
                "One Liberty Plaza, 42nd Floor, New York, NY 10006\n\n"
                "Vendor Name: Whitfield, Grant & Pearce LLP\n"
                "Vendor Address: One Liberty Plaza, 42nd Floor, New York, NY 10006\n"
                "Invoice Number: WGP-24-1893\n"
                "Invoice Date: 02/28/2024\n"
                "Due Date: 03/29/2024\n"
                "PO Number: LGL-4410\n\n"
                "Bill To Name: Orion Pharmaceuticals Inc.\n"
                "Bill To Address: 700 Route 202 South, Bridgewater, NJ 08807\n\n"
                "Legal Services — January 2024\n"
                "  Patent prosecution (42.5 hrs @ $650/hr) .. $27,625.00\n"
                "  FDA regulatory counsel (18 hrs @ $725/hr)  $13,050.00\n"
                "  Paralegal support (30 hrs @ $195/hr) ..... $5,850.00\n"
                "  Filing fees & court costs ................ $3,475.00\n\n"
                "Subtotal: $50,000.00\n"
                "Tax: $0.00\n"
                "Total Due: $50,000.00\n\n"
                "Payment Terms: Net 30\n"
            ),
            "expected": {
                "vendor_name": "Whitfield, Grant & Pearce LLP",
                "vendor_address": "One Liberty Plaza, 42nd Floor, New York, NY 10006",
                "invoice_number": "WGP-24-1893",
                "invoice_date": "02/28/2024",
                "due_date": "03/29/2024",
                "po_number": "LGL-4410",
                "bill_to_name": "Orion Pharmaceuticals Inc.",
                "bill_to_address": "700 Route 202 South, Bridgewater, NJ 08807",
                "subtotal": "$50,000.00",
                "tax": "$0.00",
                "total_due": "$50,000.00",
                "payment_terms": "Net 30",
                "__line_items": [
                    {"description": "Patent prosecution (42.5 hrs @ $650/hr)", "amount": "$27,625.00"},
                    {"description": "FDA regulatory counsel (18 hrs @ $725/hr)", "amount": "$13,050.00"},
                    {"description": "Paralegal support (30 hrs @ $195/hr)", "amount": "$5,850.00"},
                    {"description": "Filing fees & court costs", "amount": "$3,475.00"},
                ],
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── EDGE 1 — European date format, multi-currency ─────────
        {
            "document_id": "bench_inv_006",
            "doc_type": "invoice",
            "filename": "eurologic_rechnung.pdf",
            "difficulty": "edge",
            "text": (
                "EuroLogic GmbH\n"
                "Friedrichstrasse 123, 10117 Berlin, Germany\n\n"
                "Rechnung / Invoice\n\n"
                "Vendor Name: EuroLogic GmbH\n"
                "Vendor Address: Friedrichstrasse 123, 10117 Berlin, Germany\n"
                "Invoice Number: EL-2024-DE-0042\n"
                "Invoice Date: 15.03.2024\n"
                "Due Date: 14.04.2024\n\n"
                "Bill To Name: Sentinel Dynamics Corp.\n"
                "Bill To Address: 9000 North Central Expressway, Suite 1200, Dallas, TX 75231, USA\n\n"
                "SAP Integration Module License (EUR) ... EUR 45,000.00\n"
                "Implementation Consulting (80 hrs) ..... EUR 32,000.00\n"
                "Data Center Hosting (Q1 2024) .......... EUR 8,750.00\n\n"
                "Subtotal: EUR 85,750.00\n"
                "Tax: EUR 16,292.50\n"
                "Total Due: EUR 102,042.50\n\n"
                "Payment Terms: 30 Tage netto / Net 30 days\n"
                "IBAN: DE89 3704 0044 0532 0130 00\n"
                "BIC: COBADEFFXXX\n"
            ),
            "expected": {
                "vendor_name": "EuroLogic GmbH",
                "vendor_address": "Friedrichstrasse 123, 10117 Berlin, Germany",
                "invoice_number": "EL-2024-DE-0042",
                "invoice_date": "15.03.2024",
                "due_date": "14.04.2024",
                "bill_to_name": "Sentinel Dynamics Corp.",
                "bill_to_address": "9000 North Central Expressway, Suite 1200, Dallas, TX 75231, USA",
                "subtotal": "EUR 85,750.00",
                "tax": "EUR 16,292.50",
                "total_due": "EUR 102,042.50",
                "payment_terms": "30 Tage netto / Net 30 days",
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── EDGE 2 — Written-out month, partial data ──────────────
        {
            "document_id": "bench_inv_007",
            "doc_type": "invoice",
            "filename": "bluecrest_partial_inv.pdf",
            "difficulty": "edge",
            "text": (
                "BlueCrest Environmental Services\n\n"
                "Vendor Name: BlueCrest Environmental Services\n"
                "Vendor Address: 14 Lakeshore Drive, Burlington, VT 05401\n"
                "Invoice Number: BCES-9917\n"
                "Invoice Date: 22nd January 2024\n\n"
                "Bill To Name: Town of Shelburne\n\n"
                "Water quality testing — 12 sample sites ... $4,800.00\n"
                "Soil contamination assessment ............. $6,200.00\n"
                "Environmental impact summary report ....... $3,500.00\n\n"
                "Total Due: $14,500.00\n\n"
                "Payment Terms: Net 60\n"
                "Note: Subtotal and tax waived — government contract exempt.\n"
            ),
            "expected": {
                "vendor_name": "BlueCrest Environmental Services",
                "vendor_address": "14 Lakeshore Drive, Burlington, VT 05401",
                "invoice_number": "BCES-9917",
                "invoice_date": "22nd January 2024",
                "bill_to_name": "Town of Shelburne",
                "total_due": "$14,500.00",
                "payment_terms": "Net 60",
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── EDGE 3 — Multi-line address, unusual amount ───────────
        {
            "document_id": "bench_inv_008",
            "doc_type": "invoice",
            "filename": "tokyo_precision_inv.pdf",
            "difficulty": "edge",
            "text": (
                "Tokyo Precision Instruments Co., Ltd.\n\n"
                "Vendor Name: Tokyo Precision Instruments Co., Ltd.\n"
                "Vendor Address: 3-14-1 Hamamatsucho, Minato-ku, Tokyo 105-0013, Japan\n"
                "Invoice Number: TPI-JP-240315\n"
                "Invoice Date: March 15, 2024\n"
                "Due Date: May 14, 2024\n"
                "PO Number: INTL-PO-88231\n\n"
                "Bill To Name: Pacific Northwest Research Institute\n"
                "Bill To Address: 720 Broadway East, Building C, 3rd Floor, Seattle, WA 98102, United States\n\n"
                "Scanning Electron Microscope SEM-7800F (qty 1) ... $487,000.00\n"
                "Installation & Calibration ...................... $12,500.00\n"
                "Extended Warranty — 5 year ...................... $38,000.00\n"
                "Crating & International Shipping ................ $9,450.00\n\n"
                "Subtotal: $546,950.00\n"
                "Tax: $0.00\n"
                "Total Due: $546,950.00\n\n"
                "Payment Terms: 50% deposit, balance Net 60 from delivery\n"
            ),
            "expected": {
                "vendor_name": "Tokyo Precision Instruments Co., Ltd.",
                "vendor_address": "3-14-1 Hamamatsucho, Minato-ku, Tokyo 105-0013, Japan",
                "invoice_number": "TPI-JP-240315",
                "invoice_date": "March 15, 2024",
                "due_date": "May 14, 2024",
                "po_number": "INTL-PO-88231",
                "bill_to_name": "Pacific Northwest Research Institute",
                "bill_to_address": "720 Broadway East, Building C, 3rd Floor, Seattle, WA 98102, United States",
                "subtotal": "$546,950.00",
                "tax": "$0.00",
                "total_due": "$546,950.00",
                "payment_terms": "50% deposit, balance Net 60 from delivery",
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── ADVERSARIAL 1 — OCR garble, trap values ───────────────
        {
            "document_id": "bench_inv_009",
            "doc_type": "invoice",
            "filename": "ocr_scan_noisy_inv.pdf",
            "difficulty": "adversarial",
            "text": (
                "SUMNIT TECHN0L0GY S0LUTI0NS\n\n"
                "Vendor Name: Sumnit Techn0l0gy S0luti0ns\n"
                "Vendor Address: 2900 Comrnerce Blvd, Ste 310, Birrningham, AL 35203\n"
                "Invoice Nurnber: ST-2024-0331\n"
                "Invoice Date: 04/01/2024\n"
                "Due Date: 05/01/2024\n\n"
                "Bill To Narne: Arneritech Distributors lnc.\n"
                "Bill To Address: 1550 Lake Cook Rd, Deerfield, lL 60015\n\n"
                "Managed lT Services (March 2024) ........... $8,500.00\n"
                "Previous Balance (ref# 88412) .............. $12,750.00\n"
                "Cybersecurity Audit — Phase l .............. $15,000.00\n\n"
                "Subtotal: $23,500.00\n"
                "Tax: $1,645.00\n"
                "Total Due: $25,145.00\n\n"
                "Payment Terrns: Net 30\n"
                "REMIT TO: Sumnit Technology Solutions\n"
            ),
            "expected": {
                "vendor_name": "Sumnit Techn0l0gy S0luti0ns",
                "vendor_address": "2900 Comrnerce Blvd, Ste 310, Birrningham, AL 35203",
                "invoice_number": "ST-2024-0331",
                "invoice_date": "04/01/2024",
                "due_date": "05/01/2024",
                "bill_to_name": "Arneritech Distributors lnc.",
                "bill_to_address": "1550 Lake Cook Rd, Deerfield, lL 60015",
                "subtotal": "$23,500.00",
                "tax": "$1,645.00",
                "total_due": "$25,145.00",
                "payment_terms": "Net 30",
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
        # ── ADVERSARIAL 2 — Missing required fields, near-miss labels ──
        {
            "document_id": "bench_inv_010",
            "doc_type": "invoice",
            "filename": "ambiguous_statement_inv.pdf",
            "difficulty": "adversarial",
            "text": (
                "DRAKE SUPPLY CO.\n\n"
                "Vendor Name: Drake Supply Co.\n"
                "Reference No: DS-00-4182\n"
                "Statement Date: 07/15/2024\n\n"
                "Bill To Name: Martinez Construction Group\n"
                "Bill To Address: PO Box 9104, Tucson, AZ 85752\n\n"
                "Lumber — 2x4x8 SPF (bundle 200) ... $1,240.00\n"
                "Concrete Mix 80lb bags (qty 150) ... $975.00\n"
                "Rebar #4 x 20ft (qty 80) .......... $1,120.00\n"
                "Previous Credit Applied ............ -$500.00\n"
                "Account Balance .................... $14,293.00\n\n"
                "Amount This Invoice: $2,835.00\n"
                "Total Due: $2,835.00\n\n"
                "Payment Terms: COD\n"
                "Note: Account Balance of $14,293.00 includes prior invoices.\n"
            ),
            "expected": {
                "vendor_name": "Drake Supply Co.",
                "invoice_number": "DS-00-4182",
                "invoice_date": "07/15/2024",
                "bill_to_name": "Martinez Construction Group",
                "bill_to_address": "PO Box 9104, Tucson, AZ 85752",
                "total_due": "$2,835.00",
                "payment_terms": "COD",
            },
            "schema_nodes": INVOICE_SCHEMA,
        },
    ]
