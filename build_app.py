import os
import shutil
import subprocess
import sys
import stat
import time

def remove_readonly(func, path, _):
    """Helper to remove read-only files on Windows"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def build():
    # 1. Clean previous build artifacts
    print("Cleaning previous build artifacts...")
    
    # Attempt to kill the app if it's running to release file locks
    subprocess.run("taskkill /F /IM AIChatDesktop.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1) # Give OS time to release handles

    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Removing {folder}...")
            try:
                shutil.rmtree(folder, onerror=remove_readonly)
            except Exception as e:
                print(f"Initial delete failed: {e}. Retrying...")
                time.sleep(2)
                try:
                    shutil.rmtree(folder, onerror=remove_readonly)
                except Exception as e2:
                    print(f"\n❌ ERROR: Could not delete '{folder}'.")
                    print("Please ensure 'AIChatDesktop.exe' is closed and no folders are open in Explorer.")
                    return
            print(f"Removed {folder}/")
    
    spec_file = 'AIChatDesktop.spec'
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"Removed {spec_file}")
        except Exception:
            pass

    # 2. Construct PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'main.py',
        '--name', 'AIChatDesktop',
        '--windowed',  # No console window
        '--clean',     # Clean PyInstaller cache
        '--noconfirm', # Overwrite output directory
        
        # Explicitly import local modules
        '--hidden-import', 'github_handler',
        '--hidden-import', 'ai_core',
        '--hidden-import', 'ui.settings_window',
        '--hidden-import', 'ui.dev_tool_window',
        '--hidden-import', 'ui.code_chat_window',

        # Common hidden imports
        '--hidden-import', 'PIL',
        '--hidden-import', 'cryptography',
        '--hidden-import', 'pygments',
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
        print("\n✅ Build successful! Executable is in the 'dist/AIChatDesktop' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code {e.returncode}")

if __name__ == "__main__":
    build()
