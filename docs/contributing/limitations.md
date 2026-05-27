# Limitations

This document outlines known technical limitations of the CTR Toolkit, particularly those related to Blender’s APIs and the addon’s design.

## General Limitations

- **Edit Mode required** – Detection, selection, and duplication of blocks only work when the mesh is in **Edit Mode**.
- **No Ngons** – Faces with more than 4 vertices are ignored by block detection and flagged as `invalid_geometry` by the Validator.
- **Constant materials are per‑object** – The `constant_materials` dictionary is stored on each object individually. Sharing constants across objects is not supported.

## Navigator Module

- Quadblock detection expects exactly **4 quad faces** around a single central vertex.
- Triblock detection expects exactly **4 triangular faces** (one central triangle + three adjacent triangles) with correct edge sharing.
- Duplication (Duplicate All Blocks) moves the source mesh to the **root collection** temporarily to avoid a Blender bug. This is normal behaviour.

## Item List Module

- Vertex groups are **static** – they are not automatically updated when the mesh changes. You must re‑run `Generate` after editing.
- Constant material groups are stored **per scene**, not per object. Groups do not survive copying objects to another scene.

## Validator Module

- **Out‑of‑range detection** uses a **hardcoded** 1000‑unit box from `(-500,-500,-500)` to `(500,500,500)`. The optional `Range` empty is purely visual and does **not** affect validation.
- The **Remove** button deletes objects or faces irreversibly (undo is available only within the current Blender session).
- Vertex group validation requires **vertex groups** to exist. Run `Item List → Generate` first.

## Render Module

- Vertex snap modifier (`VX_WorldSnap`) requires **Blender 4.0 or newer**.
- PS1 Resolution effect uses the **Compositor**. If compositing is disabled, the effect will not be visible.
- Split Screen only works when there is an existing **Properties** area (e.g., the default right‑side panel in the 3D Viewport).
- The render effect expects a **single Color Attribute** named exactly `VertexColor`. Extra or renamed attributes break the effect.

## Export Module

- Texture remapping modifies material nodes **inside Blender** and may affect other objects sharing the same material. Use with caution.
- Massive duplication (Export Duplicates + Processed) can be slow on meshes with thousands of blocks.
- The duplicate export process temporarily disables PS1 Render and vertex snap modifiers – this is normal.

## Updater Module

- Works only with **public GitHub repositories**. Private forks are not supported.
- On some corporate networks, SSL certificate verification may fail – use the manual download option.
- After updating, Blender **must be restarted** for changes to take full effect.

## Testing Environment

- Tests run in **background mode** (`--background`). Operators that open file dialogs must be called with `'EXEC_DEFAULT'`, not `'INVOKE_DEFAULT'`.
- Keymap registration and timers are automatically skipped in background mode to prevent errors.
