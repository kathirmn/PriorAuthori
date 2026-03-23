"""
rules_engine.py  –  Microservice 2: Adjudication Engine
=========================================================
Reads EDI 278 .txt files from /edi_output.
Parses the ~ delimited segments to extract:
  • CPT code   → SV1 segment  (SV1*HC:<CPT>*...)
  • Physio days → custom MSG segment (MSG*PHYSIO_DAYS:<N>|...)
  • Member ID  → NM1*IL segment
  • Diagnosis  → HI segment
  • Patient    → NM1*QC segment

Checks extracted values against policies.json rules.
Writes a structured JSON decision file to /processed_results.

Usage:
    python rules_engine.py          # adjudicate all files in /edi_output
    python rules_engine.py <file>   # adjudicate a single EDI file by path
"""

import os
import re
import sys
import time
import json
import logging
from datetime import datetime
from glob import glob

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR              = os.path.dirname(os.path.abspath(__file__))
EDI_INPUT_DIR         = os.path.join(BASE_DIR, "validated_requests")
RESULTS_DIR           = os.path.join(BASE_DIR, "processed_results")
OUTBOUND_LETTERS_DIR  = os.path.join(BASE_DIR, "outbound_letters")
POLICIES_FILE         = os.path.join(BASE_DIR, "policies.json")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(OUTBOUND_LETTERS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("RulesEngine")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – LOAD POLICIES
# ─────────────────────────────────────────────────────────────────────────────

def load_policies(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"Loaded {len(data['policies'])} CPT rules from {os.path.basename(path)}")
    return data["policies"]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – PARSE EDI 278 FILE
# ─────────────────────────────────────────────────────────────────────────────

def parse_edi_278(filepath: str) -> dict:
    """
    Parse a ~ delimited EDI 278 file and extract key clinical fields.
    Returns a dict with: cpt_code, physio_days, member_id, diagnosis_code,
                         patient_last, patient_first, source_file
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split on ~ (segment terminator), strip whitespace from each segment
    segments = [s.strip() for s in raw.split("~") if s.strip()]

    fields = {
        "cpt_code":       None,
        "physio_days":    None,
        "member_id":      None,
        "diagnosis_code": None,
        "patient_last":   None,
        "patient_first":  None,
        "source_file":    None,
        "source_evidence": None,
    }

    for segment in segments:
        elements = segment.split("*")
        segment_id = elements[0].strip().upper()

        # SV1 – Professional Service Line
        # Format: SV1*HC:<CPT>*UN**DA
        if segment_id == "SV1" and len(elements) > 1:
            # element[1] is the composite: HC:97110
            svc_composite = elements[1]
            cpt_match = re.search(r"(?:HC|RB|WK):(\d{5})", svc_composite, re.IGNORECASE)
            if cpt_match:
                fields["cpt_code"] = cpt_match.group(1)

        # MSG – Custom clinical message
        # Format: MSG*PHYSIO_DAYS:20|EVIDENCE:Patient completed 20 days...|SOURCE_FILE:fax_ramirez_john.pdf
        elif segment_id == "MSG" and len(elements) > 1:
            msg_body = elements[1]
            days_match = re.search(r"PHYSIO_DAYS:(\d+)", msg_body, re.IGNORECASE)
            evid_match = re.search(r"EVIDENCE:([^\|~]+)", msg_body, re.IGNORECASE)
            src_match  = re.search(r"SOURCE_FILE:([^\|~]+)", msg_body, re.IGNORECASE)
            if days_match:
                fields["physio_days"] = int(days_match.group(1))
            if evid_match:
                fields["source_evidence"] = evid_match.group(1).strip()
            if src_match:
                fields["source_file"] = src_match.group(1).strip()

        # NM1*IL – Subscriber / Member
        # Format: NM1*IL*1*RAMIREZ*JOHN****MI*MBR-7741023
        elif segment_id == "NM1" and len(elements) > 1 and elements[1].strip().upper() == "IL":
            if len(elements) > 3:
                fields["patient_last"]  = elements[3].strip()
            if len(elements) > 4:
                fields["patient_first"] = elements[4].strip()
            if len(elements) > 9:
                fields["member_id"] = elements[9].strip()

        # HI – Health Care Information Codes (Diagnosis)
        # Format: HI*ABK:M54.5
        elif segment_id == "HI" and len(elements) > 1:
            diag_match = re.search(r"ABK:([A-Z][0-9A-Z.]+)", elements[1], re.IGNORECASE)
            if diag_match:
                fields["diagnosis_code"] = diag_match.group(1)

    return fields


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – ADJUDICATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def adjudicate(parsed: dict, policies: dict) -> dict:
    """
    Apply policy rules to parsed EDI fields.
    Returns: { status, reason_code, reason_message, policy_applied }
    """
    cpt_code    = parsed.get("cpt_code")
    physio_days = parsed.get("physio_days")
    diagnosis   = parsed.get("diagnosis_code") or ""

    # ── R1: Unknown CPT code ─────────────────────────────────────────────────
    if not cpt_code:
        return {
            "status":         "REJECTED",
            "reason_code":    "MISSING_CPT",
            "reason_message": "No CPT code found in the EDI 278 SV1 segment.",
            "policy_applied": None,
        }

    # ── R2: CPT not in policy database ───────────────────────────────────────
    if cpt_code not in policies:
        return {
            "status":         "REJECTED",
            "reason_code":    "CPT_NOT_COVERED",
            "reason_message": (
                f"CPT code '{cpt_code}' is not found in the policy database. "
                "Services must be listed as covered to receive authorization."
            ),
            "policy_applied": None,
        }

    policy    = policies[cpt_code]
    criteria  = policy.get("approval_criteria", {})

    # ── R3: CPT explicitly NOT_COVERED ───────────────────────────────────────
    if policy.get("status") == "NOT_COVERED":
        return {
            "status":         "REJECTED",
            "reason_code":    "CPT_NOT_COVERED",
            "reason_message": (
                f"CPT code '{cpt_code}' ({policy['description']}) is listed as NOT COVERED "
                "under current plan benefits."
            ),
            "policy_applied": policy["description"],
        }

    # ── R4: Minimum physiotherapy days requirement ────────────────────────────
    min_days = criteria.get("min_physio_days")
    if min_days is not None:
        if physio_days is None:
            return {
                "status":         "REJECTED",
                "reason_code":    "MISSING_PHYSIO_DAYS",
                "reason_message": (
                    f"CPT code '{cpt_code}' ({policy['description']}) requires documentation of "
                    f"at least {min_days} day(s) of physiotherapy, but no physio days were "
                    "recorded in the authorization request."
                ),
                "policy_applied": policy["description"],
            }
        if physio_days < min_days:
            return {
                "status":         "REJECTED",
                "reason_code":    "INSUFFICIENT_PHYSIO_DAYS",
                "reason_message": (
                    f"CPT code '{cpt_code}' ({policy['description']}) requires a minimum of "
                    f"{min_days} day(s) of physiotherapy. Request documents only "
                    f"{physio_days} day(s). Additional conservative treatment is required."
                ),
                "policy_applied": policy["description"],
            }

    # ── R5: Maximum physiotherapy days cap ───────────────────────────────────
    max_days = criteria.get("max_physio_days")
    if max_days is not None and physio_days is not None and physio_days > max_days:
        return {
            "status":         "REJECTED",
            "reason_code":    "EXCEEDS_MAX_PHYSIO_DAYS",
            "reason_message": (
                f"CPT code '{cpt_code}' ({policy['description']}) is approved for a maximum of "
                f"{max_days} day(s). Request of {physio_days} day(s) exceeds the plan limit. "
                "Please submit a separate request for extended services."
            ),
            "policy_applied": policy["description"],
        }

    # ── R6: Diagnosis code prefix validation ─────────────────────────────────
    allowed_prefixes = criteria.get("allowed_diagnosis_prefixes", [])
    if allowed_prefixes and diagnosis:
        diag_prefix = diagnosis[0].upper()
        if diag_prefix not in allowed_prefixes:
            return {
                "status":         "REJECTED",
                "reason_code":    "DIAGNOSIS_NOT_COVERED",
                "reason_message": (
                    f"Diagnosis code '{diagnosis}' (category prefix '{diag_prefix}') is not "
                    f"an approved indication for CPT '{cpt_code}' ({policy['description']}). "
                    f"Covered diagnosis categories: {', '.join(allowed_prefixes)}."
                ),
                "policy_applied": policy["description"],
            }

    # ── All rules passed → APPROVED ───────────────────────────────────────────
    return {
        "status":         "APPROVED",
        "reason_code":    "CRITERIA_MET",
        "reason_message": (
            f"All policy criteria satisfied for CPT '{cpt_code}' ({policy['description']}). "
            f"Physio days documented: {physio_days}. "
            f"Diagnosis code: {diagnosis}. Prior authorization granted."
        ),
        "policy_applied": policy["description"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 – BUILD + SAVE RESULT PAYLOAD
# ─────────────────────────────────────────────────────────────────────────────

def build_result_payload(edi_filename: str, parsed: dict, decision: dict) -> dict:
    """Assemble the final structured JSON result."""
    return {
        "adjudication_timestamp": datetime.now().isoformat(),
        "source_edi_file":        edi_filename,
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
            "source_evidence": parsed.get("source_evidence"),
        },
        "adjudication": {
            "status":         decision["status"],
            "reason_code":    decision["reason_code"],
            "reason_message": decision["reason_message"],
            "policy_applied": decision.get("policy_applied"),
        },
    }


def save_result(payload: dict, edi_filename: str):
    """Write the JSON payload to /processed_results."""
    stem      = os.path.splitext(edi_filename)[0]
    out_name  = f"{stem}_decision.json"
    out_path  = os.path.join(RESULTS_DIR, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – PROVIDER NOTIFICATION LETTER
# ─────────────────────────────────────────────────────────────────────────────

def generate_provider_letter(payload: dict) -> str | None:
    """
    Generate a professional provider notification letter (.txt) in /outbound_letters.
    Naming convention: Letter_[PatientID].txt
    Returns the output path, or None if the decision status is not final.
    """
    adj     = payload.get("adjudication", {})
    status  = adj.get("status", "")

    if status not in ("APPROVED", "REJECTED"):
        return None

    pat          = payload.get("patient", {})
    req          = payload.get("request", {})
    member_id    = pat.get("member_id", "UNKNOWN")
    first_name   = pat.get("first_name", "")
    last_name    = pat.get("last_name", "")
    full_name    = f"{first_name} {last_name}".strip() or "Unknown Patient"
    cpt_code     = req.get("cpt_code", "N/A")
    evidence     = req.get("source_evidence") or adj.get("reason_message", "No additional detail available.")
    reason_code  = adj.get("reason_code", "N/A")
    reason_msg   = adj.get("reason_message", "No reason provided.")
    timestamp    = payload.get("adjudication_timestamp", datetime.now().isoformat())
    policy       = adj.get("policy_applied") or "N/A"

    if status == "APPROVED":
        outcome_line = "We are pleased to inform you that the above request has been APPROVED."
        action_line  = (
            "Authorization has been granted. Please proceed with the service and include "
            "this reference number in all subsequent claims submissions."
        )
    else:
        outcome_line = "After careful review, the above request has been REJECTED."
        action_line  = (
            "If you believe this determination is incorrect, you may submit a peer-to-peer "
            "review request within 14 calendar days of this notice."
        )

    letter = f"""================================================================================
           PRIOR AUTHORIZATION DETERMINATION NOTICE
================================================================================

Date of Determination : {timestamp[:19].replace('T', ' ')}
Patient Name          : {full_name}
Member / Patient ID   : {member_id}
Requested CPT Code    : {cpt_code}
Policy Applied        : {policy}

--------------------------------------------------------------------------------
DETERMINATION: {status}
Reason Code   : {reason_code}
--------------------------------------------------------------------------------

{outcome_line}

Clinical Rationale:
  {reason_msg}

Supporting Clinical Evidence on Record:
  "{evidence}"

--------------------------------------------------------------------------------
ACTION REQUIRED
--------------------------------------------------------------------------------
{action_line}

This notice was generated automatically by the AI Adjudication Engine.
For questions, contact the Prior Authorization department.

================================================================================
"""

    letter_filename = f"Letter_{member_id}.txt"
    letter_path     = os.path.join(OUTBOUND_LETTERS_DIR, letter_filename)
    with open(letter_path, "w", encoding="utf-8") as f:
        f.write(letter)

    return letter_path


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – ORCHESTRATE
# ─────────────────────────────────────────────────────────────────────────────

def process_edi_file(edi_path: str, policies: dict):
    filename = os.path.basename(edi_path)
    log.info(f"Adjudicating: {filename}")

    try:
        parsed      = parse_edi_278(edi_path)
        decision    = adjudicate(parsed, policies)
        payload     = build_result_payload(filename, parsed, decision)
        out_path    = save_result(payload, filename)
        letter_path = generate_provider_letter(payload)

        status_icon = "✅" if decision["status"] == "APPROVED" else "❌"
        log.info(
            f"  {status_icon} {decision['status']}  [{decision['reason_code']}]  "
            f"→ {os.path.basename(out_path)}"
        )
        log.info(f"     {decision['reason_message']}")
        if letter_path:
            log.info(f"  ✉️  Letter generated → {os.path.basename(letter_path)}")

    except Exception as exc:
        log.error(f"Failed to adjudicate {filename}: {exc}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 – WATCHDOG MONITOR
# ─────────────────────────────────────────────────────────────────────────────

class ValidatedEDIHandler(FileSystemEventHandler):
    def __init__(self, policies):
        self.policies = policies

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".txt"):
            time.sleep(1) # wait for file to finish writing
            process_edi_file(event.src_path, self.policies)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    policies = load_policies(POLICIES_FILE)

    once_mode = "--once" in sys.argv
    if once_mode or len(sys.argv) > 1 and sys.argv[1] != "--once":
        # Process existing or specific file
        target = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--once" else None
        if target:
            if not os.path.isfile(target):
                log.error(f"File not found: {target}")
                sys.exit(1)
            process_edi_file(target, policies)
            return
        
        edi_files = sorted(glob(os.path.join(EDI_INPUT_DIR, "*.txt")))
        if not edi_files:
            log.warning(f"No .txt EDI files found in {EDI_INPUT_DIR}")
            return
        log.info(f"Found {len(edi_files)} EDI file(s) to adjudicate.")
        for edi_path in edi_files:
            process_edi_file(edi_path, policies)
        log.info(f"Done processing all. Results written to: {RESULTS_DIR}")
        return

    # Continuous watch mode
    log.info(f"Starting watchdog monitor on: {EDI_INPUT_DIR}")
    observer = Observer()
    observer.schedule(ValidatedEDIHandler(policies), EDI_INPUT_DIR, recursive=False)
    observer.start()
    log.info("Rules Engine is running. Waiting for validated requests... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log.info("Rules Engine stopped.")

if __name__ == "__main__":
    main()
