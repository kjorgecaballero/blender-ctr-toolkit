# QB/TB Export Module – User Guide

The **QB/TB Export** module exports quadblocks and triblocks to OBJ format, with advanced filtering, texture handling, folder organisation, and support for duplicate export. It is accessible from **File -> Export -> Qb/Tb (.obj)** or via quick export (`Ctrl+Shift+E`).

---

## Access

| Method             | Action                                                  |
| ------------------ | ------------------------------------------------------- |
| Main export dialog | `File` -> `Export` -> `Qb/Tb (.obj)`                    |
| Quick export       | `Ctrl+Shift+E` (uses last export location and settings) |

---

## Main Export Dialog Sections

### 1. Export Scope

- **Selection Only** – export only selected objects (otherwise exports all mesh objects).

### 2. Types

- **Quadblocks** – include valid quadblocks.
- **Triblocks** – include valid triblocks.

### 3. Preprocessing

- **Apply Modifiers** – applies all modifiers temporarily during export (does not modify original data).
- **Separate by Loose Parts** – splits meshes into separate objects for each disconnected component before validation.

### 4. Issue Filtering

These options control which objects are excluded.  
Disabled = exclude objects with that issue.  
Enabled = allow exporting objects with that issue.

| Option               | When enabled                                    |
| -------------------- | ----------------------------------------------- |
| Out of Range         | Allows objects outside the 1000x1000x1000 area. |
| Invalid UVs          | Allows objects with UVs outside 0-1 range.      |
| Invalid Triblock UVs | Allows triblocks with incorrect UV arrangement. |
| Degenerated UVs      | Allows objects with zero area UVs.              |
| Multiple Materials   | Allows blocks using more than one material.     |

> **Note:** The out‑of‑range check always uses a fixed bounding box of 1000 units (from -500 to 500 on each axis), centred at the world origin. The optional **Range Box** object is only a visual reference; it is not required for the filter to work.

### 5. Duplicates

- **Export Duplicates** – instead of exporting original blocks, duplicates every detected block by group and exports those duplicates.
- **Export Processed** – after duplication, the duplicated objects are also processed through the normal export pipeline. The final OBJ is saved inside an `export/` subfolder.

### 6. Output

- **Export to Folder** – organises exports into a structured folder hierarchy.
- **Folder Behavior** – `Replace` (overwrites existing folders) or `Incremental` (creates numbered subfolders: `001/`, `002/`, ...).
- **Path Mode** – controls texture paths in the .mtl file: Auto, Absolute, Relative, Copy, Strip.
- **Copy Textures** – copies used textures into a `textures/` folder next to the OBJ.
- **Remap Textures** – after copying, updates material nodes inside Blender to point to the copied textures (requires `Copy Textures`).

### 7. Metadata

- **Export Details (JSON)** – creates a `log/Details.json` file with export statistics, per object issues, and settings.

---

## Quick Export (`Ctrl+Shift+E`)

- Uses the same settings as the last regular export.
- Saves the OBJ with the name of the current Blender scene (or `untitled.obj`).
- Requires at least one successful regular export to store the export location.

---

## Export Statistics (Info Line)

After export, Blender's info line reports:

- Number of exported quadblocks and triblocks.
- Count of objects with UV issues (if allowed).
- Number of objects filtered out because they were out of range.
- The folder name (if `Export to Folder` was used).

---

## Workflow Example (Massive Tile Duplication)

1. Run **Navigator -> Find Blocks** to detect all blocks.
2. _(Optional)_ Add a **Range Box** (`Shift+A` -> `CTR` -> `Range Box`) if you want a visual reference of the 1000‑unit limit.
3. Open export dialog: `File -> Export -> Qb/Tb (.obj)`.
4. Enable **Export Duplicates** and **Export Processed**.
5. Disable **Out of Range** to keep all objects (including those outside the 1000‑unit area).
6. Enable **Copy Textures** and **Remap Textures** if needed.
7. Click Export. The addon will:
   - Duplicate every detected block by group.
   - Export duplicates to a `duplicates/` folder.
   - Export processed objects (with material renaming) to an `export/` subfolder.
   - Copy textures and remap material nodes.
8. Later, press `Ctrl+Shift+E` to repeat with the same settings.

---

## Troubleshooting

| Issue                                        | Solution                                                                                                                                                                                                                                                                                       |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No objects exported                          | Ensure you have valid quadblocks/triblocks and that filters are not excluding them.                                                                                                                                                                                                            |
| Quick export does nothing                    | First perform a regular export to save the export location.                                                                                                                                                                                                                                    |
| Textures not copied                          | Enable **Copy Textures** and ensure textures are not packed (packed textures are saved as files).                                                                                                                                                                                              |
| Out of range filtering ignored               | The filter always uses the fixed 1000‑unit boundary. The Range Box is only visual.                                                                                                                                                                                                             |
| Duplicates not created                       | Run `Navigator -> Find Blocks` before exporting.                                                                                                                                                                                                                                               |
| Not all quadblocks or triblocks are exported | Check which **Issue Filtering** options are enabled (e.g., Invalid UVs, Out of Range). Disable them temporarily to see if more blocks appear. Use the **Validator** module (Objects scope, filter `All Invalid`) to identify which blocks have issues, then fix those issues before exporting. |
