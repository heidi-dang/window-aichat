import os
import shutil
import subprocess
import sys

def build():
    # 1. Clean previous build artifacts
    # This fixes the "ValueError: Trying to collect PKG file ... into itself!" error
    # by removing old build folders and spec files that might be conflicting.
    print("Cleaning previous build artifacts...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Removed {folder}/")
            except Exception as e:
                print(f"Error removing {folder}: {e}")
    
    spec_file = 'AIChatDesktop.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removed {spec_file}")

    # 2. Construct PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'main.py',
        '--name', 'AIChatDesktop',
        '--windowed',  # No console window
        '--clean',     # Clean PyInstaller cache
        '--noconfirm', # Overwrite output directory
        
        # Explicitly import the local module
        '--hidden-import', 'github_handler',
        
        # Common hidden imports
        '--hidden-import', 'PIL',
        '--hidden-import', 'cryptography',
    ]

    # 3. Add data files if they exist (source;dest)
    if os.path.exists('icon.ico'):
        cmd.extend(['--icon', 'icon.ico'])
        cmd.extend(['--add-data', 'icon.ico;.'])
    
    if os.path.exists('sun-valley.tcl'):
        cmd.extend(['--add-data', 'sun-valley.tcl;.'])

    # 4. Run build
    print("Starting build process...")
    try:
        subprocess.check_call(cmd)
        print("\nBuild successful! Executable is in the 'dist/AIChatDesktop' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")

if __name__ == "__main__":
    build()