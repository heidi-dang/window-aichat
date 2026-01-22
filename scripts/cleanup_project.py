import os
import shutil


def cleanup():
    # Files to delete (Unused, redundant, or old)
    files_to_delete = [
        "main-old.py",  # Old version
        "setup_developer_tools.py",  # Already integrated into main.py
        "install_dependencies.cmd",  # Redundant (install.bat is better)
        "build_app.cmd",  # Redundant (build_app.py is better)
    ]

    # Directories to create for organization
    dirs_to_create = ["scripts"]

    # Files to move to 'scripts' folder to declutter root
    files_to_move = [
        "build_web_app.sh",
        "deploy_app.sh",
        "deploy_windows.cmd",
        "diagnose.sh",
        "fix_deployment.sh",
        "fix_env.py",
        "test_on_windows.py",
    ]

    print("=== Starting Project Cleanup ===")

    # 1. Delete unused files
    for file in files_to_delete:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"✓ Deleted: {file}")
            except Exception as e:
                print(f"❌ Error deleting {file}: {e}")
        else:
            print(f"○ Skipped (not found): {file}")

    # 2. Create scripts directory
    for directory in dirs_to_create:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")

    # 3. Move utility scripts
    for file in files_to_move:
        if os.path.exists(file):
            dest = os.path.join("scripts", file)
            try:
                shutil.move(file, dest)
                print(f"✓ Moved {file} -> {dest}")
            except Exception as e:
                print(f"❌ Error moving {file}: {e}")

    print("\n=== Cleanup Complete ===")
    print("Your project root is now cleaner.")
    print("Core logic is separated into 'ai_core.py'.")
    print("Utility scripts are in the 'scripts/' folder.")


if __name__ == "__main__":
    cleanup()
