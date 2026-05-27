# Compatibility

This document describes which Blender versions and platforms are supported, and any version‑specific features or limitations.

## Supported Blender Versions

The CTR Toolkit is officially tested on the following Blender versions:

- **3.3 LTS**
- **3.4**
- **3.5**
- **3.6 LTS**
- **4.0**
- **4.2 LTS**
- **4.5**
- **5.0**

We aim to be compatible with any Blender version **3.3 or newer**. If you encounter an issue on a version not listed, please report it.

## Operating Systems

- Windows (10, 11)
- macOS (11+)
- Linux (Ubuntu 20.04+, or any distribution that runs Blender)

## Feature Availability by Blender Version

| Feature                                         | Minimum Blender Version |
| ----------------------------------------------- | ----------------------- |
| Core tools (Navigator, List, Validator, Export) | 3.3                     |
| `wm.obj_export` (modern OBJ exporter)           | 3.3                     |
| PS1 Resolution (compositing effect)             | 3.5                     |
| Vertex Snap Modifier (`VX_WorldSnap`)           | 4.0                     |
| Split Screen (Properties → 3D View)             | 3.3 (works in all)      |

## Backward Compatibility

- `.blend` files created with older versions of the addon should load without errors.
- Constant material data and vertex group naming conventions are preserved.
- If a breaking change is necessary, a migration script will be provided in the release notes.

## Known Incompatibilities

- The addon does **not** work in Blender 2.9x or earlier.
- Some third‑party addons that heavily override OBJ export operators may cause conflicts. Disable conflicting addons if export fails.
- On macOS with Apple Silicon, the vertex snap modifier may require Rosetta 2 – this is a Blender limitation, not an addon issue.

## Reporting Compatibility Issues

Please include:

- Exact Blender version (e.g., `4.2.0`).
- A minimal `.blend` file that reproduces the issue (if possible).
- Any error messages from the System Console.
