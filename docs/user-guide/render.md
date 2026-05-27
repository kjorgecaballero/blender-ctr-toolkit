# Render Module – User Guide

The **Render** module provides PlayStation 1 style rendering tools: low resolution, pixelated textures, blending modes (additive, subtractive, half‑transparent, and additive translucent), and backface visibility control.

---

## Access

1. Open the 3D Viewport sidebar (press `N`).
2. Click the **CTR** tab.
3. Select **Render** from the mode dropdown.

---

## Main Controls

| Control                 | Description                                                                                                                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Show / Hide**         | Toggles backface visibility on materials. Works globally or on selected faces in Edit Mode.                                                                                        |
| **ON / OFF**            | Activates CTR Render mode: forces nearest neighbour texture filtering, disables shadows, ensures white vertex color attributes, and enables low resolution compositing if toggled. |
| **Apply**               | Immediately applies the selected blend mode to the active material.                                                                                                                |
| **Blend Mode dropdown** | Choose from: Half Transparent, Additive, Subtractive, Additive Translucent.                                                                                                        |

### Blend Mode Formulas

| Mode                 | Formula                           |
| -------------------- | --------------------------------- |
| Half Transparent     | `Background / 2 + Foreground / 2` |
| Additive             | `Background + Foreground`         |
| Subtractive          | `Background - Foreground`         |
| Additive Translucent | `Background + Foreground / 4`     |

---

## Advanced Overrides (Collapsible)

Click **Advanced** to expand three subsections.

### PS1 FX (Blender 3.5 and newer)

| Control                     | Description                                                             |
| --------------------------- | ----------------------------------------------------------------------- |
| **PS1 Resolution**          | Enables low resolution compositing (512x216) with a pixelation effect.  |
| **Grid Size** (Vertex Snap) | Sets the snapping interval for the vertex snap modifier (Blender 4.0+). |
| **Refresh**                 | Updates the vertex snap modifier on selected objects.                   |
| **Add**                     | Adds the VX_WorldSnap geometry node modifier to selected meshes.        |
| **Remove**                  | Removes the vertex snap modifier.                                       |

### Blending

| Control               | Description                                                            |
| --------------------- | ---------------------------------------------------------------------- |
| **Override dropdown** | Forces a specific blend method: Auto, Opaque, Clip, Hashed, Blend.     |
| **Apply**             | Applies the override to the active material (if CTR Render is active). |
| **Reset**             | Returns to automatic blend method.                                     |

### View

| Control          | Description                                                                             |
| ---------------- | --------------------------------------------------------------------------------------- |
| **Split Screen** | Converts the Properties editor area into a rendered 3D Viewport. Click again to revert. |

---

## Material Specific Properties

When a material is selected, the Material Properties tab (Properties Editor) shows extra settings:

- **PS1 Blend Mode** – per material blend mode
- **Show Backface** – per material backface visibility.
- **Blend Method Override** – same as the Blending section override.

---

## Workflow Example

1. Assign image textures to your materials.
2. Click **ON** to activate CTR Render.
3. Choose a blend mode (e.g. Additive) and click **Apply**.
4. If some faces disappear, click **Show**.
5. Enable **PS1 Resolution** for a low resolution look.
6. To snap vertices to a grid (Blender 4.0+), set a grid size and click **Add**.
7. To exit, click **OFF** – all settings revert.

---

## Troubleshooting

| Issue                                   | Solution                                                                                                                                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Materials appear black                  | Ensure the material has a texture image assigned.                                                                                                                                           |
| Vertex snap buttons missing             | Your Blender version is below 4.0. Update to use this feature.                                                                                                                              |
| Split Screen does nothing               | An existing Properties area is required (e.g. the default right side panel).                                                                                                                |
| Vertex colors do not multiply correctly | Make sure the mesh has **only one** Color Attribute and that its name has **not been changed** from the default (e.g., "Col"). Extra or renamed attributes can break the CTR Render effect. |
