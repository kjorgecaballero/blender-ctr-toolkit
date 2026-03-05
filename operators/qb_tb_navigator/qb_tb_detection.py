"""
QB/TB Detection Operators - REINDEX-SAFE NAVIGATION POINTS
Operators for detecting blocks with navigation point support
Now with material-based navigation points (reindex-safe)
Support for complete block detection (4 faces)
"""

import bpy
import bmesh

from ...utils import qb_tb_navigator


class NAVIGATOR_OT_FindBlocks(bpy.types.Operator):
    """Find all quadblocks and triblocks using edge-based topology with quad edge restriction for triblocks.
    Supports navigation from multiple disconnected starting points marked as navigation points.
    Now uses material-based navigation points for reindex-safe operation.
    Supports BOTH complete qb/tb selection AND center element selection."""
    bl_idname = "navigator.find_blocks"
    bl_label = "Navigate from Selection/Points"
    bl_description = "Find all quadblocks and triblocks. Uses selection if available, otherwise uses all navigation points"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        

        # PHASE 1: COLLECT STARTING POINTS

        start_elements = []
        use_navigation_points = False
        
        selected_verts = [v for v in bm.verts if v.select]
        selected_faces = [f for f in bm.faces if f.select]
        
        if selected_verts or selected_faces:
            if len(selected_faces) == 4 and len(selected_verts) <= 12:
                center, block_type = qb_tb_navigator.detect_block_from_selection(selected_faces)
                if center:
                    start_elements.append(center)
                    if block_type == 'QUADBLOCK':
                        self.report({'INFO'}, f"Complete quadblock detected from 4 faces. Center: vertex {center.index}")
                    else:
                        self.report({'INFO'}, f"Complete triblock detected from 4 faces. Center: face {center.index}")
                else:
                    pass  # Not a valid block, continue checking other cases
            
            if not start_elements and len(selected_verts) == 1:
                vert = selected_verts[0]
                is_valid, message = qb_tb_navigator.validate_quadblock_topology(vert)
                if is_valid:
                    start_elements.append(vert)
                    self.report({'INFO'}, f"Starting from selected quadblock center vertex: {vert.index}")
                else:
                    pass  # Not a valid quadblock center, continue
            
            if not start_elements and len(selected_faces) == 1:
                face = selected_faces[0]
                if not qb_tb_navigator.is_triangle_face(face):
                    pass  # Not a triangle, skip
                else:
                    adjacent_faces = qb_tb_navigator.find_adjacent_triangular_faces(face)
                    if qb_tb_navigator.is_valid_triblock(face, adjacent_faces):
                        start_elements.append(face)
                        self.report({'INFO'}, f"Starting from selected triblock center face: {face.index}")
                    else:
                        pass  # Not a valid triblock center, skip
            
            if not start_elements:
                if len(selected_faces) == 4:
                    self.report({'WARNING'}, 
                               "The 4 selected faces do not form a valid quadblock or triblock.\n"
                               "Make sure you selected exactly 4 quads (for quadblock) or 4 triangles (for triblock).")
                elif len(selected_verts) == 1:
                    self.report({'WARNING'}, 
                               "The selected vertex is not a valid quadblock center.\n"
                               "Make sure it's the center vertex of a quadblock (connected to 4 quad faces).")
                elif len(selected_faces) == 1:
                    self.report({'WARNING'}, 
                               "The selected face is not a valid triblock center.\n"
                               "Make sure it's a triangle face at the center of a triblock.")
                else:
                    self.report({'WARNING'}, 
                               "Invalid selection. Please select:\n"
                               "• All 4 faces of a quadblock (4 quads)\n"
                               "• All 4 faces of a triblock (4 triangles)\n"
                               "• One quadblock center vertex\n"
                               "• One triblock center face")
                return {'CANCELLED'}
        
        else:
            use_navigation_points = True
            
            # Use constant material utilities to get valid navigation points
            navigation_points_info = qb_tb_navigator.get_all_navigation_points(obj, bm)
            
            if not navigation_points_info:
                # Simplified error reporting – no detailed status needed
                if "constant_materials" not in obj or not obj["constant_materials"]:
                    self.report({'WARNING'}, "No constant materials found. Create constant materials first.")
                else:
                    self.report({'WARNING'}, "No valid navigation points found. Mark constant materials as navigation points first.")
                return {'CANCELLED'}
            
            # Collect valid navigation points
            navigation_points = []
            for mat_name, center_element, block_type in navigation_points_info:
                start_elements.append(center_element)
                navigation_points.append(f"{block_type} from '{mat_name}'")
            
            nav_points_str = ', '.join(navigation_points[:3])
            if len(navigation_points) > 3:
                nav_points_str += f" and {len(navigation_points) - 3} more"
            
            self.report({'INFO'}, f"Found {len(start_elements)} valid navigation points: {nav_points_str}")
        

        # PHASE 2: NAVIGATE FROM ALL STARTING POINTS

        all_results = qb_tb_navigator.QbTbBlockResult()
        visited_centers = set()
        visited_faces = set()
        
        for i, start_element in enumerate(start_elements):
            if isinstance(start_element, bmesh.types.BMVert):
                if start_element.index in visited_centers:
                    continue
            else:
                if start_element.index in visited_faces:
                    continue
            
            result = qb_tb_navigator.find_qb_tb_with_groups(start_element, bm)
            
            for center in result.quadblock_centers:
                if center.index not in visited_centers:
                    all_results.quadblock_centers.append(center)
                    visited_centers.add(center.index)
            
            for center in result.triblock_centers:
                if center.index not in visited_faces:
                    all_results.triblock_centers.append(center)
                    visited_faces.add(center.index)
            
            all_results.used_faces.update(result.used_faces)
            all_results.visited_verts.update(result.visited_verts)
            all_results.visited_faces.update(result.visited_faces)
            
            all_results.face_to_quadblock.update(result.face_to_quadblock)
            all_results.face_to_triblock.update(result.face_to_triblock)
            
            for block_id, faces in result.quadblock_faces_map.items():
                if block_id not in all_results.quadblock_faces_map:
                    all_results.quadblock_faces_map[block_id] = faces
                else:
                    existing_faces = set(all_results.quadblock_faces_map[block_id])
                    new_faces = [f for f in faces if f not in existing_faces]
                    all_results.quadblock_faces_map[block_id].extend(new_faces)
            
            for block_id, faces in result.triblock_faces_map.items():
                if block_id not in all_results.triblock_faces_map:
                    all_results.triblock_faces_map[block_id] = faces
                else:
                    existing_faces = set(all_results.triblock_faces_map[block_id])
                    new_faces = [f for f in faces if f not in existing_faces]
                    all_results.triblock_faces_map[block_id].extend(new_faces)
        

        # PHASE 3: CALCULATE GROUPS ONCE FOR ALL ACCUMULATED BLOCKS

        if all_results.quadblock_centers:
            all_results.quadblock_groups, all_results.quad_group_members = \
                qb_tb_navigator.assign_groups_with_vertex_separation_quads(all_results.quadblock_centers)
        
        if all_results.triblock_centers:
            all_results.triblock_groups, all_results.tri_group_members = \
                qb_tb_navigator.assign_groups_with_vertex_separation_tris(all_results.triblock_centers)
        

        # PHASE 4: APPLY SELECTION AND SAVE RESULTS

        for v in bm.verts:
            v.select = v in all_results.visited_verts
        for f in bm.faces:
            f.select = f in all_results.visited_faces
        
        bmesh.update_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        obj["quadblock_centers"] = [v.index for v in all_results.quadblock_centers]
        obj["triblock_faces"] = [f.index for f in all_results.triblock_centers]
        obj["used_face_indices"] = [f.index for f in all_results.used_faces]
        obj["block_type"] = "COMBINED"
        
        obj["quadblock_groups"] = {}
        for center_vert, group in all_results.quadblock_groups.items():
            obj["quadblock_groups"][str(center_vert.index)] = group
        
        obj["quad_group_members"] = {}
        for group, members in all_results.quad_group_members.items():
            obj["quad_group_members"][str(group)] = [v.index for v in members]
        
        obj["triblock_groups"] = {}
        for center_face, group in all_results.triblock_groups.items():
            obj["triblock_groups"][str(center_face.index)] = group
        
        obj["tri_group_members"] = {}
        for group, members in all_results.tri_group_members.items():
            obj["tri_group_members"][str(group)] = [f.index for f in members]
        
        obj["face_to_quadblock"] = {str(k): v for k, v in all_results.face_to_quadblock.items()}
        obj["face_to_triblock"] = {str(k): v for k, v in all_results.face_to_triblock.items()}
        
        obj["quadblock_faces_map"] = {str(k): v for k, v in all_results.quadblock_faces_map.items()}
        obj["triblock_faces_map"] = {str(k): v for k, v in all_results.triblock_faces_map.items()}
        
        quad_stats = []
        for group in sorted(all_results.quad_group_members.keys()):
            count = len(all_results.quad_group_members[group])
            quad_stats.append(f"Q{group}: {count}")
        
        tri_stats = []
        for group in sorted(all_results.tri_group_members.keys()):
            count = len(all_results.tri_group_members[group])
            tri_stats.append(f"T{group}: {count}")
        
        if use_navigation_points:
            self.report({'INFO'}, f"Navigated from {len(start_elements)} navigation points")
        
        self.report({'INFO'}, f"Found {len(all_results.quadblock_centers)} quadblocks in {len(all_results.quad_group_members)} groups: {', '.join(quad_stats)}")
        self.report({'INFO'}, f"Found {len(all_results.triblock_centers)} triblocks in {len(all_results.tri_group_members)} groups: {', '.join(tri_stats)}")
        
        return {'FINISHED'}


classes = [NAVIGATOR_OT_FindBlocks]