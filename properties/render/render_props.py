import bpy
from bpy.props import (
    BoolProperty, EnumProperty, StringProperty, FloatProperty
)


# Clean up old properties to avoid conflicts (from original script)

def _clean_old_props():
    props_to_remove = [
        'eye_open', 'tv_toggle', 'on_off_state', 'selection_mode',
        'pixel_analysis_result', 'ps1_prev_shadow_state', 'show_advanced_overrides'
    ]
    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


# Callback for blend mode update (must be defined before property)

def update_ps1_blend_mode(self, context):
    """Executes automatically when ps1_blend_mode changes"""
    if hasattr(self, 'ps1_blend_mode') and self.ps1_blend_mode != 'NONE':
        current_backface = getattr(self, 'ps1_show_backface', False)

        if context.scene.ps1_render_active:
            print(f"Auto change detected on material '{self.name}': {self.ps1_blend_mode}")
            try:
                # We'll import the factory inside to avoid circular imports
                from ...utils.render.material_setup import PS1MaterialFactory
                setup = PS1MaterialFactory.get_material_setup(self, self.ps1_blend_mode)
                success = setup.apply_setup()
                if success:
                    self.ps1_show_backface = current_backface
                    print(f"Material '{self.name}' updated to mode {self.ps1_blend_mode}")
            except Exception as e:
                print(f"Error updating material '{self.name}': {e}")
        else:
            self.ps1_last_active_mode = self.ps1_blend_mode
            self.ps1_show_backface = current_backface
            print(f"Mode '{self.ps1_blend_mode}' saved for material '{self.name}' (PS1 Render inactive)")


# Register all properties

def register():
    _clean_old_props()

    # Scene properties
    bpy.types.Scene.show_backfaces = BoolProperty(
        name="Show Backfaces",
        default=True,
        description="Toggle backface visibility"
    )

    bpy.types.Scene.ps1_resolution = BoolProperty(
        name="PS1 Resolution",
        default=False,
        description="Toggle PS1 resolution mode"
    )

    bpy.types.Scene.psx_render_state = BoolProperty(
        name="PSX Render State",
        default=False,
        description="PSX render system state"
    )

    bpy.types.Scene.split_screen_enabled = BoolProperty(
        name="Split Screen",
        default=False,
        description="Toggle split screen between Properties and Rendered View"
    )

    bpy.types.Scene.blend_mode = EnumProperty(
        name="Blend Mode",
        items=[
            ('HALF_TRANSPARENT', "Half Transparent", "Half Transparent mode"),
            ('ADDITIVE', "Additive", "Additive mode"),
            ('SUBTRACTIVE', "Subtractive", "Subtractive mode"),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "Additive Translucent mode")
        ],
        default='HALF_TRANSPARENT',
        description="Blend mode for PS1 rendering"
    )

    bpy.types.Scene.pixel_analysis_result = StringProperty(
        name="Pixel Analysis Result",
        default="Select an object with an image texture",
        description="Result of pixel analysis"
    )

    bpy.types.Scene.ps1_render_active = BoolProperty(
        name="PS1 Render Active",
        default=False,
        description="State of PS1 rendering"
    )

    bpy.types.Scene.ps1_prev_shadow_state = BoolProperty(
        name="Previous Shadow State",
        default=True,
        description="Stores the previous shadow state before PS1 render was activated"
    )

    bpy.types.Scene.show_advanced_overrides = BoolProperty(
        name="Show Advanced Overrides",
        default=False,
        description="Expand/collapse the advanced section"
    )

    # Material properties
    bpy.types.Material.ps1_blend_mode = EnumProperty(
        name="PS1 Blend Mode",
        items=[
            ('NONE', "None", "Not a PS1 material"),
            ('ADDITIVE', "Additive", "PS1 additive blending"),
            ('SUBTRACTIVE', "Subtractive", "PS1 subtractive blending"),
            ('HALF_TRANSPARENT', "Half Transparent", "PS1 half transparent material"),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "PS1 additive translucent material")
        ],
        default='NONE',
        update=update_ps1_blend_mode
    )

    bpy.types.Material.ps1_last_active_mode = EnumProperty(
        name="PS1 Last Active Mode",
        items=[
            ('NONE', "None", "Not a PS1 material"),
            ('ADDITIVE', "Additive", "PS1 additive blending"),
            ('SUBTRACTIVE', "Subtractive", "PS1 subtractive blending"),
            ('HALF_TRANSPARENT', "Half Transparent", "PS1 half transparent material"),
            ('ADDITIVE_TRANSLUCENT', "Additive Translucent", "PS1 additive translucent material")
        ],
        default='NONE'
    )

    bpy.types.Material.ps1_show_backface = BoolProperty(
        name="Show Backface",
        description="Show both sides of faces. When disabled, only show front faces (PS1 style)",
        default=False
    )

    bpy.types.Material.ps1_blend_method_override = EnumProperty(
        name="Blend Method Override",
        description="Override Blender's blend method for this material (AUTO = use PS1 recommendation)",
        items=[
            ('AUTO', "Auto", "Use PS1 automatic recommendation"),
            ('OPAQUE', "Opaque", "No transparency"),
            ('CLIP', "Clip", "Alpha clip (hard edges)"),
            ('HASHED', "Hashed", "Hashed transparency (PS1 style for solids)"),
            ('BLEND', "Blend", "True alpha blending")
        ],
        default='AUTO'
    )

    # Vertex snap property (only if Blender >= 4.0, but we'll register it always and let UI check)
    # The property itself is harmless on older versions, but we'll conditionally register to avoid errors.
    from ...utils.compat import is_blender_ge_4_0
    if is_blender_ge_4_0():
        bpy.types.Scene.vxsnap_grid_size = FloatProperty(
            name="Grid Step",
            description="Distance between snap points (world units)",
            default=0.1,
            min=0.001,
            max=10.0,
            step=0.1,
            precision=3
        )

def unregister():
    # Scene properties
    del bpy.types.Scene.show_backfaces
    del bpy.types.Scene.ps1_resolution
    del bpy.types.Scene.psx_render_state
    del bpy.types.Scene.split_screen_enabled
    del bpy.types.Scene.blend_mode
    del bpy.types.Scene.pixel_analysis_result
    del bpy.types.Scene.ps1_render_active
    del bpy.types.Scene.ps1_prev_shadow_state
    del bpy.types.Scene.show_advanced_overrides

    # Material properties
    del bpy.types.Material.ps1_blend_mode
    del bpy.types.Material.ps1_last_active_mode
    del bpy.types.Material.ps1_show_backface
    del bpy.types.Material.ps1_blend_method_override

    from ...utils.compat import is_blender_ge_4_0
    if is_blender_ge_4_0():
        del bpy.types.Scene.vxsnap_grid_size