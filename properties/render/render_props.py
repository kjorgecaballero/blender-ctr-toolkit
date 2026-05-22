import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, FloatProperty

def update_ps1_resolution(self, context):
    """Apply or remove PS1 compositing when resolution toggle changes."""
    if self.ps1_resolution:
        from ...utils.render.compositing import apply_ps1_compositing
        apply_ps1_compositing(context)
    else:
        from ...utils.render.compositing import remove_ps1_compositing
        remove_ps1_compositing(context)

def _clean_old_props():
    props_to_remove = [
        'eye_open', 'tv_toggle', 'on_off_state', 'selection_mode',
        'pixel_analysis_result', 'ps1_prev_shadow_state', 'show_advanced_overrides'
    ]
    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

def update_ps1_blend_mode(self, context):
    if hasattr(self, 'ps1_blend_mode') and self.ps1_blend_mode != 'NONE':
        current_backface = getattr(self, 'ps1_show_backface', False)
        if context.scene.ps1_render_active:
            try:
                from ...utils.render.material_setup import PS1MaterialFactory
                setup = PS1MaterialFactory.get_material_setup(self, self.ps1_blend_mode)
                success = setup.apply_setup()
                if success:
                    self.ps1_show_backface = current_backface
            except Exception as e:
                print(f"Error updating material '{self.name}': {e}")
        else:
            self.ps1_last_active_mode = self.ps1_blend_mode
            self.ps1_show_backface = current_backface

def register():
    _clean_old_props()

    # Scene properties
    bpy.types.Scene.show_backfaces = BoolProperty(default=True)
    # Add update callback to ps1_resolution
    bpy.types.Scene.ps1_resolution = BoolProperty(
        default=False,
        update=update_ps1_resolution
    )
    bpy.types.Scene.psx_render_state = BoolProperty(default=False)
    bpy.types.Scene.split_screen_enabled = BoolProperty(default=False)
    bpy.types.Scene.blend_mode = EnumProperty(
        items=[
            ('HALF_TRANSPARENT', "Half Transparent", ""),
            ('ADDITIVE', "Additive", ""),
            ('SUBTRACTIVE', "Subtractive", ""),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "")
        ],
        default='HALF_TRANSPARENT'
    )
    bpy.types.Scene.pixel_analysis_result = StringProperty(default="Select an object with an image texture")
    bpy.types.Scene.ps1_render_active = BoolProperty(default=False)
    bpy.types.Scene.ps1_prev_shadow_state = BoolProperty(default=True)
    bpy.types.Scene.show_advanced_overrides = BoolProperty(default=False)

    # Collapsible sections
    bpy.types.Scene.show_ps1fx_section = BoolProperty(
        name="Show PS1 FX Section",
        default=False,
        description="Expand/collapse the PS1 FX section"
    )
    bpy.types.Scene.show_blending_section = BoolProperty(
        name="Show Blending Section",
        default=False,
        description="Expand/collapse the Blending section"
    )
    bpy.types.Scene.show_view_section = BoolProperty(
        name="Show View Section",
        default=False,
        description="Expand/collapse the View section"
    )

    # Material properties
    bpy.types.Material.ps1_blend_mode = EnumProperty(
        items=[
            ('NONE', "None", ""),
            ('ADDITIVE', "Additive", ""),
            ('SUBTRACTIVE', "Subtractive", ""),
            ('HALF_TRANSPARENT', "Half Transparent", ""),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "")
        ],
        default='NONE',
        update=update_ps1_blend_mode
    )
    bpy.types.Material.ps1_last_active_mode = EnumProperty(
        items=[
            ('NONE', "None", ""),
            ('ADDITIVE', "Additive", ""),
            ('SUBTRACTIVE', "Subtractive", ""),
            ('HALF_TRANSPARENT', "Half Transparent", ""),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "")
        ],
        default='NONE'
    )
    bpy.types.Material.ps1_show_backface = BoolProperty(default=False)
    bpy.types.Material.ps1_blend_method_override = EnumProperty(
        items=[
            ('AUTO', "Auto", ""),
            ('OPAQUE', "Opaque", ""),
            ('CLIP', "Clip", ""),
            ('HASHED', "Hashed", ""),
            ('BLEND', "Blend", "")
        ],
        default='AUTO'
    )

    from ...utils.compat import is_blender_ge_4_0
    if is_blender_ge_4_0():
        bpy.types.Scene.vxsnap_grid_size = FloatProperty(default=0.1, min=0.001, max=10.0, step=0.1, precision=3)

def unregister():
    del bpy.types.Scene.show_backfaces
    del bpy.types.Scene.ps1_resolution
    del bpy.types.Scene.psx_render_state
    del bpy.types.Scene.split_screen_enabled
    del bpy.types.Scene.blend_mode
    del bpy.types.Scene.pixel_analysis_result
    del bpy.types.Scene.ps1_render_active
    del bpy.types.Scene.ps1_prev_shadow_state
    del bpy.types.Scene.show_advanced_overrides
    del bpy.types.Scene.show_ps1fx_section
    del bpy.types.Scene.show_blending_section
    del bpy.types.Scene.show_view_section

    del bpy.types.Material.ps1_blend_mode
    del bpy.types.Material.ps1_last_active_mode
    del bpy.types.Material.ps1_show_backface
    del bpy.types.Material.ps1_blend_method_override

    from ...utils.compat import is_blender_ge_4_0
    if is_blender_ge_4_0():
        del bpy.types.Scene.vxsnap_grid_size