import bpy
import bmesh
from ...utils.qb_tb_navigator.constant_material_utils import clear_all_constant_materials


def delete_block_vertex_groups(obj):
    """Delete all vertex groups whose names start with QB_ or TB_."""
    groups_to_remove = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
    for vg in groups_to_remove:
        obj.vertex_groups.remove(vg)
    return len(groups_to_remove)


class NAVIGATOR_OT_ClearBlockCache(bpy.types.Operator):
    """Reset all addon data on this object: constant materials, vertex groups, and block cache."""
    bl_idname = "navigator.clear_block_cache"
    bl_label = "Reset Addon Data"
    bl_description = "Delete ALL constant materials (restoring base materials), all QB/TB vertex groups, and the block detection cache"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text="This will DELETE the following addon data from the active object:", icon='ERROR')
        layout.separator()

        col = layout.column(align=True)
        col.label(text="• Constant materials (restored; fallback if missing)", icon='MATERIAL')
        col.label(text="• Vertex groups starting with QB_ or TB_", icon='GROUP_VERTEX')
        col.label(text="• Block detection cache", icon='FILE')
        layout.separator()
        layout.label(text="This action cannot be undone.", icon='QUESTION')

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        # Switch to OBJECT mode for safe deletion of materials and vertex groups
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            # 1. Clear constant materials (with fallback duplication)
            cleared_orig, restored_fb, failed = clear_all_constant_materials(obj, fallback_duplicate=True)
            if cleared_orig > 0 or restored_fb > 0:
                self.report({'INFO'}, f"Constant materials: {cleared_orig} restored to original, {restored_fb} created via fallback")
            if failed:
                self.report({'WARNING'}, f"Could not clear some constant materials: {', '.join(failed)}")

            # 2. Delete all QB/TB vertex groups
            vg_count = delete_block_vertex_groups(obj)
            if vg_count > 0:
                self.report({'INFO'}, f"Deleted {vg_count} vertex groups (QB_/TB_)")

            # 3. Clear block cache properties
            props_to_remove = [
                "quadblock_centers", "triblock_faces", "used_face_indices",
                "block_type", "quadblock_groups", "quad_group_members",
                "triblock_groups", "tri_group_members", "face_to_quadblock",
                "face_to_triblock", "quadblock_faces_map", "triblock_faces_map",
                "constant_materials", "multi_selected_items"
            ]
            removed_count = 0
            for prop in props_to_remove:
                if prop in obj:
                    del obj[prop]
                    removed_count += 1

            # Also remove any leftover constant_name_* properties (safety)
            const_props = [prop for prop in obj.keys() if prop.startswith("constant_name_")]
            for prop in const_props:
                del obj[prop]
                removed_count += 1

            if removed_count > 0:
                self.report({'INFO'}, f"Removed {removed_count} cache properties")

            # 4. Clear selection in edit mode (will be restored later)
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bm = bmesh.from_edit_mesh(obj.data)
                for v in bm.verts:
                    v.select = False
                for f in bm.faces:
                    f.select = False
                bmesh.update_edit_mesh(obj.data)

            total_cleared = (cleared_orig + restored_fb) + vg_count + removed_count
            self.report({'INFO'}, f"Reset complete. Cleaned {total_cleared} items.")

        except Exception as e:
            self.report({'ERROR'}, f"Error during reset: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        finally:
            # Restore original mode if needed
            if original_mode == 'EDIT_MESH' and context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


classes = [NAVIGATOR_OT_ClearBlockCache]