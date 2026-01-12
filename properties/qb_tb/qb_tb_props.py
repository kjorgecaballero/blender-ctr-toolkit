import bpy

def register():
    bpy.types.Scene.find_option = bpy.props.EnumProperty(
        items=[
            ('QUADBLOCK', 'Quadblocks', 'Find all Quadblocks'),
            ('TRIBLOCK', 'Triblocks', 'Find all Triblocks'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Find objects with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Find objects with invalid UVs'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Find triblocks with invalid UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Find objects with degenerated UVs'),
            ('NGONS', 'NGons', 'Find objects with NGons'),
            ('NON_MESH', 'Non-Mesh', 'Find non-mesh objects'),
            ('OUT_OF_RANGE', 'Out of Range', 'Find objects outside the range box'),
            ('ALL_INVALID', 'All Invalid', 'Find all invalid objects'),
        ],
        default='QUADBLOCK'
    )
    
    bpy.types.Scene.select_option = bpy.props.EnumProperty(
        items=[
            ('QUADBLOCKS', 'Quadblocks', 'Select all Quadblocks'),
            ('TRIBLOCKS', 'Triblocks', 'Select all Triblocks'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Select objects with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Select objects with invalid UVs'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Select triblocks with invalid UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Select objects with degenerated UVs'),
            ('NGONS', 'NGons', 'Select objects with NGons'),
            ('NON_MESH', 'Non-Mesh', 'Select non-mesh objects'),
            ('OUT_OF_RANGE', 'Out of Range', 'Select objects outside the range box'),
            ('ALL_INVALID', 'All Invalid', 'Select all invalid objects'),
        ],
        default='QUADBLOCKS'
    )

def unregister():
    del bpy.types.Scene.find_option
    del bpy.types.Scene.select_option