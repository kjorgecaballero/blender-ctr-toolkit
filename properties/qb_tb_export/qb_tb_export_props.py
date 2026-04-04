import bpy

def register():
    bpy.types.Scene.export_index = bpy.props.IntProperty(
        name="Export Index",
        description="Current export counter",
        default=0,
        min=0
    )
    
    bpy.types.Scene.last_export_path = bpy.props.StringProperty(
        name="Last Export Path",
        description="Last used export project folder for quick export continuity",
        default="",
        subtype='DIR_PATH'
    )
    
    bpy.types.Scene.folder_behavior = bpy.props.EnumProperty(
        name="Behavior",
        description="How to handle existing folders when exporting to folder",
        items=[
            ('REPLACE', 'Replace', 'Replace existing folder'),
            ('INCREMENTAL', 'Numerical Increment', 'Create folder with numerical increment'),
        ],
        default='INCREMENTAL'
    )
    
    bpy.types.Scene.export_quadblocks = bpy.props.BoolProperty(
        name="Quadblocks",
        description="Export Quadblocks",
        default=True
    )
    
    bpy.types.Scene.export_triblocks = bpy.props.BoolProperty(
        name="Triblocks",
        description="Export Triblocks",
        default=True
    )
    
    bpy.types.Scene.export_colors = bpy.props.BoolProperty(
        name="Vertex Colors",
        description="Export Vertex Colors",
        default=True
    )
    
    bpy.types.Scene.export_to_folder = bpy.props.BoolProperty(
        name="Export to Folder",
        description="Export OBJ to organized folder structure",
        default=False
    )
    
    bpy.types.Scene.include_textures = bpy.props.BoolProperty(
        name="Include Textures",
        description="Copy textures to texture folder",
        default=False
    )
    
    bpy.types.Scene.remap_textures = bpy.props.BoolProperty(
        name="Remap Textures",
        description="Remap model to use exported textures in texture folder",
        default=False
    )
    
    bpy.types.Scene.apply_modifiers = bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before validating and exporting",
        default=False
    )
    
    bpy.types.Scene.separate_loose_parts = bpy.props.BoolProperty(
        name="Separate by Loose Parts",
        description="Separate mesh by loose parts before validating",
        default=False
    )
    
    bpy.types.Scene.global_scale = bpy.props.FloatProperty(
        name="Scale",
        description="Global export scale",
        min=0.001, max=1000.0,
        default=1.0
    )
    
    bpy.types.Scene.export_invalid_uvs = bpy.props.BoolProperty(
        name="Invalid UVs",
        description="Export objects with UVs outside 0-1 range",
        default=False
    )
    
    bpy.types.Scene.export_invalid_triblock_uvs = bpy.props.BoolProperty(
        name="Invalid Triblock UVs",
        description="Export triblocks with incorrect UV arrangement (shared vertices mismatch)",
        default=False
    )
    
    bpy.types.Scene.export_degenerated_uvs = bpy.props.BoolProperty(
        name="Degenerated UVs",
        description="Export objects with degenerated UVs",
        default=False
    )
    
    bpy.types.Scene.path_mode = bpy.props.EnumProperty(
        name="Path Mode",
        description="Texture path handling",
        items=[
            ('AUTO', 'Auto', 'Automatic path handling'),
            ('ABSOLUTE', 'Absolute', 'Use absolute paths'),
            ('RELATIVE', 'Relative', 'Use relative paths'),
            ('COPY', 'Copy', 'Copy textures to export folder'),
            ('STRIP', 'Strip', 'Strip texture paths'),
        ],
        default='ABSOLUTE'
    )
    
    bpy.types.Scene.export_details = bpy.props.BoolProperty(
        name="Export Details (JSON)",
        description="Export a JSON file with export details",
        default=False
    )
    
    bpy.types.Scene.allow_out_of_range = bpy.props.BoolProperty(
        name="Allow Out of Range",
        description="Export objects outside the 1000x1000x1000 range",
        default=False
    )
    
    bpy.types.Scene.use_selection = bpy.props.BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False
    )
    
    # Duplicate export properties
    bpy.types.Scene.export_duplicates = bpy.props.BoolProperty(
        name="Export Duplicates",
        description="Export duplicates of detected blocks to a 'Duplicates' subfolder (ignores UV/range filters)",
        default=False
    )
    
    # Export processed duplicates with user settings
    bpy.types.Scene.export_processed_duplicates = bpy.props.BoolProperty(
        name="Export Processed Duplicates",
        description="After duplication, export the processed objects using current export settings (filters, folder, etc.)",
        default=False
    )

def unregister():
    del bpy.types.Scene.export_index
    del bpy.types.Scene.last_export_path
    del bpy.types.Scene.folder_behavior
    del bpy.types.Scene.export_quadblocks
    del bpy.types.Scene.export_triblocks
    del bpy.types.Scene.export_colors
    del bpy.types.Scene.export_to_folder
    del bpy.types.Scene.include_textures
    del bpy.types.Scene.remap_textures
    del bpy.types.Scene.apply_modifiers
    del bpy.types.Scene.separate_loose_parts
    del bpy.types.Scene.global_scale
    del bpy.types.Scene.export_invalid_uvs
    del bpy.types.Scene.export_invalid_triblock_uvs
    del bpy.types.Scene.export_degenerated_uvs
    del bpy.types.Scene.path_mode
    del bpy.types.Scene.export_details
    del bpy.types.Scene.allow_out_of_range
    del bpy.types.Scene.use_selection
    del bpy.types.Scene.export_duplicates
    del bpy.types.Scene.export_processed_duplicates