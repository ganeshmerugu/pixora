"""Golden benchmark data for bank statement documents."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import BANK_STATEMENT_SCHEMA


def get_bank_statements() -> list[dict]:
    return [
        # ── TYPICAL 1 ──────────────────────────────────────────────
        {
            "document_id": "bench_bank_001",
            "doc_type": "bank_statement",
            "filename": "chase_checking_mar2024.pdf",
            "difficulty": "typical",
            "text": (
                "CHASE\n"
                "CHECKING ACCOUNT STATEMENT\n\n"
                "Bank Name: JPMorgan Chase Bank, N.A.\n"
                "Account Holder: Jennifer L. Martinez\n"
                "Account Number: ****4738\n"
                "Statement Period: March 1, 2024 - March 31, 2024\n\n"
                "ACCOUNT SUMMARY\n"
                "Opening Balance: $5,432.18\n"
                "Total Deposits: $8,750.00\n"
                "Total Withdrawals: $7,215.63\n"
                "Closing Balance: $6,966.55\n\n"
                "DEPOSITS AND ADDITIONS\n"
                "03/01 Direct Deposit - Employer        $4,375.00\n"
                "03/15 Direct Deposit - Employer        $4,375.00\n\n"
                "WITHDRAWALS AND DEBITS\n"
                "03/02 Rent Payment - Zelle             $1,850.00\n"
                "03/05 Whole Foods Market               $127.43\n"
                "03/08 Con Edison                        $142.87\n"
                "03/10 Transfer to Savings               $500.00\n"
                "03/15 Amazon.com                        $89.99\n"
                "03/18 AT&T Wireless                     $95.00\n"
                "03/22 Trader Joe's                      $68.42\n"
                "03/25 Netflix                           $15.99\n"
                "03/28 CVS Pharmacy                      $34.56\n"
                "03/30 Gas Station Shell                 $52.37\n"
                "03/31 Monthly Service Fee                $0.00\n"
            ),
            "expected": {
                "bank_name": "JPMorgan Chase Bank, N.A.",
                "account_holder": "Jennifer L. Martinez",
                "account_number": "****4738",
                "statement_period": "March 1, 2024 - March 31, 2024",
                "opening_balance": "$5,432.18",
                "closing_balance": "$6,966.55",
                "total_deposits": "$8,750.00",
                "total_withdrawals": "$7,215.63",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── TYPICAL 2 ──────────────────────────────────────────────
        {
            "document_id": "bench_bank_002",
            "doc_type": "bank_statement",
            "filename": "wellsfargo_savings.pdf",
            "difficulty": "typical",
            "text": (
                "Wells Fargo Bank\n"
                "Way2Save Savings Statement\n\n"
                "Bank Name: Wells Fargo Bank, N.A.\n"
                "Account Holder: Michael R. Thompson\n"
                "Account Number: ****9201\n"
                "Statement Period: April 1, 2024 - April 30, 2024\n\n"
                "Opening Balance: $22,150.00\n"
                "Total Deposits: $1,500.00\n"
                "Total Withdrawals: $0.00\n"
                "Interest Earned: $18.42\n"
                "Closing Balance: $23,668.42\n\n"
                "TRANSACTIONS\n"
                "04/01 Transfer from Checking           $500.00\n"
                "04/15 Transfer from Checking           $500.00\n"
                "04/25 Transfer from Checking           $500.00\n"
                "04/30 Interest Payment                  $18.42\n"
            ),
            "expected": {
                "bank_name": "Wells Fargo Bank, N.A.",
                "account_holder": "Michael R. Thompson",
                "account_number": "****9201",
                "statement_period": "April 1, 2024 - April 30, 2024",
                "opening_balance": "$22,150.00",
                "closing_balance": "$23,668.42",
                "total_deposits": "$1,500.00",
                "total_withdrawals": "$0.00",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── TYPICAL 3 ──────────────────────────────────────────────
        {
            "document_id": "bench_bank_003",
            "doc_type": "bank_statement",
            "filename": "bofa_checking.pdf",
            "difficulty": "typical",
            "text": (
                "Bank of America\n"
                "Advantage Checking\n\n"
                "Bank Name: Bank of America, N.A.\n"
                "Account Holder: Priya N. Desai\n"
                "Account Number: ****6154\n"
                "Statement Period: February 1, 2024 - February 29, 2024\n\n"
                "Opening Balance: $3,891.22\n"
                "Total Deposits: $6,200.00\n"
                "Total Withdrawals: $5,848.17\n"
                "Closing Balance: $4,243.05\n\n"
                "DEPOSITS\n"
                "02/02 ACH Deposit - Payroll            $3,100.00\n"
                "02/16 ACH Deposit - Payroll            $3,100.00\n\n"
                "PAYMENTS AND WITHDRAWALS\n"
                "02/01 Mortgage Payment                 $2,150.00\n"
                "02/05 Kroger                            $112.34\n"
                "02/08 Spectrum Internet                  $79.99\n"
                "02/12 Target                             $65.43\n"
                "02/14 Uber Eats                          $32.18\n"
                "02/20 State Farm Insurance              $148.00\n"
                "02/25 Costco                            $245.67\n"
                "02/28 Monthly Maintenance Fee            $12.00\n"
            ),
            "expected": {
                "bank_name": "Bank of America, N.A.",
                "account_holder": "Priya N. Desai",
                "account_number": "****6154",
                "statement_period": "February 1, 2024 - February 29, 2024",
                "opening_balance": "$3,891.22",
                "closing_balance": "$4,243.05",
                "total_deposits": "$6,200.00",
                "total_withdrawals": "$5,848.17",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── TYPICAL 4 ──────────────────────────────────────────────
        {
            "document_id": "bench_bank_004",
            "doc_type": "bank_statement",
            "filename": "citi_checking.pdf",
            "difficulty": "typical",
            "text": (
                "Citibank\n"
                "Regular Checking Account\n\n"
                "Bank Name: Citibank, N.A.\n"
                "Account Holder: David W. Chen\n"
                "Account Number: ****3387\n"
                "Statement Period: June 1, 2024 - June 30, 2024\n\n"
                "Opening Balance: $12,340.56\n"
                "Total Deposits: $9,500.00\n"
                "Total Withdrawals: $11,287.92\n"
                "Closing Balance: $10,552.64\n\n"
                "CREDITS\n"
                "06/01 Wire Transfer - Client Payment   $5,000.00\n"
                "06/15 ACH Deposit - Consulting Fee     $4,500.00\n\n"
                "DEBITS\n"
                "06/03 Rent - 450 Lexington Ave         $3,200.00\n"
                "06/05 Con Edison Electric                $178.43\n"
                "06/10 Verizon Wireless                   $125.00\n"
                "06/12 Whole Foods                        $198.76\n"
                "06/18 IRS Estimated Tax Q2             $5,000.00\n"
                "06/22 Blue Apron                         $79.92\n"
                "06/25 Uber                               $42.50\n"
                "06/28 Apple iCloud                       $12.99\n"
            ),
            "expected": {
                "bank_name": "Citibank, N.A.",
                "account_holder": "David W. Chen",
                "account_number": "****3387",
                "statement_period": "June 1, 2024 - June 30, 2024",
                "opening_balance": "$12,340.56",
                "closing_balance": "$10,552.64",
                "total_deposits": "$9,500.00",
                "total_withdrawals": "$11,287.92",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── TYPICAL 5 ──────────────────────────────────────────────
        {
            "document_id": "bench_bank_005",
            "doc_type": "bank_statement",
            "filename": "pnc_checking.pdf",
            "difficulty": "typical",
            "text": (
                "PNC Bank\n"
                "Virtual Wallet Spend Account\n\n"
                "Bank Name: PNC Bank, National Association\n"
                "Account Holder: Amanda K. Wilson\n"
                "Account Number: ****8472\n"
                "Statement Period: May 1, 2024 - May 31, 2024\n\n"
                "Opening Balance: $1,876.33\n"
                "Total Deposits: $4,850.00\n"
                "Total Withdrawals: $4,512.90\n"
                "Closing Balance: $2,213.43\n\n"
                "DEPOSITS\n"
                "05/03 Direct Deposit - Employer        $2,425.00\n"
                "05/17 Direct Deposit - Employer        $2,425.00\n\n"
                "WITHDRAWALS\n"
                "05/01 Apartment Rent                   $1,350.00\n"
                "05/04 Giant Eagle Grocery               $87.65\n"
                "05/07 Duquesne Light Co                  $94.33\n"
                "05/10 T-Mobile                           $75.00\n"
                "05/14 Pittsburgh Parking Auth             $45.00\n"
                "05/20 HomeGoods                          $62.18\n"
                "05/23 Starbucks                          $28.74\n"
                "05/27 Planet Fitness                     $24.99\n"
                "05/31 Service Charge                      $0.00\n"
            ),
            "expected": {
                "bank_name": "PNC Bank, National Association",
                "account_holder": "Amanda K. Wilson",
                "account_number": "****8472",
                "statement_period": "May 1, 2024 - May 31, 2024",
                "opening_balance": "$1,876.33",
                "closing_balance": "$2,213.43",
                "total_deposits": "$4,850.00",
                "total_withdrawals": "$4,512.90",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── EDGE 1 ─────────────────────────────────────────────────
        {
            "document_id": "bench_bank_006",
            "doc_type": "bank_statement",
            "filename": "zero_balance_month.pdf",
            "difficulty": "edge",
            "text": (
                "US Bank\n"
                "Standard Checking\n\n"
                "Bank Name: U.S. Bank National Association\n"
                "Account Holder: Kevin J. Brooks\n"
                "Account Number: ****5590\n"
                "Statement Period: January 1, 2024 - January 31, 2024\n\n"
                "Opening Balance: $0.00\n"
                "Total Deposits: $0.00\n"
                "Total Withdrawals: $0.00\n"
                "Closing Balance: $0.00\n\n"
                "NO TRANSACTIONS THIS PERIOD\n\n"
                "Notice: This account has been inactive for 90 days.\n"
                "Please contact us to avoid dormancy fees.\n"
            ),
            "expected": {
                "bank_name": "U.S. Bank National Association",
                "account_holder": "Kevin J. Brooks",
                "account_number": "****5590",
                "statement_period": "January 1, 2024 - January 31, 2024",
                "opening_balance": "$0.00",
                "closing_balance": "$0.00",
                "total_deposits": "$0.00",
                "total_withdrawals": "$0.00",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── EDGE 2 ─────────────────────────────────────────────────
        {
            "document_id": "bench_bank_007",
            "doc_type": "bank_statement",
            "filename": "overdraft_negative.pdf",
            "difficulty": "edge",
            "text": (
                "Regions Bank\n"
                "LifeGreen Checking\n\n"
                "Bank Name: Regions Bank\n"
                "Account Holder: Carlos Mendoza\n"
                "Account Number: ****2716\n"
                "Statement Period: July 1, 2024 - July 31, 2024\n\n"
                "Opening Balance: $142.30\n"
                "Total Deposits: $2,100.00\n"
                "Total Withdrawals: $2,347.30\n"
                "Overdraft Fees: $72.00\n"
                "Closing Balance: -$177.00\n\n"
                "DEPOSITS\n"
                "07/15 Direct Deposit - Employer        $2,100.00\n\n"
                "WITHDRAWALS\n"
                "07/01 Auto Loan Payment                 $485.00\n"
                "07/03 Walmart                           $132.47\n"
                "07/05 Rent Payment                    $1,200.00\n"
                "07/08 Overdraft Fee                      $36.00\n"
                "07/10 Sprint Wireless                    $89.00\n"
                "07/12 Overdraft Fee                      $36.00\n"
                "07/20 Shell Gas                          $45.83\n"
                "07/25 Electric Coop                     $123.00\n"
            ),
            "expected": {
                "bank_name": "Regions Bank",
                "account_holder": "Carlos Mendoza",
                "account_number": "****2716",
                "statement_period": "July 1, 2024 - July 31, 2024",
                "opening_balance": "$142.30",
                "closing_balance": "-$177.00",
                "total_deposits": "$2,100.00",
                "total_withdrawals": "$2,347.30",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── EDGE 3 ─────────────────────────────────────────────────
        {
            "document_id": "bench_bank_008",
            "doc_type": "bank_statement",
            "filename": "foreign_currency.pdf",
            "difficulty": "edge",
            "text": (
                "HSBC\n"
                "Premier Checking - Foreign Currency\n\n"
                "Bank Name: HSBC Bank USA, N.A.\n"
                "Account Holder: Yuki Nakamura\n"
                "Account Number: ****7843\n"
                "Statement Period: August 1, 2024 - August 31, 2024\n"
                "Currency: EUR\n\n"
                "Opening Balance: €14,200.00\n"
                "Total Deposits: €5,000.00\n"
                "Total Withdrawals: €3,150.75\n"
                "Closing Balance: €16,049.25\n\n"
                "TRANSACTIONS\n"
                "08/05 Wire from JPY account (converted) €5,000.00\n"
                "08/10 Hotel Marais Paris               €890.00\n"
                "08/15 SNCF Rail                        €124.50\n"
                "08/18 Carrefour                         €87.25\n"
                "08/22 Lufthansa                       €1,450.00\n"
                "08/28 Monthly Fee                       €15.00\n"
            ),
            "expected": {
                "bank_name": "HSBC Bank USA, N.A.",
                "account_holder": "Yuki Nakamura",
                "account_number": "****7843",
                "statement_period": "August 1, 2024 - August 31, 2024",
                "opening_balance": "€14,200.00",
                "closing_balance": "€16,049.25",
                "total_deposits": "€5,000.00",
                "total_withdrawals": "€3,150.75",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── ADVERSARIAL 1 ──────────────────────────────────────────
        {
            "document_id": "bench_bank_009",
            "doc_type": "bank_statement",
            "filename": "garbled_account.pdf",
            "difficulty": "adversarial",
            "text": (
                "TD Bank\n"
                "Convenience Checking\n\n"
                "Bank Name: TD Bank, N.A.\n"
                "Account Holder: Steven P. O'Brien\n"
                "Account Number: ****4Z8l\n"
                "Statement Period: September 1, 2024 - September 30, 2024\n\n"
                "Opening Balance: $3,200.00\n"
                "Total Deposits: $5,000.00\n"
                "Total Withdrawals: $4,100.00\n"
                "Closing Balance: $4,100.00\n\n"
                "DEPOSITS\n"
                "09/01 ACH Payroll                      $2,500.00\n"
                "09/15 ACH Payroll                      $2,500.00\n\n"
                "WITHDRAWALS\n"
                "09/03 Rent                             $1,800.00\n"
                "09/10 Eversource Energy                 $145.00\n"
                "09/18 Stop & Shop                       $112.50\n"
                "09/22 Comcast                            $89.99\n"
                "09/28 Various Debit Card                $152.51\n"
            ),
            "expected": {
                "bank_name": "TD Bank, N.A.",
                "account_holder": "Steven P. O'Brien",
                "account_number": "****4Z8l",
                "statement_period": "September 1, 2024 - September 30, 2024",
                "opening_balance": "$3,200.00",
                "closing_balance": "$4,100.00",
                "total_deposits": "$5,000.00",
                "total_withdrawals": "$4,100.00",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
        # ── ADVERSARIAL 2 ──────────────────────────────────────────
        {
            "document_id": "bench_bank_010",
            "doc_type": "bank_statement",
            "filename": "ocr_zeros.pdf",
            "difficulty": "adversarial",
            "text": (
                "Fifth Third Bank\n"
                "Essential Checking\n\n"
                "Bank Name: Fifth Third Bank\n"
                "Account Holder: Laura M. Henderson\n"
                "Account Number: ****73O2\n"
                "Statement Period: October 1, 2024 - October 31, 2024\n\n"
                "Opening Balance: $4,5OO.OO\n"
                "Total Deposits: $3,OOO.OO\n"
                "Total Withdrawals: $2,8OO.OO\n"
                "Closing Balance: $4,7OO.OO\n\n"
                "DEPOSITS\n"
                "1O/O1 Direct Deposit                   $1,5OO.OO\n"
                "1O/15 Direct Deposit                   $1,5OO.OO\n\n"
                "WITHDRAWALS\n"
                "1O/O3 Mortgage                         $1,6OO.OO\n"
                "1O/1O Meijer Grocery                     $15O.OO\n"
                "1O/2O Duke Energy                        $12O.OO\n"
                "1O/25 Various                            $93O.OO\n"
            ),
            "expected": {
                "bank_name": "Fifth Third Bank",
                "account_holder": "Laura M. Henderson",
                "account_number": "****73O2",
                "statement_period": "October 1, 2024 - October 31, 2024",
                "opening_balance": "$4,5OO.OO",
                "closing_balance": "$4,7OO.OO",
                "total_deposits": "$3,OOO.OO",
                "total_withdrawals": "$2,8OO.OO",
            },
            "schema_nodes": BANK_STATEMENT_SCHEMA,
        },
    ]
