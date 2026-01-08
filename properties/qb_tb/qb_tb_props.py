import bpy

def register():
    bpy.types.Scene.find_option = bpy.props.EnumProperty(
        items=[
            ('QUADBLOCK', 'Quadblocks', 'Find all Quadblocks'),
            ('TRIBLOCK', 'Triblocks', 'Find all Triblocks'),
        ],
        default='QUADBLOCK'
    )
    
    bpy.types.Scene.select_option = bpy.props.EnumProperty(
        items=[
            ('QUADBLOCKS', 'Quadblocks', 'Select all Quadblocks'),
            ('TRIBLOCKS', 'Triblocks', 'Select all Triblocks'),
            ('ALL_INVALID', 'All Invalid', 'Select all invalid objects'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Select objects with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Select objects with invalid UVs'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Select objects with degenerated UVs'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Select triblocks with invalid UV arrangement'),
            ('NON_MESH', 'Non-Mesh', 'Select non-mesh objects'),
            ('NGONS', 'NGons', 'Select objects with NGons'),
        ],
        default='QUADBLOCKS'
    )

def unregister():
    del bpy.types.Scene.find_option
    del bpy.types.Scene.select_option