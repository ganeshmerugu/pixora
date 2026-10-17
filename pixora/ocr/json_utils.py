from __future__ import annotations
import json
import re


_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict:
    m = _CODE_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    depth = 0
    start = -1
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = -1

    cleaned = text.replace("\\'", "'").replace('\\"', '"')
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    return {}


def extract_json_array(text: str) -> list:
    m = _CODE_BLOCK_RE.search(text)
    if m:
        try:
            result = json.loads(m.group(1))
            return result if isinstance(result, list) else [result]
        except json.JSONDecodeError:
            pass

    depth = 0
    start = -1
    for i, c in enumerate(text):
        if c == "[":
            if depth == 0:
                start = i
            depth += 1
        elif c == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    result = json.loads(text[start:i + 1])
                    return result if isinstance(result, list) else [result]
                except json.JSONDecodeError:
                    start = -1

    obj = extract_json_object(text)
    return [obj] if obj else []
