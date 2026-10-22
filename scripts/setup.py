"""
Cross-Platform Automated Setup Script for SyncOps Assistant.
Initializes Python environment, dependencies, synthetic database, and executes tests.
"""

import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_step(step_name: str, cmd: list[str], cwd: Path = PROJECT_ROOT) -> bool:
    print(f"\n[STEP] {step_name}...")
    try:
        res = subprocess.run(cmd, cwd=cwd, check=True)
        print(f"[OK] {step_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {step_name} failed with exit code {e.returncode}.")
        return False

def main():
    print("=" * 65)
    print("SYNCOPS ASSISTANT: AUTOMATED SETUP & VERIFICATION")
    print("Target: Customer-Experience Reliability & SRE Triage Platform")
    print("=" * 65)

    # 1. Check Python Version
    print(f"\n[1] Checking Python runtime: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("[ERROR] Python 3.10+ required. Please upgrade your Python version.")
        sys.exit(1)
    print("[OK] Python version is compatible.")

    # 2. Virtual Environment
    venv_dir = PROJECT_ROOT / ".venv"
    if not venv_dir.exists():
        print("\n[2] Creating virtual environment (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("[OK] Virtual environment created.")
    else:
        print("\n[2] Virtual environment already exists.")

    # Determine venv executables
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
        venv_pytest = venv_dir / "Scripts" / "pytest.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
        venv_pytest = venv_dir / "bin" / "pytest"

    # 3. Install Requirements
    print("\n[3] Installing dependencies from requirements.txt...")
    req_file = PROJECT_ROOT / "requirements.txt"
    run_step("Pip Install Requirements", [str(venv_pip), "install", "-r", str(req_file)])

    # 4. Seed Synthetic Data
    print("\n[4] Initializing database and synthetic data...")
    seed_script = PROJECT_ROOT / "scripts" / "seed_data.py"
    run_step("Seed Database", [str(venv_python), str(seed_script)])

    # 5. Run Pytest Suite
    print("\n[5] Executing automated pytest test suite...")
    run_step("Execute Pytest", [str(venv_pytest), "-q"])

    print("\n" + "=" * 65)
    print("🎉 SYNCOPS ASSISTANT SETUP COMPLETE!")
    print("=" * 65)
    print("\nTo start the services on Windows PowerShell:")
    print("  1) REST API:")
    print("     .venv\\Scripts\\uvicorn app.main:app --reload --port 8000")
    print("\n  2) Streamlit Dashboard:")
    print("     .venv\\Scripts\\streamlit run dashboard/app.py --server.port 8501")
    print("\n  3) Local Slack Mock Mode:")
    print("     .venv\\Scripts\\python -m app.slack.mock")
    print("\n  4) Run Smoke Tests:")
    print("     .venv\\Scripts\\python scripts/smoke_test.py")
    print("=" * 65)

if __name__ == "__main__":
    main()
