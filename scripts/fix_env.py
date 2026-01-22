import os
import sys
import subprocess


def fix():
    # 1. Create venv if missing
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])

    # 2. Install requirements
    print("Installing dependencies...")
    pip = r"venv\Scripts\pip" if os.name == "nt" else "venv/bin/pip"
    subprocess.check_call([pip, "install", "-r", "requirements.txt"])

    print("\n✅ Environment fixed.")
    print("Please restart VS Code to ensure Pylance picks up the new environment.")


if __name__ == "__main__":
    fix()
