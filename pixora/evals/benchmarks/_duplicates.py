"""Near-duplicate benchmark pairs for dedup evaluation.

Contains 10 documents forming 5 known duplicate pairs:
- Exact duplicate (same invoice, re-scanned)
- Near duplicate (same invoice, different date)
- OCR-corrupted copy
- Transposed field values
- Different format, same data
"""
from __future__ import annotations


def get_duplicate_benchmarks() -> list[dict]:
    return [
        {
            "document_id": "dedup_inv_001a",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "Acme Corporation",
                "invoice_number": "INV-2024-00891",
                "invoice_date": "03/15/2024",
                "total_due": "$49,674.22",
                "bill_to_name": "TechStart Inc.",
            },
        },
        {
            "document_id": "dedup_inv_001b",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "Acme Corporation",
                "invoice_number": "INV-2024-00891",
                "invoice_date": "03/15/2024",
                "total_due": "$49,674.22",
                "bill_to_name": "TechStart Inc.",
            },
        },
        {
            "document_id": "dedup_inv_002a",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "Meridian Consulting Group",
                "invoice_number": "MCG-10455",
                "invoice_date": "06/01/2024",
                "total_due": "$27,840.00",
                "bill_to_name": "Riverside Unified School District",
            },
        },
        {
            "document_id": "dedup_inv_002b",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "Meridian Consulting Group",
                "invoice_number": "MCG-10455",
                "invoice_date": "07/01/2024",
                "total_due": "$27,840.00",
                "bill_to_name": "Riverside Unified School District",
            },
        },
        {
            "document_id": "dedup_inv_003a",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "Atlas Steelworks Mfg.",
                "invoice_number": "ASM-77210",
                "invoice_date": "09/20/2024",
                "total_due": "$258,619.00",
                "bill_to_name": "Consolidated Builders LLC",
            },
        },
        {
            "document_id": "dedup_inv_003b",
            "doc_type": "invoice",
            "expected": {
                "vendor_name": "At1as Stee1works Mfg.",
                "invoice_number": "ASM-772l0",
                "invoice_date": "O9/2O/2024",
                "total_due": "$258,6l9.00",
                "bill_to_name": "Conso1idated Bui1ders LLC",
            },
        },
        {
            "document_id": "dedup_med_001a",
            "doc_type": "medical",
            "expected": {
                "patient_name": "Robert J. Williams",
                "mrn": "MRN-00284719",
                "collection_date": "03/08/2024",
                "diagnosis": "Pre-diabetic condition, elevated fasting glucose",
                "ordering_physician": "Dr. Amanda Torres, MD",
            },
        },
        {
            "document_id": "dedup_med_001b",
            "doc_type": "medical",
            "expected": {
                "patient_name": "Williams, Robert J.",
                "mrn": "MRN-00284719",
                "collection_date": "03/08/2024",
                "diagnosis": "Pre-diabetic condition, elevated fasting glucose",
                "ordering_physician": "Dr. Amanda Torres, MD",
            },
        },
        {
            "document_id": "dedup_contract_001a",
            "doc_type": "contract",
            "expected": {
                "contract_number": "CTR-2024-0042",
                "party_a": "Pinnacle Software Inc.",
                "party_b": "DataVault Solutions LLC",
                "effective_date": "01/15/2024",
                "contract_value": "$750,000.00",
            },
        },
        {
            "document_id": "dedup_contract_001b",
            "doc_type": "contract",
            "expected": {
                "contract_number": "CTR-2024-0042",
                "party_a": "Pinnacle Software Inc.",
                "party_b": "DataVault Solutions LLC",
                "effective_date": "January 15, 2024",
                "contract_value": "$750,000.00",
            },
        },
    ]


EXPECTED_DUPLICATE_PAIRS: list[tuple[str, str]] = [
    ("dedup_inv_001a", "dedup_inv_001b"),
    ("dedup_inv_002a", "dedup_inv_002b"),
    ("dedup_inv_003a", "dedup_inv_003b"),
    ("dedup_med_001a", "dedup_med_001b"),
    ("dedup_contract_001a", "dedup_contract_001b"),
]
