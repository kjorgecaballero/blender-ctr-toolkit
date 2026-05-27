# Blender CTR Toolkit

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)
[![Blender](https://img.shields.io/badge/Blender-3.3%2B-orange)](https://www.blender.org/)

**A Blender addon for Crash Team Racing track development.**

---

## Features

- **Navigator** – Detect quadblocks and triblocks, select by group, duplicate entire sets.
- **Item List** – Interactive checklist, assign constant materials, navigation points, groups.
- **Validator** – Find invalid geometry, UV issues, out‑of‑range objects.
- **Render** – PS1 blend modes (additive, subtractive, half‑transparent, additive translucent), backface culling, vertex snap (Blender 4.0+), low‑resolution compositing.
- **Export** – Export to OBJ with texture copying and mass duplication. Filters out QB/TB with **issues**.
- **Material Manager** – Manage constant materials and navigation points: remap textures, rename materials, select faces by material family.
- **Range Box** – Visual 1000‑unit boundary reference.

---

## Installation

1. Download the latest `.zip` from the [Releases page](https://github.com/kjorgecaballero/blender-ctr-toolkit/releases).
2. In Blender, go to **Edit → Preferences → Add‑ons → Install…** and select the `.zip`.
3. Enable **Blender CTR Toolkit**.

See [Installation Guide](docs/installation.md) for details.

---

## Compatibility

- **Blender 3.3 to 5.0** – The addon is designed to work on any version from 3.3 LTS up to 5.0.
- **PS1 Resolution** (low‑resolution compositing) – Requires **Blender 3.5 or newer**.
- **Vertex Snap Modifier** (`VX_WorldSnap`) – Requires **Blender 4.0 or newer**.
- **Advanced Overrides (PS1 FX section)** – Only visible in Blender 3.5+ (for resolution) and 4.0+ (for vertex snap). In Blender 3.3‑3.4, these options are hidden.
- **OBJ Export** – The addon automatically uses `wm.obj_export` (Blender 3.3+) or falls back to `export_scene.obj` for older versions (handled by `compat.py`).
- All other core features (Navigator, Item List, Validator, Material Manager, Export filters) work on **Blender 3.3 and above**.

---

## Documentation

- [User Guides](docs/user-guide/index.md) – Detailed module documentation.
- [Contribution Guidelines](docs/contributing/guidelines.md) – How to report issues, submit code.
- [Testing](docs/contributing/testing.md) – Run the test suite locally.

Help buttons (documentation, tutorials, issue tracker, keymaps) are available in the CTR panel header.

---

## Exporting to CrashTeamEditor

The addon exports OBJ files that are **directly compatible** with [CrashTeamEditor](https://github.com/mateusfavarin/CrashTeamEditor).  
The exporter filters out QB/TB with issues based on the editor.

---

## Auto Updater

The addon includes an automatic updater (based on [CGCookie's updater](https://github.com/CGCookie/blender-addon-updater)).

- Checks for new releases on GitHub.
- Shows a red Blender icon in the CTR panel header when an update is available.
- One‑click installation; restart Blender to complete.

You can also check manually in **Edit → Preferences → Add‑ons → Blender CTR Toolkit → Update Settings**.

---

## Manual Testing

The `examples/` folder contains a Blender file (`scene_test.blend`) with sample meshes for manual testing.  
See [examples/README.md](examples/README.md) for test results.

---

## Contributing

Contributions are welcome! Read [Contribution Guidelines](docs/contributing/guidelines.md) and [Testing](docs/contributing/testing.md).

---

## License

GNU General Public License v2.0. See [LICENSE](LICENSE).

---
