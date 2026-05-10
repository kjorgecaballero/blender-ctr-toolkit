import sys
import os
import unittest
import bpy


# 1. Determine where the addon is installed

# test_runner.py is inside the 'tests' folder of the addon.
# The addon root is the parent directory of 'tests'.
ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The folder that contains the addon (scripts/addons) is the parent of ADDON_ROOT.
ADDONS_PARENT = os.path.dirname(ADDON_ROOT)

# Add the addons folder to sys.path (necessary in Blender 4.2+)
if ADDONS_PARENT not in sys.path:
    sys.path.insert(0, ADDONS_PARENT)

ADDON_NAME = "blender_ctr_toolkit"


# 2. Import the addon (with fallback to official enable)

try:
    # Direct import (works in all versions if sys.path is correct)
    import blender_ctr_toolkit
    print(f"Add-on '{ADDON_NAME}' imported directly from {ADDON_ROOT}")
except ModuleNotFoundError as e:
    print(f"Direct import failed: {e}. Trying to enable via addon_utils...")
    try:
        import addon_utils
        # Enable the addon by its module (must be in the addons folder)
        if addon_utils.enable(ADDON_NAME) is not None:
            import blender_ctr_toolkit
            print(f"Add-on '{ADDON_NAME}' enabled and imported successfully.")
        else:
            raise Exception(f"Could not enable add-on '{ADDON_NAME}'.")
    except Exception as enable_error:
        print(f"Failed to enable add-on: {enable_error}")
        print(f"Add-on root: {ADDON_ROOT}")
        print(f"Addons parent directory: {ADDONS_PARENT}")
        print("Contents of addons parent:")
        try:
            for item in os.listdir(ADDONS_PARENT):
                print(f"  - {item}")
        except Exception:
            print("   Could not list directory.")
        sys.exit(1)


# 3. Discover and run tests

def get_test_suite():
    """Discover all tests in the tests folder (pattern test_*.py)."""
    test_dir = os.path.dirname(__file__)
    return unittest.defaultTestLoader.discover(test_dir, pattern="test_*.py")


def run_tests():
    """Run all discovered tests and report results."""
    print("\n" + "-" * 79)
    print(f"Running tests for Blender {bpy.app.version}")
    print("-" * 79)

    suite = get_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    csv_path = os.path.join(ADDON_ROOT, "test_results.csv")
    with open(csv_path, "a") as f:
        f.write(f"{bpy.app.version},{result.testsRun},{len(result.failures)},{len(result.errors)}\n")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())