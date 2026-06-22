import bpy

class UVTextureItem(bpy.types.PropertyGroup):
    texture_path: bpy.props.StringProperty(
        name="Texture Path",
        default=""
    )
    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        items=[
            ("0", "Half Transparent", ""),
            ("1", "Additive", ""),
            ("2", "Subtractive", ""),
            ("3", "Additive Translucent", ""),
        ],
        default="0"
    )

def register():
    bpy.utils.register_class(UVTextureItem)

def unregister():
    bpy.utils.unregister_class(UVTextureItem)