"""
demo.py  –  Microservice Orchestrator
=============================================
Starts all backend engines as background daemon processes
and launches the Streamlit UI.

Usage:
    python demo.py
"""

import os
import sys
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_directories():
    """Create all required directories if they don't exist."""
    dirs = [
        "mock_faxes",
        "edi_output",
        "validated_requests",
        "processed_results",
        "outbound_letters",
    ]
    print("[SYSTEM] Checking directories...")
    for d in dirs:
        path = os.path.join(BASE_DIR, d)
        os.makedirs(path, exist_ok=True)
        print(f"         ✅ /{d}")
    print()


def launch_engine(script_name: str) -> subprocess.Popen:
    """Start a Python engine script as a non-blocking background process."""
    script_path = os.path.join(BASE_DIR, script_name)
    process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[SYSTEM] ▶  Launched {script_name}  (PID: {process.pid})")
    return process


def main():
    print("=" * 56)
    print("   PRIOR AUTH HACKATHON – MICROSERVICE ORCHESTRATOR   ")
    print("=" * 56)
    print()

    # Step 1 – Ensure all pipeline directories exist
    ensure_directories()

    # Step 2 – Start backend micro-engines as background daemons.
    #           Using Popen (non-blocking) so this script doesn't hang.
    print("[SYSTEM] Starting background engines...")
    engines = [
        "intake_engine.py",
        "validation_engine.py",
        "rules_engine.py",
    ]
    for engine in engines:
        engine_path = os.path.join(BASE_DIR, engine)
        if os.path.isfile(engine_path):
            launch_engine(engine)
        else:
            print(f"[SYSTEM] ⚠️  Engine not found, skipping: {engine}")
    print()

    # Step 3 – Launch the Streamlit UI (also non-blocking)
    print("[SYSTEM] Launching Streamlit dashboard...")
    ui_process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            os.path.join(BASE_DIR, "dashboard.py"),
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ],
        cwd=BASE_DIR,
    )
    print(f"[SYSTEM] ▶  Streamlit running  (PID: {ui_process.pid})")
    print()

    print("=" * 56)
    print("[SYSTEM] All engines running in background. UI Launched.")
    print("         Drop faxes into /mock_faxes to begin.")
    print("=" * 56)


if __name__ == "__main__":
    main()
