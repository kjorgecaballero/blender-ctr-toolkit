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

def unregister():
    del bpy.types.Scene.validator_scope
    del bpy.types.Scene.ctr_tool_mode