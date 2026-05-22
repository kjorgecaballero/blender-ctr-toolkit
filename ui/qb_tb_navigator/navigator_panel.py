import bpy
from ...icons import get_icon

def _icon(name, fallback):
    ico = get_icon(name)
    return {'icon_value': ico} if ico else {'icon': fallback}

def draw_navigator(context, layout):
    scene = context.scene
    obj = context.edit_object
    is_edit_mode = (context.mode == 'EDIT_MESH')

    box = layout.box()
    col = box.column(align=True)

    row = col.row(align=True)
    row.operator("navigator.find_blocks", text="Navigate", **_icon("navigate_icon", 'ZOOM_ALL'))
    row.operator("navigator.clear_block_cache", text="Reset", **_icon("reset_icon", 'TRASH'))

    row = col.row(align=True)
    row.operator("navigator.select_quadblocks_only", text="Quadblock", **_icon("quadblock_icon", 'VERTEXSEL'))
    row.operator("navigator.select_triblocks_only", text="Triblock", **_icon("triblock_icon", 'FACESEL'))

    row = col.row(align=True)
    row.operator("navigator.duplicate_all_blocks_by_group", text="Duplicate", **_icon("duplicate_icon", 'DUPLICATE'))
    row.operator("navigator.select_invalid_faces", text="Invalid", **_icon("invalid_icon", 'ERROR'))

    if obj and (("quad_group_members" in obj and obj["quad_group_members"]) or 
                ("tri_group_members" in obj and obj["tri_group_members"])):
        group_box = box.box()
        row = group_box.row(align=True)
        row.prop(scene, "navigator_show_group_selection",
                 icon="TRIA_DOWN" if scene.navigator_show_group_selection else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="Group Selection", icon='GROUP')

        if scene.navigator_show_group_selection:
            inner_box = group_box.box()

            if "quad_group_members" in obj and obj["quad_group_members"]:
                quad_box = inner_box.box()
                quad_icon = get_icon("quadblock_icon")
                if quad_icon:
                    quad_box.label(text="Quadblocks Groups", icon_value=quad_icon)
                else:
                    quad_box.label(text="Quadblocks Groups", icon='GROUP_VERTEX')

                row = quad_box.row(align=True)
                row.prop(scene, "navigator_selected_quad_group", text="")
                op = row.operator("navigator.select_quadblock_group", text="Select")
                op.group_number = int(scene.navigator_selected_quad_group) if scene.navigator_selected_quad_group != "0" else 0

            if "tri_group_members" in obj and obj["tri_group_members"]:
                tri_box = inner_box.box()
                tri_icon = get_icon("triblock_icon")
                if tri_icon:
                    tri_box.label(text="Triblocks Groups", icon_value=tri_icon)
                else:
                    tri_box.label(text="Triblocks Groups", icon='MENU_PANEL')

                row = tri_box.row(align=True)
                row.prop(scene, "navigator_selected_tri_group", text="")
                op = row.operator("navigator.select_triblock_group", text="Select")
                op.group_number = int(scene.navigator_selected_tri_group) if scene.navigator_selected_tri_group != "0" else 0

    if not is_edit_mode:
        layout.label(text="Enter Edit Mode to use tools", icon='ERROR')