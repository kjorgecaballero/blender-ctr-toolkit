#!/usr/bin/env python3

import subprocess
import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_RUNNER = os.path.join(SCRIPT_DIR, "tests", "test_runner.py")
BLENDER_EXECS_FILE = "blender_execs.txt"
ADDON_NAME = "blender_ctr_toolkit"          # folder name inside Blender's addons
ADDON_SOURCE = SCRIPT_DIR                   # source is the current directory
SPACER = "-" * 79

# Patterns to ignore when copying the addon
IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__", ".git", ".github", "tests", "blender_execs.txt",
    "run_tests.py", "test_results.csv", "*.pyc", ".DS_Store", "*.blend1"
)


def get_blender_execs():
    """Read blender_execs.txt and return list of executable paths."""
    if not os.path.exists(BLENDER_EXECS_FILE):
        print(f"ERROR: {BLENDER_EXECS_FILE} not found!")
        return []
    with open(BLENDER_EXECS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def get_blender_addons_path(blender_exe):
    r"""
    For a given Blender executable (portable Windows), return the path to its user addons folder.
    Example: C:\...\blender-3.3.0-windows-x64\blender.exe
    --> C:\...\blender-3.3.0-windows-x64\3.3\scripts\addons
    """
    blender_dir = os.path.dirname(blender_exe)
    # Find subdirectory that looks like a version number (e.g., "3.3", "3.4", "4.0")
    version_dir = None
    for entry in os.listdir(blender_dir):
        full = os.path.join(blender_dir, entry)
        if os.path.isdir(full) and entry[0].isdigit() and '.' in entry:
            version_dir = entry
            break
    if not version_dir:
        raise RuntimeError(f"Cannot find version folder in {blender_dir}")
    addons_path = os.path.join(blender_dir, version_dir, "scripts", "addons")
    return addons_path


def install_addon_to_blender(blender_exe):
    """Copy the addon source into the target Blender's addons folder."""
    target_addons = get_blender_addons_path(blender_exe)
    target_addon_path = os.path.join(target_addons, ADDON_NAME)

    # Ensure addons folder exists
    os.makedirs(target_addons, exist_ok=True)

    # Remove previous installation if present
    if os.path.exists(target_addon_path):
        print(f"  Removing previous installation at {target_addon_path}")
        shutil.rmtree(target_addon_path)

    # Copy the addon (excluding test files and other cruft)
    print(f"  Copying {ADDON_SOURCE} -> {target_addon_path}")
    shutil.copytree(ADDON_SOURCE, target_addon_path, ignore=IGNORE_PATTERNS)
    return True


def cleanup_addon_from_blender(blender_exe):
    """Remove the addon from Blender's addons folder after tests (optional)."""
    target_addons = get_blender_addons_path(blender_exe)
    target_addon_path = os.path.join(target_addons, ADDON_NAME)
    if os.path.exists(target_addon_path):
        print(f"  Cleaning up {target_addon_path}")
        shutil.rmtree(target_addon_path)


def main():
    blender_execs = get_blender_execs()
    if not blender_execs:
        print("No Blender executables found. Please create blender_execs.txt")
        sys.exit(1)

    any_failed = False
    for exe_path in blender_execs:
        if not os.path.exists(exe_path):
            print(f"Warning: {exe_path} not found, skipping")
            continue

        print(SPACER)
        print(f"Testing with Blender: {exe_path}")

        # Install addon into this Blender version
        try:
            install_addon_to_blender(exe_path)
        except Exception as e:
            print(f"  Failed to install addon: {e}")
            any_failed = True
            continue

        # Run tests
        cmd = [
            exe_path,
            "--background",
            "--factory-startup",
            "-y",
            "--python",
            TEST_RUNNER,
            "--"
        ]
        result = subprocess.run(cmd)

        # Cleanup (comment out to keep addon installed for manual testing)
        cleanup_addon_from_blender(exe_path)

        if result.returncode != 0:
            any_failed = True
            print(f"FAILED: {exe_path} returned {result.returncode}")
        else:
            print(f"PASSED: {exe_path}")

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()