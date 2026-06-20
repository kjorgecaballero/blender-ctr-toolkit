import bpy
import bmesh
from ...utils.qb_tb_navigator.constant_material_utils import clear_all_constant_materials
from ...icons import get_icon


def delete_block_vertex_groups(obj):
    """Delete all vertex groups whose names start with QB_ or TB_."""
    groups_to_remove = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
    for vg in groups_to_remove:
        obj.vertex_groups.remove(vg)
    return len(groups_to_remove)


class NAVIGATOR_OT_ClearBlockCache(bpy.types.Operator):
    """Reset selected addon data on this object: constant materials, vertex groups, and/or block cache."""
    bl_idname = "navigator.clear_block_cache"
    bl_label = "Reset Addon Data"
    bl_description = "Delete selected data: constant materials, vertex groups, and/or block detection cache"
    bl_options = {'REGISTER', 'UNDO'}

    clear_vertex_groups: bpy.props.BoolProperty(
        name="Vertex Groups",
        description="Delete all QB_/TB_ vertex groups",
        default=True
    )
    clear_constant_materials: bpy.props.BoolProperty(
        name="Constant Materials",
        description="Clear constant materials from this object (restore originals or create fallbacks)",
        default=False
    )
    clear_cache: bpy.props.BoolProperty(
        name="Block Cache",
        description="Delete detection data (face maps, groups, etc.)",
        default=True
    )

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
        
        icon_id = get_icon("constant_mat_icon")
        if icon_id:
            col.prop(self, "clear_constant_materials", icon_value=icon_id)
        else:
            col.prop(self, "clear_constant_materials", icon='MATERIAL')
        
        col.prop(self, "clear_vertex_groups", icon='GROUP_VERTEX')
        
        cache_icon = get_icon("quadblock_cache_icon")
        if cache_icon:
            col.prop(self, "clear_cache", icon_value=cache_icon)
        else:
            col.prop(self, "clear_cache", icon='MEMORY')

        layout.separator()
        
        if self.clear_constant_materials:
            box = layout.box()
            box.alert = True
            box.label(text="⚠️ Clearing constant materials will restore base materials", icon='ERROR')
            box.label(text="   or create fallback materials if originals are missing.")
            box.label(text="   This affects only faces using those materials on THIS object.")

        layout.separator()
        layout.label(text="This action cannot be undone.", icon='QUESTION')

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            total_cleared = 0

            # 1. Constant Materials
            if self.clear_constant_materials:
                cleared_orig, restored_fb, failed = clear_all_constant_materials(obj, fallback_duplicate=True)
                if cleared_orig > 0 or restored_fb > 0:
                    self.report({'INFO'}, f"Constant materials: {cleared_orig} restored to original, {restored_fb} created via fallback")
                if failed:
                    self.report({'WARNING'}, f"Could not clear some constant materials: {', '.join(failed)}")
                total_cleared += cleared_orig + restored_fb

            # 2. Vertex groups
            if self.clear_vertex_groups:
                vg_count = delete_block_vertex_groups(obj)
                if vg_count > 0:
                    self.report({'INFO'}, f"Deleted {vg_count} vertex groups (QB_/TB_)")
                total_cleared += vg_count

            # 3. Block cache properties (does NOT include constant_materials)
            if self.clear_cache:
                props_to_remove = [
                    "quadblock_centers", "triblock_faces", "used_face_indices",
                    "block_type", "quadblock_groups", "quad_group_members",
                    "triblock_groups", "tri_group_members", "face_to_quadblock",
                    "face_to_triblock", "quadblock_faces_map", "triblock_faces_map",
                    "multi_selected_items"
                ]
                removed_count = 0
                for prop in props_to_remove:
                    if prop in obj:
                        del obj[prop]
                        removed_count += 1

                if removed_count > 0:
                    self.report({'INFO'}, f"Removed {removed_count} cache properties")
                total_cleared += removed_count

            # Clear 3D selection
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bm = bmesh.from_edit_mesh(obj.data)
                for v in bm.verts:
                    v.select = False
                for f in bm.faces:
                    f.select = False
                bmesh.update_edit_mesh(obj.data)

            self.report({'INFO'}, f"Reset completed. Cleaned {total_cleared} items.")

        except Exception as e:
            self.report({'ERROR'}, f"Error during reset: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH' and context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


classes = [NAVIGATOR_OT_ClearBlockCache]