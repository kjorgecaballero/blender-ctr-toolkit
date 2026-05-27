# Range Box Module – User Guide

The **Range Box** module creates a visual bounding box (1000 x 1000 x 1000 units) centred at the world origin. It helps you keep track of geometry inside the intended playable area – objects outside this box are flagged as **Out of Range** by the Validator module.

> **Important:** The Out‑of‑Range detection uses a **fixed** 1000‑unit box (from -500 to 500 on each axis) that is **always active**. The Range Box object is purely **visual** and does not affect validation or export.

---

## Creating the Range Box

- **Menu:** `Add` (Shift+A) → `CTR` → `Range Box`

After creation, the empty is named **Range**, locked from transformation, and the 3D viewport clip end is increased to 9000 so you can see it from afar.

---

## How Out‑of‑Range Detection Works

- The detection uses a **hardcoded** bounding box: X, Y, Z each from -500 to 500 (total size 1000 units).
- This box is **always active**, even if you never create a Range Box.
- The **Range Box** object is only a **visual reference** – it helps you see the boundaries while modelling.
- You can move, scale, or delete the Range Box at any time; the detection remains unchanged (still uses the fixed 1000‑unit box).

---

## Using the Range Box with Validator

- Once you have a Range Box, you can visually check whether your geometry fits inside the 1000‑unit limit.
- The Validator module (Objects scope or Vertex Groups scope) includes an **Out of Range** filter that flags any object or vertex group that extends outside the fixed box.
- If no Range Box exists, detection still works – only the visual aid is missing.

---

## Technical Details

- The empty cube has a base size of 2x2x2 units. It is scaled by 500 to achieve 1000x1000x1000.
- The addon does not enforce that objects stay inside; it only provides a visual reference and validation flags.
- The detection logic never reads the Range Box object's transform; it always uses the hardcoded -500..500 limits.

---

## Example Workflow

1. Add a Range Box (optional – for visual guidance).
2. Model your mesh – ensure all vertices fit inside the box (use wireframe view to check).
3. Run Validator with filter `Out of Range`. If the mesh is inside, it will not be flagged.
4. Move the tile partially outside – Validator will flag it (even if you delete the Range Box).

---

## Troubleshooting

| Issue                               | Solution                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Range Box does not appear           | Check that the object `Range` exists in the outliner. It may be hidden – unhide it.                                                                                                                                                                                                                                                             |
| Range Box is huge and obscures view | The box is 1000 units wide. Zoom out or set the viewport clip end higher.                                                                                                                                                                                                                                                                       |
| Out of Range detection not working  | Detection is always active. Verify that your object's bounding box actually exceeds -500..500 on any axis. If using Vertex Groups scope, make sure you have **generated vertex groups** (click **Generate** in the Item List panel) and then clicked **Issues** in the Validator to populate the issue data. The Range Box is **not required**. |
