import os
import subprocess
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_mock_fax(filepath: str, patient_name: str, member_id: str, diagnosis: str, cpt: str, physio_days: str):
    """Utility to generate a basic PDF mimicking a faxed prior auth request."""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "PRIOR AUTHORIZATION REQUEST")
    c.setFont("Helvetica", 12)
    c.drawString(50, 710, f"Patient Name:  {patient_name}")
    c.drawString(50, 690, f"Member ID:     {member_id}")
    c.drawString(50, 670, f"Diagnosis Code:{diagnosis}")
    c.drawString(50, 650, f"CPT Code:      {cpt}")
    c.drawString(50, 630, f"Requested:     {physio_days}")
    c.save()

def main():
    print("==================================================")
    print("   PRIOR AUTH HACKATHON – AUTOMATED DEMO LAUNCH   ")
    print("==================================================\n")

    # ── Step A: Environment Check ──────────────────────────────────────────
    directories = [
        "mock_faxes",
        "edi_output",
        "validated_requests",
        "processed_results"
    ]
    print("[SYSTEM] Step A: Environment Check...")
    for d in directories:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"         Created missing directory: /{d}")
        else:
            print(f"         Directory already exists: /{d}")
    print("\n")

    # ── Step B: Data Generation ────────────────────────────────────────────
    print("[SYSTEM] Step B: Data Generation (Mock PDFs)...")
    
    # 1. Happy Path (Active Member, Valid Request)
    create_mock_fax(
        filepath="mock_faxes/1_Happy_Path.pdf",
        patient_name="John Ramirez",
        member_id="MBR-7741023",
        diagnosis="M54.5",
        cpt="97110",
        physio_days="10 Days of Physiotherapy"
    )
    print("         Generated: /mock_faxes/1_Happy_Path.pdf")

    # 2. Administrative Denial (Inactive Member)
    create_mock_fax(
        filepath="mock_faxes/2_Admin_Denial.pdf",
        patient_name="Gerald Hawkins",
        member_id="MBR-9901234",
        diagnosis="M54.5",
        cpt="97110",
        physio_days="10 Days of Physiotherapy"
    )
    print("         Generated: /mock_faxes/2_Admin_Denial.pdf")

    # 3. Clinical Denial (Exceeds Max Days / Not Covered Scenario)
    # CPT 99999 is likely not in policies, or asking for 100 days exceeds limits.
    create_mock_fax(
        filepath="mock_faxes/3_Clinical_Denial.pdf",
        patient_name="Sarah Thompson",
        member_id="MBR-4452987",
        diagnosis="M54.5",
        cpt="97110",
        physio_days="100 Days of Physiotherapy"
    )
    print("         Generated: /mock_faxes/3_Clinical_Denial.pdf")
    print("\n")

    # ── Step C: Pipeline Execution ─────────────────────────────────────────
    print("[SYSTEM] Step C: Pipeline Execution...")
    
    engines = [
        ("intake_engine.py", ["python", "intake_engine.py", "--once"]),
        ("validation_engine.py", ["python", "validation_engine.py", "--once"]),
        ("rules_engine.py", ["python", "rules_engine.py"])
    ]

    for script_name, cmd in engines:
        print(f"[SYSTEM] Starting {script_name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[SYSTEM] {script_name} Complete.")
            else:
                print(f"[SYSTEM] ERROR in {script_name}. Stderr below:")
                print(result.stderr)
        except Exception as e:
            print(f"[SYSTEM] Failed to execute {script_name}: {e}")
        time.sleep(1) # Small pause for logs readability
    print("\n")

    # ── Step D: Launch UI ──────────────────────────────────────────────────
    print("[SYSTEM] Step D: Launching Streamlit Dashboard...")
    try:
        subprocess.Popen(["streamlit", "run", "dashboard.py"])
        print("[SYSTEM] Dashboard launched in background.")
    except Exception as e:
        print(f"[SYSTEM] Failed to launch dashboard: {e}")

    print("\n==================================================")
    print("   DEMO INITIALIZATION COMPLETE. WAITING ON APP.  ")
    print("==================================================\n")

if __name__ == "__main__":
    main()
