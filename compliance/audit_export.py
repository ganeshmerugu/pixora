"""Compliance audit export — generates provenance packages for regulated industries.

Every extraction gets a tamper-evident audit trail: document hash, grounding evidence,
correction history, provider chain, quality scores, and cost breakdown. Downloadable
as JSON (machine-readable) or structured text for compliance teams.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from typing_extensions import Required, TypedDict


class AuditPackage(TypedDict, total=False):
    version: Required[str]
    generated_at: Required[str]
    job_id: Required[str]
    document_id: Required[str]
    document_hash: str
    filename: str
    doc_type: str
    provenance: dict[str, Any]
    extraction: dict[str, Any]
    grounding_evidence: list[dict[str, Any]]
    correction_history: list[dict[str, Any]]
    provider_chain: list[dict[str, Any]]
    quality_scores: dict[str, Any]
    sla: dict[str, Any]
    cost_breakdown: dict[str, Any]
    human_interventions: list[dict[str, Any]]
    integrity: dict[str, str]


def generate_audit_package(
    job_id: str,
    document_id: str,
    filename: str = "",
    doc_type: str = "",
    file_bytes: bytes = b"",
    extraction: dict[str, Any] | None = None,
    grounding_report: dict[str, Any] | None = None,
    quality_report: dict[str, Any] | None = None,
    trace: list[dict[str, Any]] | None = None,
    sla_result: dict[str, Any] | None = None,
    routing_decision: dict[str, Any] | None = None,
    audit_summary: dict[str, Any] | None = None,
    interventions: list[dict[str, Any]] | None = None,
) -> AuditPackage:
    now = datetime.now(timezone.utc).isoformat()

    doc_hash = hashlib.sha256(file_bytes).hexdigest() if file_bytes else ""

    grounding_evidence = []
    if grounding_report:
        for ev in grounding_report.get("evidence", []):
            grounding_evidence.append({
                "field": ev.get("field", ""),
                "extracted_value": ev.get("extracted_value", ""),
                "source_text": ev.get("source_text", ""),
                "match_type": ev.get("match_type", ""),
                "similarity_score": ev.get("similarity_score", 0),
                "page": ev.get("page", 0),
                "bbox": ev.get("bbox", {}),
            })

    correction_history = []
    if trace:
        for entry in trace:
            if "extractor_round" in entry.get("agent", "") or "self_heal" in entry.get("agent", ""):
                correction_history.append({
                    "stage": entry.get("agent", ""),
                    "detail": entry.get("detail", ""),
                    "duration_ms": entry.get("duration_ms", 0),
                })

    provider_chain = []
    if audit_summary:
        for stage in audit_summary.get("stages", []):
            if stage.get("agent") in ("extractor_round_0", "extractor_round_1", "extractor_round_2", "vlm_primary", "ocr_fallback"):
                provider_chain.append({
                    "stage": stage.get("agent", ""),
                    "detail": stage.get("detail", ""),
                    "tokens_in": stage.get("tokens_in", 0),
                    "tokens_out": stage.get("tokens_out", 0),
                    "cost_usd": stage.get("cost_usd", 0),
                    "duration_ms": stage.get("duration_ms", 0),
                })

    quality_scores = {}
    if quality_report:
        quality_scores = {
            "overall_score": quality_report.get("overall_score", 0),
            "completeness": quality_report.get("completeness", 0),
            "accuracy_confidence": quality_report.get("accuracy_confidence", 0),
            "grounding_score": quality_report.get("grounding_score", 0),
            "layout_fidelity": quality_report.get("layout_fidelity", 0),
            "recommendation": quality_report.get("recommendation", ""),
            "issues": quality_report.get("issues", []),
        }

    cost_breakdown = {}
    if audit_summary:
        cost_breakdown = {
            "total_tokens_in": audit_summary.get("total_tokens_in", 0),
            "total_tokens_out": audit_summary.get("total_tokens_out", 0),
            "total_tokens": audit_summary.get("total_tokens", 0),
            "total_cost_usd": audit_summary.get("total_cost_usd", 0),
            "total_duration_ms": audit_summary.get("total_duration_ms", 0),
        }

    clean_extraction = {}
    if extraction:
        clean_extraction = {k: v for k, v in extraction.items() if not k.startswith("_")}

    package_content = json.dumps({
        "job_id": job_id, "document_id": document_id,
        "doc_hash": doc_hash, "generated_at": now,
        "extraction_fields": len(clean_extraction),
    }, sort_keys=True)
    package_hash = hashlib.sha256(package_content.encode()).hexdigest()

    return AuditPackage(
        version="1.0",
        generated_at=now,
        job_id=job_id,
        document_id=document_id,
        document_hash=doc_hash,
        filename=filename,
        doc_type=doc_type,
        provenance={
            "platform": "pixora",
            "platform_version": "0.1.0",
            "generated_at": now,
            "document_hash_algorithm": "sha256",
        },
        extraction=clean_extraction,
        grounding_evidence=grounding_evidence,
        correction_history=correction_history,
        provider_chain=provider_chain,
        quality_scores=quality_scores,
        sla=dict(sla_result) if sla_result else {},
        cost_breakdown=cost_breakdown,
        human_interventions=interventions or [],
        integrity={
            "package_hash": package_hash,
            "hash_algorithm": "sha256",
            "content_hashed": "job_id+document_id+doc_hash+generated_at+extraction_field_count",
        },
    )


def audit_package_to_text(package: AuditPackage) -> str:
    lines = [
        "=" * 72,
        "PIXORA COMPLIANCE AUDIT REPORT",
        "=" * 72,
        "",
        f"Generated:    {package.get('generated_at', '')}",
        f"Job ID:       {package.get('job_id', '')}",
        f"Document ID:  {package.get('document_id', '')}",
        f"Document Hash (SHA-256): {package.get('document_hash', 'N/A')}",
        f"Filename:     {package.get('filename', '')}",
        f"Doc Type:     {package.get('doc_type', '')}",
        "",
        "-" * 72,
        "EXTRACTION RESULTS",
        "-" * 72,
    ]

    for field, value in package.get("extraction", {}).items():
        lines.append(f"  {field}: {value}")

    lines += ["", "-" * 72, "GROUNDING EVIDENCE", "-" * 72]
    for ev in package.get("grounding_evidence", []):
        status = "GROUNDED" if ev.get("match_type") in ("exact", "normalized", "fuzzy") else "UNGROUNDED"
        lines.append(f"  [{status}] {ev.get('field', '')}: '{ev.get('extracted_value', '')}' <- '{ev.get('source_text', '')[:60]}' ({ev.get('match_type', '')})")

    sla = package.get("sla", {})
    if sla:
        lines += ["", "-" * 72, "SLA COMPLIANCE", "-" * 72]
        lines.append(f"  Tier:     {sla.get('tier', '')}")
        lines.append(f"  Target:   {sla.get('accuracy_target', 0) * 100:.0f}%")
        lines.append(f"  Achieved: {sla.get('achieved_accuracy', 0) * 100:.1f}%")
        lines.append(f"  Met SLA:  {'YES' if sla.get('met_sla') else 'NO'}")
        lines.append(f"  Action:   {sla.get('action', '')}")

    qs = package.get("quality_scores", {})
    if qs:
        lines += ["", "-" * 72, "QUALITY SCORES", "-" * 72]
        lines.append(f"  Overall:      {qs.get('overall_score', 0) * 100:.1f}%")
        lines.append(f"  Completeness: {qs.get('completeness', 0) * 100:.1f}%")
        lines.append(f"  Grounding:    {qs.get('grounding_score', 0) * 100:.1f}%")
        lines.append(f"  Recommendation: {qs.get('recommendation', '')}")

    cost = package.get("cost_breakdown", {})
    if cost:
        lines += ["", "-" * 72, "COST BREAKDOWN", "-" * 72]
        lines.append(f"  Total Tokens: {cost.get('total_tokens', 0):,}")
        lines.append(f"  Total Cost:   ${cost.get('total_cost_usd', 0):.4f}")
        lines.append(f"  Duration:     {cost.get('total_duration_ms', 0):,}ms")

    chain = package.get("provider_chain", [])
    if chain:
        lines += ["", "-" * 72, "PROVIDER CHAIN", "-" * 72]
        for step in chain:
            lines.append(f"  {step.get('stage', '')}: {step.get('detail', '')} ({step.get('duration_ms', 0)}ms, ${step.get('cost_usd', 0):.4f})")

    integrity = package.get("integrity", {})
    if integrity:
        lines += ["", "-" * 72, "INTEGRITY", "-" * 72]
        lines.append(f"  Package Hash: {integrity.get('package_hash', '')}")
        lines.append(f"  Algorithm:    {integrity.get('hash_algorithm', '')}")

    lines += ["", "=" * 72, "END OF AUDIT REPORT", "=" * 72]
    return "\n".join(lines)
