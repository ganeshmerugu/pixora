from __future__ import annotations
import pytest
from pixora.classifiers.rules import RuleBasedClassifier
from pixora.classifiers.hybrid import HybridClassifier
from pixora.models.pipeline import DocumentProfile


def test_rule_classifier_by_extension():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(filename="report.pdf", first_page_text="")
    assert profile["doc_type"] == "document"
    assert profile["confidence"] > 0


def test_rule_classifier_by_keywords():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(
        filename="file.pdf",
        first_page_text="INVOICE\nInvoice Number: INV-2024-001\nBill To: Acme Corp\nTotal Due: $1,500.00",
    )
    assert profile["doc_type"] == "invoice"
    assert profile["confidence"] >= 0.7


def test_rule_classifier_contract():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(
        filename="file.pdf",
        first_page_text="AGREEMENT\nThis agreement is entered into by and between the parties. Terms and conditions apply. Signature required.",
    )
    assert profile["doc_type"] == "contract"


def test_rule_classifier_receipt():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(
        filename="file.pdf",
        first_page_text="RECEIPT\nStore: Coffee Shop\nTotal: $4.50\nPayment: Credit Card",
    )
    assert profile["doc_type"] == "receipt"


def test_rule_classifier_unknown():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(filename="file.pdf", first_page_text="random gibberish text")
    assert profile["doc_type"] == "document"
    assert profile["confidence"] < 0.5


def test_rule_classifier_spreadsheet():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(filename="data.xlsx", first_page_text="")
    assert profile["doc_type"] == "spreadsheet"


def test_rule_classifier_image():
    clf = RuleBasedClassifier()
    profile = clf.classify_by_rules(filename="scan.png", first_page_text="")
    assert profile["is_scanned"] is True
