import bpy

def register():
    # Find option enum
    bpy.types.Scene.find_option = bpy.props.EnumProperty(
        items=[
            ('TRIBLOCK', 'Triblocks', 'Find all Triblocks'),
            ('QUADBLOCK', 'Quadblocks', 'Find all Quadblocks'),
        ],
        default='TRIBLOCK'
    )
    
    # Select option enum
    bpy.types.Scene.select_option = bpy.props.EnumProperty(
        items=[
            ('ALL_INVALID', 'All Invalid', 'Select all invalid objects'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Select objects with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Select objects with invalid UVs'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Select objects with degenerated UVs'),
            ('TRIBLOCKS', 'Triblocks', 'Select all Triblocks'),
            ('QUADBLOCKS', 'Quadblocks', 'Select all Quadblocks'),
            ('NON_MESH', 'Non-Mesh', 'Select non-mesh objects'),
            ('NGONS', 'NGons', 'Select objects with NGons'),
        ],
        default='ALL_INVALID'
    )

def unregister():
    del bpy.types.Scene.find_option
    del bpy.types.Scene.select_option