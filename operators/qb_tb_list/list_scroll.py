"""
Pagination Operators for Quadblock/Triblock List
Moved from ui/qb_tb_list/pages_list.py
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
        obj = context.edit_object
        if not obj:
            return {'CANCELLED'}

        #  Build item list for size
        items = []
        if scene.list_display_type == 'VERTEX_GROUPS':
            for vg in obj.vertex_groups:
                if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                    items.append(vg.name)
                elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                    items.append(vg.name)
        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            if "constant_materials" in obj:
                for mat_name, info in obj["constant_materials"].items():
                    bt = info.get("block_type", "")
                    if (bt == "quadblock" and scene.list_filter_cm_qb) or \
                       (bt == "triblock" and scene.list_filter_cm_tb):
                        items.append(mat_name)

        search = scene.list_search_text.lower()
        if search:
            items = [it for it in items if search in it.lower()]

        total = len(items)
        per_page = scene.list_items_per_page
        max_scroll = max(0, total - per_page)

        if self.direction == 'UP':
            scene.list_vertical_scroll = max(0, scene.list_vertical_scroll - 1)
        else:
            scene.list_vertical_scroll = min(max_scroll, scene.list_vertical_scroll + 1)

        return {'FINISHED'}


class LIST_OT_JumpToPage(Operator):
    bl_idname = "list.jump_to_page"
    bl_label = "Jump to Page"
    bl_description = "Jump to a specific page in the list of quadblocks/triblocks"
    bl_options = {'REGISTER'}

    page_number: IntProperty(name="Page Number", default=1, min=1)

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        # Same count logic
        items = []
        if scene.list_display_type == 'VERTEX_GROUPS':
            for vg in obj.vertex_groups:
                if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                    items.append(vg.name)
                elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                    items.append(vg.name)
        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            if "constant_materials" in obj:
                for mat_name, info in obj["constant_materials"].items():
                    bt = info.get("block_type", "")
                    if (bt == "quadblock" and scene.list_filter_cm_qb) or \
                       (bt == "triblock" and scene.list_filter_cm_tb):
                        items.append(mat_name)

        search = scene.list_search_text.lower()
        if search:
            items = [it for it in items if search in it.lower()]

        total = len(items)
        per_page = scene.list_items_per_page
        total_pages = max(1, (total + per_page - 1) // per_page)
        self.page_number = max(1, min(self.page_number, total_pages))
        scene.list_vertical_scroll = (self.page_number - 1) * per_page
        return {'FINISHED'}


classes = [
    LIST_OT_VerticalScroll,
    LIST_OT_JumpToPage,
]