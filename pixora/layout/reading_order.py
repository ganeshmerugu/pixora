from __future__ import annotations
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
