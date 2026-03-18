import bpy
from bpy.props import EnumProperty

def register():
    bpy.types.Scene.ctr_tool_mode = EnumProperty(
        name="Tool Mode",
        description="Select which tool set to display",
        items=[
            ('NAVIGATOR', "Navigator", "Quadblock/Triblock navigation tools"),
            ('VALIDATOR', "Validator", "QB/TB validation tools"),
        ],
        default='NAVIGATOR'
    )

def unregister():
    del bpy.types.Scene.ctr_tool_mode