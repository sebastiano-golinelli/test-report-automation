"""Optional AI step: read reports written in free text with Claude.

The model returns structured data validated by a Pydantic schema, together with the exact quote it
took each value from. Every quote and every number is then checked against the document text: a
value that cannot be found literally in the report is discarded and the field goes to manual review.
"""

import re

from pydantic import BaseModel, Field

from .extract import ID_REGEX
from .specs import SPECS, normalize_material

MODEL = "claude-opus-5-5"
SYSTEM = (
    "You extract tensile test results from a laboratory report. Use only what the report states. "
    "If a value is not stated, return null for it and an empty quote: never estimate. "
    "Stresses must be in MPa; if the report uses another unit, convert and keep the original wording in the quote. "
    "Each quote must be copied exactly from the report, word for word."
)


class Value(BaseModel):
    value: float | None = Field(description="The number, or null if the report does not state it")
    quote: str = Field(description="Exact words from the report containing the number, or empty")


class Extraction(BaseModel):
    specimen_id: str | None
    material: str | None = Field(description="Material or alloy designation as written in the report")
    test_date: str | None = Field(description="Test date as YYYY-MM-DD, or null")
    yield_strength_mpa: Value = Field(description="Yield / proof stress (0.2% offset, upper yield point)")
    tensile_strength_mpa: Value = Field(description="Ultimate tensile strength, maximum stress")
    elongation_pct: Value = Field(description="Elongation after fracture, in percent")


def _norm(s):
    return " ".join(s.split()).lower()


def _supported(v: Value, text):
    """True if the quote is in the document and contains the number."""
    if v.value is None or not v.quote:
        return False
    if _norm(v.quote) not in _norm(text):
        return False
    numbers = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", v.quote)}
    return v.value in numbers


def ai_complete(rec, client):
    """Fill the fields of a free-text Record with Claude. Returns a list of notes for the review sheet."""
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Materials we test: {', '.join(SPECS)}.\n\nReport:\n{rec.text}"}],
        output_format=Extraction,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return ["AI declined to read this report"]
    data: Extraction = response.parsed_output
    notes = []
    if not rec.specimen_id and data.specimen_id and re.fullmatch(ID_REGEX, data.specimen_id):
        rec.specimen_id = data.specimen_id
    rec.material = rec.material or normalize_material(data.material) or data.material
    if data.test_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", data.test_date):
        rec.test_date = data.test_date
    for name, v in (("yield_mpa", data.yield_strength_mpa), ("uts_mpa", data.tensile_strength_mpa),
                    ("elongation_pct", data.elongation_pct)):
        if _supported(v, rec.text):
            setattr(rec, name, v.value)
            rec.evidence[name] = v.quote
        elif v.value is not None:
            notes.append(f"AI value for {name} ({v.value}) not found in the report text: discarded")
    rec.method = "AI"
    return notes
