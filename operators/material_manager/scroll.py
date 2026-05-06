import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, IntProperty


class MATERIAL_OT_VerticalScroll(Operator):
    bl_idname = "material.vertical_scroll"
    bl_label = "Scroll"
    direction: EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        if self.direction == 'UP':
            props.scroll = max(0, props.scroll - 1)
        else:
            props.scroll = min(max_scroll, props.scroll + 1)
        return {'FINISHED'}


class MATERIAL_OT_JumpToPage(Operator):
    bl_idname = "material.jump_to_page"
    bl_label = "Jump to Page"
    page: IntProperty(default=1, min=1)

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        safe_page = max(1, min(self.page, total_pages))
        props.scroll = (safe_page - 1) * ITEMS_PER_PAGE
        return {'FINISHED'}


classes = [MATERIAL_OT_VerticalScroll, MATERIAL_OT_JumpToPage]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)