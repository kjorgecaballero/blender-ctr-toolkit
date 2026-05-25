import bpy

class ExportSettings:
    """
    Container for export configuration settings.
    
    Stores all user preferences for the export operation including:
    - Object filtering (Quadblocks/Triblocks)
    - Export options (textures, colors, scale)
    - Folder organization
    - Validation filters
    """
    
    def __init__(self):
        """Initialize export settings with default values."""
        self.filepath = ""
        self.use_selection = False
        self.export_quadblocks = True
        self.export_triblocks = True
        self.export_colors = True
        self.export_textures = True
        self.export_to_folder = True
        self.include_textures = False
        self.remap_textures = False
        self.apply_modifiers = True
        self.separate_loose_parts = False
        self.global_scale = 1.0
        self.export_invalid_uvs = False
        self.export_invalid_triblock_uvs = False
        self.export_degenerated_uvs = False
        self.export_multiple_materials = False
        self.path_mode = 'COPY'
        self.folder_behavior = 'SUFFIX'
        self.folder_name = ""
        self.allow_out_of_range = False
        self.export_details = False   # export JSON details
        
    @classmethod
    def from_operator(cls, operator):
        """
        Create ExportSettings from operator properties.
        
        Args:
            operator: QB_TB_OT_ExportQuadTriBlocks instance
            
        Returns:
            ExportSettings: Configured settings object
        """
        settings = cls()
        settings.filepath = operator.filepath
        settings.use_selection = operator.use_selection
        settings.export_quadblocks = operator.export_quadblocks
        settings.export_triblocks = operator.export_triblocks
        settings.export_colors = operator.export_colors
        settings.export_to_folder = operator.export_to_folder
        settings.include_textures = operator.include_textures
        settings.remap_textures = operator.remap_textures
        settings.apply_modifiers = operator.apply_modifiers
        settings.separate_loose_parts = operator.separate_loose_parts
        settings.global_scale = operator.global_scale
        settings.export_invalid_uvs = operator.export_invalid_uvs
        settings.export_invalid_triblock_uvs = operator.export_invalid_triblock_uvs
        settings.export_degenerated_uvs = operator.export_degenerated_uvs
        settings.export_multiple_materials = operator.export_multiple_materials
        settings.path_mode = operator.path_mode
        settings.folder_behavior = operator.folder_behavior
        settings.allow_out_of_range = operator.allow_out_of_range
        settings.export_details = getattr(operator, 'export_details', False)
        return settings
    
    @classmethod
    def from_scene_props(cls, context):
        """
        Create ExportSettings from scene properties.
        
        Args:
            context: Blender context with scene settings
            
        Returns:
            ExportSettings: Configured settings object
        """
        settings = cls()
        settings.use_selection = context.scene.use_selection
        settings.export_quadblocks = context.scene.export_quadblocks
        settings.export_triblocks = context.scene.export_triblocks
        settings.export_colors = context.scene.export_colors
        settings.export_to_folder = context.scene.export_to_folder
        settings.include_textures = context.scene.include_textures
        settings.remap_textures = context.scene.remap_textures
        settings.apply_modifiers = context.scene.apply_modifiers
        settings.separate_loose_parts = context.scene.separate_loose_parts
        settings.global_scale = context.scene.global_scale
        settings.export_invalid_uvs = context.scene.export_invalid_uvs
        settings.export_invalid_triblock_uvs = context.scene.export_invalid_triblock_uvs
        settings.export_degenerated_uvs = context.scene.export_degenerated_uvs
        settings.export_multiple_materials = context.scene.export_multiple_materials
        settings.path_mode = context.scene.path_mode
        settings.folder_behavior = context.scene.folder_behavior
        settings.allow_out_of_range = context.scene.allow_out_of_range
        settings.export_details = getattr(context.scene, 'export_details', False)
        return settings

class ExportStats:
    """
    Container for export statistics and reporting.
    
    Tracks export results including:
    - Counts of exported objects by type
    - Objects with issues
    - Folder information
    """
    
    def __init__(self):
        """Initialize statistics with zero values."""
        self.quadblocks = 0
        self.triblocks = 0
        self.total_exported = 0
        self.objects_with_uv_issues = []
        self.exported_with_uv_issues = 0
        self.out_of_range_filtered = 0
        self.out_of_range_names = []
        self.exported_folder = None
    
    @classmethod
    def from_dict(cls, stats_dict):
        """
        Create ExportStats from statistics dictionary.
        
        Args:
            stats_dict: Dictionary with export statistics
            
        Returns:
            ExportStats: Populated statistics object
        """
        stats = cls()
        stats.quadblocks = stats_dict.get('quadblocks', 0)
        stats.triblocks = stats_dict.get('triblocks', 0)
        stats.total_exported = stats_dict.get('total_exported', 0)
        stats.exported_with_uv_issues = stats_dict.get('exported_with_uv_issues', 0)
        stats.out_of_range_filtered = stats_dict.get('out_of_range_filtered', 0)
        stats.out_of_range_names = stats_dict.get('out_of_range_names', [])
        return stats
        
    def get_report_message(self):
        """
        Generate export report message.
        
        Returns:
            str: Formatted report message for Blender info panel
        """
        report_parts = []
        
        # Build type summary
        type_parts = []
        if self.quadblocks > 0:
            type_parts.append(f"{self.quadblocks} Quadblocks")
        if self.triblocks > 0:
            type_parts.append(f"{self.triblocks} Triblocks")
        
        if type_parts:
            report_parts.append(f"Exported: {', '.join(type_parts)}")
        else:
            report_parts.append(f"Exported: {self.total_exported} objects")
        
        # Add issue warnings
        if self.exported_with_uv_issues > 0:
            report_parts.append(f"[{self.exported_with_uv_issues} with UV issues]")
        
        if self.out_of_range_filtered > 0:
            report_parts.append(f"[{self.out_of_range_filtered} outside range filtered]")
        
        # Add folder information
        if self.exported_folder:
            folder_name = self.exported_folder
            report_parts.append(f"in folder '{folder_name}'")
        
        return " ".join(report_parts)