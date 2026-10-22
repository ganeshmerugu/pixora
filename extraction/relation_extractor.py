"""Relation extraction — graph-based key-value linking.

Builds a spatial adjacency graph where nodes are text regions and edges
represent functional associations. Links keys to values using:
  score(k,v) = alpha * spatial_proximity + beta * alignment + gamma * semantic
"""
from __future__ import annotations
import math
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.models.document import BoundingBox


class TextNode(TypedDict, total=False):
    id: Required[str]
    text: Required[str]
    bbox: Required[BoundingBox]
    node_type: str
    entity_label: str
    confidence: float


class KeyValuePair(TypedDict, total=False):
    key_node: Required[str]
    value_node: Required[str]
    key_text: Required[str]
    value_text: Required[str]
    score: Required[float]
    relation_type: str
    section: str


class RelationEdge(TypedDict, total=False):
    source: Required[str]
    target: Required[str]
    proximity: float
    alignment: float
    semantic: float
    score: float
    direction: str


ALPHA_PROXIMITY = 0.4
BETA_ALIGNMENT = 0.35
GAMMA_SEMANTIC = 0.25

KEY_INDICATORS = frozenset({
    "name", "date", "number", "amount", "total", "address", "phone",
    "email", "fax", "id", "ref", "account", "invoice", "order",
    "tax", "subtotal", "discount", "balance", "due", "payment",
    "vendor", "customer", "company", "from", "to", "bill",
    "ship", "description", "quantity", "price", "rate", "unit",
})

MAX_DISTANCE_RATIO = 0.3


def _bbox_center(bbox: BoundingBox) -> tuple[float, float]:
    return bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2


def _bbox_right(bbox: BoundingBox) -> float:
    return bbox["x"] + bbox["width"]


def _bbox_bottom(bbox: BoundingBox) -> float:
    return bbox["y"] + bbox["height"]


def _euclidean(a: BoundingBox, b: BoundingBox) -> float:
    cx1, cy1 = _bbox_center(a)
    cx2, cy2 = _bbox_center(b)
    return math.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)


def _is_key_like(text: str) -> bool:
    lower = text.lower().strip().rstrip(":.")
    words = lower.split()
    return any(w in KEY_INDICATORS for w in words) or text.endswith(":")


def _alignment_score(key_bbox: BoundingBox, val_bbox: BoundingBox) -> float:
    key_cy = key_bbox["y"] + key_bbox["height"] / 2
    val_cy = val_bbox["y"] + val_bbox["height"] / 2
    y_diff = abs(key_cy - val_cy)

    h_aligned = max(0, 1.0 - y_diff / max(key_bbox["height"], 1))

    key_cx = key_bbox["x"] + key_bbox["width"] / 2
    val_cx = val_bbox["x"] + val_bbox["width"] / 2
    x_diff = abs(key_cx - val_cx)
    v_aligned = max(0, 1.0 - x_diff / max(key_bbox["width"], 1))

    if val_bbox["x"] >= _bbox_right(key_bbox) - 5:
        return 0.7 * h_aligned + 0.3
    if val_bbox["y"] >= _bbox_bottom(key_bbox) - 5:
        return 0.5 * v_aligned + 0.2
    return max(h_aligned, v_aligned) * 0.5


def _semantic_score(key_text: str, val_text: str) -> float:
    score = 0.0
    if _is_key_like(key_text) and not _is_key_like(val_text):
        score += 0.5
    if key_text.endswith(":"):
        score += 0.3
    if any(c.isdigit() for c in val_text):
        score += 0.2
    return min(score, 1.0)


class RelationExtractor:
    def __init__(
        self,
        alpha: float = ALPHA_PROXIMITY,
        beta: float = BETA_ALIGNMENT,
        gamma: float = GAMMA_SEMANTIC,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def build_graph(self, nodes: list[TextNode]) -> list[RelationEdge]:
        if not nodes:
            return []

        all_bboxes = [n["bbox"] for n in nodes]
        max_dim = max(
            max(b["x"] + b["width"] for b in all_bboxes),
            max(b["y"] + b["height"] for b in all_bboxes),
            1,
        )
        max_distance = max_dim * MAX_DISTANCE_RATIO

        edges: list[RelationEdge] = []
        for i, src in enumerate(nodes):
            for j, tgt in enumerate(nodes):
                if i == j:
                    continue

                dist = _euclidean(src["bbox"], tgt["bbox"])
                if dist > max_distance:
                    continue

                proximity = max(0, 1.0 - dist / max_distance)
                alignment = _alignment_score(src["bbox"], tgt["bbox"])
                semantic = _semantic_score(src["text"], tgt["text"])

                score = (
                    self.alpha * proximity
                    + self.beta * alignment
                    + self.gamma * semantic
                )

                if tgt["bbox"]["x"] >= _bbox_right(src["bbox"]) - 5:
                    direction = "right"
                elif tgt["bbox"]["y"] >= _bbox_bottom(src["bbox"]) - 5:
                    direction = "below"
                else:
                    direction = "other"

                edges.append(RelationEdge(
                    source=src["id"],
                    target=tgt["id"],
                    proximity=round(proximity, 4),
                    alignment=round(alignment, 4),
                    semantic=round(semantic, 4),
                    score=round(score, 4),
                    direction=direction,
                ))

        return edges

    def link(self, nodes: list[TextNode]) -> list[KeyValuePair]:
        edges = self.build_graph(nodes)
        node_map = {n["id"]: n for n in nodes}

        key_nodes = [n for n in nodes if _is_key_like(n["text"])]

        used_values: set[str] = set()
        pairs: list[KeyValuePair] = []

        for key_node in key_nodes:
            candidates = [
                e for e in edges
                if e["source"] == key_node["id"]
                and e["target"] not in used_values
                and e["direction"] in ("right", "below")
                and not _is_key_like(node_map[e["target"]]["text"])
            ]

            if not candidates:
                continue

            best = max(candidates, key=lambda e: e["score"])
            val_node = node_map[best["target"]]

            pairs.append(KeyValuePair(
                key_node=key_node["id"],
                value_node=val_node["id"],
                key_text=key_node["text"].strip().rstrip(":"),
                value_text=val_node["text"].strip(),
                score=best["score"],
                relation_type=best["direction"],
            ))
            used_values.add(val_node["id"])

        return sorted(pairs, key=lambda p: -p["score"])

    def group_sections(self, pairs: list[KeyValuePair], nodes: list[TextNode]) -> dict[str, list[KeyValuePair]]:
        if not pairs or not nodes:
            return {}

        node_map = {n["id"]: n for n in nodes}
        sections: dict[str, list[KeyValuePair]] = {}

        y_positions = sorted(set(
            node_map[p["key_node"]]["bbox"]["y"]
            for p in pairs
            if p["key_node"] in node_map
        ))

        if len(y_positions) <= 1:
            return {"main": pairs}

        gaps = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions) - 1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 50
        section_threshold = avg_gap * 2.5

        current_section = 0
        section_starts: dict[int, float] = {0: y_positions[0]}

        for i in range(1, len(y_positions)):
            if y_positions[i] - y_positions[i-1] > section_threshold:
                current_section += 1
                section_starts[current_section] = y_positions[i]

        for pair in pairs:
            if pair["key_node"] not in node_map:
                continue
            key_y = node_map[pair["key_node"]]["bbox"]["y"]
            section_idx = 0
            for idx, start_y in sorted(section_starts.items()):
                if key_y >= start_y:
                    section_idx = idx
            section_name = f"section_{section_idx}"
            sections.setdefault(section_name, []).append(pair)

        return sections
