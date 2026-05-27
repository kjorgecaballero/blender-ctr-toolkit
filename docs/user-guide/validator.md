# Validator Module – User Guide

The **Validator** module checks meshes (whole objects or vertex groups) for issues such as invalid geometry, UV problems, multiple materials, and out of range position. It can also add suffixes to object names and remove problematic objects or faces.

---

## Access

1. Open the 3D Viewport sidebar (press `N`).
2. Click the **CTR** tab.
3. Select **Validator** from the mode dropdown.

---

## Scope Selector

| Scope             | What it validates                                               |
| ----------------- | --------------------------------------------------------------- |
| **Objects**       | All mesh objects in the scene (or selection).                   |
| **Vertex Groups** | Vertex groups named `QB_*` or `TB_*` on the active mesh object. |

---

## Buttons

| Button     | Action                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------ |
| **Issues** | Runs validation and displays a report (number of valid/invalid items).                           |
| **Select** | Selects the objects / vertex groups that match the current filter.                               |
| **Clear**  | Removes stored validation data (object issues or vertex group issues).                           |
| **Remove** | Opens a dialog to delete objects or remove faces of vertex groups based on selected issue types. |

---

## Filter Dropdowns

### For Objects Scope

| Filter               | Description                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| Quadblocks           | Valid quadblock objects.                                                                                |
| Triblocks            | Valid triblock objects.                                                                                 |
| Invalid Geometry     | Objects that are not a valid quadblock or triblock (including NGons).                                   |
| Invalid UVs          | Objects with UVs outside 0-1 range.                                                                     |
| Invalid Triblock UVs | Triblocks with incorrect UV arrangement.                                                                |
| Degenerated UVs      | Objects where all UVs are identical.                                                                    |
| NGons                | Objects with faces that have more than 4 vertices.                                                      |
| Non Mesh             | Non mesh objects (empties, cameras, etc.).                                                              |
| Out of Range         | Objects whose bounding box extends outside the **fixed** 1000‑unit box (from -500 to 500 on each axis). |
| Multiple Materials   | Objects using more than one material on their faces.                                                    |
| All Invalid          | Any object with at least one issue.                                                                     |

### For Vertex Groups Scope

| Filter               | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Quadblocks           | Vertex groups forming a valid quadblock.                                                    |
| Triblocks            | Vertex groups forming a valid triblock.                                                     |
| Invalid Geometry     | Groups that do not form a valid quad or triblock.                                           |
| Invalid UVs          | Groups with UVs outside 0-1 range.                                                          |
| Invalid Triblock UVs | Triblock groups with incorrect UV arrangement.                                              |
| Degenerated UVs      | Groups where all UVs are identical.                                                         |
| Out of Range         | Groups whose faces lie outside the **fixed** 1000‑unit box (from -500 to 500 on each axis). |
| Multiple Materials   | Groups whose faces use more than one material.                                              |
| All Invalid          | Any group with at least one issue.                                                          |

---

## Workflow Example

1. Model a quadblock – ensure all vertices fit inside the fixed 1000‑unit box (from -500 to 500 on each axis). You can optionally add a **Range Box** (`Shift+A` -> CTR -> Range Box) as a visual reference.
2. Switch to Validator (Objects scope, filter `Out of Range`).
3. Click **Issues** – if you see `out_of_range`, adjust your mesh.
4. Click **Select** – offending objects are highlighted.
5. Fix them manually, then click **Issues** again to update.
6. When ready, click **Remove** (tick `Out of Range`) to delete any still invalid objects.

For vertex groups inside a single mesh:

- Set scope to **Vertex Groups**, filter `Out of Range`.
- First, run **Navigate** in the Navigator panel to detect blocks.
- Then generate vertex groups (`Item List` -> **Generate**).
- Click **Issues** – groups with faces outside the fixed box are flagged.
- Click **Select** – those faces are selected in Edit Mode.
- Fix them, then click **Clear** and **Issues** to re‑validate.

---

## Troubleshooting

| Issue                                      | Solution                                                                                                                                                                         |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Select does nothing in Vertex Groups scope | Ensure you are in Edit Mode and the mesh has vertex groups named `QB_*` or `TB_*`. Generate them if missing.                                                                     |
| Out of Range flag never appears            | The detection uses a **fixed** 1000‑unit box from -500 to 500. Verify that your object/faces actually extend beyond those limits. The optional Range Box object is not required. |
| Suffixes are not added (Objects scope)     | Make sure you are in **Object Mode** (not Edit Mode) and then click the **Issues** button.                                                                                       |
| Remove deletes too many objects            | Uncheck unwanted issue types in the dialog before confirming.                                                                                                                    |
