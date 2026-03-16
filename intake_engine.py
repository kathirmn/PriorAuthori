"""
intake_engine.py  –  Microservice 1: Intake Engine
====================================================
Monitors /mock_faxes for incoming PDF faxes.
Extracts Patient Name, Member ID, Diagnosis Code, CPT Code, and
'Days of Physiotherapy' using pdfplumber + spaCy + Regex,
then writes a standards-conformant EDI 278 file to /edi_output.

OCR Support:
    If pdfplumber extracts fewer than 50 characters (indicating a
    scanned / image-only fax), the engine automatically falls back to
    pdf2image + pytesseract OCR before passing text through the
    existing spaCy / Regex extraction pipeline.

Usage:
    python intake_engine.py           # continuous watch mode
    python intake_engine.py --once    # process all existing PDFs and exit
"""

import os
import re
import sys
import time
import uuid
import logging
from datetime import datetime

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import spacy
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
WATCH_DIR       = os.path.join(BASE_DIR, "mock_faxes")
OUTPUT_DIR      = os.path.join(BASE_DIR, "edi_output")
PROCESSED_DIR   = os.path.join(BASE_DIR, "processed_results")   # future use

# ── OCR configuration ──────────────────────────────────────────────────────
# Minimum character count from pdfplumber before OCR fallback is triggered.
OCR_THRESHOLD = 50

# Windows: if Tesseract is not on your PATH, uncomment and set the path below.
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Windows: if Poppler is not on your PATH, set the path to its bin/ directory.
# e.g. POPPLER_PATH = r"C:\poppler\Library\bin"
POPPLER_PATH = r"C:\Users\Kathir.M.N\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
# ───────────────────────────────────────────────────────────────────────────

for d in (WATCH_DIR, OUTPUT_DIR, PROCESSED_DIR):
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("IntakeEngine")

# Load spaCy model once at startup
log.info("Loading spaCy model …")
NLP = spacy.load("en_core_web_sm")
log.info("spaCy model loaded.")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – PDF TEXT EXTRACTION  (with OCR fallback)
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Return concatenated plain text from all pages of a PDF.

    Strategy:
        1. PRIMARY  – pdfplumber (fast; works on PDFs with embedded text).
        2. FALLBACK – pdf2image + pytesseract OCR (triggered when pdfplumber
           yields fewer than OCR_THRESHOLD characters, which indicates a
           scanned / image-only fax with no selectable text layer).
    """
    # ── Primary: pdfplumber ───────────────────────────────────────────────
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    native_text = "\n".join(text_parts)

    if len(native_text.strip()) >= OCR_THRESHOLD:
        log.info("  [pdfplumber] Native text extracted successfully.")
        return native_text

    # ── Fallback: OCR via pdf2image + pytesseract ────────────────────────
    log.warning(
        f"  [OCR] Native text length ({len(native_text.strip())} chars) is below "
        f"threshold ({OCR_THRESHOLD}). This appears to be a scanned/image-only fax. "
        "Switching to OCR …"
    )
    convert_kwargs = dict(dpi=300)
    if POPPLER_PATH:
        convert_kwargs["poppler_path"] = POPPLER_PATH

    pages_as_images = convert_from_path(pdf_path, **convert_kwargs)
    ocr_parts = []
    for i, img in enumerate(pages_as_images, start=1):
        page_ocr_text = pytesseract.image_to_string(img)
        log.info(f"  [OCR] Page {i}: extracted {len(page_ocr_text)} characters.")
        ocr_parts.append(page_ocr_text)

    ocr_text = "\n".join(ocr_parts)
    log.info(f"  [OCR] Total OCR text: {len(ocr_text)} characters extracted.")
    return ocr_text


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – INFORMATION EXTRACTION  (spaCy + Regex)
# ─────────────────────────────────────────────────────────────────────────────

def extract_fields(raw_text: str) -> dict:
    """
    Parse raw fax text and return a dict with:
        patient_name, member_id, diagnosis_code, cpt_code, physio_days
    Falls back to 'UNKNOWN' for any field that cannot be found.
    """
    data = {
        "patient_name":   "UNKNOWN",
        "member_id":      "UNKNOWN",
        "diagnosis_code": "UNKNOWN",
        "cpt_code":       "UNKNOWN",
        "physio_days":    "UNKNOWN",
        "source_evidence": "UNKNOWN",
    }

    # ── 2a. Regex extractions ─────────────────────────────────────────────────

    # Member ID  (e.g. "MBR-7741023")
    member_id_match = re.search(r"Member\s*ID\s*[:\-]?\s*([A-Z0-9\-]+)", raw_text, re.IGNORECASE)
    if member_id_match:
        data["member_id"] = member_id_match.group(1).strip()

    # Diagnosis ICD-10 code  (e.g. "M54.5", "S83.006A")
    diag_match = re.search(
        r"(?:Diagnosis\s*Code[^:]*:|ICD-?10[^:]*:)\s*([A-Z][0-9]{2}\.?[0-9A-Z]{0,4})",
        raw_text, re.IGNORECASE
    )
    if diag_match:
        data["diagnosis_code"] = diag_match.group(1).strip()

    # CPT Code  (5-digit code after "CPT" keyword)
    cpt_match = re.search(
        r"(?:CPT\s*Code[^:]*:|CPT[^:]*:)\s*(\d{5})",
        raw_text, re.IGNORECASE
    )
    if cpt_match:
        data["cpt_code"] = cpt_match.group(1).strip()

    # Days of Physiotherapy  (e.g. "20 Days of Physiotherapy")
    physio_match = re.search(
        r"(\d+)\s+Days?\s+of\s+Physio(?:therapy)?",
        raw_text, re.IGNORECASE
    )
    if physio_match:
        data["physio_days"] = physio_match.group(1).strip()
        for line in raw_text.splitlines():
            if re.search(r"(\d+)\s+Days?\s+of\s+Physio(?:therapy)?", line, re.IGNORECASE):
                data["source_evidence"] = line.strip()
                break

    # ── 2b. Patient Name via spaCy NER then regex fallback ───────────────────
    # First try the clearly labelled field
    # First try the clearly labelled field — stop before known next-line keywords
    # Pattern: "Patient Name: Firstname [Middle] Lastname" – limit to 3 name tokens max
    # Use a line-by-line approach: find the line containing "Patient Name" and extract from it
    patient_name_line = ""
    for line in raw_text.splitlines():
        if re.search(r"Patient\s*Name", line, re.IGNORECASE):
            patient_name_line = line
            break

    name_label_match = re.search(
        r"Patient\s*Name\s*[:\-]\s*([A-Z][a-zA-Z\-']+(?:\s+[A-Z][a-zA-Z\-'.]+){0,2})",
        patient_name_line
    )
    if name_label_match:
        data["patient_name"] = name_label_match.group(1).strip()
    else:
        # Fall back: run spaCy NER on the first 800 chars (usually the header section)
        doc = NLP(raw_text[:800])
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            data["patient_name"] = persons[0]

    return data


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – EDI 278 GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def build_edi_278(fields: dict, source_filename: str) -> str:
    """
    Build a standards-inspired EDI 278 transaction string.

    Segments used:
        ISA  – Interchange Control Header
        GS   – Functional Group Header
        ST   – Transaction Set Header (278)
        BHT  – Beginning of Hierarchical Transaction
        HL   – Hierarchical Level (Information Source / Subscriber / Patient)
        NM1  – Individual or Organizational Name
        HI   – Health Care Information Codes  (Diagnosis)
        SV1  – Professional Service          (CPT / procedure)
        MSG  – Message Text                  (custom: physio days)
        SE   – Transaction Set Trailer
        GE   – Functional Group Trailer
        IEA  – Interchange Control Trailer
    """
    now         = datetime.now()
    date_str    = now.strftime("%Y%m%d")       # CCYYMMDD
    time_str    = now.strftime("%H%M")          # HHMM
    isa_date    = now.strftime("%y%m%d")        # YYMMDD for ISA
    ctrl_num    = now.strftime("%d%H%M%S")      # Simple unique control number
    st_ctrl     = "0001"

    # Normalise patient name → LAST*FIRST format for NM1
    name_parts  = fields["patient_name"].split()
    if len(name_parts) >= 2:
        last_name   = name_parts[-1].upper()
        first_name  = name_parts[0].upper()
    else:
        last_name   = fields["patient_name"].upper()
        first_name  = "UN"

    seg = "~\n"   # segment terminator + newline for readability

    edi = (
        f"ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
        f"{isa_date}*{time_str}*^*00501*{ctrl_num}*0*P*:{seg}"
        f"GS*HI*SENDER*RECEIVER*{date_str}*{time_str}*1*X*005010X217{seg}"
        f"ST*278*{st_ctrl}*005010X217{seg}"
        f"BHT*0007*13*{ctrl_num}*{date_str}*{time_str}*RQ{seg}"
        # HL 1 – Information Source (Insurance/Payer)
        f"HL*1**20*1{seg}"
        f"NM1*PR*2*BLUECROSS INSURANCE*****PI*BCBS001{seg}"
        # HL 2 – Subscriber
        f"HL*2*1*22*1{seg}"
        f"NM1*IL*1*{last_name}*{first_name}****MI*{fields['member_id']}{seg}"
        # HL 3 – Patient (same as subscriber in this case)
        f"HL*3*2*PT*0{seg}"
        f"NM1*QC*1*{last_name}*{first_name}****MI*{fields['member_id']}{seg}"
        # Diagnosis
        f"HI*ABK:{fields['diagnosis_code']}{seg}"
        # Requested Service / CPT
        f"SV1*HC:{fields['cpt_code']}*UN**DA{seg}"
        # Custom clinical note: Days of Physiotherapy
        f"MSG*PHYSIO_DAYS:{fields['physio_days']}|EVIDENCE:{fields['source_evidence']}|SOURCE_FILE:{source_filename}{seg}"
        f"SE*13*{st_ctrl}{seg}"
        f"GE*1*1{seg}"
        f"IEA*1*{ctrl_num}{seg}"
    )
    return edi


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 – ORCHESTRATE: PDF → FIELDS → EDI → FILE
# ─────────────────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: str):
    filename = os.path.basename(pdf_path)
    log.info(f"Processing: {filename}")

    try:
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text.strip():
            log.warning(
                f"No text extracted from {filename} (even after OCR attempt) – skipping."
            )
            return

        fields = extract_fields(raw_text)
        log.info(
            f"  Extracted → Patient: '{fields['patient_name']}' | "
            f"Member ID: {fields['member_id']} | "
            f"Dx: {fields['diagnosis_code']} | "
            f"CPT: {fields['cpt_code']} | "
            f"Physio Days: {fields['physio_days']}"
        )

        edi_str  = build_edi_278(fields, filename)
        stem     = os.path.splitext(filename)[0]
        out_name = f"{stem}_EDI278.txt"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(edi_str)

        log.info(f"  ✓ EDI 278 saved → {out_path}")

    except Exception as exc:
        log.error(f"Failed to process {filename}: {exc}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – WATCHDOG FILE SYSTEM MONITOR
# ─────────────────────────────────────────────────────────────────────────────

class FaxHandler(FileSystemEventHandler):
    """Triggered when a new file appears in the watched directory."""

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(".pdf"):
            # Brief sleep lets the file finish writing before we open it
            time.sleep(1)
            process_pdf(event.src_path)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    once_mode = "--once" in sys.argv

    if once_mode:
        # Process every existing PDF in WATCH_DIR, then exit
        log.info(f"[--once mode] Scanning {WATCH_DIR} for existing PDFs …")
        pdfs = [f for f in os.listdir(WATCH_DIR) if f.lower().endswith(".pdf")]
        if not pdfs:
            log.warning("No PDF files found in mock_faxes/.")
        for pdf_file in pdfs:
            process_pdf(os.path.join(WATCH_DIR, pdf_file))
        log.info("Done processing all PDFs.")
        return

    # Continuous watch mode
    log.info(f"Starting watchdog monitor on: {WATCH_DIR}")
    observer = Observer()
    observer.schedule(FaxHandler(), WATCH_DIR, recursive=False)
    observer.start()
    log.info("Intake Engine is running. Drop PDFs into /mock_faxes … (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log.info("Intake Engine stopped.")


if __name__ == "__main__":
    main()
