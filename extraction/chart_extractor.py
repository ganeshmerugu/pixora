"""Chart data extraction — extracts structured data from chart/graph images.

Uses VLM (vision-language model) when available, otherwise returns description-based markdown.
"""
from __future__ import annotations
import logging
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.ocr.json_utils import extract_json_object

logger = logging.getLogger(__name__)

CHART_EXTRACTION_PROMPT = """Analyze this chart/graph image and extract ALL data precisely.

Return JSON:
{
  "chart_type": "bar|line|pie|scatter|area|stacked_bar|grouped_bar|donut|waterfall",
  "title": "Chart title if visible",
  "axes": {
    "x": {"label": "X axis label", "type": "categorical|numeric|date"},
    "y": {"label": "Y axis label", "type": "numeric", "unit": "$M or % or count"}
  },
  "legend": ["Series A", "Series B"],
  "data_points": [
    {"labels": ["Category", "Series"], "value": 123.4}
  ],
  "annotations": ["any text annotations visible on the chart"],
  "source": "Source attribution if shown"
}

Rules:
- Extract EVERY visible data point, not just a summary
- Include exact numeric values (read from axis/labels)
- Preserve series/category names exactly as shown
- Note any footnotes or source attributions"""

CHART_MARKDOWN_PROMPT = """Describe this chart/graph image in detail as markdown.

Include:
1. Chart type and title
2. Axes labels and ranges
3. All data series with their values
4. Key trends or patterns
5. Any annotations, footnotes, or source notes

Format as structured markdown with headers and bullet points.
Be precise with numbers — read them from the chart, don't estimate."""


class ChartData(TypedDict, total=False):
    chart_type: str
    title: str
    axes: dict[str, Any]
    legend: list[str]
    data_points: list[dict[str, Any]]
    annotations: list[str]
    source: str
    markdown: str
    raw_text: str


async def extract_chart_data(
    image_bytes: bytes,
    vlm_provider: Any = None,
) -> ChartData:
    if vlm_provider and hasattr(vlm_provider, "analyze_image"):
        try:
            resp = await vlm_provider.analyze_image(image_bytes, CHART_EXTRACTION_PROMPT)
            content = resp.get("content", "")
            parsed = extract_json_object(content)
            if parsed and parsed.get("data_points"):
                md = _chart_data_to_markdown(parsed)
                parsed["markdown"] = md
                parsed["raw_text"] = content
                return ChartData(**parsed)
        except Exception as exc:
            logger.warning("chart_extractor: structured extraction failed: %s", exc)

        try:
            resp = await vlm_provider.analyze_image(image_bytes, CHART_MARKDOWN_PROMPT)
            content = resp.get("content", "")
            if content.strip():
                return ChartData(markdown=content, raw_text=content)
        except Exception as exc:
            logger.warning("chart_extractor: markdown extraction failed: %s", exc)

    return ChartData(markdown="[Chart image — requires VLM for data extraction]", raw_text="")


def _chart_data_to_markdown(data: dict) -> str:
    lines: list[str] = []

    title = data.get("title", "")
    chart_type = data.get("chart_type", "chart")
    if title:
        lines.append(f"### {title}")
    lines.append(f"*{chart_type.replace('_', ' ').title()} Chart*")
    lines.append("")

    axes = data.get("axes", {})
    if axes:
        x = axes.get("x", {})
        y = axes.get("y", {})
        if x.get("label"):
            lines.append(f"**X-axis:** {x['label']}")
        if y.get("label"):
            unit = f" ({y['unit']})" if y.get("unit") else ""
            lines.append(f"**Y-axis:** {y['label']}{unit}")
        lines.append("")

    legend = data.get("legend", [])
    if legend:
        lines.append(f"**Series:** {', '.join(legend)}")
        lines.append("")

    data_points = data.get("data_points", [])
    if data_points:
        all_labels = set()
        for dp in data_points:
            for lbl in dp.get("labels", []):
                all_labels.add(lbl)

        lines.append("| " + " | ".join(["Category", "Value"]) + " |")
        lines.append("| --- | --- |")
        for dp in data_points:
            labels = ", ".join(str(l) for l in dp.get("labels", []))
            value = dp.get("value", "")
            lines.append(f"| {labels} | {value} |")
        lines.append("")

    annotations = data.get("annotations", [])
    for ann in annotations:
        lines.append(f"*Note: {ann}*")

    source = data.get("source", "")
    if source:
        lines.append(f"*Source: {source}*")

    return "\n".join(lines)


def chart_data_to_text(data: ChartData) -> str:
    if data.get("markdown"):
        return data["markdown"]
    if data.get("data_points"):
        return _chart_data_to_markdown(dict(data))
    return data.get("raw_text", "")
