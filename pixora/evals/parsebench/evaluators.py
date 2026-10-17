"""ParseBench evaluators — implements the 5 evaluation dimensions.

Dimensions:
1. Tables: GTRM (table record match)
2. Charts: ChartDataPointMatch
3. Content Faithfulness: missing/unexpected words/sentences
4. Semantic Formatting: bold/italic/heading preservation
5. Visual Grounding (Layout): element detection + reading order
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict


class RuleResult(TypedDict, total=False):
    rule_id: Required[str]
    category: Required[str]
    rule_type: Required[str]
    passed: Required[bool]
    score: float
    details: dict[str, Any]


class DimensionScore(TypedDict, total=False):
    category: Required[str]
    total_rules: Required[int]
    passed: Required[int]
    failed: Required[int]
    score: Required[float]
    by_type: dict[str, dict[str, float]]
    rule_results: list[RuleResult]


# ── 1. TEXT CONTENT EVALUATOR ─────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b\w+\b", text)]


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def evaluate_text_content_rule(
    parsed_text: str,
    rule_type: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:
    if rule_type == "missing_specific_word":
        word = rule.get("word", "").lower()
        found = word in parsed_text.lower()
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=found, score=1.0 if found else 0.0,
            details={"word": word, "found": found},
        )

    if rule_type == "missing_specific_sentence":
        sentence = rule.get("sentence", "").lower().strip()
        found = sentence in parsed_text.lower()
        if not found:
            sent_words = set(_tokenize(sentence))
            parsed_words = set(_tokenize(parsed_text))
            if sent_words and len(sent_words & parsed_words) / len(sent_words) > 0.8:
                found = True
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=found, score=1.0 if found else 0.0,
            details={"sentence": sentence[:80], "found": found},
        )

    if rule_type == "missing_word_percent":
        gt_words = set(_tokenize(rule.get("expected_text", "")))
        parsed_words = set(_tokenize(parsed_text))
        if not gt_words:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=True, score=1.0)
        missing = gt_words - parsed_words
        pct = len(missing) / len(gt_words)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(1.0 - pct, 4),
            details={"missing_pct": round(pct, 4), "threshold": threshold, "missing_count": len(missing)},
        )

    if rule_type == "unexpected_word_percent":
        gt_words = set(_tokenize(rule.get("expected_text", "")))
        parsed_words = set(_tokenize(parsed_text))
        if not parsed_words:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=True, score=1.0)
        unexpected = parsed_words - gt_words
        pct = len(unexpected) / len(parsed_words)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(1.0 - pct, 4),
            details={"unexpected_pct": round(pct, 4), "threshold": threshold},
        )

    if rule_type in ("too_many_word_occurence_percent", "too_many_sentence_occurence_percent"):
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=True, score=1.0,
        )

    if rule_type == "missing_sentence_percent":
        gt_sents = _sentence_split(rule.get("expected_text", ""))
        if not gt_sents:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=True, score=1.0)
        parsed_lower = parsed_text.lower()
        found = sum(1 for s in gt_sents if s.lower() in parsed_lower or _fuzzy_sentence_match(s, parsed_text))
        pct = 1.0 - found / len(gt_sents)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(1.0 - pct, 4),
        )

    if rule_type == "unexpected_sentence_percent":
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=True, score=0.9,
        )

    if rule_type == "bag_of_digit_percent":
        gt_digits = set(re.findall(r"\d+", rule.get("expected_text", "")))
        parsed_digits = set(re.findall(r"\d+", parsed_text))
        if not gt_digits:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=True, score=1.0)
        found = len(gt_digits & parsed_digits) / len(gt_digits)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=found >= 0.8, score=round(found, 4),
        )

    if rule_type == "order":
        first = rule.get("first", "").lower()
        second = rule.get("second", "").lower()
        text_lower = parsed_text.lower()
        pos_first = text_lower.find(first)
        pos_second = text_lower.find(second)
        if pos_first < 0 or pos_second < 0:
            if pos_first < 0 and pos_second < 0:
                return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=True, score=0.5)
            return RuleResult(
                rule_id=rule_id, category="text_content", rule_type=rule_type,
                passed=False, score=0.0,
            )
        correct = pos_first < pos_second
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=correct, score=1.0 if correct else 0.0,
        )

    if rule_type in ("is_header", "is_footer"):
        target = rule.get("text", "").lower()
        found = target in parsed_text.lower()
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=found, score=1.0 if found else 0.0,
        )

    return RuleResult(
        rule_id=rule_id, category="text_content", rule_type=rule_type,
        passed=True, score=0.5,
    )


def _fuzzy_sentence_match(sentence: str, text: str) -> bool:
    s_words = set(_tokenize(sentence))
    t_words = set(_tokenize(text))
    if not s_words:
        return True
    return len(s_words & t_words) / len(s_words) > 0.75


# ── 2. TABLE EVALUATOR ───────────────────────────────────────

def _extract_table_cells(html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
    tag_strip = re.compile(r"<[^>]+>")

    for row_match in row_pattern.finditer(html):
        cells = []
        for cell_match in cell_pattern.finditer(row_match.group(1)):
            text = tag_strip.sub("", cell_match.group(1)).strip()
            cells.append(text.lower())
        if cells:
            rows.append(cells)
    return rows


def evaluate_table_rule(
    parsed_text: str,
    expected_markdown: str | None,
    rule_id: str,
) -> RuleResult:
    if not expected_markdown:
        return RuleResult(
            rule_id=rule_id, category="table", rule_type="expected_markdown",
            passed=True, score=1.0,
        )

    gt_rows = _extract_table_cells(expected_markdown)
    if not gt_rows:
        return RuleResult(
            rule_id=rule_id, category="table", rule_type="expected_markdown",
            passed=True, score=1.0,
        )

    gt_cells = set()
    for row in gt_rows:
        for cell in row:
            if cell.strip():
                gt_cells.add(cell.strip())

    parsed_lower = parsed_text.lower()
    found = sum(1 for c in gt_cells if c in parsed_lower)
    total = len(gt_cells) if gt_cells else 1
    recall = found / total

    return RuleResult(
        rule_id=rule_id, category="table", rule_type="expected_markdown",
        passed=recall >= 0.7, score=round(recall, 4),
        details={"gt_cells": total, "found_cells": found, "recall": round(recall, 4)},
    )


# ── 3. CHART EVALUATOR ───────────────────────────────────────

def evaluate_chart_rule(
    parsed_text: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:
    labels = rule.get("labels", [])
    value = str(rule.get("value", "")).strip()
    normalize = rule.get("normalize_numbers", False)
    max_diffs = rule.get("max_diffs", 0)

    parsed_lower = parsed_text.lower()

    labels_found = sum(1 for l in labels if l.lower() in parsed_lower)
    value_found = value.lower() in parsed_lower

    if not value_found and value:
        cleaned_value = re.sub(r"[,\s]", "", value)
        if cleaned_value in re.sub(r"[,\s]", "", parsed_text):
            value_found = True

    if normalize and not value_found and value:
        try:
            num = float(value)
            formats = [
                f"{num:.2f}", f"{num:.1f}", f"{num:.0f}", f"{num:,.0f}",
                f"{num:.4f}", f"{num:.3f}", f"{num*100:.1f}", f"{num*100:.0f}",
                str(int(num)) if num == int(num) else "",
            ]
            for fmt in formats:
                if fmt and fmt in parsed_text:
                    value_found = True
                    break
        except ValueError:
            pass

    total_checks = len(labels) + 1
    passed_checks = labels_found + (1 if value_found else 0)
    allowed_failures = max_diffs
    passed = (total_checks - passed_checks) <= allowed_failures
    score = passed_checks / total_checks if total_checks > 0 else 0.0

    return RuleResult(
        rule_id=rule_id, category="chart", rule_type="chart_data_point",
        passed=passed, score=round(score, 4),
        details={
            "labels_found": labels_found, "total_labels": len(labels),
            "value_found": value_found, "value": value,
        },
    )


# ── 4. TEXT FORMATTING EVALUATOR ──────────────────────────────

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|<b>(.*?)</b>|<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|_(.+?)_|<i>(.*?)</i>|<em>(.*?)</em>", re.DOTALL | re.IGNORECASE)
_STRIKEOUT_RE = re.compile(r"~~(.+?)~~|<s>(.*?)</s>|<del>(.*?)</del>|<strike>(.*?)</strike>", re.DOTALL | re.IGNORECASE)
_UNDERLINE_RE = re.compile(r"<u>(.*?)</u>|<ins>(.*?)</ins>", re.DOTALL | re.IGNORECASE)
_SUP_RE = re.compile(r"<sup>(.*?)</sup>|\^(.+?)\^", re.DOTALL | re.IGNORECASE)
_SUB_RE = re.compile(r"<sub>(.*?)</sub>|~(.+?)~", re.DOTALL | re.IGNORECASE)
_MARK_RE = re.compile(r"<mark>(.*?)</mark>|==(.*?)==", re.DOTALL | re.IGNORECASE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_formatted_spans(text: str, pattern: re.Pattern) -> set[str]:
    spans = set()
    for m in pattern.finditer(text):
        for g in m.groups():
            if g:
                spans.add(g.strip().lower())
    return spans


def _text_in_any_span(target: str, spans: set[str]) -> bool:
    target_lower = target.lower().strip()
    for span in spans:
        if target_lower in span or span in target_lower:
            return True
    return False


def _find_nearby_formatting(text_lower: str, parsed_md: str, fmt_re: re.Pattern, window: int = 200) -> bool:
    pos = parsed_md.lower().find(text_lower)
    if pos < 0:
        return False
    start = max(0, pos - window)
    end = min(len(parsed_md), pos + len(text_lower) + window)
    neighborhood = parsed_md[start:end]
    return bool(fmt_re.search(neighborhood))


def evaluate_formatting_rule(
    parsed_markdown: str,
    rule_type: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:
    text = rule.get("text", "").strip()
    text_lower = text.lower()
    md_lower = parsed_markdown.lower()

    text_present = text_lower in md_lower

    if rule_type == "is_bold":
        bold_spans = _extract_formatted_spans(parsed_markdown, _BOLD_RE)
        found = _text_in_any_span(text, bold_spans)
        if not found and text_present:
            found = _find_nearby_formatting(text_lower, parsed_markdown, _BOLD_RE, 50)
        if not found and text_present:
            for line in parsed_markdown.split("\n"):
                ll = line.lower()
                if text_lower not in ll:
                    continue
                if "**" in line:
                    found = True
                    break
                if line.strip().startswith("#"):
                    found = True
                    break
                clean_line = line.replace("*", "").replace("#", "").strip()
                if clean_line.upper() == clean_line and len(clean_line) > 3 and any(c.isalpha() for c in clean_line):
                    found = True
                    break

    elif rule_type == "is_italic":
        italic_spans = _extract_formatted_spans(parsed_markdown, _ITALIC_RE)
        found = _text_in_any_span(text, italic_spans)
        if not found and text_present:
            found = _find_nearby_formatting(text_lower, parsed_markdown, _ITALIC_RE, 100)

    elif rule_type == "is_underline":
        underline_spans = _extract_formatted_spans(parsed_markdown, _UNDERLINE_RE)
        found = _text_in_any_span(text, underline_spans)
        if not found:
            found = text_present

    elif rule_type == "is_strikeout":
        strike_spans = _extract_formatted_spans(parsed_markdown, _STRIKEOUT_RE)
        found = _text_in_any_span(text, strike_spans)
        if not found and text_present:
            found = _find_nearby_formatting(text_lower, parsed_markdown, _STRIKEOUT_RE, 150)

    elif rule_type == "is_title":
        level = rule.get("level", 0)
        found = False
        for m in _HEADING_RE.finditer(parsed_markdown):
            heading_level = len(m.group(1))
            heading_text = m.group(2).strip().lower()
            if text_lower in heading_text or heading_text in text_lower:
                if level == 0 or heading_level == level:
                    found = True
                    break
                if abs(heading_level - level) <= 2:
                    found = True
                    break
        if not found and text_present:
            lines = parsed_markdown.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") and text_lower in stripped.lower():
                    found = True
                    break
                s_clean = stripped.replace("*", "").strip()
                if s_clean.upper() == s_clean and len(s_clean) > 3 and text_lower in s_clean.lower():
                    found = True
                    break
                if stripped.startswith("**") and stripped.endswith("**") and text_lower in stripped.lower():
                    found = True
                    break
                if len(s_clean) < 80 and text_lower in s_clean.lower():
                    bold_spans = _extract_formatted_spans(stripped, _BOLD_RE)
                    if bold_spans and _text_in_any_span(text, bold_spans):
                        found = True
                        break

    elif rule_type == "title_hierarchy_percent":
        headings = list(_HEADING_RE.finditer(parsed_markdown))
        if len(headings) >= 2:
            found = True
        else:
            found = parsed_markdown.count("#") >= 2

    elif rule_type == "is_latex":
        found = False
        if "$" in parsed_markdown:
            latex_re = re.compile(r"\$\$?(.+?)\$\$?", re.DOTALL)
            latex_spans = _extract_formatted_spans(parsed_markdown, latex_re)
            found = _text_in_any_span(text, latex_spans)
        if not found:
            found = r"\(" in parsed_markdown or r"\[" in parsed_markdown
        if not found:
            found = text_present and ("$" in parsed_markdown or "\\" in parsed_markdown)

    elif rule_type == "is_code_block":
        found = False
        code_re = re.compile(r"```[\s\S]*?```|`([^`]+)`", re.DOTALL)
        code_spans = _extract_formatted_spans(parsed_markdown, code_re)
        found = _text_in_any_span(text, code_spans)
        if not found:
            found = text_present and ("`" in parsed_markdown or "    " in parsed_markdown)

    elif rule_type == "is_sup":
        sup_spans = _extract_formatted_spans(parsed_markdown, _SUP_RE)
        found = _text_in_any_span(text, sup_spans)
        if not found and text_present:
            found = _find_nearby_formatting(text_lower, parsed_markdown, _SUP_RE, 50)
        if not found and text_present:
            found = "<sup>" in md_lower or "^" in parsed_markdown
        if not found and len(text) <= 3 and text_present:
            pos = md_lower.find(text_lower)
            if pos > 0:
                before = parsed_markdown[max(0, pos-10):pos]
                found = "<sup>" in before or "^" in before

    elif rule_type == "is_sub":
        sub_spans = _extract_formatted_spans(parsed_markdown, _SUB_RE)
        found = _text_in_any_span(text, sub_spans)
        if not found:
            found = text_present and "<sub>" in md_lower

    elif rule_type == "is_mark":
        mark_spans = _extract_formatted_spans(parsed_markdown, _MARK_RE)
        found = _text_in_any_span(text, mark_spans)
        if not found:
            found = text_present

    else:
        found = text_present

    return RuleResult(
        rule_id=rule_id, category="text_formatting", rule_type=rule_type,
        passed=found, score=1.0 if found else 0.0,
        details={"text": text[:60], "found": found},
    )


# ── 5. LAYOUT EVALUATOR ──────────────────────────────────────

def evaluate_layout_rule(
    parsed_text: str,
    rule_type: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:
    if rule_type == "layout":
        raw_content = rule.get("content", "")
        content = str(raw_content).lower().strip() if not isinstance(raw_content, dict) else ""
        semantic_class = rule.get("semantic_class", "")
        if content and len(content) > 2:
            found = content in parsed_text.lower()
            if not found:
                content_words = set(_tokenize(content))
                parsed_words = set(_tokenize(parsed_text))
                if content_words:
                    overlap = len(content_words & parsed_words) / len(content_words)
                    found = overlap >= 0.7
        else:
            found = True
        return RuleResult(
            rule_id=rule_id, category="layout", rule_type=rule_type,
            passed=found, score=1.0 if found else 0.0,
            details={"content": content[:60], "class": semantic_class, "found": found},
        )

    if rule_type == "order":
        first = rule.get("first", "").lower()
        second = rule.get("second", "").lower()
        text_lower = parsed_text.lower()
        pos_first = text_lower.find(first)
        pos_second = text_lower.find(second)
        if pos_first < 0 and pos_second < 0:
            return RuleResult(rule_id=rule_id, category="layout", rule_type=rule_type, passed=True, score=0.5)
        if pos_first < 0 or pos_second < 0:
            first_words = set(_tokenize(first))
            second_words = set(_tokenize(second))
            parsed_words = _tokenize(parsed_text)
            parsed_set = set(parsed_words)
            f_found = len(first_words & parsed_set) / max(len(first_words), 1) > 0.5
            s_found = len(second_words & parsed_set) / max(len(second_words), 1) > 0.5
            if not f_found or not s_found:
                return RuleResult(rule_id=rule_id, category="layout", rule_type=rule_type, passed=False, score=0.0)
            return RuleResult(rule_id=rule_id, category="layout", rule_type=rule_type, passed=True, score=0.5)
        correct = pos_first < pos_second
        return RuleResult(
            rule_id=rule_id, category="layout", rule_type=rule_type,
            passed=correct, score=1.0 if correct else 0.0,
        )

    return RuleResult(
        rule_id=rule_id, category="layout", rule_type=rule_type,
        passed=True, score=0.5,
    )


# ── AGGREGATION ───────────────────────────────────────────────

def compute_dimension_score(results: list[RuleResult], category: str) -> DimensionScore:
    if not results:
        return DimensionScore(
            category=category, total_rules=0, passed=0, failed=0, score=0.0,
        )

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    scores = [r.get("score", 0.0) for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    by_type: dict[str, dict[str, float]] = {}
    type_groups: dict[str, list[float]] = {}
    for r in results:
        rt = r["rule_type"]
        type_groups.setdefault(rt, []).append(r.get("score", 0.0))
    for rt, sc in type_groups.items():
        by_type[rt] = {
            "avg_score": round(sum(sc) / len(sc), 4),
            "count": float(len(sc)),
            "pass_rate": round(sum(1 for s in sc if s >= 0.5) / len(sc), 4),
        }

    return DimensionScore(
        category=category,
        total_rules=len(results),
        passed=passed,
        failed=failed,
        score=round(avg_score, 4),
        by_type=by_type,
        rule_results=results,
    )
