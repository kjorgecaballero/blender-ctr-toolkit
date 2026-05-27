# Keymaps (Keyboard Shortcuts) – User Guide

The CTR Toolkit provides several default keyboard shortcuts to speed up common tasks. All shortcuts are active only in the **3D Viewport** and **Edit Mode** (where applicable).

---

## Default Shortcuts

| Shortcut       | Action                        | Module                | Mode                 |
| -------------- | ----------------------------- | --------------------- | -------------------- |
| `Ctrl+Shift+E` | Quick Export                  | QB/TB Export          | Any (Object or Edit) |
| `Ctrl+L`       | Navigate block under cursor   | Navigator             | Edit Mode (Mesh)     |
| `Ctrl+Shift+D` | Duplicate block with constant | Navigator / List      | Edit Mode (Mesh)     |
| `Ctrl+Shift+S` | Toggle block seams            | Navigator (Edge menu) | Edit Mode (Mesh)     |

---

## Detailed Descriptions

### `Ctrl+Shift+E` – Quick Export

- Exports all detected quadblocks/triblocks using the last used export settings.
- Saves the OBJ with the scene name (or `untitled.obj`).
- Requires at least one regular export first (to store the export path).
- See QB/TB Export User Guide for details.

### `Ctrl+L` – Navigate Block Under Cursor

- Place the mouse over a face that belongs to a quadblock or triblock.
- Press `Ctrl+L` – the entire block (all 4 faces) becomes selected.
- Works with multiple blocks when using box, circle, or lasso selection.
- Equivalent to clicking the **Navigate** button in the Navigator panel.

### `Ctrl+Shift+D` – Duplicate Block with Constant

- Select faces of a quadblock/triblock (or place cursor inside one).
- Press `Ctrl+Shift+D` – creates a copy of the block as a separate object, preserving its constant material.
- The new object is placed in the same location; move it manually afterward.
- Equivalent to using the **Duplicate Selected** button in the Block List.

### `Ctrl+Shift+S` – Toggle Block Seams

- In Edit Mode, open the **Edge** menu (or UV menu).
- This shortcut marks/seams the edges that separate blocks.
- Useful for UV unwrapping or checking block boundaries.

---

## How to View Current Shortcuts

1. In the CTR panel header, click the **keyboard icon**.
2. A popup displays all default shortcuts.
3. The popup also tells you where to customise them.

---

## Customising Shortcuts

You can change or add new shortcuts:

1. Go to **Edit -> Preferences -> Keymap**.
2. Search for the operator name (e.g. `qb_tb.quick_export`).
3. Click the edit icon next to the existing shortcut.
4. Press your desired key combination.
5. Click **Assign** and save preferences.

### Operator Names for Customisation

| Action                        | Operator ID                     |
| ----------------------------- | ------------------------------- |
| Quick Export                  | `qb_tb.quick_export`            |
| Navigate block under cursor   | `navigator.cursor_select_block` |
| Duplicate block with constant | `list.duplicate_selection`      |
| Toggle block seams            | `list.toggle_block_seams`       |

You can also assign shortcuts to other operators like `psx.toggle_ctr_render` (Render ON/OFF) or `ctr.add_range_box`.

---

## Conflicts with Blender Defaults

None of the CTR Toolkit shortcuts conflict with Blender's native shortcuts:

- `Ctrl+Shift+E` – not used by Blender.
- `Ctrl+L` – default is "Select Linked" (works only in Edit Mode). CTR Toolkit uses the same key but overrides it when a block is detected. Pressing `Ctrl+L` on a non block face still runs Blender's "Select Linked".
- `Ctrl+Shift+D` – not used by Blender.
- `Ctrl+Shift+S` – default is "Save As". In Edit Mode, this shortcut is overridden for the Edge menu only. Outside Edit Mode, it still saves the file.

---

## Troubleshooting

| Issue                                 | Solution                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| Shortcuts do not work                 | Make sure you are in the correct mode (e.g. Edit Mode for navigation).              |
| `Ctrl+L` selects too many faces       | You are not on a block centre face – Blender's native "Select Linked" runs instead. |
| Shortcut conflicts with another addon | Change the shortcut in Keymap preferences.                                          |
| Popup shows wrong shortcuts           | The popup only shows defaults, not your custom ones.                                |
