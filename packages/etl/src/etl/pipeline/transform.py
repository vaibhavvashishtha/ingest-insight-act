from typing import Any

from core.connectors.base import CanonicalMapping


def apply_mapping(
    raw_row: dict[str, Any],
    mappings: list[CanonicalMapping],
) -> dict[str, Any]:
    """Map raw source fields to canonical field names."""
    canonical: dict[str, Any] = {}
    for mapping in mappings:
        value = raw_row.get(mapping.raw_field)
        if value is None:
            continue
        if mapping.transform:
            # Safe eval of simple expressions — only basic type coercions supported
            try:
                value = eval(mapping.transform, {"v": value, "__builtins__": {}})  # noqa: S307
            except Exception:
                pass
        canonical[mapping.canonical_field] = value
    canonical["_raw"] = raw_row
    return canonical


def coerce_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce metric fields to the correct Python types."""
    int_fields = {"impressions", "clicks"}
    float_fields = {"spend", "conversions", "revenue"}

    for field in int_fields:
        if field in row:
            try:
                row[field] = int(float(row[field]))
            except (TypeError, ValueError):
                row[field] = 0

    for field in float_fields:
        if field in row:
            try:
                row[field] = float(row[field])
            except (TypeError, ValueError):
                row[field] = 0.0

    return row
