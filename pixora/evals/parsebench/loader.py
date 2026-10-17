"""ParseBench dataset loader — downloads from HuggingFace and organizes by category."""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any
from typing_extensions import Required, TypedDict

logger = logging.getLogger(__name__)

DATASET_ID = "llamaindex/ParseBench"
CATEGORIES = ["chart", "table", "text_content", "text_formatting", "layout"]

CACHE_DIR = os.environ.get(
    "PIXORA_PARSEBENCH_CACHE",
    str(Path.home() / ".cache" / "pixora" / "parsebench"),
)


class ParseBenchRule(TypedDict, total=False):
    pdf: Required[str]
    category: Required[str]
    id: Required[str]
    type: Required[str]
    rule: dict[str, Any]
    page: int | None
    expected_markdown: str | None
    tags: list[str]


class ParseBenchDataset:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self._rules: dict[str, list[ParseBenchRule]] = {}
        self._loaded = False

    def load(self, categories: list[str] | None = None, max_per_category: int = 0) -> None:
        cats = categories or CATEGORIES
        try:
            from datasets import load_dataset
            logger.info("parsebench: loading dataset from HuggingFace...")
            ds = load_dataset(DATASET_ID, cache_dir=self.cache_dir)

            split_map = {
                "chart": "chart",
                "table": "table",
                "text_content": "text_content",
                "text_formatting": "text_formatting",
                "layout": "layout",
            }

            for cat in cats:
                split_name = split_map.get(cat, cat)
                if split_name in ds:
                    all_data = ds[split_name]
                elif "parse-bench" in ds:
                    all_data = ds["parse-bench"]
                else:
                    all_data = ds[list(ds.keys())[0]]

                rules: list[ParseBenchRule] = []
                for row in all_data:
                    row_cat = row.get("category", cat)
                    if row_cat != cat and split_name not in ds:
                        continue
                    rule_data = row.get("rule", "{}")
                    if isinstance(rule_data, str):
                        try:
                            rule_data = json.loads(rule_data)
                        except json.JSONDecodeError:
                            rule_data = {}

                    rules.append(ParseBenchRule(
                        pdf=row.get("pdf", ""),
                        category=cat,
                        id=row.get("id", ""),
                        type=row.get("type", ""),
                        rule=rule_data,
                        page=row.get("page"),
                        expected_markdown=row.get("expected_markdown"),
                        tags=row.get("tags", []),
                    ))
                    if max_per_category and len(rules) >= max_per_category:
                        break

                self._rules[cat] = rules
                logger.info("parsebench: loaded %d rules for category '%s'", len(rules), cat)

            self._loaded = True

        except ImportError:
            logger.error("parsebench: 'datasets' package required. Install: pip install datasets")
            raise
        except Exception as exc:
            logger.error("parsebench: failed to load dataset: %s", exc)
            raise

    def load_from_jsonl(self, directory: str, categories: list[str] | None = None) -> None:
        cats = categories or CATEGORIES
        for cat in cats:
            filepath = os.path.join(directory, f"{cat}.jsonl")
            if not os.path.exists(filepath):
                logger.warning("parsebench: file not found: %s", filepath)
                continue

            rules: list[ParseBenchRule] = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    rule_data = row.get("rule", {})
                    if isinstance(rule_data, str):
                        try:
                            rule_data = json.loads(rule_data)
                        except json.JSONDecodeError:
                            rule_data = {}

                    rules.append(ParseBenchRule(
                        pdf=row.get("pdf", ""),
                        category=cat,
                        id=row.get("id", ""),
                        type=row.get("type", ""),
                        rule=rule_data,
                        page=row.get("page"),
                        expected_markdown=row.get("expected_markdown"),
                        tags=row.get("tags", []),
                    ))
            self._rules[cat] = rules
            logger.info("parsebench: loaded %d rules from %s", len(rules), filepath)

        self._loaded = True

    def get_rules(self, category: str) -> list[ParseBenchRule]:
        return self._rules.get(category, [])

    def get_all_rules(self) -> list[ParseBenchRule]:
        all_rules: list[ParseBenchRule] = []
        for rules in self._rules.values():
            all_rules.extend(rules)
        return all_rules

    def get_unique_pdfs(self, category: str | None = None) -> list[str]:
        seen: set[str] = set()
        pdfs: list[str] = []
        rules = self.get_rules(category) if category else self.get_all_rules()
        for r in rules:
            if r["pdf"] not in seen:
                seen.add(r["pdf"])
                pdfs.append(r["pdf"])
        return pdfs

    def get_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {"loaded": self._loaded, "categories": {}}
        total = 0
        for cat, rules in self._rules.items():
            pdfs = set(r["pdf"] for r in rules)
            stats["categories"][cat] = {
                "rules": len(rules),
                "unique_pdfs": len(pdfs),
                "types": list(set(r["type"] for r in rules)),
            }
            total += len(rules)
        stats["total_rules"] = total
        return stats
