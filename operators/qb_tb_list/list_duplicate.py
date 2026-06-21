import bpy
import bmesh
import re
import time
from mathutils import Vector
from bpy.types import Operator
from ...utils.qb_tb_navigator import (
    assign_groups_with_vertex_separation_quads,
    assign_groups_with_vertex_separation_tris,
)


def duplicate_selected_faces_bmesh(bm):
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        return [], 0

    ret = bmesh.ops.duplicate(bm, geom=selected_faces, use_select_history=False)
    new_faces = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMFace)]

    for f in selected_faces:
        f.select = False
    for f in new_faces:
        f.select = True

    return new_faces, len(selected_faces)


class LIST_OT_DuplicateSelection(Operator):
    bl_idname = "list.duplicate_selection"
    bl_label = "Duplicate Block(s) with Constant"
    bl_description = "Duplicate selected blocks, restore base material, and assign a new constant with numeric suffix"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def _get_next_constant_name(self, obj, original_const_name):
        cleaned_name = re.sub(r'_\d+$', '', original_const_name)
        if '_ID' not in cleaned_name:
            pattern = cleaned_name
        else:
            base_part, id_part = cleaned_name.rsplit('_ID', 1)
            pattern = f"{base_part}_ID{id_part}"

        max_suffix = 0
        for mat in bpy.data.materials:
            if mat.get("ctr_block_type") is not None and mat.name.startswith(pattern):
                suffix_match = re.search(r'_(\d+)$', mat.name)
                if suffix_match:
                    max_suffix = max(max_suffix, int(suffix_match.group(1)))
        next_suffix = max_suffix + 1
        return f"{pattern}_{next_suffix:03d}"

    def execute(self, context):
        start_total = time.time()
        print("\n" + "="*60)
        print("--- DEBUG: Duplicate operator STARTED ---")
        obj = context.edit_object
        context.tool_settings.mesh_select_mode = (False, False, True)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        selected_faces = [f for f in bm.faces if f.select]

        if not selected_faces:
            self.report({'WARNING'}, "No faces selected.")
            return {'CANCELLED'}

        print(f"[DEBUG] Selected {len(selected_faces)} faces.")

        # Get current detection maps
        face_to_quad = obj.get("face_to_quadblock", {})
        face_to_tri = obj.get("face_to_triblock", {})
        quad_centers = set(obj.get("quadblock_centers", []))
        triblock_faces = set(obj.get("triblock_faces", []))
        quad_faces_map = obj.get("quadblock_faces_map", {})
        tri_faces_map = obj.get("triblock_faces_map", {})
        selected_verts = [v for v in bm.verts if v.select]

        # Detect blocks in selection
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

        print(f"[DEBUG] Found {len(found_blocks)} blocks in selection: {found_blocks}")

        if not found_blocks:
            self.report({'WARNING'}, "No blocks found in selection. Run 'Find All Blocks' first.")
            return {'CANCELLED'}

        # Gather info for each block
        blocks_info = []
        for block_type, block_id in found_blocks:
            if block_type == 'quadblock':
                face_indices = quad_faces_map.get(str(block_id), [])
            else:
                face_indices = tri_faces_map.get(str(block_id), [])
            if len(face_indices) != 4:
                continue

            const_mat = None
            const_material_name = None
            for f_idx in face_indices:
                if f_idx >= len(bm.faces):
                    continue
                face = bm.faces[f_idx]
                mat_idx = face.material_index
                if mat_idx < len(obj.material_slots):
                    mat = obj.material_slots[mat_idx].material
                    if mat and mat.get("ctr_block_type") is not None:
                        const_material_name = mat.name
                        const_mat = mat
                        break
            if not const_material_name or not const_mat:
                continue

            base_mat_name = const_mat.get("ctr_original_material",
                                           const_material_name.split('_ID')[0] if '_ID' in const_material_name else const_material_name)
            is_nav = const_mat.get("ctr_is_navigation_point", False)

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

        print(f"[DEBUG] Blocks info gathered: {len(blocks_info)} blocks.")

        # Duplicate ALL selected faces at once
        t0 = time.time()
        new_faces, _ = duplicate_selected_faces_bmesh(bm)
        all_new_face_indices = [f.index for f in new_faces]
        bmesh.update_edit_mesh(obj.data)
        if not new_faces:
            self.report({'ERROR'}, "Duplicate operation failed.")
            return {'CANCELLED'}
        print(f"[DEBUG] Duplicated {len(new_faces)} faces in {time.time()-t0:.3f}s")

        # Refresh bmesh and find new centers
        t0 = time.time()
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
            else:
                for f in bm.faces:
                    if (f.calc_center_bounds() - info['center_co']).length < 0.001 and f.index != info['id']:
                        if len(f.verts) == 3:
                            adj = self.find_adjacent_triangular_faces(f)
                            if len(adj) == 3:
                                new_center = f
                                break
            if not new_center:
                print(f"[WARNING] Could not locate duplicated block for {info['const_name']}")
                continue

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

        found_centers = sum(1 for info in blocks_info if 'new_center' in info)
        print(f"[DEBUG] Found {found_centers} new centers in {time.time()-t0:.3f}s")

        # Material assignments
        t0 = time.time()
        assignments = []
        new_constant_names = []

        for info in blocks_info:
            if 'new_face_indices' not in info:
                continue

            base_mat = bpy.data.materials.get(info['base_mat_name'])
            if not base_mat:
                self.report({'ERROR'}, f"Base material '{info['base_mat_name']}' not found")
                continue
            if info['base_mat_name'] not in obj.data.materials:
                obj.data.materials.append(base_mat)

            new_const_name = self._get_next_constant_name(obj, info['const_name'])
            final_new_name = new_const_name
            counter = 1
            while final_new_name in bpy.data.materials:
                final_new_name = f"{new_const_name}_{counter:03d}"
                counter += 1

            original_const_mat = bpy.data.materials.get(info['const_name'])
            if not original_const_mat:
                self.report({'ERROR'}, f"Original constant material '{info['const_name']}' not found")
                continue

            new_mat = original_const_mat.copy()
            new_mat.name = final_new_name
            new_mat["ctr_block_type"] = info['type']
            new_mat["ctr_block_id"] = info['new_center'].index if info['type'] == 'quadblock' else info['new_center'].index
            new_mat["ctr_original_material"] = info['base_mat_name']
            new_mat["ctr_is_navigation_point"] = info['is_navigation_point']

            if final_new_name not in obj.data.materials:
                obj.data.materials.append(new_mat)

            base_mat_index = obj.data.materials.find(info['base_mat_name'])
            new_mat_index = obj.data.materials.find(final_new_name)

            assignments.append((info['new_face_indices'], base_mat_index))
            assignments.append((info['new_face_indices'], new_mat_index))
            new_constant_names.append(final_new_name)
            info['final_new_name'] = final_new_name

        # Apply material assignments to faces
        for face_indices, mat_idx in assignments:
            for fidx in face_indices:
                if fidx < len(bm.faces):
                    bm.faces[fidx].material_index = mat_idx
        bmesh.update_edit_mesh(obj.data)

        print(f"[DEBUG] Created {len(new_constant_names)} new constant materials: {new_constant_names} in {time.time()-t0:.3f}s")

        # UPDATE NAVIGATION MAPS
        t0 = time.time()
        for info in blocks_info:
            if 'new_center' not in info:
                continue
            if info['type'] == 'quadblock':
                center_idx = info['new_center'].index
                quad_centers.add(center_idx)
                for f_idx in info['new_face_indices']:
                    face_to_quad[str(f_idx)] = center_idx
                quad_faces_map[str(center_idx)] = info['new_face_indices']
            else:
                center_idx = info['new_center'].index
                triblock_faces.add(center_idx)
                for f_idx in info['new_face_indices']:
                    face_to_tri[str(f_idx)] = center_idx
                tri_faces_map[str(center_idx)] = info['new_face_indices']

        obj["face_to_quadblock"] = face_to_quad
        obj["face_to_triblock"] = face_to_tri
        obj["quadblock_centers"] = list(quad_centers)
        obj["triblock_faces"] = list(triblock_faces)
        obj["quadblock_faces_map"] = quad_faces_map
        obj["triblock_faces_map"] = tri_faces_map

        all_used = set(obj.get("used_face_indices", []))
        for info in blocks_info:
            if 'new_face_indices' in info:
                all_used.update(info['new_face_indices'])
        obj["used_face_indices"] = list(all_used)
        print(f"[DEBUG] Navigation maps updated in {time.time()-t0:.3f}s")

        # NAVIGATE ONLY FROM THE NEW POINTS
        t0 = time.time()
        print("[DEBUG] Starting navigation-point management...")

        # Backup current navigation state of all materials on this object
        nav_state_backup = {}
        for slot in obj.material_slots:
            mat = slot.material
            if mat and mat.get("ctr_block_type") is not None:
                nav_state_backup[mat.name] = mat.get("ctr_is_navigation_point", False)

        print(f"[DEBUG] Backed up navigation states for {len(nav_state_backup)} materials.")
        print(f"  States: {nav_state_backup}")

        # Deactivate ALL navigation points
        for mat_name in nav_state_backup:
            mat = bpy.data.materials.get(mat_name)
            if mat:
                mat["ctr_is_navigation_point"] = False
        print("[DEBUG] All navigation points deactivated.")

        # Activate ONLY the newly duplicated materials
        for new_name in new_constant_names:
            mat = bpy.data.materials.get(new_name)
            if mat:
                mat["ctr_is_navigation_point"] = True
        print(f"[DEBUG] Activated ONLY these new navigation points: {new_constant_names}")

        # Ensure we are in OBJECT mode to update materials properly
        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = obj
        obj.select_set(True)
        obj.data.update()
        context.view_layer.update()

        # Switch to EDIT mode for find_blocks
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        if context.edit_object is None:
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')

        # Log current materials and their nav state before find_blocks
        print("[DEBUG] Materials in object BEFORE find_blocks (only new points should be active):")
        active_nav_count = 0
        for slot in obj.material_slots:
            if slot.material:
                mat = slot.material
                nav = mat.get("ctr_is_navigation_point", False)
                block = mat.get("ctr_block_type")
                if nav:
                    active_nav_count += 1
                print(f"  {mat.name}: block_type={block}, is_nav={nav}")
        print(f"[DEBUG] Active navigation points: {active_nav_count}")

        print("[DEBUG] Running find_blocks in EDIT mode (only from new navigation points)...")
        find_start = time.time()
        bpy.ops.navigator.find_blocks()
        find_end = time.time()
        print(f"[DEBUG] find_blocks completed in {find_end-find_start:.3f}s")

        # Restore original navigation states
        for mat_name, was_nav in nav_state_backup.items():
            mat = bpy.data.materials.get(mat_name)
            if mat:
                mat["ctr_is_navigation_point"] = was_nav
        print("[DEBUG] Restored original navigation states.")
        print(f"[DEBUG] Navigation management took {time.time()-t0:.3f}s")

        # Return to EDIT mode and select duplicated faces
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        for f in bm.faces:
            f.select = False
        for fidx in all_new_face_indices:
            if fidx < len(bm.faces):
                bm.faces[fidx].select = True
        bmesh.update_edit_mesh(obj.data)

        total_time = time.time() - start_total
        self.report({'INFO'}, f"Duplication complete. Processed {len(new_constant_names)} blocks in {total_time:.2f}s")
        print(f"--- DEBUG: Duplicate operator FINISHED in {total_time:.2f}s ---")
        print("="*60 + "\n")
        return {'FINISHED'}

    def find_adjacent_triangular_faces(self, central_face):
        if len(central_face.verts) != 3:
            return []
        adjacent = []
        for edge in central_face.edges:
            for face in edge.link_faces:
                if face != central_face and len(face.verts) == 3 and face not in adjacent:
                    adjacent.append(face)
        return adjacent


classes = [LIST_OT_DuplicateSelection]