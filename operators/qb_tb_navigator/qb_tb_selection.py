"""
QB/TB Selection Operators
Operators for selecting quadblocks and triblocks
"""

import bpy
import bmesh
from bpy_extras import view3d_utils


class NAVIGATOR_OT_SelectQuadblocksOnly(bpy.types.Operator):
    """Select only quadblock centers from current detection"""
    bl_idname = "navigator.select_quadblocks_only"
    bl_label = "Select Quadblocks Only"
    bl_description = "Select only quadblock centers from current detection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if "quadblock_centers" in obj:
            quadblock_centers = obj["quadblock_centers"]
            for vert_index in quadblock_centers:
                if vert_index < len(bm.verts):
                    bm.verts[vert_index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, "Selected quadblock centers only")
        return {'FINISHED'}


class NAVIGATOR_OT_SelectTriblocksOnly(bpy.types.Operator):
    """Select only triblock centers from current detection"""
    bl_idname = "navigator.select_triblocks_only"
    bl_label = "Select Triblocks Only"
    bl_description = "Select only triblock centers from current detection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if "triblock_faces" in obj:
            triblock_faces = obj["triblock_faces"]
            for face_index in triblock_faces:
                if face_index < len(bm.faces):
                    bm.faces[face_index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, "Selected triblock centers only")
        return {'FINISHED'}


class NAVIGATOR_OT_SelectInvalidFaces(bpy.types.Operator):
    """Select faces that are not part of any detected block (potential errors)"""
    bl_idname = "navigator.select_invalid_faces"
    bl_label = "Select Invalid Faces"
    bl_description = "Select faces that are not part of any detected block (potential errors)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if "used_face_indices" not in obj:
            self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
            return {'CANCELLED'}
        
        used_faces = set(obj["used_face_indices"])
        
        invalid_count = 0
        for face in bm.faces:
            if face.index not in used_faces:
                face.select = True
                invalid_count += 1
        
        bmesh.update_edit_mesh(obj.data)
        
        if invalid_count > 0:
            self.report({'INFO'}, f"Selected {invalid_count} invalid/unassigned faces")
        else:
            self.report({'INFO'}, "All faces are part of valid blocks")
        
        return {'FINISHED'}


class NAVIGATOR_OT_SelectQuadblockGroup(bpy.types.Operator):
    """Select quadblocks from a specific group"""
    bl_idname = "navigator.select_quadblock_group"
    bl_label = "Select Quadblocks By Group"
    bl_description = "Select quadblocks from a specific group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_number: bpy.props.IntProperty(
        name="Group Number",
        description="Group number to select",
        min=1,
        max=20,
        default=1
    )
    
    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')
    
    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if "quad_group_members" in obj:
            quad_group_members = obj["quad_group_members"]
            group_key = str(self.group_number)
            if group_key in quad_group_members:
                selected_count = 0
                for vert_index in quad_group_members[group_key]:
                    if vert_index < len(bm.verts):
                        bm.verts[vert_index].select = True
                        selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} quadblocks from group {self.group_number}")
            else:
                self.report({'WARNING'}, f"Quadblock group {self.group_number} not found")
        else:
            self.report({'WARNING'}, "No quadblock groups found. Run Find Blocks first.")
        
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class NAVIGATOR_OT_SelectTriblockGroup(bpy.types.Operator):
    """Select triblocks from a specific group"""
    bl_idname = "navigator.select_triblock_group"
    bl_label = "Select Triblocks By Group"
    bl_description = "Select triblocks from a specific group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_number: bpy.props.IntProperty(
        name="Group Number",
        description="Group number to select",
        min=1,
        max=20,
        default=1
    )
    
    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')
    
    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        if "tri_group_members" in obj:
            tri_group_members = obj["tri_group_members"]
            group_key = str(self.group_number)
            if group_key in tri_group_members:
                selected_count = 0
                for face_index in tri_group_members[group_key]:
                    if face_index < len(bm.faces):
                        bm.faces[face_index].select = True
                        selected_count += 1
                
                self.report({'INFO'}, f"Selected {selected_count} triblocks from group {self.group_number}")
            else:
                self.report({'WARNING'}, f"Triblock group {self.group_number} not found")
        else:
            self.report({'WARNING'}, "No triblock groups found. Run Find Blocks first.")
        
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class NAVIGATOR_OT_CursorSelectBlock(bpy.types.Operator):
    """Select entire quadblocks or triblocks under cursor or in current selection"""
    bl_idname = "navigator.cursor_select_block"
    bl_label = "Select Block Under Cursor"
    bl_description = "Select entire quadblocks or triblocks under cursor or in current selection based on saved indices (like L key for blocks). Use with box/circle/lasso selection for multiple blocks."
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')
    
    def invoke(self, context, event):
        return self.execute_cursor_mode(context, event)
    
    def execute(self, context):
        return self.execute_selection_mode(context, additive=False)
    
    def execute_cursor_mode(self, context, event):
        obj = context.edit_object
        
        if "face_to_quadblock" not in obj or "face_to_triblock" not in obj:
            self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        face_to_quadblock = obj["face_to_quadblock"]
        face_to_triblock = obj["face_to_triblock"]
        quadblock_faces_map = obj["quadblock_faces_map"]
        triblock_faces_map = obj["triblock_faces_map"]
        
        quadblocks_to_select = set()
        triblocks_to_select = set()
        
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        depsgraph = context.evaluated_depsgraph_get()
        result, location, normal, index, hit_obj, matrix = context.scene.ray_cast(depsgraph, ray_origin, view_vector)
        
        if not result or hit_obj != obj:
            self.report({'WARNING'}, "No face under cursor in current object")
            return {'CANCELLED'}
        
        if index < 0 or index >= len(bm.faces):
            self.report({'WARNING'}, "Face index out of range")
            return {'CANCELLED'}
        
        face_index = index
        
        if str(face_index) in face_to_quadblock:
            center_index = int(face_to_quadblock[str(face_index)])
            quadblocks_to_select.add(center_index)
        
        elif str(face_index) in face_to_triblock:
            center_index = int(face_to_triblock[str(face_index)])
            triblocks_to_select.add(center_index)
        
        else:
            self.report({'WARNING'}, "Face under cursor is not part of any detected block")
            return {'CANCELLED'}
        
        for center_index in quadblocks_to_select:
            if center_index < len(bm.verts):
                bm.verts[center_index].select = True
            
            if str(center_index) in quadblock_faces_map:
                for f_index in quadblock_faces_map[str(center_index)]:
                    if f_index < len(bm.faces):
                        bm.faces[f_index].select = True
        
        for center_index in triblocks_to_select:
            if str(center_index) in triblock_faces_map:
                for f_index in triblock_faces_map[str(center_index)]:
                    if f_index < len(bm.faces):
                        bm.faces[f_index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        
        total_blocks = len(quadblocks_to_select) + len(triblocks_to_select)
        if total_blocks == 1:
            if quadblocks_to_select:
                self.report({'INFO'}, f"Selected quadblock with center vertex {list(quadblocks_to_select)[0]}")
            else:
                self.report({'INFO'}, f"Selected triblock with center face {list(triblocks_to_select)[0]}")
        else:
            self.report({'INFO'}, f"Selected {len(quadblocks_to_select)} quadblocks and {len(triblocks_to_select)} triblocks")
        
        return {'FINISHED'}
    
    def execute_selection_mode(self, context, additive=False):
        obj = context.edit_object
        
        if "face_to_quadblock" not in obj or "face_to_triblock" not in obj:
            self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
            return {'CANCELLED'}
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        face_to_quadblock = obj["face_to_quadblock"]
        face_to_triblock = obj["face_to_triblock"]
        quadblock_faces_map = obj["quadblock_faces_map"]
        triblock_faces_map = obj["triblock_faces_map"]
        
        quadblocks_to_select = set()
        triblocks_to_select = set()
        
        selected_faces = [f for f in bm.faces if f.select]
        
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected. Select faces or use cursor mode.")
            return {'CANCELLED'}
        
        for face in selected_faces:
            face_index = face.index
            
            if str(face_index) in face_to_quadblock:
                center_index = int(face_to_quadblock[str(face_index)])
                quadblocks_to_select.add(center_index)
            
            elif str(face_index) in face_to_triblock:
                center_index = int(face_to_triblock[str(face_index)])
                triblocks_to_select.add(center_index)
        
        if not additive:
            for v in bm.verts:
                v.select = False
            for f in bm.faces:
                f.select = False
        
        for center_index in quadblocks_to_select:
            if center_index < len(bm.verts):
                bm.verts[center_index].select = True
            
            if str(center_index) in quadblock_faces_map:
                for f_index in quadblock_faces_map[str(center_index)]:
                    if f_index < len(bm.faces):
                        bm.faces[f_index].select = True
        
        for center_index in triblocks_to_select:
            if str(center_index) in triblock_faces_map:
                for f_index in triblock_faces_map[str(center_index)]:
                    if f_index < len(bm.faces):
                        bm.faces[f_index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        
        total_blocks = len(quadblocks_to_select) + len(triblocks_to_select)
        if total_blocks == 0:
            self.report({'WARNING'}, "No blocks found in selected area")
        else:
            self.report({'INFO'}, f"Selected {len(quadblocks_to_select)} quadblocks and {len(triblocks_to_select)} triblocks")
        
        return {'FINISHED'}

classes = [
    NAVIGATOR_OT_SelectQuadblocksOnly,
    NAVIGATOR_OT_SelectTriblocksOnly,
    NAVIGATOR_OT_SelectQuadblockGroup,
    NAVIGATOR_OT_SelectTriblockGroup,
    NAVIGATOR_OT_CursorSelectBlock,
    NAVIGATOR_OT_SelectInvalidFaces,
]