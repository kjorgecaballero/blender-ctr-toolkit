import bpy
import bmesh


class NAVIGATOR_OT_ClearBlockCache(bpy.types.Operator):
    bl_idname = "navigator.clear_block_cache"
    bl_label = "Clear"
    bl_description = "Clear quadblock/triblock cache and selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        # Show custom confirmation dialog
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text="This cannot be undone.", icon='ERROR')

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Clear selection
        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False
        
        bmesh.update_edit_mesh(obj.data)
        
        # List of properties to remove
        props_to_remove = [
            "quadblock_centers", "triblock_faces", "used_face_indices",
            "block_type", "quadblock_groups", "quad_group_members",
            "triblock_groups", "tri_group_members", "face_to_quadblock",
            "face_to_triblock", "quadblock_faces_map", "triblock_faces_map",
            "constant_materials", "multi_selected_items"
        ]
        
        # Remove each property if it exists
        removed_count = 0
        for prop in props_to_remove:
            if prop in obj:
                del obj[prop]
                removed_count += 1
        
        # Also remove constant name properties
        const_props = [prop for prop in obj.keys() if prop.startswith("constant_name_")]
        for prop in const_props:
            del obj[prop]
            removed_count += 1
        
        # Show success message
        if removed_count > 0:
            self.report({'INFO'}, f"Block cache cleared ({removed_count} properties removed)")
        else:
            self.report({'INFO'}, "No block cache found to clear")
        
        return {'FINISHED'}


classes = [NAVIGATOR_OT_ClearBlockCache]