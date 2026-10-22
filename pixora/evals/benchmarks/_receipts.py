"""Golden benchmark data — Receipts (10 documents: 5 typical, 3 edge, 2 adversarial)."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import RECEIPT_SCHEMA


def get_receipts() -> list[dict]:
    """Return 10 receipt benchmark documents with ground-truth extractions."""
    return [
        # ── TYPICAL 1 — Grocery ───────────────────────────────────
        {
            "document_id": "bench_rcpt_001",
            "doc_type": "receipt",
            "filename": "whole_foods_receipt.png",
            "difficulty": "typical",
            "text": (
                "WHOLE FOODS MARKET\n"
                "Store #10421 — Austin, TX\n\n"
                "Store Name: WHOLE FOODS MARKET\n"
                "Store Address: 525 N Lamar Blvd, Austin, TX 78703\n"
                "Date: 03/10/2024\n"
                "Time: 14:32\n\n"
                "Organic Bananas          $1.49\n"
                "Avocado (2)              $3.98\n"
                "Sourdough Bread          $5.99\n"
                "Almond Milk 64oz         $4.49\n"
                "Wild Salmon Fillet       $14.99\n"
                "Mixed Greens Salad       $6.49\n"
                "Sparkling Water 12pk     $5.99\n\n"
                "Subtotal: $43.42\n"
                "Tax: $3.58\n"
                "Total: $47.00\n\n"
                "Payment Method: VISA\n"
                "Card Last Four: 4821\n"
                "Auth: 892341\n\n"
                "THANK YOU FOR SHOPPING WITH US\n"
            ),
            "expected": {
                "store_name": "WHOLE FOODS MARKET",
                "store_address": "525 N Lamar Blvd, Austin, TX 78703",
                "date": "03/10/2024",
                "time": "14:32",
                "subtotal": "$43.42",
                "tax": "$3.58",
                "total": "$47.00",
                "payment_method": "VISA",
                "card_last_four": "4821",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── TYPICAL 2 — Restaurant ────────────────────────────────
        {
            "document_id": "bench_rcpt_002",
            "doc_type": "receipt",
            "filename": "bistro_verde_receipt.jpg",
            "difficulty": "typical",
            "text": (
                "Bistro Verde\n"
                "147 Main Street, Greenwich, CT 06830\n\n"
                "Store Name: Bistro Verde\n"
                "Store Address: 147 Main Street, Greenwich, CT 06830\n"
                "Date: 05/18/2024\n"
                "Time: 19:47\n\n"
                "Server: Anthony\n"
                "Table: 12\n\n"
                "1 Burrata Appetizer        $16.00\n"
                "1 Grilled Branzino         $34.00\n"
                "1 Truffle Risotto          $28.00\n"
                "2 Glass Pinot Noir         $30.00\n"
                "1 Tiramisu                 $14.00\n\n"
                "Subtotal: $122.00\n"
                "Tax: $7.75\n"
                "Total: $129.75\n\n"
                "Payment Method: AMEX\n"
                "Card Last Four: 1003\n"
                "Tip: ________\n"
                "Total with Tip: ________\n"
            ),
            "expected": {
                "store_name": "Bistro Verde",
                "store_address": "147 Main Street, Greenwich, CT 06830",
                "date": "05/18/2024",
                "time": "19:47",
                "subtotal": "$122.00",
                "tax": "$7.75",
                "total": "$129.75",
                "payment_method": "AMEX",
                "card_last_four": "1003",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── TYPICAL 3 — Gas station ───────────────────────────────
        {
            "document_id": "bench_rcpt_003",
            "doc_type": "receipt",
            "filename": "shell_gas_receipt.png",
            "difficulty": "typical",
            "text": (
                "SHELL\n"
                "Station #4492\n"
                "8801 Westheimer Rd, Houston, TX 77063\n\n"
                "Store Name: SHELL\n"
                "Store Address: 8801 Westheimer Rd, Houston, TX 77063\n"
                "Date: 08/22/2024\n"
                "Time: 07:14\n\n"
                "Pump #6\n"
                "Unleaded Plus 89\n"
                "14.832 GAL @ $3.299/GAL\n\n"
                "Subtotal: $48.91\n"
                "Tax: $0.00\n"
                "Total: $48.91\n\n"
                "Payment Method: Debit\n"
                "Card Last Four: 7733\n"
            ),
            "expected": {
                "store_name": "SHELL",
                "store_address": "8801 Westheimer Rd, Houston, TX 77063",
                "date": "08/22/2024",
                "time": "07:14",
                "subtotal": "$48.91",
                "tax": "$0.00",
                "total": "$48.91",
                "payment_method": "Debit",
                "card_last_four": "7733",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── TYPICAL 4 — Pharmacy ──────────────────────────────────
        {
            "document_id": "bench_rcpt_004",
            "doc_type": "receipt",
            "filename": "cvs_pharmacy_receipt.png",
            "difficulty": "typical",
            "text": (
                "CVS/pharmacy\n"
                "Store #3318 — Arlington, VA\n\n"
                "Store Name: CVS/pharmacy\n"
                "Store Address: 1201 S Hayes St, Arlington, VA 22202\n"
                "Date: 01/09/2024\n"
                "Time: 10:05\n\n"
                "Rx# 5829174 Lisinopril 10mg  $12.00\n"
                "Rx# 5829175 Metformin 500mg  $8.00\n"
                "Tylenol Extra Strength 100ct  $9.49\n"
                "Band-Aid Flex Fabric 30ct     $4.79\n\n"
                "Subtotal: $34.28\n"
                "Tax: $0.86\n"
                "Total: $35.14\n\n"
                "Payment Method: Mastercard\n"
                "Card Last Four: 5590\n"
            ),
            "expected": {
                "store_name": "CVS/pharmacy",
                "store_address": "1201 S Hayes St, Arlington, VA 22202",
                "date": "01/09/2024",
                "time": "10:05",
                "subtotal": "$34.28",
                "tax": "$0.86",
                "total": "$35.14",
                "payment_method": "Mastercard",
                "card_last_four": "5590",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── TYPICAL 5 — Hardware store ────────────────────────────
        {
            "document_id": "bench_rcpt_005",
            "doc_type": "receipt",
            "filename": "home_depot_receipt.png",
            "difficulty": "typical",
            "text": (
                "The Home Depot\n"
                "Store #0554\n"
                "2400 South Loop W, Houston, TX 77054\n\n"
                "Store Name: The Home Depot\n"
                "Store Address: 2400 South Loop W, Houston, TX 77054\n"
                "Date: 04/13/2024\n"
                "Time: 11:22\n\n"
                "DeWalt 20V Drill Kit         $179.00\n"
                "Gorilla Wood Glue 18oz       $8.97\n"
                "3/4in Plywood 4x8 (qty 3)   $134.97\n"
                "Minwax Stain Dark Walnut     $12.98\n"
                "80-Grit Sandpaper 50pk       $14.97\n\n"
                "Subtotal: $350.89\n"
                "Tax: $28.95\n"
                "Total: $379.84\n\n"
                "Payment Method: VISA\n"
                "Card Last Four: 2019\n"
            ),
            "expected": {
                "store_name": "The Home Depot",
                "store_address": "2400 South Loop W, Houston, TX 77054",
                "date": "04/13/2024",
                "time": "11:22",
                "subtotal": "$350.89",
                "tax": "$28.95",
                "total": "$379.84",
                "payment_method": "VISA",
                "card_last_four": "2019",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── EDGE 1 — Tip line filled, restaurant ──────────────────
        {
            "document_id": "bench_rcpt_006",
            "doc_type": "receipt",
            "filename": "sakura_sushi_tip_receipt.jpg",
            "difficulty": "edge",
            "text": (
                "SAKURA SUSHI & RAMEN\n"
                "4420 University Ave, San Diego, CA 92105\n\n"
                "Store Name: SAKURA SUSHI & RAMEN\n"
                "Store Address: 4420 University Ave, San Diego, CA 92105\n"
                "Date: 12.06.2024\n"
                "Time: 20:18\n\n"
                "Spicy Tuna Roll (2)    $24.00\n"
                "Tonkotsu Ramen         $17.00\n"
                "Edamame                $6.00\n"
                "Sake Carafe            $15.00\n"
                "Mochi Ice Cream        $8.00\n\n"
                "Subtotal: $70.00\n"
                "Tax: $5.43\n"
                "Total: $75.43\n\n"
                "Tip: $15.00\n"
                "Grand Total: $90.43\n\n"
                "Payment Method: Apple Pay\n"
                "Card Last Four: 9281\n"
            ),
            "expected": {
                "store_name": "SAKURA SUSHI & RAMEN",
                "store_address": "4420 University Ave, San Diego, CA 92105",
                "date": "12.06.2024",
                "time": "20:18",
                "subtotal": "$70.00",
                "tax": "$5.43",
                "total": "$75.43",
                "payment_method": "Apple Pay",
                "card_last_four": "9281",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── EDGE 2 — Return/refund receipt ────────────────────────
        {
            "document_id": "bench_rcpt_007",
            "doc_type": "receipt",
            "filename": "target_return_receipt.png",
            "difficulty": "edge",
            "text": (
                "TARGET\n"
                "Store T-1843 Minneapolis, MN\n\n"
                "*** RETURN / REFUND ***\n\n"
                "Store Name: TARGET\n"
                "Store Address: 900 Nicollet Mall, Minneapolis, MN 55403\n"
                "Date: 07/30/2024\n"
                "Time: 15:55\n\n"
                "RETURN: Dyson V8 Vacuum      -$349.99\n"
                "RETURN: Vacuum Filter 2pk    -$24.99\n\n"
                "Subtotal: -$374.98\n"
                "Tax: -$29.06\n"
                "Total: -$404.04\n\n"
                "REFUND ISSUED\n"
                "Payment Method: Original VISA\n"
                "Card Last Four: 6614\n"
                "Refund may take 3-5 business days.\n"
            ),
            "expected": {
                "store_name": "TARGET",
                "store_address": "900 Nicollet Mall, Minneapolis, MN 55403",
                "date": "07/30/2024",
                "time": "15:55",
                "subtotal": "-$374.98",
                "tax": "-$29.06",
                "total": "-$404.04",
                "payment_method": "Original VISA",
                "card_last_four": "6614",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── EDGE 3 — Split payment, long date format ──────────────
        {
            "document_id": "bench_rcpt_008",
            "doc_type": "receipt",
            "filename": "costco_split_receipt.png",
            "difficulty": "edge",
            "text": (
                "COSTCO WHOLESALE\n"
                "Warehouse #482\n\n"
                "Store Name: COSTCO WHOLESALE\n"
                "Store Address: 4849 Alabama Ave SE, Washington, DC 20019\n"
                "Date: September 3, 2024\n"
                "Time: 13:09\n\n"
                "KS Olive Oil 2L          $14.99\n"
                "Kirkland Salmon 3lb      $29.99\n"
                "KS Paper Towels 15pk     $22.49\n"
                "Samsung 65in TV          $549.99\n"
                "KS Batteries AA 72pk     $18.49\n\n"
                "Subtotal: $635.95\n"
                "Tax: $38.16\n"
                "Total: $674.11\n\n"
                "Payment Method: Split\n"
                "  Costco Cash Card  $200.00\n"
                "  VISA ****3847     $474.11\n\n"
                "Card Last Four: 3847\n"
                "Member# 110938472855\n"
            ),
            "expected": {
                "store_name": "COSTCO WHOLESALE",
                "store_address": "4849 Alabama Ave SE, Washington, DC 20019",
                "date": "September 3, 2024",
                "time": "13:09",
                "subtotal": "$635.95",
                "tax": "$38.16",
                "total": "$674.11",
                "payment_method": "Split",
                "card_last_four": "3847",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── ADVERSARIAL 1 — OCR garble, trap totals ───────────────
        {
            "document_id": "bench_rcpt_009",
            "doc_type": "receipt",
            "filename": "faded_receipt_scan.jpg",
            "difficulty": "adversarial",
            "text": (
                "TRADER J0E'S\n"
                "Store #728\n\n"
                "Store Name: TRADER J0E'S\n"
                "Store Address: 14O1 25th St NW, Washington, DC 2OOO7\n"
                "Date: O6/11/2O24\n"
                "Time: 16:4O\n\n"
                "Org Eggs Dz              $4.99\n"
                "TJ Peanut Butter         $2.99\n"
                "Everything Bagels        $3.49\n"
                "Mandarin 0ranges 3lb     $4.49\n"
                "Chkn Tikka Masala        $3.99\n\n"
                "Coupons Saved            $4.50\n\n"
                "Subtotal: $15.45\n"
                "Tax: $0.93\n"
                "Total: $16.38\n\n"
                "Payment Method: Cash\n"
                "  Tendered:  $20.00\n"
                "  Change:    $3.62\n"
            ),
            "expected": {
                "store_name": "TRADER J0E'S",
                "store_address": "14O1 25th St NW, Washington, DC 2OOO7",
                "date": "O6/11/2O24",
                "time": "16:4O",
                "subtotal": "$15.45",
                "tax": "$0.93",
                "total": "$16.38",
                "payment_method": "Cash",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
        # ── ADVERSARIAL 2 — Near-miss labels, missing fields ──────
        {
            "document_id": "bench_rcpt_010",
            "doc_type": "receipt",
            "filename": "handwritten_receipt_scan.jpg",
            "difficulty": "adversarial",
            "text": (
                "JOE'S AUTO REPAIR\n"
                "Est. 1987\n\n"
                "Store Name: JOE'S AUTO REPAIR\n"
                "Store Address: 3322 W Cermak Rd, Chicago, IL 60623\n"
                "Date: 10/02/2024\n\n"
                "Oil Change (Synthetic 5W-30) ... $74.99\n"
                "Tire Rotation .................. $29.99\n"
                "Cabin Air Filter ............... $22.00\n"
                "Shop supplies & disposal fee ... $6.50\n\n"
                "Est. Total: $185.00  <-- estimate, not actual\n\n"
                "Subtotal: $133.48\n"
                "Tax: $10.28\n"
                "Total: $143.76\n\n"
                "Payment Method: Discover\n"
                "Card Last Four: 8001\n"
                "Customer copy — thank you!\n"
            ),
            "expected": {
                "store_name": "JOE'S AUTO REPAIR",
                "store_address": "3322 W Cermak Rd, Chicago, IL 60623",
                "date": "10/02/2024",
                "subtotal": "$133.48",
                "tax": "$10.28",
                "total": "$143.76",
                "payment_method": "Discover",
                "card_last_four": "8001",
            },
            "schema_nodes": RECEIPT_SCHEMA,
        },
    ]
