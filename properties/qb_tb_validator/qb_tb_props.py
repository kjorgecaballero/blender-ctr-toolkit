import bpy

def get_validator_items(self, context):
    """Return the list of validator options based on current scope."""
    scene = context.scene
    if scene.validator_scope == 'OBJECTS':
        items = [
            ('QUADBLOCK', "Quadblocks", "Quadblock objects"),
            ('TRIBLOCK', "Triblocks", "Triblock objects"),
            ('INVALID_GEOMETRY', "Invalid Geometry", "Objects with invalid geometry"),
            ('INVALID_UVS', "Invalid UVs", "Objects with invalid UVs"),
            ('INVALID_TRIBLOCK_UVS', "Invalid Triblock UVs", "Triblocks with invalid UV arrangement"),
            ('DEGENERATED_UVS', "Degenerated UVs", "Objects with degenerated UVs"),
            ('NGONS', "NGons", "Objects with NGons"),
            ('NON_MESH', "Non-Mesh", "Non-mesh objects"),
            ('OUT_OF_RANGE', "Out of Range", "Objects outside the range box"),
            ('ALL_INVALID', "All Invalid", "All invalid objects"),
        ]
    else:  # VERTEX_GROUPS
        items = [
            ('QUADBLOCK', "Quadblocks", "Valid quadblock vertex groups"),
            ('TRIBLOCK', "Triblocks", "Valid triblock vertex groups"),
            ('INVALID_GEOMETRY', "Invalid Geometry", "Groups with invalid geometry"),
            ('INVALID_UVS', "Invalid UVs", "Groups with UVs outside 0-1 range"),
            ('INVALID_TRIBLOCK_UVS', "Invalid Triblock UVs", "Triblocks with incorrect UV arrangement"),
            ('DEGENERATED_UVS', "Degenerated UVs", "Groups with all UVs identical"),
            ('ALL_INVALID', "All Invalid", "All groups with any issue"),
        ]
    return items

def register():
    bpy.types.Scene.validator_option = bpy.props.EnumProperty(
        name="Option",
        description="Filter to apply",
        items=get_validator_items
    )

def unregister():
    del bpy.types.Scene.validator_option