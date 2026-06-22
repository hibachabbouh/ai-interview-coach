
from typing import Optional

from json_repair import repair_json


def safe_parse_llm_json(text: Optional[str]) -> Optional[dict]:

    if not text or not text.strip():
        raise ValueError("Empty LLM response — cannot parse JSON")

    result = repair_json(text, return_objects=True)

    if result == "" or result is None:
        raise ValueError(f"No JSON found in LLM response: {text[:200]!r}")

    if not isinstance(result, dict):
        raise ValueError(
            f"Expected a JSON object, got {type(result).__name__}: "
            f"{str(result)[:200]!r}"
        )

    return result
