# Navigator Module – User Guide

The **Navigator** module detects, selects and duplicates quadblocks and triblocks.

---

## Access

1. Open the 3D Viewport sidebar (press `N`).
2. Click the **CTR** tab.
3. Select **Navigator** from the mode dropdown.

---

## Detection and Navigation

### Find Blocks (Navigate button)

Detects all quadblocks and triblocks in the active mesh. Can start from:

- **Navigation points** (constant materials marked as navigation points)
- **Current selection** (all faces of a QB/TB, a quadblock centre vertex, or a triblock centre face)

After detection, the addon stores:

- Centre vertices/faces
- Face to block maps
- Groups (blocks that do not share vertices)

### Reset (Clear Cache)

Deletes all addon data on the object: constant materials (restored from backup or fallback), QB/TB vertex groups, and the block detection cache.

> This action cannot be undone.

---

## Selection Tools

| Button        | Action                                                                             |
| ------------- | ---------------------------------------------------------------------------------- |
| **Quadblock** | Selects only the centre vertices of all quadblocks.                                |
| **Triblock**  | Selects only the centre faces of all triblocks.                                    |
| **Invalid**   | Selects faces that are not part of any detected block (useful for finding errors). |

### Group Selection (collapsible)

Blocks are automatically grouped (1 to 8 or more) so that blocks in the same group never share vertices.

- Quadblock groups dropdown + Select button
- Triblock groups dropdown + Select button

---

## Duplication

### Duplicate All Blocks by Group (Duplicate button)

Opens a file dialog to choose an export directory. Then:

1. Duplicates all quadblocks and triblocks by group inside the original mesh.
2. Exports the duplicated blocks to an OBJ file (`duplicates.obj`) with associated textures.
3. Imports the OBJ back, separates loose parts into individual objects.
4. Renames objects based on constant material IDs.
5. **Reassigns constant materials to their original base material** – each duplicated object that originally used a constant material (`Base_ID`) is converted to use the base material (`Base`) instead.
6. Moves all result objects to a collection named `Processed_Blocks`.

> The process temporarily disables PS1 Render and vertex snap modifiers, handles material suffixes (`.001` -> `_001`), and avoids reference bugs.

---

## Cursor / Selection Navigation

- **Navigate from cursor** – Press `Ctrl+L` with the mouse over a face that belongs to a quadblock or triblock. The entire block becomes selected. Works in Edit Mode and supports multi block selection.
- **Navigate from selected faces** – Same operator, but uses the current face selection to select whole blocks.

---

## Keyboard Shortcuts (Default)

| Shortcut       | Action                                             |
| -------------- | -------------------------------------------------- |
| `Ctrl+L`       | Select the entire block under the cursor.          |
| `Ctrl+Shift+D` | Duplicate the block under cursor / selected faces. |
| `Ctrl+Shift+S` | Toggle block seams (Edge menu).                    |

You can customise these in Edit > Preferences > Keymap.

---

## Troubleshooting

| Issue                                                            | Solution                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **No blocks found**                                              | • **Using selection:** Ensure you have selected either: 4 faces forming a complete quadblock or triblock, **OR** a single vertex that is a quadblock centre, **OR** a single triangle face that is a triblock centre.<br>• **Using navigation points:** Verify each constant material is marked as "Is Navigation Point" in the Block List and applied to exactly 4 faces that form a valid block.<br>• Run **Find Blocks** again after correcting the selection or navigation points. |
| **"No valid navigation points found"**                           | Open the **Constant Material Manager** → **Block List** → select a constant material → check **"Is Navigation Point"**. The material must be applied to exactly 4 faces that form a valid quadblock or triblock.                                                                                                                                                                                                                                                                       |
| **Blocks not detected from selection**                           | • **Quadblocks:** Select exactly 4 **quad faces** that meet at a single centre vertex.<br>• **Triblocks:** Select exactly 4 **triangle faces** arranged as a central triangle touching the other three.<br>• **Centre start:** Select a single vertex (quadblock) OR a single triangle face (triblock) that is a valid block centre.                                                                                                                                                   |
| **"Constant material has no texture node" warning during Remap** | PS1 Render mode can block texture node creation. The addon **temporarily disables** PS1 Render, performs the remap, then re‑enables it. No action is needed from you.                                                                                                                                                                                                                                                                                                                  |
| **Shortcuts not working**                                        | • Ensure you are in **Edit Mode**.<br>• Check for conflicts in **Edit > Preferences > Keymap**.<br>• Try resetting to factory keymap if conflicts persist.                                                                                                                                                                                                                                                                                                                             |
| **"Face index out of range" error**                              | The block cache is outdated. Run **Reset (Clear Cache)** followed by **Find Blocks** again.                                                                                                                                                                                                                                                                                                                                                                                            |
