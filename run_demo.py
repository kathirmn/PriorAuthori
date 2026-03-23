import os
import sys
import subprocess


def main():
    print("==================================================")
    print("   PRIOR AUTH HACKATHON – LIVE DEMO ENVIRONMENT   ")
    print("==================================================\n")

    # ── Step A: Environment Setup ──────────────────────────────────────────
    directories = [
        "mock_faxes",
        "edi_output",
        "validated_requests",
        "processed_results",
        "outbound_letters",
    ]
    print("[SYSTEM] Step A: Environment Setup...")
    for d in directories:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"         Created missing directory: /{d}")
        else:
            print(f"         Directory ready: /{d}")
    print()

    # ── Step B: Launch UI ──────────────────────────────────────────────────
    print("[SYSTEM] Step B: Launching Streamlit Dashboard...")
    try:
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard.py"])
        print("[SYSTEM] Dashboard launched in background.")
    except Exception as e:
        print(f"[SYSTEM] Failed to launch dashboard: {e}")

    print()
    print("==================================================")
    print("  [SYSTEM] Demo environment live. Folders are")
    print("  ready. Waiting for manual file drop...         ")
    print("==================================================\n")


if __name__ == "__main__":
    main()
