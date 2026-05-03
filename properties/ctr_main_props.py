import bpy
from bpy.props import EnumProperty

def register():
    bpy.types.Scene.ctr_tool_mode = EnumProperty(
        name="Tool Mode",
        description="Select which tool set to display",
        items=[
            ('NAVIGATOR', "Navigator", "Quadblock/Triblock navigation tools"),
            ('VALIDATOR', "Validator", "QB/TB validation tools"),
            ('RENDER', "Render", "PS1-style rendering tools"),
        ],
        default='NAVIGATOR'
    )

    bpy.types.Scene.validator_scope = EnumProperty(
        name="Scope",
        description="What to validate",
        items=[
            ('OBJECTS', "Objects", "Validate all objects in the scene"),
            ('VERTEX_GROUPS', "Vertex Groups", "Validate vertex groups of active mesh object"),
        ],
        default='OBJECTS'
    )

    # Material filter for the custom Material Manager
    bpy.types.Scene.ctr_material_filter = EnumProperty(
        name="Material Filter",
        description="Filter materials shown in the CTR Material Manager",
        items=[
            ('ALL', "All", "Show all materials"),
            ('NORMAL', "Normal", "Show only normal materials (not constant)"),
            ('CONSTANT', "Constant", "Show only constant materials"),
            ('NAV_POINT', "Nav Point", "Show only navigation point materials"),
        ],
        default='ALL'
    )

def unregister():
    del bpy.types.Scene.ctr_material_filter
    del bpy.types.Scene.validator_scope
    del bpy.types.Scene.ctr_tool_mode