# Material Manager – User Guide

The **Material Manager** is a dedicated panel in the Properties Editor that helps you handle constant materials – duplicates of a base material that share the same texture but have a different ID (e.g. `Ground_ID01`, `Ground_ID02`).

---

## Access

- Select a mesh object.
- Go to the **Properties Editor** → **Material** tab.
- Look for the **Constant Material Manager** panel.

---

## Layout

| Element             | Description                                                                                           |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| **Filter dropdown** | Show All, Normal (non constant), Constant, or Nav Point materials.                                    |
| **Search bar**      | Filter by name.                                                                                       |
| **Action row 1**    | Assign, Select, Deselect (works on the selected material in the list).                                |
| **Action row 2**    | Rename, Remap, Refresh.                                                                               |
| **List**            | Displays materials with a checkbox icon to select/deselect. Pagination appears if more than 10 items. |

---

## Operations

### Assign, Select, Deselect (Edit Mode required)

- **Assign** – Assigns the selected material to the currently selected faces. If the faces belong to a quadblock or triblock, the whole block receives the material.

  > Cannot assign constant/navigation materials with this button – use the Block List panel instead.

- **Select** – Opens a popup to choose the selection scope:
  - Checked: only the exact material.
  - Full: the base material + all its constants (including nav points).
  - Constants: only constant materials (excludes base and nav points).
  - Nav Points: only navigation point constants.
    The operator selects all faces using those materials.

- **Deselect** – Same scopes, but deselects faces.

### Rename Material

- **Normal materials** – enter a new name.
- **Constant materials** – the dialog splits the name into Material (base) and ID (suffix).
  - Changing the base name renames the entire family (base + all constants that share that base).
  - Changing the ID only affects the selected constant.
  - The operator checks for name uniqueness and ID uniqueness across the object.

### Remap Material

Changes the texture image for the selected material and all derived materials (base + constants).

- Type the image name or click the folder icon to load an image from disk.
- If the selected material lacks a texture node, the operator temporarily disables PS1 Render (if active) to safely create the node.

### Refresh List

- **Refresh** – rebuilds the material list (useful after adding/renaming materials).
- Check **Purge unused** before confirming to delete all unused data blocks (materials, textures, images).

---

## Workflow Example

1. Filter by **Constant** to see all constant materials.
2. Select a constant, click **Rename**, change its ID (e.g. from `01` to `99`).
3. To change the texture for an entire family, select any constant of that family, click **Remap**, choose a new image. All constants that share the same base will update.
4. Use **Select** with scope `Full` to select all faces of a material family, then assign a different material.

---

## Troubleshooting

| Issue                                     | Solution                                                                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Assign button disabled                    | You cannot assign constant/navigation materials via the Material Manager – use the Block List panel (Constant Materials mode). |
| Remap does nothing                        | The material may have no texture node. Toggle PS1 Render off and on, then try again.                                           |
| Renaming fails with "name already exists" | Choose a unique name; constant IDs must be unique per object.                                                                  |
