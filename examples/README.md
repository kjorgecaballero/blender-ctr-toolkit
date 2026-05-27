# Test Scene: qb_tb Module Compatibility

**Scene created with:** Blender 3.3  
**Maximum supported version:** 5.0 (tested)

## Purpose

This `.blend` file is intended for **manual testing** only.  
It contains sample meshes to help you verify that the CTR Toolkit addon works correctly on your Blender version.  
No automated tests depend on this file; the automated test suite creates its own temporary scenes.

## Test Results

| Blender Version | Status        | Notes                                 |
| --------------- | ------------- | ------------------------------------- |
| 3.3             | Fully Working | Scene created in this version         |
| 3.6             | Fully Working | All features functional               |
| 4.0             | Fully Working | No compatibility issues               |
| 4.2             | Fully Working | Module behaves as expected            |
| 4.5             | Fully Working | Stable performance                    |
| 5.0             | Fully Working | Full compatibility confirmed          |
| 3.4, 3.5        | Not Tested    | Expected to work (same series as 3.3) |
| 4.1, 4.3, 4.4   | Not Tested    | Expected to work (minor versions)     |
| < 3.3           | Not Supported | Scene uses features from Blender 3.3+ |

## How to Use

1. Open the `.blend` file in Blender.
2. Enable the **CTR Toolkit** addon if not already enabled.
3. Switch to the **CTR** tab in the 3D Viewport sidebar (press `N`).
4. Test features:
   - **Navigator** – Run `Find Blocks` on the example meshes.
   - **Item List** – Generate vertex groups or assign constant materials.
   - **Validator** – Run `Issues` to see validation results.
   - **Render** – Enable CTR Render to test blend modes.
   - **Export** – Try exporting the scene to OBJ.

If you encounter any issues on a tested version, please report them on the [GitHub issue tracker](https://github.com/kjorgecaballero/blender-ctr-toolkit/issues).

---

_This file is part of the [Blender CTR Toolkit](https://github.com/kjorgecaballero/blender-ctr-toolkit)._
