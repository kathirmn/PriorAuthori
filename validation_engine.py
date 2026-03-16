"""
validation_engine.py  –  Microservice 1.5: Administrative Validation Engine
=============================================================================
Sits between Intake (MS-1) and Adjudication (MS-2) in the pipeline.

  /edi_output  ──►  [validation_engine]  ──►  /validated_requests  (VALID)
                                          └──►  /processed_results  (REJECTED admin denial)

Monitors /edi_output for EDI 278 .txt files. For each file:
  1. Parse Member ID from NM1*IL segment (Loop 2000C – Subscriber).
  2. Look up the member in member_database.json.
  3. Validate:
       a) Member exists in database.
       b) Status == 'Active'.
       c) Today's date is between effective_date and term_date (inclusive).
  4a. VALID   → Move EDI file to /validated_requests for clinical adjudication.
  4b. INVALID → Write REJECTED JSON to /processed_results. Delete EDI from /edi_output.

Usage:
    python validation_engine.py          # continuous watch mode
    python validation_engine.py --once   # process all existing files then exit
"""

import os
import re
import sys
import json
import shutil
import logging
from datetime import date, datetime
from glob import glob
from time import sleep

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
WATCH_DIR       = os.path.join(BASE_DIR, "edi_output")
VALIDATED_DIR   = os.path.join(BASE_DIR, "validated_requests")
RESULTS_DIR     = os.path.join(BASE_DIR, "processed_results")
MEMBER_DB_PATH  = os.path.join(BASE_DIR, "member_database.json")

for d in (WATCH_DIR, VALIDATED_DIR, RESULTS_DIR):
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ValidationEngine")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – LOAD MEMBER DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def load_member_db(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    members = data.get("members", {})
    log.info(f"Loaded {len(members)} member records from {os.path.basename(path)}")
    return members


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – PARSE MEMBER ID FROM EDI 278
# ─────────────────────────────────────────────────────────────────────────────

def parse_member_id(filepath: str) -> dict:
    """
    Parse EDI 278 file and extract key identifiers.
    Returns dict with: member_id, patient_last, patient_first,
                       cpt_code, physio_days, diagnosis_code, source_file
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    segments = [s.strip() for s in raw.split("~") if s.strip()]

    parsed = {
        "member_id":      None,
        "patient_last":   None,
        "patient_first":  None,
        "cpt_code":       None,
        "physio_days":    None,
        "diagnosis_code": None,
        "source_file":    None,
    }

    for segment in segments:
        elements = segment.split("*")
        seg_id   = elements[0].strip().upper()

        # NM1*IL – Subscriber loop (Loop 2000C): holds the Member ID
        # Format: NM1*IL*1*LASTNAME*FIRSTNAME****MI*MBR-XXXXXXX
        if seg_id == "NM1" and len(elements) > 1 and elements[1].strip().upper() == "IL":
            if len(elements) > 3:
                parsed["patient_last"]  = elements[3].strip()
            if len(elements) > 4:
                parsed["patient_first"] = elements[4].strip()
            # Element index 9: ID code qualifier is MI, element 9 is the ID itself
            if len(elements) > 9:
                parsed["member_id"] = elements[9].strip()

        # SV1 – CPT code
        elif seg_id == "SV1" and len(elements) > 1:
            cpt_match = re.search(r"(?:HC|RB|WK):(\d{5})", elements[1], re.IGNORECASE)
            if cpt_match:
                parsed["cpt_code"] = cpt_match.group(1)

        # MSG – Physio days and source file
        elif seg_id == "MSG" and len(elements) > 1:
            days_match = re.search(r"PHYSIO_DAYS:(\d+)",     elements[1], re.IGNORECASE)
            src_match  = re.search(r"SOURCE_FILE:([^\|~]+)", elements[1], re.IGNORECASE)
            if days_match:
                parsed["physio_days"] = int(days_match.group(1))
            if src_match:
                parsed["source_file"] = src_match.group(1).strip()

        # HI – Diagnosis code
        elif seg_id == "HI" and len(elements) > 1:
            diag_match = re.search(r"ABK:([A-Z][0-9A-Z.]+)", elements[1], re.IGNORECASE)
            if diag_match:
                parsed["diagnosis_code"] = diag_match.group(1)

    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – MEMBER ELIGIBILITY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_member(member_id: str, member_db: dict) -> tuple[bool, str, str]:
    """
    Validate member eligibility.
    Returns: (is_valid: bool, reason_code: str, reason_message: str)
    """
    today = date.today()

    # Check 1: Member exists
    if not member_id:
        return (
            False,
            "MEMBER_ID_MISSING",
            "No Member ID could be extracted from the EDI 278 NM1*IL segment.",
        )

    record = member_db.get(member_id)
    if not record:
        return (
            False,
            "MEMBER_NOT_FOUND",
            f"Member ID '{member_id}' does not exist in the eligibility database. "
            "Authorization cannot be processed for an unrecognized member.",
        )

    # Check 2: Status must be Active
    status = record.get("status", "").strip()
    if status.lower() != "active":
        return (
            False,
            "MEMBER_INACTIVE",
            f"Member '{member_id}' ({record.get('first_name')} {record.get('last_name')}) "
            f"has a coverage status of '{status}'. Only Active members are eligible for "
            "prior authorization. Please verify enrollment status.",
        )

    # Check 3: Today must be within effective_date → term_date window
    try:
        effective_dt = datetime.strptime(record["effective_date"], "%Y-%m-%d").date()
        term_dt      = datetime.strptime(record["term_date"],      "%Y-%m-%d").date()
    except (KeyError, ValueError) as exc:
        return (
            False,
            "INVALID_DATE_RECORD",
            f"Member '{member_id}' has a malformed date record in the database: {exc}",
        )

    if today < effective_dt:
        return (
            False,
            "COVERAGE_NOT_YET_EFFECTIVE",
            f"Member '{member_id}' coverage does not begin until {effective_dt}. "
            f"Today is {today}. Request submitted before the effective date.",
        )

    if today > term_dt:
        return (
            False,
            "COVERAGE_TERMINATED",
            f"Member '{member_id}' ({record.get('first_name')} {record.get('last_name')}) "
            f"coverage terminated on {term_dt}. "
            f"Today is {today}. Authorization cannot be granted for expired coverage.",
        )

    # All checks passed
    return (
        True,
        "MEMBER_ELIGIBLE",
        f"Member '{member_id}' ({record.get('first_name')} {record.get('last_name')}) "
        f"is Active with valid coverage from {effective_dt} to {term_dt}.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4A – ROUTE: VALID → /validated_requests
# ─────────────────────────────────────────────────────────────────────────────

def route_valid(edi_path: str, parsed: dict, reason_message: str):
    """Move EDI file to /validated_requests."""
    filename = os.path.basename(edi_path)
    dest     = os.path.join(VALIDATED_DIR, filename)
    shutil.move(edi_path, dest)
    log.info(f"  ✅ ELIGIBLE  →  Moved to /validated_requests: {filename}")
    log.info(f"     {reason_message}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4B – ROUTE: INVALID → REJECTED JSON + delete EDI
# ─────────────────────────────────────────────────────────────────────────────

def route_invalid(edi_path: str, parsed: dict, reason_code: str, reason_message: str):
    """
    Write an Administrative Denial JSON to /processed_results,
    then delete the EDI file from /edi_output.
    """
    filename = os.path.basename(edi_path)

    payload = {
        "adjudication_timestamp": datetime.now().isoformat(),
        "source_edi_file":        filename,
        "original_fax_file":      parsed.get("source_file", "UNKNOWN"),
        "patient": {
            "last_name":      parsed.get("patient_last",   "UNKNOWN"),
            "first_name":     parsed.get("patient_first",  "UNKNOWN"),
            "member_id":      parsed.get("member_id",      "UNKNOWN"),
            "diagnosis_code": parsed.get("diagnosis_code", "UNKNOWN"),
        },
        "request": {
            "cpt_code":    parsed.get("cpt_code"),
            "physio_days": parsed.get("physio_days"),
        },
        "adjudication": {
            "status":         "REJECTED",
            "stage":          "Administrative Validation",
            "reason_code":    reason_code,
            "reason_message": f"Administrative Denial: {reason_message}",
        },
    }

    stem     = os.path.splitext(filename)[0]
    out_name = f"{stem}_decision.json"
    out_path = os.path.join(RESULTS_DIR, out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Remove EDI file from /edi_output — it must NOT reach clinical adjudication
    os.remove(edi_path)

    log.info(f"  ❌ REJECTED  →  Decision written: {out_name}")
    log.info(f"     [{reason_code}] {reason_message}")
    log.info(f"     EDI file deleted from /edi_output.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – ORCHESTRATE
# ─────────────────────────────────────────────────────────────────────────────

def process_edi_file(edi_path: str, member_db: dict):
    filename = os.path.basename(edi_path)
    log.info(f"Validating: {filename}")

    try:
        parsed    = parse_member_id(edi_path)
        member_id = parsed.get("member_id")

        is_valid, reason_code, reason_message = validate_member(member_id, member_db)

        if is_valid:
            route_valid(edi_path, parsed, reason_message)
        else:
            route_invalid(edi_path, parsed, reason_code, reason_message)

    except Exception as exc:
        log.error(f"Unexpected error processing {filename}: {exc}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# WATCHDOG HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class EDIHandler(FileSystemEventHandler):
    def __init__(self, member_db):
        self.member_db = member_db

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(".txt"):
            sleep(1)   # allow file write to complete
            process_edi_file(event.src_path, self.member_db)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    member_db = load_member_db(MEMBER_DB_PATH)
    once_mode = "--once" in sys.argv

    if once_mode:
        log.info(f"[--once mode] Scanning {WATCH_DIR} for existing EDI files …")
        edi_files = sorted(glob(os.path.join(WATCH_DIR, "*.txt")))
        if not edi_files:
            log.warning("No .txt EDI files found in /edi_output.")
        for edi_path in edi_files:
            process_edi_file(edi_path, member_db)
        log.info("Administrative validation complete.")
        return

    # Continuous watch mode
    log.info(f"Starting watchdog monitor on: {WATCH_DIR}")
    handler  = EDIHandler(member_db)
    observer = Observer()
    observer.schedule(handler, WATCH_DIR, recursive=False)
    observer.start()
    log.info("Validation Engine is running. Waiting for EDI files … (Ctrl+C to stop)")
    try:
        while True:
            sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log.info("Validation Engine stopped.")


if __name__ == "__main__":
    main()
