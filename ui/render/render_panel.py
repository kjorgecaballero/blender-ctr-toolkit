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

    # Row 2: Toggle CTR Render + Apply
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
        # Apply scope selector (moved to top, no extra space)
        scope_row = adv_box.row(align=True)
        scope_row.label(text="Apply:", icon='SHADING_RENDERED')
        scope_row.prop(scene, "blend_apply_scope", text="")

        # PS1 FX SECTION (only for Blender 3.5+)
        if is_blender_ge_3_5():
            ps1fx_box = adv_box.box()
            row = ps1fx_box.row(align=True)
            row.prop(scene, "show_ps1fx_section", text="",
                     icon='TRIA_DOWN' if scene.show_ps1fx_section else 'TRIA_RIGHT',
                     emboss=False)
            row.label(text="PS1 FX", **_icon("psx_icon", 'FILE_MOVIE'))
            if scene.show_ps1fx_section:
                col_inner = ps1fx_box.column(align=True)

                # 512×216 Resolution toggle
                row_toggle = col_inner.row(align=True)
                row_toggle.prop(scene, "ps1_resolution", text="512×216 Resolution", **_icon("resolution_icon", 'FILE_MOVIE'), toggle=True)

                if is_blender_ge_4_0():
                    col_inner.separator()
                    col_inner.label(text="Vertex Snap", icon='SNAP_GRID')
                    row_snap = col_inner.row(align=True)
                    row_snap.prop(scene, "vxsnap_grid_size", text="Grid Size")
                    row_snap.operator("vxsnap.update_snap", text="Refresh", icon='FILE_REFRESH')
                    row_snap = col_inner.row(align=True)
                    row_snap.operator("vxsnap.add_snap", text="Add", icon='ADD')
                    row_snap.operator("vxsnap.remove_snap", text="Remove", icon='REMOVE')

        # BLENDING SECTION
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
                # Blend Method row: Default button
                row_blend = col_inner.row(align=True)
                row_blend.operator("psx.reset_material_overrides", text="Default", icon='RECOVER_LAST')
                row_blend.prop(material, "ps1_blend_method_override", text="")

                col_inner.separator()
                col_inner.label(text="Transparency Overlap:", icon='SHADING_RENDERED')
                row_overlap = col_inner.row(align=True)
                # Second Default button 
                row_overlap.operator("psx.reset_overlap_default", text="Default", icon='RECOVER_LAST')

                if material.ps1_transparency_overlap_mode == 'MANUAL':
                    current_overlap = material.ps1_transparency_overlap_manual
                else:
                    current_overlap = material.ps1_transparency_overlap_manual

                toggle_op = row_overlap.operator("psx.toggle_overlap", text="Overlap",
                                                 depress=current_overlap,
                                                 icon='CHECKBOX_HLT' if current_overlap else 'CHECKBOX_DEHLT')
                toggle_op.value = not current_overlap
            else:
                col_inner.label(text="No active material", icon='ERROR')

        # VIEW SECTION
        view_box = adv_box.box()
        row = view_box.row(align=True)
        row.prop(scene, "show_view_section", text="",
                 icon='TRIA_DOWN' if scene.show_view_section else 'TRIA_RIGHT',
                 emboss=False)
        row.label(text="View", icon='VIEW3D')
        if scene.show_view_section:
            col_inner = view_box.column(align=True)
            col_inner.operator("psx.toggle_split_screen", text="Split Screen", **_icon("split_screen_icon", 'VIEWZOOM'))