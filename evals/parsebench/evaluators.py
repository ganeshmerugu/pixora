"""ParseBench evaluators — implements the 5 evaluation dimensions.

All rule schemas verified against actual JSONL data:
  text_content: bag_of_word, bag_of_sentence, bag_of_digit, word, sentence, before/after
  text_formatting: text, level, formula, code, language, title_hierarchy
  table: expected_markdown
  chart: labels, value, normalize_numbers, max_diffs
  layout: content, semantic_class, before/after
"""
from __future__ import annotations
import re
from collections import Counter
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


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b\w+\b", text)]


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 5]


def _fuzzy_find(needle: str, haystack: str) -> int:
    pos = haystack.find(needle)
    if pos >= 0:
        return pos

    words = _tokenize(needle)
    sig_words = [w for w in words if len(w) >= 4]
    if not sig_words:
        sig_words = words[:3] if words else []
    if not sig_words:
        return -1

    best_pos = -1
    found_count = 0
    for w in sig_words:
        p = haystack.find(w)
        if p >= 0:
            found_count += 1
            if best_pos < 0 or p < best_pos:
                best_pos = p

    if found_count >= max(1, len(sig_words) * 0.6):
        return best_pos
    return -1


# ── 1. TEXT CONTENT EVALUATOR ─────────────────────────────────

def evaluate_text_content_rule(
    parsed_text: str,
    rule_type: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:

    # --- missing_specific_word: rule.word ---
    if rule_type == "missing_specific_word":
        word = rule.get("word", "").lower()
        if not word:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        found = word in text_lower
        if not found and len(word) >= 4:
            parsed_words = set(_tokenize(parsed_text))
            for pw in parsed_words:
                if len(pw) == len(word) and sum(a != b for a, b in zip(pw, word)) <= 1:
                    found = True
                    break
        return _bool_result(rule_id, "text_content", rule_type, found)

    # --- missing_specific_sentence: rule.sentence ---
    if rule_type == "missing_specific_sentence":
        sentence = rule.get("sentence", "").lower().strip()
        if not sentence:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        found = sentence in text_lower
        if not found:
            found = _fuzzy_find(sentence, text_lower) >= 0
        if not found:
            sent_words = set(_tokenize(sentence))
            parsed_words = set(_tokenize(parsed_text))
            if sent_words and len(sent_words & parsed_words) / len(sent_words) > 0.7:
                found = True
        return _bool_result(rule_id, "text_content", rule_type, found)

    # --- missing_word_percent: rule.bag_of_word {word: count} ---
    if rule_type == "missing_word_percent":
        bag = rule.get("bag_of_word", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        gt_words = set(w.lower() for w in bag.keys())
        parsed_words = set(_tokenize(parsed_text))
        missing = gt_words - parsed_words
        pct = len(missing) / len(gt_words)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- unexpected_word_percent: rule.bag_of_word {word: count} ---
    if rule_type == "unexpected_word_percent":
        bag = rule.get("bag_of_word", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        gt_words = set(w.lower() for w in bag.keys())
        parsed_words = set(_tokenize(parsed_text))
        if not parsed_words:
            return _pass(rule_id, "text_content", rule_type)
        unexpected = parsed_words - gt_words
        pct = len(unexpected) / len(parsed_words)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- too_many_word_occurence_percent: rule.bag_of_word {word: expected_count} ---
    if rule_type == "too_many_word_occurence_percent":
        bag = rule.get("bag_of_word", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        parsed_counts = Counter(_tokenize(parsed_text))
        total_words = 0
        over_count = 0
        for word, expected in bag.items():
            w = word.lower()
            total_words += 1
            actual = parsed_counts.get(w, 0)
            if actual > expected * 2:
                over_count += 1
        pct = over_count / total_words if total_words > 0 else 0.0
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- missing_sentence_percent: rule.bag_of_sentence {sentence: count} ---
    if rule_type == "missing_sentence_percent":
        bag = rule.get("bag_of_sentence", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        found = 0
        for sent in bag.keys():
            s = sent.lower().strip()
            if s in text_lower or _fuzzy_find(s, text_lower) >= 0:
                found += 1
        pct = 1.0 - found / len(bag)
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- unexpected_sentence_percent: rule.bag_of_sentence + original_md ---
    if rule_type == "unexpected_sentence_percent":
        bag = rule.get("bag_of_sentence", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        gt_sentences = set(s.lower().strip() for s in bag.keys())
        parsed_sentences = _sentence_split(parsed_text)
        if not parsed_sentences:
            return _pass(rule_id, "text_content", rule_type)
        unexpected = 0
        for ps in parsed_sentences:
            ps_lower = ps.lower().strip()
            if len(ps_lower) < 10:
                continue
            matched = False
            for gs in gt_sentences:
                if ps_lower in gs or gs in ps_lower:
                    matched = True
                    break
                ps_words = set(_tokenize(ps_lower))
                gs_words = set(_tokenize(gs))
                if ps_words and gs_words and len(ps_words & gs_words) / len(ps_words) > 0.6:
                    matched = True
                    break
            if not matched:
                unexpected += 1
        pct = unexpected / len(parsed_sentences) if parsed_sentences else 0.0
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- too_many_sentence_occurence_percent: rule.bag_of_sentence {sent: expected_count} ---
    if rule_type == "too_many_sentence_occurence_percent":
        bag = rule.get("bag_of_sentence", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        total = 0
        over = 0
        for sent, expected in bag.items():
            s = sent.lower().strip()
            if not s:
                continue
            total += 1
            actual = text_lower.count(s)
            if actual > expected * 2:
                over += 1
        pct = over / total if total > 0 else 0.0
        threshold = rule.get("threshold", 0.1)
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=pct <= threshold, score=round(max(0.0, 1.0 - pct), 4),
        )

    # --- bag_of_digit_percent: rule.bag_of_digit {digit_char: count} ---
    if rule_type == "bag_of_digit_percent":
        bag = rule.get("bag_of_digit", {})
        if not bag:
            return _pass(rule_id, "text_content", rule_type)
        gt_total = sum(bag.values())
        if gt_total == 0:
            return _pass(rule_id, "text_content", rule_type)
        parsed_digit_counts = Counter(c for c in parsed_text if c.isdigit())
        matched = 0
        for digit, expected in bag.items():
            actual = parsed_digit_counts.get(str(digit), 0)
            if actual > 0:
                matched += min(actual, expected)
        recall = matched / gt_total
        return RuleResult(
            rule_id=rule_id, category="text_content", rule_type=rule_type,
            passed=recall >= 0.8, score=round(recall, 4),
        )

    # --- order: rule.before + rule.after ---
    if rule_type == "order":
        first = rule.get("before", "").lower()
        second = rule.get("after", "").lower()
        if not first or not second:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        pos_first = _fuzzy_find(first, text_lower)
        pos_second = _fuzzy_find(second, text_lower)
        if pos_first < 0 and pos_second < 0:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=False, score=0.0)
        if pos_first < 0 or pos_second < 0:
            return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=False, score=0.0)
        correct = pos_first < pos_second
        return _bool_result(rule_id, "text_content", rule_type, correct)

    # --- is_header / is_footer: rule.text ---
    if rule_type in ("is_header", "is_footer"):
        target = rule.get("text", "").lower().strip()
        if not target:
            return _pass(rule_id, "text_content", rule_type)
        text_lower = parsed_text.lower()
        found = target in text_lower
        if not found:
            found = _fuzzy_find(target, text_lower) >= 0
        return _bool_result(rule_id, "text_content", rule_type, found)

    return RuleResult(rule_id=rule_id, category="text_content", rule_type=rule_type, passed=False, score=0.0)


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
        return _pass(rule_id, "table", "expected_markdown")

    # Try HTML table extraction
    gt_rows = _extract_table_cells(expected_markdown)

    # Also try markdown pipe table extraction
    if not gt_rows:
        gt_rows = _extract_markdown_table(expected_markdown)

    if not gt_rows:
        return _pass(rule_id, "table", "expected_markdown")

    gt_cells = set()
    for row in gt_rows:
        for cell in row:
            c = cell.strip()
            if c and len(c) > 0:
                gt_cells.add(c)

    if not gt_cells:
        return _pass(rule_id, "table", "expected_markdown")

    parsed_lower = parsed_text.lower()
    found = sum(1 for c in gt_cells if c in parsed_lower)
    recall = found / len(gt_cells)

    return RuleResult(
        rule_id=rule_id, category="table", rule_type="expected_markdown",
        passed=recall >= 0.7, score=round(recall, 4),
        details={"gt_cells": len(gt_cells), "found_cells": found},
    )


def _extract_markdown_table(md: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in md.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[-:\s|]+\|$", line):
            continue
        cells = [c.strip().lower() for c in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)
    return rows


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

    labels_found = sum(1 for lb in labels if lb.lower() in parsed_lower)
    value_found = value.lower() in parsed_lower if value else True

    if not value_found and value:
        cleaned_value = re.sub(r"[,\s]", "", value)
        if cleaned_value and cleaned_value in re.sub(r"[,\s]", "", parsed_text):
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

    total_checks = len(labels) + (1 if value else 0)
    if total_checks == 0:
        return _pass(rule_id, "chart", "chart_data_point")
    passed_checks = labels_found + (1 if value_found and value else 0)
    passed = (total_checks - passed_checks) <= max_diffs
    score = passed_checks / total_checks

    return RuleResult(
        rule_id=rule_id, category="chart", rule_type="chart_data_point",
        passed=passed, score=round(score, 4),
    )


# ── 4. TEXT FORMATTING EVALUATOR ──────────────────────────────

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|<b>(.*?)</b>|<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|_(.+?)_|<i>(.*?)</i>|<em>(.*?)</em>", re.DOTALL | re.IGNORECASE)
_STRIKEOUT_RE = re.compile(r"~~(.+?)~~|<s>(.*?)</s>|<del>(.*?)</del>|<strike>(.*?)</strike>", re.DOTALL | re.IGNORECASE)
_UNDERLINE_RE = re.compile(r"<u>(.*?)</u>|<ins>(.*?)</ins>", re.DOTALL | re.IGNORECASE)
_SUP_RE = re.compile(r"<sup>(.*?)</sup>|\^(.+?)\^", re.DOTALL | re.IGNORECASE)
_SUB_RE = re.compile(r"<sub>(.*?)</sub>|~(.+?)~", re.DOTALL | re.IGNORECASE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_formatted_spans(text: str, pattern: re.Pattern) -> set[str]:
    spans = set()
    for m in pattern.finditer(text):
        for g in m.groups():
            if g:
                spans.add(g.strip().lower())
    return spans


def _text_in_any_span(target: str, spans: set[str]) -> bool:
    t = target.lower().strip()
    for span in spans:
        if t in span or span in t:
            return True
    return False


def evaluate_formatting_rule(
    parsed_markdown: str,
    rule_type: str,
    rule: dict,
    rule_id: str,
) -> RuleResult:
    text = rule.get("text", "").strip()
    text_lower = text.lower()
    md_lower = parsed_markdown.lower()
    # Strip markdown formatting for content-level matching
    md_clean = md_lower.replace("*", "").replace("#", "").replace("<sup>", "").replace("</sup>", "")
    text_present = text_lower in md_lower or text_lower in md_clean

    found = False

    if rule_type == "is_bold":
        bold_spans = _extract_formatted_spans(parsed_markdown, _BOLD_RE)
        found = _text_in_any_span(text, bold_spans)
        if not found and text_present:
            for line in parsed_markdown.split("\n"):
                clean_line = line.replace("*", "").replace("#", "").strip().lower()
                if text_lower not in line.lower() and text_lower not in clean_line:
                    continue
                if "**" in line:
                    found = True
                    break
                if line.strip().startswith("#"):
                    found = True
                    break

    elif rule_type == "is_italic":
        italic_spans = _extract_formatted_spans(parsed_markdown, _ITALIC_RE)
        found = _text_in_any_span(text, italic_spans)
        if not found and text_present:
            for line in parsed_markdown.split("\n"):
                clean_line = line.replace("*", "").strip().lower()
                if text_lower not in clean_line:
                    continue
                single_star = re.findall(r"(?<!\*)\*(?!\*)", line)
                if len(single_star) >= 2:
                    found = True
                    break

    elif rule_type == "is_underline":
        underline_spans = _extract_formatted_spans(parsed_markdown, _UNDERLINE_RE)
        found = _text_in_any_span(text, underline_spans)
        if not found:
            found = text_present

    elif rule_type == "is_strikeout":
        strike_spans = _extract_formatted_spans(parsed_markdown, _STRIKEOUT_RE)
        found = _text_in_any_span(text, strike_spans)

    elif rule_type == "is_title":
        level = rule.get("level", 0)
        for m in _HEADING_RE.finditer(parsed_markdown):
            heading_level = len(m.group(1))
            heading_text = m.group(2).replace("*", "").strip().lower()
            if text_lower in heading_text or heading_text in text_lower:
                if level == 0 or abs(heading_level - level) <= 2:
                    found = True
                    break
        if not found and text_present:
            for line in parsed_markdown.split("\n"):
                stripped = line.strip()
                s_clean = stripped.replace("*", "").replace("#", "").strip()
                if text_lower not in s_clean.lower():
                    continue
                if stripped.startswith("#"):
                    found = True
                    break
                if "**" in stripped and len(s_clean) < 100:
                    found = True
                    break
                if s_clean == s_clean.upper() and len(s_clean) > 3 and any(c.isalpha() for c in s_clean):
                    found = True
                    break

    elif rule_type == "title_hierarchy_percent":
        hierarchy = rule.get("title_hierarchy", [])
        if not hierarchy:
            found = True
        else:
            headings = list(_HEADING_RE.finditer(parsed_markdown))
            levels_found = set(len(m.group(1)) for m in headings)
            found = len(levels_found) >= 2

    elif rule_type == "is_latex":
        formula = rule.get("formula", rule.get("text", ""))
        found = "$" in parsed_markdown and formula.lower() in md_lower
        if not found:
            found = r"\(" in parsed_markdown or r"\[" in parsed_markdown
        if not found and text_present:
            found = "$" in parsed_markdown or "\\" in parsed_markdown

    elif rule_type == "is_code_block":
        code = rule.get("code", rule.get("text", ""))
        code_lower = code.lower().strip()
        found = code_lower in md_lower
        if not found:
            found = "`" in parsed_markdown and code_lower in md_clean

    elif rule_type == "is_sup":
        sup_spans = _extract_formatted_spans(parsed_markdown, _SUP_RE)
        found = _text_in_any_span(text, sup_spans)
        if not found and text_present:
            found = "<sup>" in md_lower or "^" in parsed_markdown

    elif rule_type == "is_sub":
        sub_spans = _extract_formatted_spans(parsed_markdown, _SUB_RE)
        found = _text_in_any_span(text, sub_spans)
        if not found:
            found = text_present and "<sub>" in md_lower

    elif rule_type == "is_mark":
        found = text_present

    else:
        found = text_present

    return RuleResult(
        rule_id=rule_id, category="text_formatting", rule_type=rule_type,
        passed=found, score=1.0 if found else 0.0,
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
        if content and len(content) > 2:
            parsed_lower = parsed_text.lower()
            found = content in parsed_lower
            if not found:
                content_words = set(_tokenize(content))
                parsed_words = set(_tokenize(parsed_text))
                if content_words:
                    overlap = len(content_words & parsed_words) / len(content_words)
                    found = overlap >= 0.7
        else:
            found = True
        return _bool_result(rule_id, "layout", rule_type, found)

    if rule_type == "order":
        first = rule.get("before", "").lower()
        second = rule.get("after", "").lower()
        if not first or not second:
            return _pass(rule_id, "layout", rule_type)
        text_lower = parsed_text.lower()
        pos_first = _fuzzy_find(first, text_lower)
        pos_second = _fuzzy_find(second, text_lower)
        if pos_first < 0 or pos_second < 0:
            return RuleResult(rule_id=rule_id, category="layout", rule_type=rule_type, passed=False, score=0.0)
        correct = pos_first < pos_second
        return _bool_result(rule_id, "layout", rule_type, correct)

    return RuleResult(rule_id=rule_id, category="layout", rule_type=rule_type, passed=False, score=0.0)


# ── HELPERS ──────────────────────────────────────────────────

def _pass(rule_id: str, category: str, rule_type: str) -> RuleResult:
    return RuleResult(rule_id=rule_id, category=category, rule_type=rule_type, passed=True, score=1.0)


def _bool_result(rule_id: str, category: str, rule_type: str, passed: bool) -> RuleResult:
    return RuleResult(rule_id=rule_id, category=category, rule_type=rule_type, passed=passed, score=1.0 if passed else 0.0)


# ── AGGREGATION ───────────────────────────────────────────────

def compute_dimension_score(results: list[RuleResult], category: str) -> DimensionScore:
    if not results:
        return DimensionScore(category=category, total_rules=0, passed=0, failed=0, score=0.0)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    # Dimension score = pass rate (passed / total), not average of individual scores
    score = passed / len(results)

    by_type: dict[str, dict[str, float]] = {}
    type_groups: dict[str, list[RuleResult]] = {}
    for r in results:
        type_groups.setdefault(r["rule_type"], []).append(r)
    for rt, group in type_groups.items():
        rt_passed = sum(1 for r in group if r["passed"])
        by_type[rt] = {
            "avg_score": round(sum(r.get("score", 0.0) for r in group) / len(group), 4),
            "count": float(len(group)),
            "pass_rate": round(rt_passed / len(group), 4),
        }

    return DimensionScore(
        category=category,
        total_rules=len(results),
        passed=passed,
        failed=failed,
        score=round(score, 4),
        by_type=by_type,
        rule_results=results,
    )
