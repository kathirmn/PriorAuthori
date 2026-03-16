"""
generate_mock_faxes.py
Generates two realistic mock medical fax PDFs and saves them to /mock_faxes.
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "mock_faxes")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_fax(filename: str, content_blocks: list):
    """Build a simple fax-style PDF."""
    path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=letter,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("FaxTitle", parent=styles["Heading1"],
                                 alignment=TA_CENTER, fontSize=14, spaceAfter=6)
    header_style = ParagraphStyle("SectionHeader", parent=styles["Heading2"],
                                  fontSize=11, spaceAfter=4, textColor="#333333")
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=10, leading=16, spaceAfter=2)

    story = []
    story.append(Paragraph("MEDICAL FAX TRANSMISSION", title_style))
    story.append(Paragraph("Sunrise Regional Medical Center | Fax: (800) 555-0199", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color="black"))
    story.append(Spacer(1, 0.1 * inch))

    for block_type, text in content_blocks:
        if block_type == "header":
            story.append(Paragraph(text, header_style))
        elif block_type == "body":
            story.append(Paragraph(text, body_style))
        elif block_type == "spacer":
            story.append(Spacer(1, 0.1 * inch))
        elif block_type == "hr":
            story.append(HRFlowable(width="100%", thickness=0.5, color="grey"))

    doc.build(story)
    print(f"[+] Created: {path}")
    return path


# ── FAX 1 ──────────────────────────────────────────────────────────────────────
fax1_content = [
    ("header", "PRIOR AUTHORIZATION REQUEST"),
    ("spacer", ""),
    ("header", "Referring Physician"),
    ("body", "Physician Name: Dr. Emily Chen, MD"),
    ("body", "NPI: 1234567890"),
    ("body", "Phone: (312) 555-0142   |   Fax: (312) 555-0199"),
    ("spacer", ""),
    ("header", "Patient Information"),
    ("body", "Patient Name: John A. Ramirez"),
    ("body", "Date of Birth: 04/15/1978"),
    ("body", "Member ID: MBR-7741023"),
    ("body", "Insurance Plan: BlueCross Premier PPO"),
    ("spacer", ""),
    ("header", "Clinical Information"),
    ("body", "Primary Diagnosis Code (ICD-10): M54.5 — Low Back Pain"),
    ("body", "Requested Procedure (CPT Code): 97110 — Therapeutic Exercises"),
    ("spacer", ""),
    ("header", "Clinical Justification"),
    ("body", (
        "Patient presents with chronic low back pain following a workplace injury sustained in "
        "January 2026. Conservative management including NSAIDs has proven insufficient. "
        "Lumbar MRI (02/10/2026) reveals L4-L5 disc herniation with mild nerve impingement. "
        "Requesting authorization for 20 Days of Physiotherapy sessions over an 8-week period "
        "to restore functional mobility and reduce pain levels. Patient is motivated and compliant."
    )),
    ("spacer", ""),
    ("hr", ""),
    ("body", "Date of Request: 03/14/2026"),
    ("body", "Physician Signature: Dr. Emily Chen, MD  [Signed Electronically]"),
]

# ── FAX 2 ──────────────────────────────────────────────────────────────────────
fax2_content = [
    ("header", "PRIOR AUTHORIZATION REQUEST"),
    ("spacer", ""),
    ("header", "Referring Physician"),
    ("body", "Physician Name: Dr. Marcus Webb, MD"),
    ("body", "NPI: 9876543210"),
    ("body", "Phone: (415) 555-0231   |   Fax: (415) 555-0299"),
    ("spacer", ""),
    ("header", "Patient Information"),
    ("body", "Patient Name: Sarah L. Thompson"),
    ("body", "Date of Birth: 09/22/1990"),
    ("body", "Member ID: MBR-4452987"),
    ("body", "Insurance Plan: Aetna Choice POS II"),
    ("spacer", ""),
    ("header", "Clinical Information"),
    ("body", "Primary Diagnosis Code (ICD-10): S83.006A — Unspecified tear of medial meniscus, right knee"),
    ("body", "Requested Procedure (CPT Code): 97530 — Therapeutic Activities"),
    ("spacer", ""),
    ("header", "Clinical Justification"),
    ("body", (
        "Patient sustained a right knee medial meniscus tear during a sports activity in "
        "February 2026. Post-surgical follow-up following arthroscopic partial meniscectomy "
        "performed on 02/28/2026. Patient currently experiencing significant reduction in ROM "
        "and quadriceps weakness. Requesting authorization for 30 Days of Physiotherapy "
        "to facilitate post-operative rehabilitation. Goal is to restore full weight-bearing "
        "ambulation and return to baseline functional activities within 12 weeks."
    )),
    ("spacer", ""),
    ("hr", ""),
    ("body", "Date of Request: 03/14/2026"),
    ("body", "Physician Signature: Dr. Marcus Webb, MD  [Signed Electronically]"),
]

build_fax("fax_ramirez_john.pdf", fax1_content)
build_fax("fax_thompson_sarah.pdf", fax2_content)
print("\n[✓] Both mock fax PDFs have been generated in /mock_faxes.")
