"""
Pagination Operators for Quadblock/Triblock List
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, IntProperty


class LIST_OT_VerticalScroll(Operator):
    bl_idname = "list.vertical_scroll"
    bl_label = "Vertical Scroll"
    bl_description = "Scroll vertically through the list of quadblocks/triblocks"
    bl_options = {'REGISTER'}

    direction: EnumProperty(
        name="Direction",
        items=[('UP', 'Up', ''), ('DOWN', 'Down', '')],
        default='UP'
    )

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        scene = context.scene
        from .list_multi_selection import _get_filtered_display_items
        obj = context.edit_object
        if not obj:
            return {'CANCELLED'}

        items = _get_filtered_display_items(context, obj, scene)
        total = len(items)
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)

        if self.direction == 'UP':
            scene.list_vertical_scroll = max(0, scene.list_vertical_scroll - 1)
        else:
            scene.list_vertical_scroll = min(max_scroll, scene.list_vertical_scroll + 1)

        return {'FINISHED'}


class LIST_OT_JumpToPage(Operator):
    bl_idname = "list.jump_to_page"
    bl_label = "Jump to Page"
    bl_description = "Jump to a specific page in the list"
    bl_options = {'REGISTER'}

    page_number: IntProperty(name="Page Number", default=1, min=1)

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        scene = context.scene
        from .list_multi_selection import _get_filtered_display_items
        obj = context.edit_object
        if not obj:
            return {'CANCELLED'}

        items = _get_filtered_display_items(context, obj, scene)
        total = len(items)
        ITEMS_PER_PAGE = 10
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.page_number = max(1, min(self.page_number, total_pages))
        scene.list_vertical_scroll = (self.page_number - 1) * ITEMS_PER_PAGE
        return {'FINISHED'}


classes = [
    LIST_OT_VerticalScroll,
    LIST_OT_JumpToPage,
]