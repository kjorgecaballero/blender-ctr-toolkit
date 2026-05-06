import bpy
from bpy.types import Operator
from bpy.props import BoolProperty


class MATERIAL_OT_RefreshList(Operator):
    """Rebuild the material list (after adding/renaming materials) and optionally purge unused data blocks"""
    bl_idname = "material.refresh_list"
    bl_label = "Refresh"
    bl_description = "Rebuild the material list (after adding/renaming materials)"
    bl_options = {'REGISTER'}

    purge_unused: BoolProperty(
        name="Purge unused",
        description="Delete all unused materials, textures, and images",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "purge_unused")

    def execute(self, context):
        if self.purge_unused:
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
            self.report({'INFO'}, "Purged unused data blocks")
        context.scene.ctr_material_list._update_items(context)
        self.report({'INFO'}, "Material list refreshed")
        return {'FINISHED'}


classes = [MATERIAL_OT_RefreshList]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)