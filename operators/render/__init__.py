import bpy
from . import backface, toggle_ps1, blend_mode, material_overrides, analyze_image, split_screen
from ...utils.compat import is_blender_ge_4_0

# Core operators always present
core_classes = (
    backface.SetBackfaceVisibility,
    toggle_ps1.TogglePS1Resolution,
    toggle_ps1.ToggleCTRRender,
    blend_mode.ApplyBlendMode,
    material_overrides.ApplyMaterialOverrides,
    material_overrides.ResetMaterialOverrides,
    analyze_image.AnalyzeImage,
    split_screen.ToggleSplitScreen,
)

# Vertex snap operators only for Blender >= 4.0
if is_blender_ge_4_0():
    from . import vertex_snap
    vertex_classes = (
        vertex_snap.VXSNAP_OT_add,
        vertex_snap.VXSNAP_OT_remove,
        vertex_snap.VXSNAP_OT_update,
    )
else:
    vertex_classes = ()

classes = core_classes + vertex_classes

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)