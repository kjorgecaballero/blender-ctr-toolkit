# Testing the CTR Toolkit

This guide explains how to run the CTR Toolkit test suite locally and how to write new tests.

---

# Prerequisites

- **Python 3.11 or higher** installed on your system.
- **One or more Blender versions** installed locally (portable or standard).
- A **`blender_execs.txt`** file in the project root, containing the full paths to each `blender.exe` (one per line).

## Example `blender_execs.txt` (Windows)

```txt
C:\Users\YourName\Blender\blender-3.3.0-windows-x64\blender.exe
C:\Users\YourName\Blender\blender-4.0.0-windows-x64\blender.exe
C:\Users\YourName\Blender\blender-4.2.0-windows-x64\blender.exe
```

On macOS/Linux, use the path to the `blender` executable instead.

Example:

```txt
/Applications/Blender.app/Contents/MacOS/Blender
```

---

# Running Tests Locally

1. Open a terminal in the project root folder.
2. Run the orchestrator script:

```bash
python run_tests.py
```

This script will:

- Copy the addon into each Blender version's `scripts/addons` folder.
- Launch each Blender in background mode (`--background`).
- Execute the test suite inside that Blender.
- Report a summary in the terminal.

---

# Test Results

- A summary is printed directly in the terminal (pass/fail per Blender version).
- Detailed results are saved in `test_results.csv`.

The CSV file contains:

- Blender version
- Number of executed tests
- Failures
- Errors

---

# Writing New Tests

Place new test files inside the `tests/` folder.

Test files must follow this naming convention:

```txt
test_*.py
```

This allows Python's `unittest` discovery system to find them automatically.

Use Python's built-in `unittest` framework.

Each test file can directly import addon modules.

---

# Example Test Structure

```python
import unittest
import bpy


class MyFeatureTest(unittest.TestCase):

    def setUp(self):
        # Start from a clean Blender file before each test
        bpy.ops.wm.read_homefile(use_empty=True)

    def test_operator_registered(self):
        self.assertTrue(hasattr(bpy.ops.myaddon, 'my_operator'))

    def test_feature_works(self):
        bpy.ops.mesh.primitive_cube_add()

        obj = bpy.context.active_object

        self.assertEqual(obj.name, "Cube")
```

---

# Important Notes for Test Writers

## Avoid UI Dependencies

Tests run in background mode:

```bash
--background
```

Because of this:

- Do not rely on:
  - `bpy.context.area`
  - `bpy.context.window`
  - UI panels
  - dialogs
  - screen regions

Operators that open file dialogs must be executed using:

```python
'EXEC_DEFAULT'
```

instead of:

```python
'INVOKE_DEFAULT'
```

---

## Protect Keymaps and Timers

In your addon's `__init__.py`, wrap keymap/timer registration logic like this:

```python
if not bpy.app.background:
    register_keymaps()
```

This prevents failures in headless environments.

---

## Reset the Scene Between Tests

Always start tests from a clean file:

```python
def setUp(self):
    bpy.ops.wm.read_homefile(use_empty=True)
```

This prevents state leakage between tests.

---

## Skip Tests Conditionally

Use `@unittest.skipIf` when:

- A test requires a specific Blender version.
- A test requires a UI environment.
- A feature only exists in certain Blender releases.

Example:

```python
@unittest.skipIf(
    bpy.app.version < (4, 0, 0),
    "Requires Blender 4.0+"
)
def test_new_feature(self):
    pass
```

---

# Continuous Integration

The test suite runs automatically on GitHub Actions for:

- Every push
- Every pull request

The workflow:

1. Uses `blender-downloader` to fetch Blender versions:
   - 3.3
   - 3.6
   - 4.2

2. Runs:

```bash
python run_tests.py
```

3. Uploads `test_results.csv` as a workflow artifact.

You do **not** need to commit `blender_execs.txt` to the repository.

The CI environment downloads its own Blender copies automatically.

---

# Troubleshooting Tests

| Issue                                                        | Solution                                                                                                 |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'blender_ctr_toolkit'` | Ensure `blender_execs.txt` contains valid Blender paths and that Blender folders are write-accessible.   |
| Tests fail only on specific Blender versions                 | Check for Blender API differences using `bpy.app.version`.                                               |
| `bpy.ops.wm.obj_export` not found                            | Some Blender versions use `export_scene.obj`. Use the compatibility layer provided by the addon.         |
| Test hangs indefinitely                                      | Avoid infinite loops and operators that require user interaction. Use `'EXEC_DEFAULT'` for file dialogs. |

---

# Recommended Project Structure

```txt
blender-ctr-toolkit/
├── operators/
├── ui/
├── utils/
├── tests/
│   ├── test_export.py
│   ├── test_import.py
│   └── test_materials.py
├── run_tests.py
├── blender_execs.txt
└── test_results.csv
```

---

# Best Practices

- Keep tests isolated.
- Avoid relying on object names unless necessary.
- Use temporary data whenever possible.
- Prefer deterministic tests over random behavior.
- Test operators, utilities, and compatibility layers separately.
- Write regression tests for every reported bug you fix.

---

# Example Version Compatibility Check

```python
if bpy.app.version >= (4, 0, 0):
    # Blender 4.x code
else:
    # Blender 3.x fallback
```

---

# Running a Single Test File

You can also run a specific test module manually:

```bash
python -m unittest tests.test_export
```

Or from Blender directly:

```bash
blender --background --python tests/test_export.py
```

---

# Final Notes

A good automated test suite helps ensure:

- Blender version compatibility
- Stable exports/imports
- Reliable operator behavior
- Safer refactors
- Faster development cycles

When adding new features to the CTR Toolkit, consider adding at least one automated test alongside the implementation.
