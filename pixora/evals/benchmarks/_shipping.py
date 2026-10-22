"""Golden benchmark data for shipping / logistics documents."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import SHIPPING_SCHEMA


def get_shipping() -> list[dict]:
    return [
        # ── TYPICAL 1 ──────────────────────────────────────────────
        {
            "document_id": "bench_ship_001",
            "doc_type": "shipping",
            "filename": "fedex_domestic.pdf",
            "difficulty": "typical",
            "text": (
                "FedEx\n"
                "SHIPPING LABEL / BILL OF LADING\n\n"
                "Tracking Number: 7948 2913 4820 0047\n"
                "Carrier: FedEx Ground\n"
                "Ship Date: 03/18/2024\n"
                "Delivery Date: 03/22/2024\n\n"
                "FROM:\n"
                "Shipper Name: Cascade Electronics Inc.\n"
                "Shipper Address: 2400 NW Thurman St, Portland, OR 97210\n\n"
                "TO:\n"
                "Recipient Name: Mark Sullivan\n"
                "Recipient Address: 789 Congress Ave, Suite 200, Austin, TX 78701\n\n"
                "PACKAGE DETAILS\n"
                "Weight: 4.2 lbs\n"
                "Dimensions: 12 x 10 x 6 in\n"
                "Service: FedEx Ground\n"
                "Shipping Cost: $18.75\n\n"
                "Reference: ORD-2024-08847\n"
            ),
            "expected": {
                "tracking_number": "7948 2913 4820 0047",
                "carrier": "FedEx Ground",
                "ship_date": "03/18/2024",
                "delivery_date": "03/22/2024",
                "shipper_name": "Cascade Electronics Inc.",
                "shipper_address": "2400 NW Thurman St, Portland, OR 97210",
                "recipient_name": "Mark Sullivan",
                "recipient_address": "789 Congress Ave, Suite 200, Austin, TX 78701",
                "weight": "4.2 lbs",
                "shipping_cost": "$18.75",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── TYPICAL 2 ──────────────────────────────────────────────
        {
            "document_id": "bench_ship_002",
            "doc_type": "shipping",
            "filename": "ups_ground.pdf",
            "difficulty": "typical",
            "text": (
                "UPS\n"
                "SHIPMENT RECEIPT\n\n"
                "Tracking Number: 1Z999AA10123456784\n"
                "Carrier: UPS Ground\n"
                "Ship Date: 05/02/2024\n"
                "Delivery Date: 05/07/2024\n\n"
                "Shipper Name: Horizon Office Supplies\n"
                "Shipper Address: 310 Fifth Ave, New York, NY 10001\n\n"
                "Recipient Name: Jennifer Park\n"
                "Recipient Address: 1520 Peachtree St NW, Atlanta, GA 30309\n\n"
                "Weight: 11.8 lbs\n"
                "Declared Value: $245.00\n"
                "Shipping Cost: $24.50\n\n"
                "Service Level: UPS Ground\n"
                "Signature Required: No\n"
            ),
            "expected": {
                "tracking_number": "1Z999AA10123456784",
                "carrier": "UPS Ground",
                "ship_date": "05/02/2024",
                "delivery_date": "05/07/2024",
                "shipper_name": "Horizon Office Supplies",
                "shipper_address": "310 Fifth Ave, New York, NY 10001",
                "recipient_name": "Jennifer Park",
                "recipient_address": "1520 Peachtree St NW, Atlanta, GA 30309",
                "weight": "11.8 lbs",
                "shipping_cost": "$24.50",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── TYPICAL 3 ──────────────────────────────────────────────
        {
            "document_id": "bench_ship_003",
            "doc_type": "shipping",
            "filename": "usps_priority.pdf",
            "difficulty": "typical",
            "text": (
                "UNITED STATES POSTAL SERVICE\n"
                "PRIORITY MAIL LABEL\n\n"
                "Tracking Number: 9405 5036 9930 0451 2847 63\n"
                "Carrier: USPS Priority Mail\n"
                "Ship Date: 02/14/2024\n"
                "Delivery Date: 02/17/2024\n\n"
                "Shipper Name: Amy Chen\n"
                "Shipper Address: 44 Montgomery St, Apt 3B, San Francisco, CA 94104\n\n"
                "Recipient Name: David Chen\n"
                "Recipient Address: 8721 Sunset Blvd, Los Angeles, CA 90069\n\n"
                "Weight: 2.1 lbs\n"
                "Flat Rate Box: Medium\n"
                "Shipping Cost: $15.50\n"
            ),
            "expected": {
                "tracking_number": "9405 5036 9930 0451 2847 63",
                "carrier": "USPS Priority Mail",
                "ship_date": "02/14/2024",
                "delivery_date": "02/17/2024",
                "shipper_name": "Amy Chen",
                "shipper_address": "44 Montgomery St, Apt 3B, San Francisco, CA 94104",
                "recipient_name": "David Chen",
                "recipient_address": "8721 Sunset Blvd, Los Angeles, CA 90069",
                "weight": "2.1 lbs",
                "shipping_cost": "$15.50",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── TYPICAL 4 ──────────────────────────────────────────────
        {
            "document_id": "bench_ship_004",
            "doc_type": "shipping",
            "filename": "dhl_international.pdf",
            "difficulty": "typical",
            "text": (
                "DHL Express\n"
                "INTERNATIONAL WAYBILL\n\n"
                "Tracking Number: 1234567890\n"
                "Carrier: DHL Express Worldwide\n"
                "Ship Date: 04/10/2024\n"
                "Delivery Date: 04/14/2024\n\n"
                "Shipper Name: TechParts GmbH\n"
                "Shipper Address: Industriestrasse 42, 80939 Munich, Germany\n\n"
                "Recipient Name: Karen Williams\n"
                "Recipient Address: 500 Boylston St, Floor 16, Boston, MA 02116\n\n"
                "Weight: 6.5 lbs\n"
                "Contents: Electronic Components\n"
                "Declared Value: $1,200.00\n"
                "Shipping Cost: $87.40\n\n"
                "Customs Reference: DE-EXP-2024-89012\n"
            ),
            "expected": {
                "tracking_number": "1234567890",
                "carrier": "DHL Express Worldwide",
                "ship_date": "04/10/2024",
                "delivery_date": "04/14/2024",
                "shipper_name": "TechParts GmbH",
                "shipper_address": "Industriestrasse 42, 80939 Munich, Germany",
                "recipient_name": "Karen Williams",
                "recipient_address": "500 Boylston St, Floor 16, Boston, MA 02116",
                "weight": "6.5 lbs",
                "shipping_cost": "$87.40",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── TYPICAL 5 ──────────────────────────────────────────────
        {
            "document_id": "bench_ship_005",
            "doc_type": "shipping",
            "filename": "fedex_overnight.pdf",
            "difficulty": "typical",
            "text": (
                "FedEx\n"
                "EXPRESS OVERNIGHT SHIPMENT\n\n"
                "Tracking Number: 4568 7291 0038\n"
                "Carrier: FedEx Priority Overnight\n"
                "Ship Date: 06/20/2024\n"
                "Delivery Date: 06/21/2024\n\n"
                "Shipper Name: Sterling Law Group PLLC\n"
                "Shipper Address: 1900 K Street NW, Suite 750, Washington, DC 20006\n\n"
                "Recipient Name: Honorable Judge Patricia Yamamoto\n"
                "Recipient Address: 401 Courthouse Square, Alexandria, VA 22314\n\n"
                "Weight: 0.8 lbs\n"
                "Contents: Legal Documents\n"
                "Shipping Cost: $42.15\n"
            ),
            "expected": {
                "tracking_number": "4568 7291 0038",
                "carrier": "FedEx Priority Overnight",
                "ship_date": "06/20/2024",
                "delivery_date": "06/21/2024",
                "shipper_name": "Sterling Law Group PLLC",
                "shipper_address": "1900 K Street NW, Suite 750, Washington, DC 20006",
                "recipient_name": "Honorable Judge Patricia Yamamoto",
                "recipient_address": "401 Courthouse Square, Alexandria, VA 22314",
                "weight": "0.8 lbs",
                "shipping_cost": "$42.15",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── EDGE 1 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ship_006",
            "doc_type": "shipping",
            "filename": "multi_package.pdf",
            "difficulty": "edge",
            "text": (
                "UPS\n"
                "MULTI-PACKAGE SHIPMENT\n\n"
                "Tracking Number: 1Z999BB20198765432\n"
                "Carrier: UPS 2nd Day Air\n"
                "Ship Date: 07/08/2024\n"
                "Delivery Date: 07/10/2024\n\n"
                "Shipper Name: Atlas Furniture Co.\n"
                "Shipper Address: 900 Industrial Blvd, High Point, NC 27260\n\n"
                "Recipient Name: Sarah Mitchell\n"
                "Recipient Address: 4200 Wisconsin Ave NW, Apt 612, Washington, DC 20016\n\n"
                "Package 1 of 3: 42.0 lbs - 36x24x18 in\n"
                "Package 2 of 3: 38.5 lbs - 30x20x16 in\n"
                "Package 3 of 3: 15.2 lbs - 24x12x12 in\n\n"
                "Weight: 95.7 lbs\n"
                "Shipping Cost: $142.80\n\n"
                "Signature Required: Yes - Adult Signature\n"
            ),
            "expected": {
                "tracking_number": "1Z999BB20198765432",
                "carrier": "UPS 2nd Day Air",
                "ship_date": "07/08/2024",
                "delivery_date": "07/10/2024",
                "shipper_name": "Atlas Furniture Co.",
                "shipper_address": "900 Industrial Blvd, High Point, NC 27260",
                "recipient_name": "Sarah Mitchell",
                "recipient_address": "4200 Wisconsin Ave NW, Apt 612, Washington, DC 20016",
                "weight": "95.7 lbs",
                "shipping_cost": "$142.80",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── EDGE 2 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ship_007",
            "doc_type": "shipping",
            "filename": "customs_declaration.pdf",
            "difficulty": "edge",
            "text": (
                "USPS\n"
                "CUSTOMS DECLARATION AND DISPATCH NOTE - CP 72\n\n"
                "Tracking Number: CX 123 456 789 US\n"
                "Carrier: USPS Priority Mail International\n"
                "Ship Date: 08/15/2024\n"
                "Delivery Date: 08/25/2024\n\n"
                "Shipper Name: Maria Gonzalez\n"
                "Shipper Address: 1010 Common St, New Orleans, LA 70112\n\n"
                "Recipient Name: Kenji Yamamoto\n"
                "Recipient Address: 3-14-1 Hiyoshi, Kohoku-ku, Yokohama 223-8521, Japan\n\n"
                "CUSTOMS INFORMATION\n"
                "Contents Type: Gift\n"
                "Item 1: Handmade Jewelry Set - Qty 1 - Value $85.00\n"
                "Item 2: Louisiana Hot Sauce Collection - Qty 3 - Value $24.00\n"
                "Total Declared Value: $109.00\n\n"
                "Weight: 3.4 lbs\n"
                "Shipping Cost: $54.75\n\n"
                "HS Tariff Number: 7113.19.5000\n"
            ),
            "expected": {
                "tracking_number": "CX 123 456 789 US",
                "carrier": "USPS Priority Mail International",
                "ship_date": "08/15/2024",
                "delivery_date": "08/25/2024",
                "shipper_name": "Maria Gonzalez",
                "shipper_address": "1010 Common St, New Orleans, LA 70112",
                "recipient_name": "Kenji Yamamoto",
                "recipient_address": "3-14-1 Hiyoshi, Kohoku-ku, Yokohama 223-8521, Japan",
                "weight": "3.4 lbs",
                "shipping_cost": "$54.75",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── EDGE 3 ─────────────────────────────────────────────────
        {
            "document_id": "bench_ship_008",
            "doc_type": "shipping",
            "filename": "return_label.pdf",
            "difficulty": "edge",
            "text": (
                "FedEx\n"
                "RETURN SHIPPING LABEL\n\n"
                "Tracking Number: 6129 0084 5537 1122\n"
                "Carrier: FedEx Ground Return\n"
                "Ship Date: 09/05/2024\n"
                "Delivery Date: 09/12/2024\n\n"
                "Shipper Name: Tyler Brooks\n"
                "Shipper Address: 221 Baker St, Apt 4, Minneapolis, MN 55401\n\n"
                "Recipient Name: Amazon.com Returns Center\n"
                "Recipient Address: 4750 W Mohave St, Phoenix, AZ 85043\n\n"
                "Weight: 1.3 lbs\n"
                "Return Authorization: RMA-2024-0094521\n"
                "Shipping Cost: $0.00\n\n"
                "PREPAID RETURN - No charge to sender\n"
                "Original Order: 114-8293751-2948371\n"
            ),
            "expected": {
                "tracking_number": "6129 0084 5537 1122",
                "carrier": "FedEx Ground Return",
                "ship_date": "09/05/2024",
                "delivery_date": "09/12/2024",
                "shipper_name": "Tyler Brooks",
                "shipper_address": "221 Baker St, Apt 4, Minneapolis, MN 55401",
                "recipient_name": "Amazon.com Returns Center",
                "recipient_address": "4750 W Mohave St, Phoenix, AZ 85043",
                "weight": "1.3 lbs",
                "shipping_cost": "$0.00",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── ADVERSARIAL 1 ──────────────────────────────────────────
        {
            "document_id": "bench_ship_009",
            "doc_type": "shipping",
            "filename": "delivery_before_ship.pdf",
            "difficulty": "adversarial",
            "text": (
                "DHL Express\n"
                "SHIPMENT CONFIRMATION\n\n"
                "Tracking Number: 93612849OO274\n"
                "Carrier: DHL Express\n"
                "Ship Date: 11/20/2024\n"
                "Delivery Date: 11/15/2024\n\n"
                "Shipper Name: QuickParts Ltd.\n"
                "Shipper Address: 128 Harbor Dr, San Diego, CA 92101\n\n"
                "Recipient Name: QuickParts Ltd.\n"
                "Recipient Address: 450 Lexington Ave, New York, NY 10017\n\n"
                "Weight: 8.0 lbs\n"
                "Shipping Cost: $67.90\n\n"
                "NOTE: Delivery date 11/15/2024 precedes ship date 11/20/2024.\n"
            ),
            "expected": {
                "tracking_number": "93612849OO274",
                "carrier": "DHL Express",
                "ship_date": "11/20/2024",
                "delivery_date": "11/15/2024",
                "shipper_name": "QuickParts Ltd.",
                "shipper_address": "128 Harbor Dr, San Diego, CA 92101",
                "recipient_name": "QuickParts Ltd.",
                "recipient_address": "450 Lexington Ave, New York, NY 10017",
                "weight": "8.0 lbs",
                "shipping_cost": "$67.90",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
        # ── ADVERSARIAL 2 ──────────────────────────────────────────
        {
            "document_id": "bench_ship_010",
            "doc_type": "shipping",
            "filename": "conflicting_addresses.pdf",
            "difficulty": "adversarial",
            "text": (
                "UPS\n"
                "SHIPPING CONFIRMATION\n\n"
                "Tracking Number: IZ888CC3O456789O12\n"
                "Carrier: UPS Next Day Air\n"
                "Ship Date: 10/01/2024\n"
                "Delivery Date: 10/02/2024\n\n"
                "Shipper Name: Global Imports LLC\n"
                "Shipper Address: 100 Main St, Chicago, IL 60601\n\n"
                "Recipient Name: Global Imports LLC\n"
                "Recipient Address: 100 Main St, Chicago, IL 60601\n\n"
                "Deliver To: 5500 Wayzata Blvd, Minneapolis, MN 55416\n\n"
                "Weight: 22.4 lbs\n"
                "Shipping Cost: $98.50\n\n"
                "NOTE: Shipper and recipient addresses are identical.\n"
                "Actual delivery address differs from recipient address.\n"
            ),
            "expected": {
                "tracking_number": "IZ888CC3O456789O12",
                "carrier": "UPS Next Day Air",
                "ship_date": "10/01/2024",
                "delivery_date": "10/02/2024",
                "shipper_name": "Global Imports LLC",
                "shipper_address": "100 Main St, Chicago, IL 60601",
                "recipient_name": "Global Imports LLC",
                "recipient_address": "100 Main St, Chicago, IL 60601",
                "weight": "22.4 lbs",
                "shipping_cost": "$98.50",
            },
            "schema_nodes": SHIPPING_SCHEMA,
        },
    ]
