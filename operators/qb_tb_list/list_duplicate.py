import bpy
import bmesh
import time
import re
from mathutils import Vector
from bpy.types import Operator


def duplicate_selected_faces_bmesh(bm):
    """Duplicate selected faces in bmesh and return list of new faces."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        return [], 0

    old_face_count = len(bm.faces)
    ret = bmesh.ops.duplicate(bm, geom=selected_faces, use_select_history=False)
    new_faces = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMFace)]

    # Deselect originals, select new faces
    for f in selected_faces:
        f.select = False
    for f in new_faces:
        f.select = True

    return new_faces, old_face_count


def deep_copy_idprop_group(group):
    """
    Recursively convert Blender IDPropertyGroup (or any mapping/list)
    to plain Python dicts/lists so we can safely copy and modify them.
    """
    if hasattr(group, 'items'):          # mapping (dict, IDPropertyGroup, etc.)
        return {k: deep_copy_idprop_group(v) for k, v in group.items()}
    elif isinstance(group, (list, tuple)):
        return [deep_copy_idprop_group(item) for item in group]
    else:
        return group                     # primitive (str, int, float, bool)


class LIST_OT_DuplicateSelection(Operator):
    bl_idname = "list.duplicate_selection"
    bl_label = "Duplicate Block(s) with Constant"
    bl_description = "Duplicate selected blocks, restore base material, and assign a new constant with numeric suffix"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def _get_next_constant_name(self, obj, base_mat_name):
        """
        Return a new unique constant material name derived from base_mat_name,
        using an incremental numeric suffix (001, 002, ...).
        """
        const_dict = obj.get("constant_materials", {})
        max_num = 0
        for const_name, info in const_dict.items():
            if info.get("original_material") == base_mat_name:
                # Extract trailing numeric suffix (e.g., "001", "042")
                match = re.search(r'(\d+)$', const_name)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
                    except ValueError:
                        pass
        next_num = max_num + 1
        return f"{base_mat_name}{next_num:03d}"

    def execute(self, context):
        print("--- DEBUG: Duplicate operator started ---")
        obj = context.edit_object

        # Ensure face selection mode
        context.tool_settings.mesh_select_mode = (False, False, True)

        # 1. Get selected faces
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        selected_faces = [f for f in bm.faces if f.select]

        if not selected_faces:
            self.report({'WARNING'}, "No faces selected.")
            return {'CANCELLED'}

        # 2. Detect blocks with constant material within selection
        face_to_quad = obj.get("face_to_quadblock", {})
        face_to_tri = obj.get("face_to_triblock", {})
        quad_centers = set(obj.get("quadblock_centers", []))
        selected_verts = [v for v in bm.verts if v.select]

        found_blocks = set()
        for face in selected_faces:
            idx = str(face.index)
            if idx in face_to_quad:
                found_blocks.add(('quadblock', int(face_to_quad[idx])))
            elif idx in face_to_tri:
                found_blocks.add(('triblock', int(face_to_tri[idx])))

        for vert in selected_verts:
            if vert.index in quad_centers:
                found_blocks.add(('quadblock', vert.index))

        if not found_blocks:
            self.report({'WARNING'}, "No blocks with constant material found in selection.")
            return {'CANCELLED'}

        # 3. Store info for each block (including center coordinate and navigation status)
        blocks_info = []
        const_materials = obj.get("constant_materials", {})
        for block_type, block_id in found_blocks:
            const_prop = f"constant_name_{block_type}_{block_id}"
            if const_prop not in obj:
                continue
            const_name = obj[const_prop]
            const_info = const_materials.get(const_name, {})
            base_mat_name = const_info.get("original_material",
                                            const_name.split('_ID')[0] if '_ID' in const_name else const_name)
            is_nav_point = const_info.get("is_navigation_point", False)

            if block_type == 'quadblock':
                center_vert = bm.verts[block_id] if block_id < len(bm.verts) else None
                if not center_vert:
                    continue
                center_co = center_vert.co.copy()
            else:  # triblock
                center_face = bm.faces[block_id] if block_id < len(bm.faces) else None
                if not center_face:
                    continue
                center_co = center_face.calc_center_bounds()
            blocks_info.append({
                'type': block_type,
                'id': block_id,
                'const_name': const_name,
                'base_mat_name': base_mat_name,
                'center_co': center_co,
                'is_navigation_point': is_nav_point,
            })

        if not blocks_info:
            self.report({'ERROR'}, "None of the selected blocks have a constant material.")
            return {'CANCELLED'}

        # 4. Duplicate ALL selected faces
        new_faces, old_face_count = duplicate_selected_faces_bmesh(bm)
        bmesh.update_edit_mesh(obj.data)

        if not new_faces:
            self.report({'ERROR'}, "Duplicate operation failed. No new faces created.")
            return {'CANCELLED'}

        new_face_indices = [f.index for f in new_faces]

        # 5. Refresh bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        new_const_names = []

        # 6. Process each original block
        processed = 0
        for info in blocks_info:
            # Find duplicated center by coordinate
            new_center = None
            if info['type'] == 'quadblock':
                for v in bm.verts:
                    if (v.co - info['center_co']).length < 0.001 and v.index != info['id']:
                        if len(v.link_faces) == 4:
                            new_center = v
                            break
            else:
                for f in bm.faces:
                    if (f.calc_center_bounds() - info['center_co']).length < 0.001 and f.index != info['id']:
                        if len(f.verts) == 3:
                            adj = self.find_adjacent_triangular_faces(f)
                            if len(adj) == 3:
                                new_center = f
                                break
            if not new_center:
                self.report({'WARNING'}, f"Could not locate duplicated block for {info['const_name']}")
                continue

            # Get the 4 faces of this block
            if info['type'] == 'quadblock':
                face_indices = [f.index for f in new_center.link_faces]
            else:
                adj = self.find_adjacent_triangular_faces(new_center)
                if len(adj) != 3:
                    self.report({'WARNING'}, f"Triblock at face {new_center.index} does not have 3 adjacent triangles.")
                    continue
                face_indices = [new_center.index] + [f.index for f in adj]

            if len(face_indices) != 4:
                self.report({'WARNING'}, f"Block {info['const_name']} has {len(face_indices)} faces, expected 4.")
                continue

            # Restore base material
            base_mat = bpy.data.materials.get(info['base_mat_name'])
            if not base_mat:
                self.report({'ERROR'}, f"Base material '{info['base_mat_name']}' not found")
                continue
            if info['base_mat_name'] not in obj.data.materials:
                obj.data.materials.append(base_mat)
            base_mat_index = obj.data.materials.find(info['base_mat_name'])

            for idx in face_indices:
                bm.faces[idx].material_index = base_mat_index
            bmesh.update_edit_mesh(obj.data)

            # Generate new constant name using incremental numeric suffix
            new_const_name = self._get_next_constant_name(obj, info['base_mat_name'])
            final_new_name = new_const_name
            counter = 1
            while final_new_name in bpy.data.materials or (final_new_name in obj.get("constant_materials", {})):
                final_new_name = f"{new_const_name}_{counter:03d}"
                counter += 1

            # Create new constant material
            new_mat = base_mat.copy()
            new_mat.name = final_new_name
            if final_new_name not in obj.data.materials:
                obj.data.materials.append(new_mat)
            new_mat_index = obj.data.materials.find(final_new_name)

            for idx in face_indices:
                bm.faces[idx].material_index = new_mat_index
            bmesh.update_edit_mesh(obj.data)

            # Update constant_materials - INHERIT navigation point status
            if "constant_materials" not in obj:
                obj["constant_materials"] = {}
            const_dict = obj["constant_materials"]
            const_dict[final_new_name] = {
                "block_type": info['type'],
                "block_id": new_center.index if info['type'] == 'quadblock' else new_center.index,
                "original_material": info['base_mat_name'],
                "assigned_time": time.time(),
                "is_navigation_point": info['is_navigation_point'],   # Inherit from original
            }
            obj["constant_materials"] = const_dict

            const_prop = f"constant_name_{info['type']}_{new_center.index if info['type'] == 'quadblock' else new_center.index}"
            obj[const_prop] = final_new_name

            # Delete old constant material if unused
            old_mat = bpy.data.materials.get(info['const_name'])
            if old_mat and old_mat.users == 0:
                bpy.data.materials.remove(old_mat)

            new_const_names.append(final_new_name)
            processed += 1

        # NAVIGATION POINT HANDLING
        # Temporarily replace constant_materials with only the newly created ones,
        # but force them to be navigation points for the detection step.
        if new_const_names:
            print(f"DEBUG: New constant materials: {new_const_names}")

            # Save original constant_materials as a plain Python dict
            original_const_materials = None
            if "constant_materials" in obj:
                original_const_materials = deep_copy_idprop_group(obj["constant_materials"])

            # Build temporary dict containing only the new materials, marked as navigation points
            temp_const_materials = {}
            for mat_name in new_const_names:
                if original_const_materials and mat_name in original_const_materials:
                    # Copy the entry (plain dict)
                    temp_const_materials[mat_name] = original_const_materials[mat_name].copy()
                    # Force navigation point = True for detection
                    temp_const_materials[mat_name]["is_navigation_point"] = True
                else:
                    # Fallback (should not happen)
                    temp_const_materials[mat_name] = {
                        "block_type": "quadblock",
                        "block_id": 0,
                        "original_material": "",
                        "assigned_time": time.time(),
                        "is_navigation_point": True,
                    }

            # Replace the property temporarily
            obj["constant_materials"] = temp_const_materials

            # Force a full mesh update
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bmesh.update_edit_mesh(obj.data)

            # Clear selection
            bpy.ops.mesh.select_all(action='DESELECT')

            # Call find_blocks – now it will only see the new blocks
            print("DEBUG: Calling navigator.find_blocks with TEMPORARY constant materials (only new blocks)")
            bpy.ops.navigator.find_blocks()

            # Restore original constant_materials (which already has the correct inherited flags)
            if original_const_materials is not None:
                obj["constant_materials"] = original_const_materials
            else:
                if "constant_materials" in obj:
                    del obj["constant_materials"]

            # Print the number of detected blocks after the call
            quad_count = len(obj.get("quadblock_centers", []))
            tri_count = len(obj.get("triblock_faces", []))
            print(f"DEBUG: After detection - quadblocks: {quad_count}, triblocks: {tri_count}")

        # Select duplicated faces
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        for f in bm.faces:
            f.select = False
        for idx in new_face_indices:
            if idx < len(bm.faces):
                bm.faces[idx].select = True
        bmesh.update_edit_mesh(obj.data)

        self.report({'INFO'}, f"Duplication complete. Processed {processed} blocks.")
        print("--- DEBUG: Duplicate operator finished ---")
        return {'FINISHED'}

    def find_adjacent_triangular_faces(self, central_face):
        """Find 3 triangular faces adjacent to central face"""
        if len(central_face.verts) != 3:
            return []
        adjacent = []
        for edge in central_face.edges:
            for face in edge.link_faces:
                if face != central_face and len(face.verts) == 3 and face not in adjacent:
                    adjacent.append(face)
        return adjacent


classes = [LIST_OT_DuplicateSelection]