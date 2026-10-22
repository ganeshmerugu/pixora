"""Golden benchmark data for government documents."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import GOVERNMENT_SCHEMA


def get_government() -> list[dict]:
    return [
        # ── TYPICAL 1 ──────────────────────────────────────────────
        {
            "document_id": "bench_gov_001",
            "doc_type": "government",
            "filename": "business_license.pdf",
            "difficulty": "typical",
            "text": (
                "CITY OF SEATTLE\n"
                "DEPARTMENT OF FINANCE AND ADMINISTRATIVE SERVICES\n"
                "BUSINESS LICENSE\n\n"
                "Document Type: Business License\n"
                "Document Number: BL-2024-038741\n"
                "Issuing Authority: City of Seattle Department of Finance\n"
                "Issue Date: 01/15/2024\n"
                "Expiration Date: 01/15/2025\n\n"
                "Full Name: Emerald City Coffee Roasters LLC\n"
                "Address: 1847 Pike Place, Seattle, WA 98101\n"
                "Status: Active\n\n"
                "Business Type: Retail Food Establishment\n"
                "NAICS Code: 722515\n"
                "Owner: Katherine M. Lindstrom\n\n"
                "This license must be posted in a conspicuous location.\n"
            ),
            "expected": {
                "document_type": "Business License",
                "document_number": "BL-2024-038741",
                "issuing_authority": "City of Seattle Department of Finance",
                "issue_date": "01/15/2024",
                "expiration_date": "01/15/2025",
                "full_name": "Emerald City Coffee Roasters LLC",
                "address": "1847 Pike Place, Seattle, WA 98101",
                "status": "Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── TYPICAL 2 ──────────────────────────────────────────────
        {
            "document_id": "bench_gov_002",
            "doc_type": "government",
            "filename": "building_permit.pdf",
            "difficulty": "typical",
            "text": (
                "COUNTY OF MARICOPA, ARIZONA\n"
                "PLANNING AND DEVELOPMENT DEPARTMENT\n"
                "BUILDING PERMIT\n\n"
                "Document Type: Building Permit\n"
                "Document Number: BP-MC-2024-14829\n"
                "Issuing Authority: Maricopa County Planning and Development\n"
                "Issue Date: 03/01/2024\n"
                "Expiration Date: 03/01/2026\n\n"
                "Full Name: Desert Ridge Development Corp.\n"
                "Address: 18200 N Tatum Blvd, Phoenix, AZ 85032\n"
                "Status: Approved\n\n"
                "Project Description: New single-family residence, 2,850 sq ft\n"
                "Estimated Cost: $425,000\n"
                "Contractor: Sonoran Builders Inc. (ROC #298471)\n"
                "Zoning: R1-10\n"
            ),
            "expected": {
                "document_type": "Building Permit",
                "document_number": "BP-MC-2024-14829",
                "issuing_authority": "Maricopa County Planning and Development",
                "issue_date": "03/01/2024",
                "expiration_date": "03/01/2026",
                "full_name": "Desert Ridge Development Corp.",
                "address": "18200 N Tatum Blvd, Phoenix, AZ 85032",
                "status": "Approved",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── TYPICAL 3 ──────────────────────────────────────────────
        {
            "document_id": "bench_gov_003",
            "doc_type": "government",
            "filename": "property_tax_assessment.pdf",
            "difficulty": "typical",
            "text": (
                "COMMONWEALTH OF VIRGINIA\n"
                "FAIRFAX COUNTY\n"
                "REAL PROPERTY TAX ASSESSMENT\n\n"
                "Document Type: Tax Assessment\n"
                "Document Number: TA-FFX-2024-092847\n"
                "Issuing Authority: Fairfax County Department of Tax Administration\n"
                "Issue Date: 02/01/2024\n\n"
                "Full Name: James R. and Emily P. Thornton\n"
                "Address: 9421 Georgetown Pike, Great Falls, VA 22066\n"
                "Status: Current\n\n"
                "Tax Year: 2024\n"
                "Land Value: $485,000\n"
                "Improvement Value: $672,000\n"
                "Total Assessed Value: $1,157,000\n"
                "Tax Rate: $1.11 per $100\n"
                "Annual Tax Due: $12,842.70\n"
            ),
            "expected": {
                "document_type": "Tax Assessment",
                "document_number": "TA-FFX-2024-092847",
                "issuing_authority": "Fairfax County Department of Tax Administration",
                "issue_date": "02/01/2024",
                "expiration_date": None,
                "full_name": "James R. and Emily P. Thornton",
                "address": "9421 Georgetown Pike, Great Falls, VA 22066",
                "status": "Current",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── TYPICAL 4 ──────────────────────────────────────────────
        {
            "document_id": "bench_gov_004",
            "doc_type": "government",
            "filename": "voter_registration.pdf",
            "difficulty": "typical",
            "text": (
                "STATE OF GEORGIA\n"
                "SECRETARY OF STATE\n"
                "VOTER REGISTRATION CONFIRMATION\n\n"
                "Document Type: Voter Registration Card\n"
                "Document Number: VR-GA-2024-5829104\n"
                "Issuing Authority: Georgia Secretary of State Elections Division\n"
                "Issue Date: 04/10/2024\n\n"
                "Full Name: Maria Elena Vasquez\n"
                "Address: 342 Moreland Ave NE, Atlanta, GA 30307\n"
                "Status: Active\n\n"
                "County: DeKalb\n"
                "Congressional District: 5\n"
                "State Senate District: 36\n"
                "Precinct: DK07-2A\n"
                "Polling Place: Candler Park Community Center\n"
            ),
            "expected": {
                "document_type": "Voter Registration Card",
                "document_number": "VR-GA-2024-5829104",
                "issuing_authority": "Georgia Secretary of State Elections Division",
                "issue_date": "04/10/2024",
                "expiration_date": None,
                "full_name": "Maria Elena Vasquez",
                "address": "342 Moreland Ave NE, Atlanta, GA 30307",
                "status": "Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── TYPICAL 5 ──────────────────────────────────────────────
        {
            "document_id": "bench_gov_005",
            "doc_type": "government",
            "filename": "vehicle_title.pdf",
            "difficulty": "typical",
            "text": (
                "STATE OF TEXAS\n"
                "DEPARTMENT OF MOTOR VEHICLES\n"
                "CERTIFICATE OF TITLE\n\n"
                "Document Type: Vehicle Title\n"
                "Document Number: 04829174381\n"
                "Issuing Authority: Texas Department of Motor Vehicles\n"
                "Issue Date: 05/22/2024\n\n"
                "Full Name: Christopher L. Dawson\n"
                "Address: 2914 Westheimer Rd, Houston, TX 77098\n"
                "Status: Clear\n\n"
                "Vehicle: 2024 Tesla Model 3 Long Range\n"
                "VIN: 5YJ3E1EA5RF123456\n"
                "Color: Pearl White Multi-Coat\n"
                "Odometer: 00,247 miles\n"
                "Lien Holder: Tesla Finance LLC\n"
            ),
            "expected": {
                "document_type": "Vehicle Title",
                "document_number": "04829174381",
                "issuing_authority": "Texas Department of Motor Vehicles",
                "issue_date": "05/22/2024",
                "expiration_date": None,
                "full_name": "Christopher L. Dawson",
                "address": "2914 Westheimer Rd, Houston, TX 77098",
                "status": "Clear",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── EDGE 1 ─────────────────────────────────────────────────
        {
            "document_id": "bench_gov_006",
            "doc_type": "government",
            "filename": "expired_license.pdf",
            "difficulty": "edge",
            "text": (
                "CITY AND COUNTY OF DENVER\n"
                "EXCISE AND LICENSES\n"
                "LIQUOR LICENSE\n\n"
                "Document Type: Liquor License\n"
                "Document Number: LQ-DEN-2021-04817\n"
                "Issuing Authority: Denver Excise and Licenses Department\n"
                "Issue Date: 07/01/2021\n"
                "Expiration Date: 06/30/2023\n\n"
                "Full Name: Mile High Taphouse LLC\n"
                "Address: 1540 Larimer St, Denver, CO 80202\n"
                "Status: Expired\n\n"
                "License Type: Hotel and Restaurant\n"
                "Original Issue: 07/01/2019\n\n"
                "NOTICE: This license expired on 06/30/2023.\n"
                "Continued operation without a valid license is a violation.\n"
            ),
            "expected": {
                "document_type": "Liquor License",
                "document_number": "LQ-DEN-2021-04817",
                "issuing_authority": "Denver Excise and Licenses Department",
                "issue_date": "07/01/2021",
                "expiration_date": "06/30/2023",
                "full_name": "Mile High Taphouse LLC",
                "address": "1540 Larimer St, Denver, CO 80202",
                "status": "Expired",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── EDGE 2 ─────────────────────────────────────────────────
        {
            "document_id": "bench_gov_007",
            "doc_type": "government",
            "filename": "multi_jurisdiction.pdf",
            "difficulty": "edge",
            "text": (
                "DISTRICT OF COLUMBIA\n"
                "DEPARTMENT OF CONSUMER AND REGULATORY AFFAIRS\n"
                "GENERAL BUSINESS LICENSE\n\n"
                "Document Type: General Business License\n"
                "Document Number: BBL-302948-2024\n"
                "Issuing Authority: DC Department of Consumer and Regulatory Affairs\n"
                "Issue Date: 02/15/2024\n"
                "Expiration Date: 02/15/2026\n\n"
                "Full Name: Potomac Consulting Group Inc.\n"
                "Address: 1333 H Street NW, Suite 400, Washington, DC 20005\n"
                "Status: Active\n\n"
                "Also registered in:\n"
                "  - Virginia (SCC #08294715) - Active\n"
                "  - Maryland (SDAT #D19384721) - Active\n"
                "  - Delaware (File #7284910) - Active\n\n"
                "Multi-state operations approved.\n"
            ),
            "expected": {
                "document_type": "General Business License",
                "document_number": "BBL-302948-2024",
                "issuing_authority": "DC Department of Consumer and Regulatory Affairs",
                "issue_date": "02/15/2024",
                "expiration_date": "02/15/2026",
                "full_name": "Potomac Consulting Group Inc.",
                "address": "1333 H Street NW, Suite 400, Washington, DC 20005",
                "status": "Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── EDGE 3 ─────────────────────────────────────────────────
        {
            "document_id": "bench_gov_008",
            "doc_type": "government",
            "filename": "amended_filing.pdf",
            "difficulty": "edge",
            "text": (
                "STATE OF CALIFORNIA\n"
                "SECRETARY OF STATE\n"
                "CERTIFICATE OF AMENDMENT\n\n"
                "Document Type: Certificate of Amendment\n"
                "Document Number: AMD-C4928371-2024\n"
                "Issuing Authority: California Secretary of State\n"
                "Issue Date: 08/20/2024\n\n"
                "Full Name: Pacific Coast Ventures LLC (formerly: Bay Area Holdings LLC)\n"
                "Address: 44 Montgomery St, Suite 3200, San Francisco, CA 94104\n"
                "Status: Amended - Active\n\n"
                "Original Filing: LLC-C4928371 dated 03/15/2019\n"
                "Amendment Type: Name Change\n"
                "Previous Name: Bay Area Holdings LLC\n"
                "New Name: Pacific Coast Ventures LLC\n"
                "Effective Date of Amendment: 08/20/2024\n\n"
                "Filing Fee Paid: $30.00\n"
            ),
            "expected": {
                "document_type": "Certificate of Amendment",
                "document_number": "AMD-C4928371-2024",
                "issuing_authority": "California Secretary of State",
                "issue_date": "08/20/2024",
                "expiration_date": None,
                "full_name": "Pacific Coast Ventures LLC (formerly: Bay Area Holdings LLC)",
                "address": "44 Montgomery St, Suite 3200, San Francisco, CA 94104",
                "status": "Amended - Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── ADVERSARIAL 1 ──────────────────────────────────────────
        {
            "document_id": "bench_gov_009",
            "doc_type": "government",
            "filename": "future_issue_date.pdf",
            "difficulty": "adversarial",
            "text": (
                "STATE OF FLORIDA\n"
                "DEPARTMENT OF BUSINESS AND PROFESSIONAL REGULATION\n"
                "CONTRACTOR LICENSE\n\n"
                "Document Type: Contractor License\n"
                "Document Number: CGC-I62O489\n"
                "Issuing Authority: Florida Department of Business and Professional Regulation\n"
                "Issue Date: 12/31/2029\n"
                "Expiration Date: 12/31/2031\n\n"
                "Full Name: Sunshine State Builders Inc.\n"
                "Address: 8901 Collins Ave, Miami Beach, FL 33154\n"
                "Status: Active\n\n"
                "License Category: General Contractor\n"
                "Qualifier: Roberto J. Menendez\n\n"
                "NOTE: Issue date 12/31/2029 is in the future.\n"
            ),
            "expected": {
                "document_type": "Contractor License",
                "document_number": "CGC-I62O489",
                "issuing_authority": "Florida Department of Business and Professional Regulation",
                "issue_date": "12/31/2029",
                "expiration_date": "12/31/2031",
                "full_name": "Sunshine State Builders Inc.",
                "address": "8901 Collins Ave, Miami Beach, FL 33154",
                "status": "Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
        # ── ADVERSARIAL 2 ──────────────────────────────────────────
        {
            "document_id": "bench_gov_010",
            "doc_type": "government",
            "filename": "conflicting_authority.pdf",
            "difficulty": "adversarial",
            "text": (
                "STATE OF NEW YORK\n"
                "DEPARTMENT OF STATE\n"
                "DIVISION OF CORPORATIONS\n\n"
                "Document Type: Certificate of Incorporation\n"
                "Document Number: DOS-ID# 6O4829l-OO1\n"
                "Issuing Authority: New Jersey Division of Revenue\n"
                "Issue Date: 06/01/2024\n\n"
                "Full Name: Empire Logistics Corp.\n"
                "Address: 120 Broadway, Floor 29, New York, NY 10271\n"
                "Status: Active\n\n"
                "Incorporation State: New York\n"
                "Registered Agent: CT Corporation System\n"
                "Authorized Shares: 10,000,000 Common\n\n"
                "NOTE: Header says New York but issuing authority says New Jersey.\n"
            ),
            "expected": {
                "document_type": "Certificate of Incorporation",
                "document_number": "DOS-ID# 6O4829l-OO1",
                "issuing_authority": "New Jersey Division of Revenue",
                "issue_date": "06/01/2024",
                "expiration_date": None,
                "full_name": "Empire Logistics Corp.",
                "address": "120 Broadway, Floor 29, New York, NY 10271",
                "status": "Active",
            },
            "schema_nodes": GOVERNMENT_SCHEMA,
        },
    ]
