HARNESS_CONFIG = {
    "max_correction_rounds": 3,
    "scoring": {
        "base_threshold": 0.80,
        "floor": 0.65,
        "ceiling": 0.90,
    },
    "entropy": {
        "field_coverage_threshold": 1.0,
        "duplicate_threshold": 0.95,
        "confidence_decline_threshold": -0.05,
    },
    "maintenance_score_weights": {
        "field_entropy": 0.30,
        "stale_ratio": 0.30,
        "confidence_norm": 0.20,
        "duplication": 0.20,
    },
}

DIMENSION_WEIGHTS: dict[str, float] = {
    "completeness": 2.5,
    "grounding": 3.0,
    "value_accuracy": 2.5,
    "type_accuracy": 1.5,
    "cross_field": 2.0,
    "table_structure": 2.0,
    "reading_order": 1.0,
    "ontology_compliance": 1.5,
}
