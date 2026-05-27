# Item List Module – User Guide

The **Item List** module displays all detected quadblocks and triblocks in a sortable, filterable list.  
It allows you to select, group, duplicate, and manage constant materials and vertex groups for each block.

---

## Access

1. Open the 3D Viewport sidebar (press `N`).
2. Click the **CTR** tab.
3. Expand the **Navigation List** panel (it is collapsed by default).

> **Requirement:** You must be in **Edit Mode** on a mesh that has block detection data (run **Navigate** from the Navigator panel first).

---

## Display Modes

The panel can show blocks in two different ways. Switch between them using the two buttons at the top of the panel.

| Mode              | Description                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Vertex Groups** | Displays each block as a vertex group (`QB_` for quadblocks, `TB_` for triblocks). Use this mode to generate, clear, and validate vertex groups. |
| **Constant Mat**  | Displays each block as a constant material (material name with `_ID` suffix). Use this mode to assign, clear, and manage navigation points.      |

---

## Vertex Groups Mode

### Prerequisites

- Blocks must be detected (`Navigate` button in Navigator panel).
- Vertex groups are **not** automatically created. You must generate them explicitly.

### Main Controls

| Button       | Action                                                                                                                                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Generate** | Creates a vertex group for every detected quadblock and triblock. Existing block groups are **removed** first to ensure a clean state.                     |
| **Clear**    | Removes vertex groups. A dialog lets you choose: **Clear All** (all groups) or **Clear only selected blocks** (based on face/vertex selection in 3D view). |
| **Groups**   | Dropdown menu that lets you select a vertex group by name and immediately select its vertices/faces in the 3D view.                                        |
| **Check**    | Adds the currently selected blocks (by faces/vertices) to the multi‑selection checklist (see below).                                                       |

### Filters and Sorting

- **QB / TB icons** – Toggle display of quadblocks / triblocks.
- **Check All** – Checks all visible items in the list (respects filters and search).
- **Uncheck All** – Unchecks all visible items.
- **Sort by type** – Toggle between QB‑first / TB‑first sorting.
- **Sort alphabetically** – Toggle A‑Z / Z‑A sorting.
- **Material filter** – Dropdown to show only blocks that use a specific material.
- **Issue filter** – Dropdown to show blocks with specific validation issues (Invalid UVs, Out of Range, Degenerated UVs, etc.). Issues are stored by the **Validate Groups** operator (see below).
- **Search box** – Filters block names, IDs, or material names.

### Multi‑Selection and 3D Selection

- Each item in the list has a **checkbox** on the left.
- Checking/unchecking an item automatically **selects/deselects** the corresponding geometry in the 3D view.
- Use the **Select Multi Checked** operator (available from the **Check** button’s dropdown) to select all checked items in 3D.
- Use the **Add to Checklist** button (next to the list) to add the currently selected 3D blocks to the checklist.

### Validation

| Button                            | Action                                                                                                                                                                                                       |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Validate Groups**               | Analyses every vertex group (or constant material) and stores issues (invalid geometry, UV problems, out of range, etc.) in the object. These issues then become available in the **Issue filter** dropdown. |
| **Warning icon** (on a list item) | Opens a popup with detailed issues for that block.                                                                                                                                                           |

---

## Constant Materials Mode

### Prerequisites

- Blocks must be detected (`Navigate` button in Navigator panel).
- A base material must already be assigned to each block (normal material, not constant).

### Main Controls

| Button                | Action                                                                                                                                                                                                                                                                              |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Assign**            | Opens a dialog to assign a constant material to the **selected block** (one block at a time). The base material name is fixed; you only edit the **ID** part. The final material name becomes `Base_IDid`. IDs must be unique across all constant materials on the object.          |
| **Clear**             | Opens a dialog to clear constant materials. Options: **Clear All**, **Clear Invalid Only** (only broken navigation points), or clear only the selected block. If the original base material is missing, you can enable **Duplicate if missing** to create a fallback base material. |
| **Groups** (dropdown) | Manages **constant material groups** (see below).                                                                                                                                                                                                                                   |
| **Check**             | Adds the currently selected blocks (by faces/vertices) to the multi‑selection checklist.                                                                                                                                                                                            |

### Filters and Sorting (Constant Materials)

- **QB / TB icons** – Toggle display of quadblock / triblock constant materials.
- **Check All / Uncheck All** – Same as vertex groups mode.
- **Sort by type / alphabetically** – Same as vertex groups mode.
- **Material filter** – Dropdown to show only a specific constant material name.
- **Navigation filter** – Three‑state filter: `All` / `Navigation Points` / `Constant Materials (non‑nav)`.
- **Search box** – Filters constant material names, original material names, IDs, or block types.

### Navigation Points

- Each constant material can be marked as a **navigation point**.
- In the list, a special icon (nav point or constant material) toggles the navigation status.
- Navigation points are used by the **Navigator** panel as starting points for block detection.
- The **Navigation filter** dropdown also contains a **Toggle Navigation State** button that marks/unmarks **all currently visible items** as navigation points at once.

### Group Management (Constant Materials)

- You can organise constant materials into named **groups**.
- **Groups dropdown** (labelled with the current active group name) opens the **Manage Groups** dialog.
- In the dialog:
  - Select an existing group from the dropdown.
  - **New Group** – creates a new empty group.
  - **Delete Group** – removes the selected group (does not delete materials).
  - **Add Checked Items** – adds all currently checked list items to the selected group.
  - **Remove Checked Items** – removes checked items from the group.
- When a group is active (selected from the dropdown), the list **only shows materials belonging to that group**.

### Duplicate Block with Constant

- Use the **Duplicate Constant** operator (available from the **Mesh** menu or `Ctrl+Shift+D`) to duplicate selected blocks while preserving constant materials.
- The duplicated block receives a **new unique constant name** (numeric suffix, e.g., `Grass_ID1` → `Grass_ID2`), and its material is set to a **copy of the base material**.
- The operator automatically runs `Find Blocks` on the duplicated geometry so that the new block is detected and added to the list.

---

## Troubleshooting

| Issue                                                  | Solution                                                                                                                                                                                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **No items appear in the list**                        | • Make sure you have run **Navigate** in the Navigator panel.<br>• For Vertex Groups mode, click **Generate** after detection.<br>• Check that the QB/TB filter icons are enabled.<br>• Clear any active material, group, or search filter. |
| **“No blocks found” when assigning constant material** | • Select exactly **one** quadblock or triblock (its 4 faces or its centre vertex/face).<br>• Ensure the block already has a **normal material** assigned.                                                                                   |
| **ID already used error**                              | Every constant material on the same object must have a unique ID. Choose a different ID value.                                                                                                                                              |
| **Constant material name already exists**              | The full name (`Base_IDvalue`) is already used by another material (could be a normal material or a different constant). Rename or delete the conflicting material.                                                                         |
| **Navigation point not recognised by Find Blocks**     | • The constant material must be applied to **exactly 4 faces** that form a valid quadblock or triblock.<br>• Re‑run **Find Blocks** after marking the navigation point.                                                                     |
| **Group management dialog does not show my groups**    | Groups are saved per **scene** (not per object). If you switch scenes, groups are not transferred.                                                                                                                                          |
| **“Duplicate if missing” does not work**               | The fallback mechanism requires the constant material to contain an `_ID` suffix. It strips the suffix to create the base material name.                                                                                                    |

---

## Keyboard Shortcuts (Contextual)

| Shortcut       | Action                                                                    |
| -------------- | ------------------------------------------------------------------------- |
| `Ctrl+Shift+D` | Duplicate the selected block(s) with constant material.                   |
| `Ctrl+Shift+S` | Toggle block seams (marks/unmarks external edges of all detected blocks). |

These shortcuts are active in **Edit Mode** when a mesh with block data is selected.
