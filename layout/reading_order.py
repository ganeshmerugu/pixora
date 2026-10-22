from __future__ import annotations
import heapq
from pixora.layout.detector import DetectedZone


def sort_by_reading_order(zones: list[DetectedZone], num_columns: int = 1) -> list[DetectedZone]:
    if not zones:
        return []

    type_priority = {"HEADER": 0, "TEXT": 1, "TABLE": 1, "FIGURE_CAPTION": 2, "FOOTER": 3}

    if num_columns <= 1:
        return sorted(zones, key=lambda z: (
            type_priority.get(z["zone_type"], 1),
            z["bbox"]["y"],
            z["bbox"]["x"],
        ))

    headers = [z for z in zones if z["zone_type"] == "HEADER"]
    footers = [z for z in zones if z["zone_type"] == "FOOTER"]
    body = [z for z in zones if z["zone_type"] not in ("HEADER", "FOOTER")]

    if not body:
        return sorted(headers, key=lambda z: z["bbox"]["y"]) + sorted(footers, key=lambda z: z["bbox"]["y"])

    page_width = max(z["bbox"]["x"] + z["bbox"]["width"] for z in body) if body else 1
    col_width = page_width / num_columns

    def column_index(zone: DetectedZone) -> int:
        center_x = zone["bbox"]["x"] + zone["bbox"]["width"] / 2
        return min(int(center_x / col_width), num_columns - 1)

    body_sorted = sorted(body, key=lambda z: (column_index(z), z["bbox"]["y"]))

    result = sorted(headers, key=lambda z: z["bbox"]["y"])
    result.extend(body_sorted)
    result.extend(sorted(footers, key=lambda z: z["bbox"]["y"]))
    return result


def sort_by_spatial_proximity(
    zones: list[DetectedZone],
    page_width: float = 0,
    page_height: float = 0,
) -> list[DetectedZone]:
    if len(zones) < 3:
        return sort_by_reading_order(zones)

    headers = [z for z in zones if z["zone_type"] == "HEADER"]
    footers = [z for z in zones if z["zone_type"] == "FOOTER"]
    body = [z for z in zones if z["zone_type"] not in ("HEADER", "FOOTER")]

    if len(body) < 2:
        ordered_body = body
    else:
        ordered_body = _agglomerative_order(body, page_width, page_height)

    result = sorted(headers, key=lambda z: z["bbox"]["y"])
    result.extend(ordered_body)
    result.extend(sorted(footers, key=lambda z: z["bbox"]["y"]))
    return result


def _bbox_area(z: DetectedZone) -> float:
    return z["bbox"]["width"] * z["bbox"]["height"]


def _bounding_area(a: DetectedZone, b: DetectedZone) -> float:
    x0 = min(a["bbox"]["x"], b["bbox"]["x"])
    y0 = min(a["bbox"]["y"], b["bbox"]["y"])
    x1 = max(a["bbox"]["x"] + a["bbox"]["width"], b["bbox"]["x"] + b["bbox"]["width"])
    y1 = max(a["bbox"]["y"] + a["bbox"]["height"], b["bbox"]["y"] + b["bbox"]["height"])
    return (x1 - x0) * (y1 - y0)


def _whitespace_distance(a: DetectedZone, b: DetectedZone) -> float:
    return _bounding_area(a, b) - _bbox_area(a) - _bbox_area(b)


def _zones_between(zones_set: set[str], all_zones: dict[str, DetectedZone], a: DetectedZone, b: DetectedZone) -> bool:
    x0 = min(a["bbox"]["x"], b["bbox"]["x"])
    y0 = min(a["bbox"]["y"], b["bbox"]["y"])
    x1 = max(a["bbox"]["x"] + a["bbox"]["width"], b["bbox"]["x"] + b["bbox"]["width"])
    y1 = max(a["bbox"]["y"] + a["bbox"]["height"], b["bbox"]["y"] + b["bbox"]["height"])

    a_id = a["zone_id"]
    b_id = b["zone_id"]

    for zid in zones_set:
        if zid == a_id or zid == b_id:
            continue
        z = all_zones[zid]
        zx = z["bbox"]["x"]
        zy = z["bbox"]["y"]
        zx2 = zx + z["bbox"]["width"]
        zy2 = zy + z["bbox"]["height"]
        if zx < x1 and zx2 > x0 and zy < y1 and zy2 > y0:
            return True
    return False


class _GroupNode:
    __slots__ = ("zone_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "children")

    def __init__(self, zone: DetectedZone):
        self.zone_id = zone["zone_id"]
        self.bbox_x = zone["bbox"]["x"]
        self.bbox_y = zone["bbox"]["y"]
        self.bbox_w = zone["bbox"]["width"]
        self.bbox_h = zone["bbox"]["height"]
        self.children: list[_GroupNode] = []

    def as_zone(self) -> DetectedZone:
        from pixora.models.document import BoundingBox
        return DetectedZone(
            zone_id=self.zone_id,
            zone_type="GROUP",
            bbox=BoundingBox(x=self.bbox_x, y=self.bbox_y, width=self.bbox_w, height=self.bbox_h),
        )


def _agglomerative_order(body: list[DetectedZone], page_width: float, page_height: float) -> list[DetectedZone]:
    zone_map = {z["zone_id"]: z for z in body}
    active: set[str] = set(zone_map.keys())
    nodes: dict[str, _GroupNode] = {z["zone_id"]: _GroupNode(z) for z in body}

    heap: list[tuple[float, str, str]] = []
    body_list = list(body)
    for i in range(len(body_list)):
        for j in range(i + 1, len(body_list)):
            d = _whitespace_distance(body_list[i], body_list[j])
            heapq.heappush(heap, (d, body_list[i]["zone_id"], body_list[j]["zone_id"]))

    group_counter = 0
    while len(active) > 1 and heap:
        dist, id_a, id_b = heapq.heappop(heap)
        if id_a not in active or id_b not in active:
            continue

        za = zone_map[id_a]
        zb = zone_map[id_b]
        if _zones_between(active, zone_map, za, zb):
            continue

        group_counter += 1
        from pixora.models.document import BoundingBox
        gx = min(za["bbox"]["x"], zb["bbox"]["x"])
        gy = min(za["bbox"]["y"], zb["bbox"]["y"])
        gx2 = max(za["bbox"]["x"] + za["bbox"]["width"], zb["bbox"]["x"] + zb["bbox"]["width"])
        gy2 = max(za["bbox"]["y"] + za["bbox"]["height"], zb["bbox"]["y"] + zb["bbox"]["height"])

        gid = f"group_{group_counter}"
        group_zone = DetectedZone(
            zone_id=gid, zone_type="GROUP",
            bbox=BoundingBox(x=gx, y=gy, width=gx2 - gx, height=gy2 - gy),
        )
        zone_map[gid] = group_zone

        gnode = _GroupNode(group_zone)
        gnode.children = [nodes[id_a], nodes[id_b]]
        nodes[gid] = gnode

        active.discard(id_a)
        active.discard(id_b)
        active.add(gid)

        for other_id in active:
            if other_id == gid:
                continue
            d = _whitespace_distance(group_zone, zone_map[other_id])
            heapq.heappush(heap, (d, gid, other_id))

    root_ids = list(active)
    result: list[DetectedZone] = []
    for rid in sorted(root_ids, key=lambda r: (zone_map[r]["bbox"]["y"], zone_map[r]["bbox"]["x"])):
        _flatten_node(nodes[rid], result, {z["zone_id"]: z for z in body})
    return result


def _flatten_node(node: _GroupNode, out: list[DetectedZone], leaf_map: dict[str, DetectedZone]) -> None:
    if not node.children:
        if node.zone_id in leaf_map:
            out.append(leaf_map[node.zone_id])
        return
    sorted_children = sorted(node.children, key=lambda c: (c.bbox_y, c.bbox_x))
    for child in sorted_children:
        _flatten_node(child, out, leaf_map)
