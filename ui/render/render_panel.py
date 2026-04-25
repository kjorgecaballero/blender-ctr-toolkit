import bpy
from ...utils.compat import is_blender_ge_4_0

def draw_render(context, layout):
    scene = context.scene

    # Main container box (same as Navigator and Validator)
    box = layout.box()
    col = box.column(align=True)

    # Row 1: Show / Hide backfaces
    row = col.row(align=True)
    op_show = row.operator("psx.set_backface", text="Show", icon='SHADING_WIRE')
    op_show.show = True
    op_hide = row.operator("psx.set_backface", text="Hide", icon='HIDE_OFF')
    op_hide.show = False

    # Row 2: Split screen and PS1 FX
    row = col.row(align=True)
    row.operator("psx.toggle_split_screen", text="Split", icon='VIEWZOOM')
    row.operator("psx.toggle_ps1_resolution", text="PS1 FX", icon='RENDER_STILL')

    # Row 3: Toggle CTR Render and Apply blend mode
    row = col.row(align=True)
    render_text = "ON" if scene.psx_render_state else "OFF"
    row.operator("psx.toggle_ctr_render", text=render_text, icon='RENDER_ANIMATION')
    row.operator("psx.apply_blend_mode", text="Apply", icon='CHECKMARK')

    # Blend mode dropdown (full width row)
    row = col.row(align=True)
    row.prop(scene, "blend_mode", text="")

    # Advanced collapsible section (exactly like Navigator's group selection)
    adv_box = box.box()
    row = adv_box.row(align=True)
    row.prop(scene, "show_advanced_overrides", text="",
             icon='TRIA_DOWN' if scene.show_advanced_overrides else 'TRIA_RIGHT',
             emboss=False)
    row.label(text="Advanced", icon='SETTINGS')

    if scene.show_advanced_overrides:
        inner = adv_box.column(align=True)
        material = context.active_object.active_material if context.active_object else None
        if material:
            row = inner.row(align=True)
            row.prop(material, "ps1_blend_method_override", text="Blending")
            row = inner.row(align=True)
            row.operator("psx.apply_material_overrides", text="Apply")
            row.operator("psx.reset_material_overrides", text="Reset")
        else:
            inner.label(text="No active material", icon='ERROR')

        # Vertex Snap (World Grid) – only for Blender 4.0+
        if is_blender_ge_4_0():
            inner.separator()
            inner.label(text="Vertex Snap", icon='SNAP_GRID')
            row = inner.row(align=True)
            row.prop(scene, "vxsnap_grid_size", text="Grid Size")
            row.operator("vxsnap.update_snap", text="Refresh", icon='FILE_REFRESH')
            row = inner.row(align=True)
            row.operator("vxsnap.add_snap", text="Add Snap", icon='ADD')
            row.operator("vxsnap.remove_snap", text="Remove", icon='REMOVE')