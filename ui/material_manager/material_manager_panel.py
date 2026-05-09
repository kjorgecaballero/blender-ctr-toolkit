import bpy
from bpy.types import Panel

from ..qb_tb_list.list_helpers import get_material_image_icon
from ..help_utils import CTR_HelpUtils


class CTR_PT_MaterialManager(Panel):
    bl_label = "CTR Material Manager"
    bl_idname = "CTR_PT_material_manager"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ctr_material_list
        obj = context.active_object

        # Filter dropdown + help buttons on the same row
        row = layout.row(align=True)
        row.prop(props, "filter_type", text="")
        row.separator(factor=1.0)
        CTR_HelpUtils.draw_help_buttons_into_row(row)

        # Search bar
        row = layout.row(align=True)
        row.prop(props, "search_text", text="", icon='VIEWZOOM')

        # First row: Assign, Select, Deselect
        row1 = layout.row(align=True)

        assign_disabled = False
        if props.selected_index >= 0 and props.selected_index < len(props.items):
            selected_mat_name = props.items[props.selected_index].name
            if obj and "constant_materials" in obj and selected_mat_name in obj["constant_materials"]:
                assign_disabled = True

        assign_row = row1.row(align=True)
        assign_row.enabled = not assign_disabled
        assign_row.operator("material.assign_selected", text="Assign", icon='CHECKMARK')

        row1.operator("material.select_by_material", text="Select", icon='RESTRICT_SELECT_OFF')
        row1.operator("material.deselect_by_material", text="Deselect", icon='RESTRICT_SELECT_ON')

        # Second row: Rename, Remap, Refresh
        row2 = layout.row(align=True)

        rename_row = row2.row(align=True)
        rename_row.enabled = (props.selected_index >= 0 and props.selected_index < len(props.items))
        rename_row.operator("material.rename_material", text="Rename", icon='OUTLINER_DATA_FONT')

        remap_row = row2.row(align=True)
        remap_row.enabled = (props.selected_index >= 0 and props.selected_index < len(props.items))
        remap_row.operator("material.remap_material", text="Remap", icon='FILE_REFRESH')

        row2.operator("material.refresh_list", text="Refresh", icon='FILE_REFRESH')

        # List area
        total = len(props.items)
        if total == 0:
            layout.box().label(text="No materials match the filter", icon='INFO')
            return

        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        safe_scroll = min(props.scroll, max_scroll)
        start = safe_scroll
        end = min(start + ITEMS_PER_PAGE, total)

        box = layout.box()
        count_row = box.row()
        count_row.alignment = 'CENTER'
        count_row.label(text=f"Materials: {total}  (page {(safe_scroll // ITEMS_PER_PAGE) + 1} of {max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)})")

        for idx in range(start, end):
            item = props.items[idx]
            mat_name = item.name
            row = box.row(align=True)

            is_sel = (idx == props.selected_index)
            icon = 'CHECKBOX_HLT' if is_sel else 'CHECKBOX_DEHLT'
            op = row.operator("material.toggle_selection", text="", icon=icon, emboss=False)
            op.index = idx

            icon_id = get_material_image_icon(mat_name)
            if isinstance(icon_id, int) and icon_id != 0:
                row.label(text=mat_name, icon_value=icon_id)
            else:
                row.label(text=mat_name, icon='MATERIAL')

            if is_sel:
                row.alert = True

        if total > ITEMS_PER_PAGE:
            pagination_row = box.row(align=True)
            pagination_row.alignment = 'CENTER'
            current_page = (safe_scroll // ITEMS_PER_PAGE) + 1
            total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            up = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_UP')
            up.direction = 'UP'
            first = pagination_row.operator("material.jump_to_page", text="<<", icon='REW')
            first.page = 1
            prev = pagination_row.operator("material.jump_to_page", text="<", icon='PREV_KEYFRAME')
            prev.page = current_page - 1 if current_page > 1 else 1
            pagination_row.label(text=f"[{current_page}/{total_pages}]")
            nxt = pagination_row.operator("material.jump_to_page", text=">", icon='NEXT_KEYFRAME')
            nxt.page = current_page + 1 if current_page < total_pages else total_pages
            last = pagination_row.operator("material.jump_to_page", text=">>", icon='FF')
            last.page = total_pages
            down = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_DOWN')
            down.direction = 'DOWN'


def register():
    bpy.utils.register_class(CTR_PT_MaterialManager)


def unregister():
    bpy.utils.unregister_class(CTR_PT_MaterialManager)