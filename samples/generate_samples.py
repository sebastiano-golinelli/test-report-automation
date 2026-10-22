"""Generate the synthetic tensile-test reports used by the demo.

Three fictional labs, three layouts:
  - Lab Alpha:      key-value lines, MPa, ISO dates
  - Beta Testing:   a table, US units (ksi) and US dates
  - Gamma Metrology: free text written by a technician (no fixed fields)
Some reports contain deliberate problems (missing value, impossible value, a resubmitted
specimen, a result below the material specification) so the pipeline has something to catch.

All data is invented. Run:  python samples/generate_samples.py
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).parent
OUT = HERE / "pdfs"
KSI = 6.894757                     # MPa per ksi

ALPHA = [
    dict(id="AL-001", material="Al 6061-T6", yield_mpa=276, uts_mpa=311, elong=12.4, date="2026-09-14",
         remarks="Fracture inside gauge length. Nothing to report."),
    dict(id="AL-002", material="Al 6061-T6", yield_mpa=281, uts_mpa=316, elong=11.8, date="2026-09-14",
         remarks="Slight necking, fracture at 45 degrees."),
    dict(id="AL-003", material="Al 6061-T6", yield_mpa=262, uts_mpa=294, elong=6.5, date="2026-09-15",
         remarks="Porosity visible on fracture surface, low ductility."),
    dict(id="ST-101", material="S355JR", yield_mpa=381, uts_mpa=528, elong=26.0, date="2026-09-16",
         remarks="Cup-and-cone fracture."),
    dict(id="ST-102", material="S355JR", yield_mpa=372, uts_mpa=515, elong=24.5, date="2026-09-16",
         remarks="Cup-and-cone fracture."),
]
BETA = [  # values in ksi, dates MM/DD/YYYY
    dict(id="AL-004", material="Al 6061-T6", yield_ksi=40.2, uts_ksi=45.1, elong=12.0, date="09/18/2026",
         remarks="Normal ductile failure."),
    dict(id="ST-103", material="S355JR", yield_ksi=54.0, uts_ksi=76.3, elong=None, date="09/18/2026",
         remarks="Extensometer slipped, elongation not recorded."),
    dict(id="TI-201", material="Ti-6Al-4V", yield_ksi=133.5, uts_ksi=143.0, elong=14.0, date="09/21/2026",
         remarks="Normal ductile failure."),
    dict(id="TI-202", material="Ti-6Al-4V", yield_ksi=145.6, uts_ksi=139.2, elong=13.0, date="09/21/2026",
         remarks="Values transcribed from handwritten sheet."),
]
GAMMA = [
    dict(id="TI-203", material="Ti-6Al-4V", yield_mpa=905, uts_mpa=968, elong=13.5, date="2026-10-03",
         text=("Report on specimen TI-203, machined from Ti-6Al-4V bar stock. The test was carried out on "
               "3 October 2026 at room temperature. Plastic deformation began at roughly 905 MPa (0.2% offset) "
               "and the specimen failed at a peak stress of 968 MPa, after stretching by 13.5 percent of its "
               "gauge length. The fracture surface showed a classic cup-and-cone pattern.")),
    dict(id="ST-104", material="S355JR", yield_mpa=366, uts_mpa=502, elong=25.0, date="2026-10-03",
         text=("Specimen ST-104 (structural steel, grade S355JR) was pulled to failure on 3 October 2026. "
               "The upper yield point was observed at 366 MPa; the curve then rose to a maximum of 502 MPa "
               "before necking. Total elongation after fracture: 25 percent. No anomalies.")),
    dict(id="AL-005", material="Al 6061-T6", yield_mpa=288, uts_mpa=322, elong=10.9, date="2026-10-06",
         text=("On 6 October 2026 we tested AL-005, an Al 6061-T6 extrusion. Proof stress at 0.2% plastic "
               "strain came out at 288 MPa, while ultimate strength reached 322 MPa. Elongation measured on "
               "the broken halves was 10.9 percent.")),
]
RESUBMITTED = dict(ALPHA[3], date="2026-09-23", remarks="Resubmitted after re-test request.")   # ST-101 again

styles = getSampleStyleSheet()


def _doc(path, title, subtitle):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm)
    head = [Paragraph(title, styles["Title"]), Paragraph(subtitle, styles["Normal"]), Spacer(1, 8 * mm)]
    return doc, head


def alpha_pdf(s, path):
    doc, story = _doc(path, "LAB ALPHA - Tensile Test Certificate", "ISO 6892-1, method B, room temperature")
    for line in (f"Specimen ID: {s['id']}", f"Material: {s['material']}", f"Test date: {s['date']}",
                 f"Yield strength (Rp0.2): {s['yield_mpa']} MPa", f"Tensile strength (Rm): {s['uts_mpa']} MPa",
                 f"Elongation at break (A): {s['elong']} %", f"Remarks: {s['remarks']}"):
        story += [Paragraph(line, styles["Normal"]), Spacer(1, 3 * mm)]
    doc.build(story)


def beta_pdf(s, path):
    doc, story = _doc(path, "BETA TESTING SERVICES", "Tension test report - ASTM E8/E8M")
    rows = [["Parameter", "Value", "Unit"],
            ["Specimen", s["id"], ""], ["Alloy / grade", s["material"], ""], ["Date tested", s["date"], ""],
            ["0.2% offset yield strength", f"{s['yield_ksi']:.1f}", "ksi"],
            ["Ultimate tensile strength", f"{s['uts_ksi']:.1f}", "ksi"],
            ["Elongation in 2 in.", "" if s["elong"] is None else f"{s['elong']:.1f}", "%"],
            ["Notes", s["remarks"], ""]]
    t = Table(rows, colWidths=[65 * mm, 75 * mm, 20 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde3ee")),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]))
    story.append(t)
    doc.build(story)


def gamma_pdf(s, path):
    doc, story = _doc(path, "Gamma Metrology", "Mechanical testing - technician's report")
    story.append(Paragraph(s["text"], styles["BodyText"]))
    doc.build(story)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.pdf"):
        old.unlink()
    truth = []
    for s in ALPHA:
        alpha_pdf(s, OUT / f"alpha_{s['id']}.pdf")
        truth.append(dict(file=f"alpha_{s['id']}.pdf", id=s["id"], material=s["material"], yield_mpa=s["yield_mpa"],
                          uts_mpa=s["uts_mpa"], elongation_pct=s["elong"], test_date=s["date"]))
    alpha_pdf(RESUBMITTED, OUT / "alpha_ST-101_resubmitted.pdf")
    truth.append(dict(file="alpha_ST-101_resubmitted.pdf", id="ST-101", material="S355JR", yield_mpa=381,
                      uts_mpa=528, elongation_pct=26.0, test_date="2026-09-23"))
    for s in BETA:
        beta_pdf(s, OUT / f"beta_{s['id']}.pdf")
        m, d, y = s["date"].split("/")
        truth.append(dict(file=f"beta_{s['id']}.pdf", id=s["id"], material=s["material"],
                          yield_mpa=round(s["yield_ksi"] * KSI, 1), uts_mpa=round(s["uts_ksi"] * KSI, 1),
                          elongation_pct=s["elong"], test_date=f"{y}-{m}-{d}"))
    for s in GAMMA:
        gamma_pdf(s, OUT / f"gamma_{s['id']}.pdf")
        truth.append(dict(file=f"gamma_{s['id']}.pdf", id=s["id"], material=s["material"], yield_mpa=s["yield_mpa"],
                          uts_mpa=s["uts_mpa"], elongation_pct=s["elong"], test_date=s["date"]))
    (HERE / "ground_truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    print(f"{len(truth)} reports written to {OUT}")


if __name__ == "__main__":
    main()
