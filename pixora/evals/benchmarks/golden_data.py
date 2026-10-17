"""Golden benchmark dataset — 100 enterprise documents across 10 types and 3 difficulty tiers.
Aggregates all per-type benchmark modules."""
from __future__ import annotations

from pixora.evals.benchmarks._invoices import get_invoices
from pixora.evals.benchmarks._receipts import get_receipts
from pixora.evals.benchmarks._contracts import get_contracts
from pixora.evals.benchmarks._medical import get_medical
from pixora.evals.benchmarks._forms import get_forms
from pixora.evals.benchmarks._scientific import get_scientific
from pixora.evals.benchmarks._bank_statements import get_bank_statements
from pixora.evals.benchmarks._insurance import get_insurance
from pixora.evals.benchmarks._shipping import get_shipping
from pixora.evals.benchmarks._government import get_government

GOLDEN_BENCHMARKS: list[dict] = [
    *get_invoices(),
    *get_receipts(),
    *get_contracts(),
    *get_medical(),
    *get_forms(),
    *get_scientific(),
    *get_bank_statements(),
    *get_insurance(),
    *get_shipping(),
    *get_government(),
]
