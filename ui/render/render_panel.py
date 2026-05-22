import bpy
from ...utils.compat import is_blender_ge_3_5, is_blender_ge_4_0
from ...icons import get_icon

def _icon(name, fallback):
    ico = get_icon(name)
    return {'icon_value': ico} if ico else {'icon': fallback}

def draw_render(context, layout):
    scene = context.scene

    box = layout.box()
    col = box.column(align=True)

    # Row 1: Show/Hide backfaces
    row = col.row(align=True)
    op_show = row.operator("psx.set_backface", text="Show", icon='HIDE_OFF')
    op_show.show = True
    op_hide = row.operator("psx.set_backface", text="Hide", icon='HIDE_ON')
    op_hide.show = False

    # Row 2: Toggle CTR Render (circular radio toggle) + Apply
    row = col.row(align=True)
    if scene.psx_render_state:
        toggle_icon = 'RADIOBUT_ON'
    else:
        toggle_icon = 'RADIOBUT_OFF'
    row.operator("psx.toggle_ctr_render", text="ON" if scene.psx_render_state else "OFF", icon=toggle_icon)
    row.operator("psx.apply_blend_mode", text="Apply", icon='CHECKMARK')

    # Blend mode dropdown
    row = col.row(align=True)
    row.prop(scene, "blend_mode", text="")

    # Advanced section
    adv_box = box.box()
    row = adv_box.row(align=True)
    row.prop(scene, "show_advanced_overrides", text="",
             icon='TRIA_DOWN' if scene.show_advanced_overrides else 'TRIA_RIGHT',
             emboss=False)
    row.label(text="Advanced", icon='SETTINGS')

    if scene.show_advanced_overrides:
        # PS1 FX SECTION – only for Blender 3.5+
        if is_blender_ge_3_5():
            ps1fx_box = adv_box.box()
            row = ps1fx_box.row(align=True)
            row.prop(scene, "show_ps1fx_section", text="",
                     icon='TRIA_DOWN' if scene.show_ps1fx_section else 'TRIA_RIGHT',
                     emboss=False)
            # Header with custom psx_icon
            row.label(text="PS1 FX", **_icon("psx_icon", 'FILE_MOVIE'))
            if scene.show_ps1fx_section:
                col_inner = ps1fx_box.column(align=True)
                
                # PS1 Resolution toggle (blue when active) with custom resolution_icon
                row_toggle = col_inner.row(align=True)
                row_toggle.prop(scene, "ps1_resolution", text="PS1 Resolution", **_icon("resolution_icon", 'FILE_MOVIE'), toggle=True)
                
                if is_blender_ge_4_0():
                    col_inner.separator()
                    col_inner.label(text="Vertex Snap", icon='SNAP_GRID')
                    row_snap = col_inner.row(align=True)
                    row_snap.prop(scene, "vxsnap_grid_size", text="Grid Size")
                    row_snap.operator("vxsnap.update_snap", text="Refresh", icon='FILE_REFRESH')
                    row_snap = col_inner.row(align=True)
                    row_snap.operator("vxsnap.add_snap", text="Add", icon='ADD')
                    row_snap.operator("vxsnap.remove_snap", text="Remove", icon='REMOVE')
        # If Blender < 3.5, the PS1 FX section is not drawn at all

        # Blending section (always visible)
        blending_box = adv_box.box()
        row = blending_box.row(align=True)
        row.prop(scene, "show_blending_section", text="",
                 icon='TRIA_DOWN' if scene.show_blending_section else 'TRIA_RIGHT',
                 emboss=False)
        row.label(text="Blending", icon='MATERIAL')

        if scene.show_blending_section:
            col_inner = blending_box.column(align=True)
            material = context.active_object.active_material if context.active_object else None
            if material:
                row = col_inner.row(align=True)
                row.prop(material, "ps1_blend_method_override", text="")
                row = col_inner.row(align=True)
                row.operator("psx.apply_material_overrides", text="Apply", icon='CHECKMARK')
                row.operator("psx.reset_material_overrides", text="Reset", icon='LOOP_BACK')
            else:
                col_inner.label(text="No active material", icon='ERROR')

        # View section (always visible)
        view_box = adv_box.box()
        row = view_box.row(align=True)
        row.prop(scene, "show_view_section", text="",
                 icon='TRIA_DOWN' if scene.show_view_section else 'TRIA_RIGHT',
                 emboss=False)
        row.label(text="View", icon='VIEW3D')
        if scene.show_view_section:
            col_inner = view_box.column(align=True)
            col_inner.operator("psx.toggle_split_screen", text="Split Screen", **_icon("split_screen_icon", 'VIEWZOOM'))