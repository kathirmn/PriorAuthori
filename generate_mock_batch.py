"""
generate_mock_batch.py  –  Bulk test-data generator for hackathon demo
======================================================================
Creates 30 unique prior-auth fax PDFs inside /mock_faxes_batch using
the fpdf library.

Data mix:
  50%  → APPROVE path  (valid member, CPT 72148, ≥10 physio days)
  30%  → CLINICAL REJECT  (valid member, CPT 72148, <10 physio days)
  20%  → ADMIN REJECT  (invalid member ID)

Run:
    python generate_mock_batch.py
"""

import os
import random
from datetime import datetime, timedelta

from fpdf import FPDF

# ─────────────────────────────────────────────────────────────────────────────
# DATA POOLS
# ─────────────────────────────────────────────────────────────────────────────

VALID_MEMBERS = [
    {"member_id": "MBR-7741023", "first": "John",   "last": "Ramirez",  "dob": "1978-04-15"},
    {"member_id": "MBR-4452987", "first": "Sarah",  "last": "Thompson", "dob": "1990-09-22"},
    {"member_id": "MBR-3378561", "first": "Priya",  "last": "Nair",     "dob": "2001-03-08"},
]

INVALID_MEMBERS = [
    {"member_id": "MBR-UNKNOWN99",  "first": "John",    "last": "Ghost"},
    {"member_id": "MBR-EXPIRED12",  "first": "Carlos",  "last": "Vega"},
    {"member_id": "MBR-INVALID77",  "first": "Anika",   "last": "Patel"},
    {"member_id": "MBR-NOSUCH55",   "first": "Darnell", "last": "Brooks"},
    {"member_id": "MBR-TERMED03",   "first": "Lisa",    "last": "Chang"},
    {"member_id": "MBR-FAKE42",     "first": "Omar",    "last": "Hassan"},
]

# Extra names so we get 30 unique patients for the APPROVE / CLINICAL paths
EXTRA_NAMES = [
    ("Michael",  "Chen"),      ("Amanda",  "Foster"),
    ("David",    "Kim"),       ("Rachel",  "Martinez"),
    ("Brian",    "O'Sullivan"),("Keiko",   "Tanaka"),
    ("Marcus",   "Williams"),  ("Elena",   "Petrova"),
    ("James",    "Nguyen"),    ("Fatima",  "Al-Rashid"),
    ("Tyler",    "Anderson"),  ("Nadia",   "Johansson"),
    ("Robert",   "Garcia"),    ("Hannah",  "Becker"),
    ("Samuel",   "Okafor"),    ("Isabella","Russo"),
    ("Nathan",   "Wright"),    ("Mei",     "Liu"),
    ("Derek",    "Patel"),     ("Grace",   "Kelly"),
    ("Oscar",    "Rivera"),    ("Yuki",    "Sato"),
    ("Kevin",    "Adams"),     ("Layla",   "Sharif"),
]

DIAGNOSIS_CODES = ["M54.5", "M79.3", "S83.006A", "M17.11", "G89.29", "M47.812"]

APPROVE_NOTES = [
    "Patient has completed {days} Days of Physiotherapy with no significant improvement in lumbar pain. "
    "Range of motion remains limited. Requesting MRI Lumbar Spine to rule out disc herniation.",
    "Documented {days} Days of Physiotherapy over the past 8 weeks. Patient reports persistent radiculopathy. "
    "Clinical examination shows positive straight-leg raise. MRI indicated to guide treatment plan.",
    "Conservative management including {days} Days of Physiotherapy, NSAIDs, and activity modification has failed to resolve symptoms. "
    "Patient continues to report significant functional limitations. Advanced imaging requested.",
    "After {days} Days of Physiotherapy, patient shows minimal progress. "
    "Neurological examination findings warrant further investigation via lumbar MRI."
]

REJECT_NOTES = [
    "Patient has completed {days} Days of Physiotherapy. Requesting MRI Lumbar Spine for evaluation of lower back pain.",
    "Requesting authorization for lumbar MRI. Patient has had {days} Days of Physiotherapy so far.",
    "Patient presents with {days} Days of Physiotherapy. Mild improvement noted but requesting imaging for confirmation.",
    "Initial evaluation after {days} Days of Physiotherapy. Patient reports intermittent discomfort. MRI requested.",
]

ADMIN_NOTES = [
    "Requesting prior authorization for scheduled procedure. Patient presents with chronic pain symptoms.",
    "Standard prior auth request for outpatient procedure. Please review and advise.",
    "Authorization requested for planned intervention. Patient has documented clinical need.",
    "Routine prior authorization submission for upcoming procedure date.",
]

RANDOM_CPTS = ["97110", "99213", "72148", "27447", "00000"]

REFERRING_DOCS = [
    "Dr. Emily Watson, MD",  "Dr. Raj Kapoor, MD",
    "Dr. Lisa Fernandez, DO", "Dr. Thomas Park, MD",
    "Dr. Sarah Ellis, MD",    "Dr. Kevin Sharma, MD",
]

FACILITIES = [
    "Regional Medical Center",
    "University Health System",
    "Community Orthopedic Clinic",
    "Metro Spine & Pain Institute",
    "Lakeside Physical Therapy",
]


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_fax_pdf(filepath: str, *, patient_first: str, patient_last: str,
                     member_id: str, diagnosis: str, cpt: str,
                     physio_days: int, clinical_notes: str):
    """Create a single fax-style PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    fax_date = (datetime.now() - timedelta(days=random.randint(0, 5))).strftime("%m/%d/%Y")
    doc = random.choice(REFERRING_DOCS)
    facility = random.choice(FACILITIES)

    # ── Fax Header ──
    pdf.set_font("Courier", "B", 14)
    pdf.cell(0, 8, "FAX TRANSMISSION", ln=True, align="C")
    pdf.set_font("Courier", "", 11)
    pdf.cell(0, 6, "=" * 60, ln=True, align="C")
    pdf.ln(4)

    pdf.cell(0, 6, f"TO:    Utilization Management Department", ln=True)
    pdf.cell(0, 6, f"FROM:  {doc}", ln=True)
    pdf.cell(0, 6, f"FAX#:  (555) {random.randint(100,999)}-{random.randint(1000,9999)}", ln=True)
    pdf.cell(0, 6, f"DATE:  {fax_date}", ln=True)
    pdf.cell(0, 6, f"RE:    Prior Authorization Request", ln=True)
    pdf.cell(0, 6, f"PAGES: 1 of 1", ln=True)
    pdf.ln(4)
    pdf.cell(0, 6, "-" * 60, ln=True, align="C")
    pdf.ln(4)

    # ── Patient Information Block ──
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "PATIENT INFORMATION", ln=True)
    pdf.set_font("Courier", "", 11)
    pdf.cell(0, 6, f"  Patient Name:    {patient_first} {patient_last}", ln=True)
    pdf.cell(0, 6, f"  Member ID:       {member_id}", ln=True)
    pdf.cell(0, 6, f"  Diagnosis Code:  {diagnosis}", ln=True)
    pdf.cell(0, 6, f"  CPT Code:        {cpt}", ln=True)
    pdf.cell(0, 6, f"  Physio Days:     {physio_days}", ln=True)
    pdf.cell(0, 6, f"  Facility:        {facility}", ln=True)
    pdf.ln(6)

    # ── Clinical Notes Block ──
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "CLINICAL NOTES", ln=True)
    pdf.set_font("Courier", "", 11)
    pdf.multi_cell(0, 6, f"  {clinical_notes}")
    pdf.ln(8)

    # ── Footer ──
    pdf.cell(0, 6, "-" * 60, ln=True, align="C")
    pdf.set_font("Courier", "I", 10)
    pdf.cell(0, 6, f"Electronically submitted by {doc}", ln=True, align="C")
    pdf.cell(0, 6, f"Date: {fax_date}", ln=True, align="C")

    pdf.output(filepath)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    accepted_dir = os.path.join(base_dir, "mock_faxes_batch", "accepted")
    rejected_dir = os.path.join(base_dir, "mock_faxes_batch", "rejected")
    os.makedirs(accepted_dir, exist_ok=True)
    os.makedirs(rejected_dir, exist_ok=True)

    print("=" * 55)
    print("  MOCK FAX BATCH GENERATOR  –  30 Test PDFs")
    print("=" * 55)
    print(f"Accepted Output: {accepted_dir}")
    print(f"Rejected Output: {rejected_dir}\n")

    # Build the batch plan: 15 approve, 9 clinical reject, 6 admin reject
    batch = []
    name_pool = list(EXTRA_NAMES)
    random.shuffle(name_pool)

    # ── 15 × APPROVE path ──
    for i in range(15):
        member = random.choice(VALID_MEMBERS)
        first, last = name_pool.pop() if name_pool else (member["first"], member["last"])
        days = random.randint(12, 40)
        notes = random.choice(APPROVE_NOTES).format(days=days)
        batch.append({
            "first": first, "last": last,
            "member_id": member["member_id"],
            "diagnosis": random.choice(DIAGNOSIS_CODES),
            "cpt": "72148",
            "days": days,
            "notes": notes,
            "path": "APPROVE",
        })

    # ── 9 × CLINICAL REJECT path ──
    for i in range(9):
        member = random.choice(VALID_MEMBERS)
        first, last = name_pool.pop() if name_pool else (member["first"], member["last"])
        days = random.randint(1, 9)
        notes = random.choice(REJECT_NOTES).format(days=days)
        batch.append({
            "first": first, "last": last,
            "member_id": member["member_id"],
            "diagnosis": random.choice(DIAGNOSIS_CODES),
            "cpt": "72148",
            "days": days,
            "notes": notes,
            "path": "CLINICAL REJECT",
        })

    # ── 6 × ADMIN REJECT path ──
    for i in range(6):
        inv = random.choice(INVALID_MEMBERS)
        days = random.randint(5, 25)
        notes = random.choice(ADMIN_NOTES)
        batch.append({
            "first": inv["first"], "last": inv["last"],
            "member_id": inv["member_id"],
            "diagnosis": random.choice(DIAGNOSIS_CODES),
            "cpt": random.choice(RANDOM_CPTS),
            "days": days,
            "notes": notes,
            "path": "ADMIN REJECT",
        })

    # Shuffle so paths are interleaved
    random.shuffle(batch)

    # ── Generate PDFs ──
    for idx, entry in enumerate(batch, start=1):
        filename = f"Fax_{idx:02d}_{entry['last']}.pdf"
        if entry["path"] == "APPROVE":
            filepath = os.path.join(accepted_dir, filename)
        else:
            filepath = os.path.join(rejected_dir, filename)

        generate_fax_pdf(
            filepath,
            patient_first=entry["first"],
            patient_last=entry["last"],
            member_id=entry["member_id"],
            diagnosis=entry["diagnosis"],
            cpt=entry["cpt"],
            physio_days=entry["days"],
            clinical_notes=entry["notes"],
        )

        tag = {"APPROVE": "✅", "CLINICAL REJECT": "🔬", "ADMIN REJECT": "🛑"}[entry["path"]]
        print(f"  {tag}  [{idx:02d}/30]  {filename:<35s} ({entry['path']})")

    print(f"\n{'=' * 55}")
    print(f"  Done! {len(batch)} PDFs saved to /mock_faxes_batch")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
