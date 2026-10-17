"""Golden benchmark data for insurance documents."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import INSURANCE_SCHEMA


def get_insurance() -> list[dict]:
    return [
        # ── TYPICAL 1 ──────────────────────────────────────────────
        {
            "document_id": "bench_ins_001",
            "doc_type": "insurance",
            "filename": "statefarm_auto.pdf",
            "difficulty": "typical",
            "text": (
                "STATE FARM MUTUAL AUTOMOBILE INSURANCE COMPANY\n"
                "AUTO INSURANCE POLICY DECLARATIONS\n\n"
                "Policy Number: 928-4471-C08-37A\n"
                "Insured Name: Robert A. Fitzgerald\n"
                "Insurer: State Farm Mutual Automobile Insurance Company\n"
                "Effective Date: 01/15/2024\n"
                "Expiration Date: 07/15/2024\n\n"
                "VEHICLE: 2022 Toyota Camry SE\n"
                "VIN: 4T1G11AK2NU123456\n\n"
                "COVERAGES\n"
                "Bodily Injury Liability:    $100,000/$300,000\n"
                "Property Damage Liability:  $50,000\n"
                "Collision:                  $500 Deductible\n"
                "Comprehensive:              $250 Deductible\n"
                "Uninsured Motorist:         $100,000/$300,000\n\n"
                "Premium: $1,247.00\n"
                "Coverage Amount: $300,000\n"
                "Deductible: $500\n\n"
                "Agent: Patricia Morales\n"
                "Agency: 4521 Elm Street, Columbus, OH 43215\n"
                "Phone: (614) 555-0182\n"
            ),
            "expected": {
                "policy_number": "928-4471-C08-37A",
                "insured_name": "Robert A. Fitzgerald",
                "insurer": "State Farm Mutual Automobile Insurance Company",
                "effective_date": "01/15/2024",
                "expiration_date": "07/15/2024",
                "premium": "$1,247.00",
                "coverage_amount": "$300,000",
                "deductible": "$500",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── TYPICAL 2 ──────────────────────────────────────────────
        {
            "document_id": "bench_ins_002",
            "doc_type": "insurance",
            "filename": "allstate_home.pdf",
            "difficulty": "typical",
            "text": (
                "Allstate Insurance Company\n"
                "HOMEOWNERS POLICY DECLARATIONS PAGE\n\n"
                "Policy Number: HO-0946-2837-01\n"
                "Insured Name: Sandra K. Whitmore\n"
                "Insurer: Allstate Insurance Company\n"
                "Effective Date: 04/01/2024\n"
                "Expiration Date: 04/01/2025\n\n"
                "Property Address: 1287 Maple Ridge Dr, Naperville, IL 60540\n\n"
                "COVERAGES\n"
                "Dwelling (Coverage A):       $425,000\n"
                "Other Structures (B):         $42,500\n"
                "Personal Property (C):       $212,500\n"
                "Loss of Use (D):            $127,500\n"
                "Personal Liability (E):      $300,000\n"
                "Medical Payments (F):          $5,000\n\n"
                "Premium: $2,856.00\n"
                "Coverage Amount: $425,000\n"
                "Deductible: $2,500\n\n"
                "Mortgage Company: Wells Fargo Home Mortgage\n"
                "Loan Number: 1049382756\n"
            ),
            "expected": {
                "policy_number": "HO-0946-2837-01",
                "insured_name": "Sandra K. Whitmore",
                "insurer": "Allstate Insurance Company",
                "effective_date": "04/01/2024",
                "expiration_date": "04/01/2025",
                "premium": "$2,856.00",
                "coverage_amount": "$425,000",
                "deductible": "$2,500",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── TYPICAL 3 ──────────────────────────────────────────────
        {
            "document_id": "bench_ins_003",
            "doc_type": "insurance",
            "filename": "geico_auto_claim.pdf",
            "difficulty": "typical",
            "text": (
                "GEICO\n"
                "Government Employees Insurance Company\n"
                "AUTO CLAIM SUMMARY\n\n"
                "Policy Number: 4729-38-1056\n"
                "Insured Name: Anthony D. Reyes\n"
                "Insurer: GEICO General Insurance Company\n"
                "Effective Date: 09/01/2023\n"
                "Expiration Date: 03/01/2024\n\n"
                "Claim Number: CLM-2024-0087432\n"
                "Date of Loss: 01/22/2024\n"
                "Type of Loss: Collision - Rear End\n\n"
                "Vehicle: 2021 Honda Accord Sport\n"
                "VIN: 1HGCV1F34MA654321\n\n"
                "Premium: $892.00\n"
                "Coverage Amount: $250,000\n"
                "Deductible: $1,000\n\n"
                "Damage Estimate: $4,872.00\n"
                "Deductible Applied: $1,000.00\n"
                "Payment Issued: $3,872.00\n"
            ),
            "expected": {
                "policy_number": "4729-38-1056",
                "insured_name": "Anthony D. Reyes",
                "insurer": "GEICO General Insurance Company",
                "effective_date": "09/01/2023",
                "expiration_date": "03/01/2024",
                "premium": "$892.00",
                "coverage_amount": "$250,000",
                "deductible": "$1,000",
                "claim_number": "CLM-2024-0087432",
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── TYPICAL 4 ──────────────────────────────────────────────
        {
            "document_id": "bench_ins_004",
            "doc_type": "insurance",
            "filename": "aetna_health.pdf",
            "difficulty": "typical",
            "text": (
                "Aetna\n"
                "HEALTH INSURANCE ID CARD / SUMMARY OF BENEFITS\n\n"
                "Policy Number: W348921-PPO-2024\n"
                "Insured Name: Michelle T. Granger\n"
                "Insurer: Aetna Life Insurance Company\n"
                "Effective Date: 01/01/2024\n"
                "Expiration Date: 12/31/2024\n\n"
                "Plan Type: PPO\n"
                "Group Number: 89471\n"
                "Member ID: XGH892341201\n\n"
                "Premium: $487.00\n"
                "Coverage Amount: $1,000,000\n"
                "Deductible: $3,000\n\n"
                "Copays:\n"
                "  Primary Care Visit: $25\n"
                "  Specialist Visit: $50\n"
                "  Emergency Room: $250\n"
                "  Prescription (Generic): $10\n\n"
                "Out-of-Pocket Maximum: $8,000\n"
            ),
            "expected": {
                "policy_number": "W348921-PPO-2024",
                "insured_name": "Michelle T. Granger",
                "insurer": "Aetna Life Insurance Company",
                "effective_date": "01/01/2024",
                "expiration_date": "12/31/2024",
                "premium": "$487.00",
                "coverage_amount": "$1,000,000",
                "deductible": "$3,000",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── TYPICAL 5 ──────────────────────────────────────────────
        {
            "document_id": "bench_ins_005",
            "doc_type": "insurance",
            "filename": "metlife_term_life.pdf",
            "difficulty": "typical",
            "text": (
                "MetLife\n"
                "TERM LIFE INSURANCE POLICY\n\n"
                "Policy Number: TL-90284756-2024\n"
                "Insured Name: Gregory S. Nakamura\n"
                "Insurer: Metropolitan Life Insurance Company\n"
                "Effective Date: 03/15/2024\n"
                "Expiration Date: 03/15/2044\n\n"
                "Term: 20 Year Level Term\n"
                "Face Amount / Coverage Amount: $750,000\n\n"
                "Premium: $68.50\n"
                "Payment Frequency: Monthly\n"
                "Deductible: $0\n\n"
                "Beneficiary: Lisa M. Nakamura (Spouse) - 100%\n"
                "Contingent Beneficiary: Emily Nakamura (Daughter) - 100%\n\n"
                "Underwriting Class: Preferred Non-Tobacco\n"
            ),
            "expected": {
                "policy_number": "TL-90284756-2024",
                "insured_name": "Gregory S. Nakamura",
                "insurer": "Metropolitan Life Insurance Company",
                "effective_date": "03/15/2024",
                "expiration_date": "03/15/2044",
                "premium": "$68.50",
                "coverage_amount": "$750,000",
                "deductible": "$0",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── EDGE 1 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ins_006",
            "doc_type": "insurance",
            "filename": "multi_vehicle.pdf",
            "difficulty": "edge",
            "text": (
                "Progressive Insurance\n"
                "MULTI-VEHICLE AUTO POLICY\n\n"
                "Policy Number: 0081-4927-3A\n"
                "Insured Name: The Rodriguez Family Trust\n"
                "Insurer: Progressive Casualty Insurance Company\n"
                "Effective Date: 06/01/2024\n"
                "Expiration Date: 12/01/2024\n\n"
                "Vehicle 1: 2023 Ford F-150 XLT - VIN: 1FTFW1E87NFA98765\n"
                "Vehicle 2: 2022 Honda CR-V EX - VIN: 7FARW2H53NE012345\n"
                "Vehicle 3: 2020 Toyota Corolla LE - VIN: JTDEPRAE5LJ567890\n\n"
                "COMBINED COVERAGES\n"
                "Bodily Injury: $250,000/$500,000 per vehicle\n"
                "Property Damage: $100,000 per vehicle\n"
                "Collision Deductible: $500 each vehicle\n"
                "Comprehensive Deductible: $250 each vehicle\n\n"
                "Premium: $3,412.00\n"
                "Coverage Amount: $500,000\n"
                "Deductible: $500\n\n"
                "Multi-Vehicle Discount Applied: 15%\n"
            ),
            "expected": {
                "policy_number": "0081-4927-3A",
                "insured_name": "The Rodriguez Family Trust",
                "insurer": "Progressive Casualty Insurance Company",
                "effective_date": "06/01/2024",
                "expiration_date": "12/01/2024",
                "premium": "$3,412.00",
                "coverage_amount": "$500,000",
                "deductible": "$500",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── EDGE 2 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ins_007",
            "doc_type": "insurance",
            "filename": "rider_amendment.pdf",
            "difficulty": "edge",
            "text": (
                "Nationwide Insurance\n"
                "POLICY AMENDMENT / RIDER\n\n"
                "Policy Number: HO-7283-9104-R2\n"
                "Insured Name: Patricia E. Langford\n"
                "Insurer: Nationwide Mutual Insurance Company\n"
                "Effective Date: 02/01/2024\n"
                "Expiration Date: 02/01/2025\n\n"
                "AMENDMENT TYPE: Scheduled Personal Property Rider\n"
                "Rider Effective Date: 05/15/2024\n\n"
                "SCHEDULED ITEMS:\n"
                "1. Engagement Ring - Appraised $12,500 - Coverage $12,500\n"
                "2. Rolex Submariner Watch - Appraised $9,800 - Coverage $9,800\n"
                "3. Steinway Model B Piano - Appraised $45,000 - Coverage $45,000\n\n"
                "Additional Premium: $187.00\n"
                "Base Policy Premium: $2,340.00\n"
                "Total Premium: $2,527.00\n\n"
                "Premium: $2,527.00\n"
                "Coverage Amount: $67,300\n"
                "Deductible: $0\n\n"
                "Claim Number: N/A\n"
            ),
            "expected": {
                "policy_number": "HO-7283-9104-R2",
                "insured_name": "Patricia E. Langford",
                "insurer": "Nationwide Mutual Insurance Company",
                "effective_date": "02/01/2024",
                "expiration_date": "02/01/2025",
                "premium": "$2,527.00",
                "coverage_amount": "$67,300",
                "deductible": "$0",
                "claim_number": "N/A",
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── EDGE 3 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ins_008",
            "doc_type": "insurance",
            "filename": "reinstatement.pdf",
            "difficulty": "edge",
            "text": (
                "Liberty Mutual Insurance\n"
                "POLICY REINSTATEMENT NOTICE\n\n"
                "Policy Number: BOP-2024-38291\n"
                "Insured Name: Cornerstone Bakery LLC\n"
                "Insurer: Liberty Mutual Fire Insurance Company\n"
                "Original Effective Date: 01/01/2024\n"
                "Policy Lapsed: 04/01/2024\n"
                "Reinstatement Effective Date: 04/18/2024\n"
                "Effective Date: 04/18/2024\n"
                "Expiration Date: 01/01/2025\n\n"
                "Lapse Reason: Non-payment of premium\n"
                "Reinstatement Fee: $75.00\n\n"
                "Premium: $4,125.00\n"
                "Coverage Amount: $500,000\n"
                "Deductible: $1,000\n\n"
                "NOTE: Coverage was NOT in effect from 04/01/2024 to 04/17/2024.\n"
                "Claims during the lapse period are excluded.\n"
            ),
            "expected": {
                "policy_number": "BOP-2024-38291",
                "insured_name": "Cornerstone Bakery LLC",
                "insurer": "Liberty Mutual Fire Insurance Company",
                "effective_date": "04/18/2024",
                "expiration_date": "01/01/2025",
                "premium": "$4,125.00",
                "coverage_amount": "$500,000",
                "deductible": "$1,000",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── ADVERSARIAL 1 ──────────────────────────────────────────
        {
            "document_id": "bench_ins_009",
            "doc_type": "insurance",
            "filename": "expired_future_claim.pdf",
            "difficulty": "adversarial",
            "text": (
                "Farmers Insurance\n"
                "CLAIM FILING\n\n"
                "Policy Number: FA-83ZZ-1O94-Q7\n"
                "Insured Name: Daniel J. Kowalski\n"
                "Insurer: Farmers Insurance Exchange\n"
                "Effective Date: 01/01/2023\n"
                "Expiration Date: 01/01/2024\n\n"
                "Claim Number: FRM-2024-99821\n"
                "Date of Loss: 06/15/2025\n\n"
                "Description: Water damage to basement from burst pipe.\n"
                "Estimated Damage: $18,400.00\n\n"
                "Premium: $1,890.00\n"
                "Coverage Amount: $350,000\n"
                "Deductible: $2,500\n\n"
                "NOTICE: Policy expired 01/01/2024. Claim date 06/15/2025\n"
                "is after policy expiration.\n"
            ),
            "expected": {
                "policy_number": "FA-83ZZ-1O94-Q7",
                "insured_name": "Daniel J. Kowalski",
                "insurer": "Farmers Insurance Exchange",
                "effective_date": "01/01/2023",
                "expiration_date": "01/01/2024",
                "premium": "$1,890.00",
                "coverage_amount": "$350,000",
                "deductible": "$2,500",
                "claim_number": "FRM-2024-99821",
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
        # ── ADVERSARIAL 2 ──────────────────────────────────────────
        {
            "document_id": "bench_ins_010",
            "doc_type": "insurance",
            "filename": "premium_exceeds_coverage.pdf",
            "difficulty": "adversarial",
            "text": (
                "Zurich Insurance\n"
                "COMMERCIAL LIABILITY POLICY\n\n"
                "Policy Number: CGL-2024-004817\n"
                "Insured Name: Brightside Events LLC\n"
                "Insurer: Zurich American Insurance Company\n"
                "Effective Date: 07/01/2024\n"
                "Expiration Date: 07/01/2025\n\n"
                "Coverage Type: Commercial General Liability\n"
                "Each Occurrence Limit: $500\n\n"
                "Premium: $12,400.00\n"
                "Coverage Amount: $500\n"
                "Deductible: $10,000\n\n"
                "General Aggregate: $1,000\n"
                "Products/Completed Ops Aggregate: $500\n\n"
                "NOTE: Premium of $12,400 exceeds per-occurrence coverage of $500.\n"
            ),
            "expected": {
                "policy_number": "CGL-2024-004817",
                "insured_name": "Brightside Events LLC",
                "insurer": "Zurich American Insurance Company",
                "effective_date": "07/01/2024",
                "expiration_date": "07/01/2025",
                "premium": "$12,400.00",
                "coverage_amount": "$500",
                "deductible": "$10,000",
                "claim_number": None,
            },
            "schema_nodes": INSURANCE_SCHEMA,
        },
    ]
