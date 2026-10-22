"""Rule-based extraction from the PDF reports.

Each parser returns a Record. Fields it cannot read stay None and are listed in `missing`:
nothing is guessed. Reports in free text are recognised, read as far as rules allow, and handed to
the optional AI step (see ai.py) or to manual review.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pdfplumber

from .specs import normalize_material

KSI_TO_MPA = 6.894757
FIELDS = ("specimen_id", "material", "yield_mpa", "uts_mpa", "elongation_pct", "test_date")
ID_REGEX = r"[A-Z]{2}-\d{3}"                  # specimen IDs such as TI-203
ID_PATTERN = rf"\b({ID_REGEX})\b"


@dataclass
class Record:
    file: str
    layout: str
    specimen_id: str | None = None
    material: str | None = None
    yield_mpa: float | None = None
    uts_mpa: float | None = None
    elongation_pct: float | None = None
    test_date: str | None = None              # ISO yyyy-mm-dd
    remarks: str = ""
    method: str = "rules"                     # "rules", "AI" or "rules (incomplete)"
    evidence: dict = field(default_factory=dict)   # AI only: field -> quote from the document
    text: str = ""

    @property
    def missing(self):
        return [f for f in FIELDS if getattr(self, f) in (None, "")]


def read_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        tables = [t for page in pdf.pages for t in page.extract_tables()]
    return text, tables


def _number(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def parse_alpha(text, rec):
    def line(label):
        m = re.search(rf"^{label}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else None

    rec.specimen_id = line("Specimen ID")
    rec.material = normalize_material(line("Material")) or line("Material")
    rec.test_date = line("Test date")
    rec.yield_mpa = _number(r"Yield strength[^:]*:\s*([\d.]+)\s*MPa", text)
    rec.uts_mpa = _number(r"Tensile strength[^:]*:\s*([\d.]+)\s*MPa", text)
    rec.elongation_pct = _number(r"Elongation[^:]*:\s*([\d.]+)\s*%", text)
    rec.remarks = line("Remarks") or ""


def parse_beta(tables, rec):
    rows = {r[0].strip().lower(): (r[1] or "").strip() for t in tables for r in t if r and r[0]}
    units = {r[0].strip().lower(): (r[2] or "").strip().lower() for t in tables for r in t if r and len(r) > 2 and r[0]}

    def stress(key):
        value = rows.get(key)
        if not value:
            return None
        v = float(value)
        return round(v * KSI_TO_MPA, 1) if units.get(key) == "ksi" else v

    rec.specimen_id = rows.get("specimen") or None
    rec.material = normalize_material(rows.get("alloy / grade")) or rows.get("alloy / grade")
    date = rows.get("date tested")
    rec.test_date = datetime.strptime(date, "%m/%d/%Y").date().isoformat() if date else None
    rec.yield_mpa = stress("0.2% offset yield strength")
    rec.uts_mpa = stress("ultimate tensile strength")
    elong = rows.get("elongation in 2 in.")
    rec.elongation_pct = float(elong) if elong else None
    rec.remarks = rows.get("notes", "")


def parse_free_text(text, rec):
    """Only what a rule can read safely: the specimen ID and a known material name.

    The numbers are written in prose ("plastic deformation began at roughly 905 MPa"), and guessing
    which number is the yield strength with a regex is exactly the kind of silent error we avoid.
    """
    m = re.search(ID_PATTERN, text)
    rec.specimen_id = m.group(1) if m else None
    rec.material = normalize_material(text)
    rec.method = "rules (incomplete)"


def extract(path):
    path = Path(path)
    text, tables = read_pdf(path)
    head = text[:200].upper()
    if "LAB ALPHA" in head:
        rec = Record(path.name, "Lab Alpha (key-value)", text=text)
        parse_alpha(text, rec)
    elif "BETA TESTING SERVICES" in head:
        rec = Record(path.name, "Beta Testing (table, ksi)", text=text)
        parse_beta(tables, rec)
    else:
        rec = Record(path.name, "Free text", text=text)
        parse_free_text(text, rec)
    return rec
