import bpy

def register():
    # Unified option for both Find and Select
    bpy.types.Scene.validator_option = bpy.props.EnumProperty(
        name="Option",
        description="Object type to find or select",
        items=[
            ('QUADBLOCK', 'Quadblocks', 'Quadblock objects'),
            ('TRIBLOCK', 'Triblocks', 'Triblock objects'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Objects with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Objects with invalid UVs'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Triblocks with invalid UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Objects with degenerated UVs'),
            ('NGONS', 'NGons', 'Objects with NGons'),
            ('NON_MESH', 'Non-Mesh', 'Non-mesh objects'),
            ('OUT_OF_RANGE', 'Out of Range', 'Objects outside the range box'),
            ('ALL_INVALID', 'All Invalid', 'All invalid objects'),
        ],
        default='QUADBLOCK'
    )

def unregister():
    del bpy.types.Scene.validator_option