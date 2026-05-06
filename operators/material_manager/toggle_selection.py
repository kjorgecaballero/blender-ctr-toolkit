import bpy
from bpy.types import Operator
from bpy.props import IntProperty


class MATERIAL_OT_ToggleSelection(Operator):
    bl_idname = "material.toggle_selection"
    bl_label = "Select Material"
    index: IntProperty()

    def execute(self, context):
        props = context.scene.ctr_material_list
        if self.index < 0 or self.index >= len(props.items):
            return {'CANCELLED'}
        if props.selected_index == self.index:
            props.selected_index = -1
        else:
            props.selected_index = self.index
        return {'FINISHED'}


classes = [MATERIAL_OT_ToggleSelection]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)