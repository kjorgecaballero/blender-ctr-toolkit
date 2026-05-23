import bpy

def register():
    bpy.types.Scene.validator_object_option = bpy.props.EnumProperty(
        name="Object Filter",
        description="Filter to apply to objects",
        items=[
            ('QUADBLOCK', "Quadblocks", "Quadblock objects"),
            ('TRIBLOCK', "Triblocks", "Triblock objects"),
            ('INVALID_GEOMETRY', "Invalid Geometry", "Objects with invalid geometry"),
            ('INVALID_UVS', "Invalid UVs", "Objects with UVs outside 0-1 range"),
            ('INVALID_TRIBLOCK_UVS', "Invalid Triblock UVs", "Triblocks with incorrect UV arrangement"),
            ('DEGENERATED_UVS', "Degenerated UVs", "Objects with degenerated UVs"),
            ('NGONS', "NGons", "Objects with NGons"),
            ('NON_MESH', "Non-Mesh", "Non-mesh objects"),
            ('OUT_OF_RANGE', "Out of Range", "Objects outside the range box"),
            ('MULTIPLE_MATERIALS', "Multiple Materials", "Objects with more than one material"),
            ('ALL_INVALID', "All Invalid", "All invalid objects"),
        ],
        default='ALL_INVALID'
    )
    bpy.types.Scene.validator_vertex_group_option = bpy.props.EnumProperty(
        name="Vertex Group Filter",
        description="Filter to apply to vertex groups",
        items=[
            ('QUADBLOCK', "Quadblocks", "Valid quadblock vertex groups"),
            ('TRIBLOCK', "Triblocks", "Valid triblock vertex groups"),
            ('INVALID_GEOMETRY', "Invalid Geometry", "Groups with invalid geometry"),
            ('INVALID_UVS', "Invalid UVs", "Groups with UVs outside 0-1 range"),
            ('INVALID_TRIBLOCK_UVS', "Invalid Triblock UVs", "Triblocks with incorrect UV arrangement"),
            ('DEGENERATED_UVS', "Degenerated UVs", "Groups with all UVs identical"),
            ('OUT_OF_RANGE', "Out of Range", "Groups with vertices outside the range box"),
            ('MULTIPLE_MATERIALS', "Multiple Materials", "Groups with more than one material on their faces"),
            ('ALL_INVALID', "All Invalid", "All groups with any issue"),
        ],
        default='ALL_INVALID'
    )

def unregister():
    del bpy.types.Scene.validator_object_option
    del bpy.types.Scene.validator_vertex_group_option