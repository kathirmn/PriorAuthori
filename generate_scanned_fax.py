"""
generate_scanned_fax.py
========================
Creates a mock 'scanned' (image-only) fax PDF to test the OCR fallback in
intake_engine.py.

Strategy
--------
1. Render the fax content as a PNG image using Pillow (ImageDraw + ImageFont).
   The image contains real text but is stored as pixels — there is NO selectable
   text layer whatsoever.
2. Embed that image into a single-page PDF using a raw reportlab canvas
   (drawImage), which paints the image directly with no frame/margin constraints.
3. Save the result to /mock_faxes/fax_scanned_walker_emily.pdf.

When intake_engine.py opens this PDF with pdfplumber it will extract 0
characters (< 50 threshold), triggering the OCR path via pdf2image +
pytesseract.
"""

import io
import os

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "mock_faxes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_PDF = os.path.join(OUTPUT_DIR, "fax_scanned_walker_emily.pdf")

# ── Fax content ────────────────────────────────────────────────────────────────
FAX_LINES = [
    "================================================",
    "         MEDICAL FAX TRANSMISSION               ",
    "  Sunrise Regional Medical Center | Fax: (800) 555-0199",
    "================================================",
    "",
    "PRIOR AUTHORIZATION REQUEST",
    "",
    "-- Referring Physician --",
    "Physician Name: Dr. Rachel Kim, MD",
    "NPI: 5551239876",
    "Phone: (212) 555-0187   |   Fax: (212) 555-0188",
    "",
    "-- Patient Information --",
    "Patient Name: Emily R. Walker",
    "Date of Birth: 07/30/1985",
    "Member ID: MBR-9983401",
    "Insurance Plan: UnitedHealthcare Choice Plus",
    "",
    "-- Clinical Information --",
    "Primary Diagnosis Code (ICD-10): M75.1 - Rotator Cuff Syndrome",
    "Requested Procedure (CPT Code): 97012 - Mechanical Traction",
    "",
    "-- Clinical Justification --",
    "Patient presents with right shoulder rotator cuff tendinopathy",
    "confirmed by MRI on 02/20/2026. Conservative treatment with",
    "anti-inflammatories has been ineffective over 6 weeks.",
    "Requesting authorization for 15 Days of Physiotherapy over",
    "a 5-week period to restore shoulder range of motion and reduce",
    "pain. Patient is compliant and motivated for rehabilitation.",
    "",
    "------------------------------------------------",
    "Date of Request: 03/14/2026",
    "Physician Signature: Dr. Rachel Kim, MD  [Signed Electronically]",
    "================================================",
]

# ── Step 1: Render text onto a PIL image ──────────────────────────────────────

def render_text_to_image(lines: list) -> Image.Image:
    """
    Draw fax text onto a white background image.
    Tries common monospace fonts; falls back to PIL's built-in default.
    """
    font_size   = 22
    line_height = font_size + 8
    padding     = 60

    font = None
    for candidate in ("cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"):
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except IOError:
            continue
    if font is None:
        font = ImageFont.load_default()

    img_width  = 1275                                                   # 8.5 in @ 150 dpi
    img_height = max(1650, padding * 2 + line_height * (len(lines) + 4))  # ≥ 11 in @ 150 dpi

    img  = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(img)

    y = padding
    for line in lines:
        draw.text((padding, y), line, fill="black", font=font)
        y += line_height

    return img


# ── Step 2: Render image and save to a temp PNG ───────────────────────────────
print("[*] Rendering fax content to image …")
fax_image = render_text_to_image(FAX_LINES)
print(f"    Image size: {fax_image.size[0]}×{fax_image.size[1]} px")

tmp_png = os.path.join(OUTPUT_DIR, "_tmp_scanned_fax.png")
fax_image.save(tmp_png, format="PNG", dpi=(150, 150))
print(f"[*] Temporary PNG saved: {tmp_png}")

# ── Step 3: Draw image directly onto a PDF page using reportlab canvas ─────────
# Using canvas.drawImage() avoids the frame/margin issues of SimpleDocTemplate
# and guarantees no text layer is written to the PDF.
print(f"[*] Building image-only PDF → {OUTPUT_PDF}")

page_w, page_h = letter   # 612 pt × 792 pt

c = canvas.Canvas(OUTPUT_PDF, pagesize=letter)
# drawImage(path, x, y, width, height) – x/y is bottom-left corner in points
c.drawImage(tmp_png, 0, 0, width=page_w, height=page_h, preserveAspectRatio=False)
c.showPage()
c.save()

# Clean up temp PNG
os.remove(tmp_png)
print("[*] Temporary PNG removed.")

print(f"\n[✓] Scanned fax PDF created: {OUTPUT_PDF}")
print("    This PDF contains NO native text layer.")
print("    intake_engine.py will trigger the OCR fallback when processing it.")

