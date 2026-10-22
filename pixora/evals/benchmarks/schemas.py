"""Shared extraction schema definitions per document type.
Each schema_nodes list defines the fields the extractor should find."""
from __future__ import annotations

INVOICE_SCHEMA = [
    {"name": "vendor_name", "field_type": "STRING", "required": True},
    {"name": "vendor_address", "field_type": "STRING"},
    {"name": "invoice_number", "field_type": "STRING", "required": True},
    {"name": "invoice_date", "field_type": "DATE", "required": True},
    {"name": "due_date", "field_type": "DATE"},
    {"name": "po_number", "field_type": "STRING"},
    {"name": "bill_to_name", "field_type": "STRING"},
    {"name": "bill_to_address", "field_type": "STRING"},
    {"name": "subtotal", "field_type": "CURRENCY"},
    {"name": "tax", "field_type": "CURRENCY"},
    {"name": "total_due", "field_type": "CURRENCY", "required": True},
    {"name": "payment_terms", "field_type": "STRING"},
]

RECEIPT_SCHEMA = [
    {"name": "store_name", "field_type": "STRING", "required": True},
    {"name": "store_address", "field_type": "STRING"},
    {"name": "date", "field_type": "DATE", "required": True},
    {"name": "time", "field_type": "STRING"},
    {"name": "subtotal", "field_type": "CURRENCY"},
    {"name": "tax", "field_type": "CURRENCY"},
    {"name": "total", "field_type": "CURRENCY", "required": True},
    {"name": "payment_method", "field_type": "STRING"},
    {"name": "card_last_four", "field_type": "STRING"},
]

CONTRACT_SCHEMA = [
    {"name": "agreement_type", "field_type": "STRING", "required": True},
    {"name": "effective_date", "field_type": "DATE", "required": True},
    {"name": "provider_name", "field_type": "STRING", "required": True},
    {"name": "provider_address", "field_type": "STRING"},
    {"name": "client_name", "field_type": "STRING", "required": True},
    {"name": "client_address", "field_type": "STRING"},
    {"name": "initial_term", "field_type": "STRING"},
    {"name": "annual_fee", "field_type": "CURRENCY"},
    {"name": "governing_law", "field_type": "STRING"},
    {"name": "liability_cap", "field_type": "CURRENCY"},
]

MEDICAL_SCHEMA = [
    {"name": "patient_name", "field_type": "STRING", "required": True},
    {"name": "date_of_birth", "field_type": "DATE", "required": True},
    {"name": "mrn", "field_type": "STRING", "required": True},
    {"name": "ordering_physician", "field_type": "STRING"},
    {"name": "collection_date", "field_type": "DATE"},
    {"name": "report_date", "field_type": "DATE"},
    {"name": "diagnosis", "field_type": "STRING"},
    {"name": "glucose_fasting", "field_type": "NUMBER"},
    {"name": "hemoglobin", "field_type": "NUMBER"},
]

FORM_SCHEMA = [
    {"name": "form_type", "field_type": "STRING", "required": True},
    {"name": "name", "field_type": "STRING", "required": True},
    {"name": "business_name", "field_type": "STRING"},
    {"name": "tax_classification", "field_type": "STRING"},
    {"name": "address", "field_type": "STRING"},
    {"name": "city_state_zip", "field_type": "STRING"},
    {"name": "ein", "field_type": "STRING", "required": True, "validation_rules": [{"type": "regex", "params": {"pattern": r"^\d{2}-\d{7}$"}, "message": "EIN must be XX-XXXXXXX"}]},
    {"name": "signature_date", "field_type": "DATE"},
]

SCIENTIFIC_SCHEMA = [
    {"name": "title", "field_type": "STRING", "required": True},
    {"name": "authors", "field_type": "STRING", "required": True},
    {"name": "journal", "field_type": "STRING"},
    {"name": "publication_date", "field_type": "DATE"},
    {"name": "doi", "field_type": "STRING"},
    {"name": "abstract", "field_type": "STRING"},
    {"name": "keywords", "field_type": "STRING"},
    {"name": "conclusion", "field_type": "STRING"},
]

BANK_STATEMENT_SCHEMA = [
    {"name": "bank_name", "field_type": "STRING", "required": True},
    {"name": "account_holder", "field_type": "STRING", "required": True},
    {"name": "account_number", "field_type": "STRING", "required": True},
    {"name": "statement_period", "field_type": "STRING"},
    {"name": "opening_balance", "field_type": "CURRENCY"},
    {"name": "closing_balance", "field_type": "CURRENCY", "required": True},
    {"name": "total_deposits", "field_type": "CURRENCY"},
    {"name": "total_withdrawals", "field_type": "CURRENCY"},
]

INSURANCE_SCHEMA = [
    {"name": "policy_number", "field_type": "STRING", "required": True},
    {"name": "insured_name", "field_type": "STRING", "required": True},
    {"name": "insurer", "field_type": "STRING", "required": True},
    {"name": "effective_date", "field_type": "DATE"},
    {"name": "expiration_date", "field_type": "DATE"},
    {"name": "premium", "field_type": "CURRENCY"},
    {"name": "coverage_amount", "field_type": "CURRENCY"},
    {"name": "deductible", "field_type": "CURRENCY"},
    {"name": "claim_number", "field_type": "STRING"},
]

SHIPPING_SCHEMA = [
    {"name": "tracking_number", "field_type": "STRING", "required": True},
    {"name": "carrier", "field_type": "STRING", "required": True},
    {"name": "ship_date", "field_type": "DATE", "required": True},
    {"name": "delivery_date", "field_type": "DATE"},
    {"name": "shipper_name", "field_type": "STRING"},
    {"name": "shipper_address", "field_type": "STRING"},
    {"name": "recipient_name", "field_type": "STRING"},
    {"name": "recipient_address", "field_type": "STRING"},
    {"name": "weight", "field_type": "STRING"},
    {"name": "shipping_cost", "field_type": "CURRENCY"},
]

GOVERNMENT_SCHEMA = [
    {"name": "document_type", "field_type": "STRING", "required": True},
    {"name": "document_number", "field_type": "STRING", "required": True},
    {"name": "issuing_authority", "field_type": "STRING", "required": True},
    {"name": "issue_date", "field_type": "DATE"},
    {"name": "expiration_date", "field_type": "DATE"},
    {"name": "full_name", "field_type": "STRING"},
    {"name": "address", "field_type": "STRING"},
    {"name": "status", "field_type": "STRING"},
]
