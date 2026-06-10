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

    ret = bmesh.ops.duplicate(bm, geom=selected_faces, use_select_history=False)
    new_faces = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMFace)]

    # Deselect originals, select new faces
    for f in selected_faces:
        f.select = False
    for f in new_faces:
        f.select = True

    return new_faces, len(selected_faces)


def deep_copy_idprop_group(group):
    """
    Recursively convert Blender IDPropertyGroup (or any mapping/list)
    to plain Python dicts/lists so we can safely copy and modify them.
    """
    if hasattr(group, 'items'):
        return {k: deep_copy_idprop_group(v) for k, v in group.items()}
    elif isinstance(group, (list, tuple)):
        return [deep_copy_idprop_group(item) for item in group]
    else:
        return group


class LIST_OT_DuplicateSelection(Operator):
    bl_idname = "list.duplicate_selection"
    bl_label = "Duplicate Block(s) with Constant"
    bl_description = "Duplicate selected blocks, restore base material, and assign a new constant with numeric suffix"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def _get_next_constant_name(self, obj, original_const_name):
        """
        Return a new unique constant material name derived from the original constant name,
        preserving the base and ID and adding an incremental numeric suffix.
        Example: "window_tex_IDwindow_nav" -> "window_tex_IDwindow_nav_001"
                 "window_tex_IDwindow_nav_001" -> "window_tex_IDwindow_nav_002"
        """
        const_dict = obj.get("constant_materials", {})
        # Strip any trailing numeric suffix
        cleaned_name = re.sub(r'_\d+$', '', original_const_name)
        if '_ID' not in cleaned_name:
            pattern = cleaned_name
        else:
            base_part, id_part = cleaned_name.rsplit('_ID', 1)
            pattern = f"{base_part}_ID{id_part}"
        
        max_suffix = 0
        for const_name in const_dict.keys():
            if const_name.startswith(pattern):
                suffix_match = re.search(r'_(\d+)$', const_name)
                if suffix_match:
                    max_suffix = max(max_suffix, int(suffix_match.group(1)))
        next_suffix = max_suffix + 1
        return f"{pattern}_{next_suffix:03d}"

    def execute(self, context):
        print("--- DEBUG: Duplicate operator started ---")
        obj = context.edit_object
        context.tool_settings.mesh_select_mode = (False, False, True)

        # Initial bmesh and selection
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        selected_faces = [f for f in bm.faces if f.select]

        if not selected_faces:
            self.report({'WARNING'}, "No faces selected.")
            return {'CANCELLED'}

        # Detect blocks in selection
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
            self.report({'WARNING'}, "No blocks found in selection. Run 'Find All Blocks' first.")
            return {'CANCELLED'}

        # Gather block info (center coordinates, constant materials, etc.)
        blocks_info = []
        const_dict = obj.get("constant_materials", {})
        quad_faces_map = obj.get("quadblock_faces_map", {})
        tri_faces_map = obj.get("triblock_faces_map", {})

        for block_type, block_id in found_blocks:
            # Get face indices for this block
            if block_type == 'quadblock':
                face_indices = quad_faces_map.get(str(block_id), [])
            else:
                face_indices = tri_faces_map.get(str(block_id), [])
            if len(face_indices) != 4:
                continue

            # Find constant material on block
            const_material_name = None
            for f_idx in face_indices:
                if f_idx >= len(bm.faces):
                    continue
                face = bm.faces[f_idx]
                mat_idx = face.material_index
                if mat_idx < len(obj.material_slots):
                    mat = obj.material_slots[mat_idx].material
                    if mat and mat.name in const_dict:
                        const_material_name = mat.name
                        break
            if not const_material_name:
                continue

            const_info = const_dict[const_material_name]
            base_mat_name = const_info.get("original_material",
                                           const_material_name.split('_ID')[0] if '_ID' in const_material_name else const_material_name)
            is_nav = const_info.get("is_navigation_point", False)

            # Get center coordinate
            if block_type == 'quadblock' and block_id < len(bm.verts):
                center_co = bm.verts[block_id].co.copy()
            elif block_type == 'triblock' and block_id < len(bm.faces):
                center_co = bm.faces[block_id].calc_center_bounds()
            else:
                continue

            blocks_info.append({
                'type': block_type,
                'id': block_id,
                'const_name': const_material_name,
                'base_mat_name': base_mat_name,
                'center_co': center_co,
                'is_navigation_point': is_nav,
                'original_faces': face_indices,
            })

        if not blocks_info:
            self.report({'ERROR'}, "None of the selected blocks have a constant material.")
            return {'CANCELLED'}

        # Duplicate ALL selected faces at once
        new_faces, _ = duplicate_selected_faces_bmesh(bm)
        # Store indices of all newly created faces (constant and non-constant)
        all_new_face_indices = [f.index for f in new_faces]
        bmesh.update_edit_mesh(obj.data)
        if not new_faces:
            self.report({'ERROR'}, "Duplicate operation failed.")
            return {'CANCELLED'}

        # Refresh bmesh and find new centers for each block
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        for info in blocks_info:
            new_center = None
            if info['type'] == 'quadblock':
                for v in bm.verts:
                    if (v.co - info['center_co']).length < 0.001 and v.index != info['id']:
                        if len(v.link_faces) == 4:
                            new_center = v
                            break
            else:  # triblock
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

            # Get the 4 faces of the duplicated block
            if info['type'] == 'quadblock':
                new_face_indices = [f.index for f in new_center.link_faces]
            else:
                adj = self.find_adjacent_triangular_faces(new_center)
                if len(adj) != 3:
                    continue
                new_face_indices = [new_center.index] + [f.index for f in adj]

            if len(new_face_indices) != 4:
                continue

            info['new_center'] = new_center
            info['new_face_indices'] = new_face_indices

        # Prepare material assignments (base temporary + constant) for all blocks
        assignments = []  # list of (face_indices, material_index)
        new_const_names = []

        for info in blocks_info:
            if 'new_face_indices' not in info:
                continue

            # Restore base material (temporary)
            base_mat = bpy.data.materials.get(info['base_mat_name'])
            if not base_mat:
                self.report({'ERROR'}, f"Base material '{info['base_mat_name']}' not found")
                continue
            if info['base_mat_name'] not in obj.data.materials:
                obj.data.materials.append(base_mat)
            base_mat_index = obj.data.materials.find(info['base_mat_name'])
            assignments.append((info['new_face_indices'], base_mat_index))

            # Generate new constant name
            new_const_name = self._get_next_constant_name(obj, info['const_name'])
            final_new_name = new_const_name
            counter = 1
            while final_new_name in bpy.data.materials or (final_new_name in obj.get("constant_materials", {})):
                final_new_name = f"{new_const_name}_{counter:03d}"
                counter += 1

            # Duplicate original constant material
            original_const_mat = bpy.data.materials.get(info['const_name'])
            if not original_const_mat:
                self.report({'ERROR'}, f"Original constant material '{info['const_name']}' not found")
                continue
            new_mat = original_const_mat.copy()
            new_mat.name = final_new_name
            if final_new_name not in obj.data.materials:
                obj.data.materials.append(new_mat)
            new_mat_index = obj.data.materials.find(final_new_name)

            assignments.append((info['new_face_indices'], new_mat_index))
            new_const_names.append(final_new_name)
            info['final_new_name'] = final_new_name

        # Apply all material assignments at once
        for face_indices, mat_idx in assignments:
            for fidx in face_indices:
                if fidx < len(bm.faces):
                    bm.faces[fidx].material_index = mat_idx
        bmesh.update_edit_mesh(obj.data)

        # Update constant_materials dictionary and custom properties
        if "constant_materials" not in obj:
            obj["constant_materials"] = {}
        const_dict = obj["constant_materials"]

        for info in blocks_info:
            if 'final_new_name' not in info:
                continue
            const_dict[info['final_new_name']] = {
                "block_type": info['type'],
                "block_id": info['new_center'].index if info['type'] == 'quadblock' else info['new_center'].index,
                "original_material": info['base_mat_name'],
                "assigned_time": time.time(),
                "is_navigation_point": info['is_navigation_point'],
            }
            const_prop = f"constant_name_{info['type']}_{info['new_center'].index if info['type'] == 'quadblock' else info['new_center'].index}"
            obj[const_prop] = info['final_new_name']

        # Navigation point refresh (same as original)
        if new_const_names:
            original_const_materials = deep_copy_idprop_group(obj["constant_materials"]) if "constant_materials" in obj else None
            temp_const_materials = {}
            for mat_name in new_const_names:
                if original_const_materials and mat_name in original_const_materials:
                    temp_const_materials[mat_name] = original_const_materials[mat_name].copy()
                    temp_const_materials[mat_name]["is_navigation_point"] = True
                else:
                    temp_const_materials[mat_name] = {
                        "block_type": "quadblock",
                        "block_id": 0,
                        "original_material": "",
                        "assigned_time": time.time(),
                        "is_navigation_point": True,
                    }
            obj["constant_materials"] = temp_const_materials
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.navigator.find_blocks()
            if original_const_materials is not None:
                obj["constant_materials"] = original_const_materials
            else:
                if "constant_materials" in obj:
                    del obj["constant_materials"]

        # Select ALL duplicated faces (not just the constant ones)
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        for f in bm.faces:
            f.select = False
        for fidx in all_new_face_indices:
            if fidx < len(bm.faces):
                bm.faces[fidx].select = True
        bmesh.update_edit_mesh(obj.data)

        self.report({'INFO'}, f"Duplication complete. Processed {len([b for b in blocks_info if 'final_new_name' in b])} blocks.")
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