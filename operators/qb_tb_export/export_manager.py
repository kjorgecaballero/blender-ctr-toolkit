import os
import shutil
import bpy
from .preprocessing import QB_TB_Preprocessor
from .validation_handler import ValidationHandler
from .texture_handler import TextureHandler
from .details_exporter import DetailsExporter
from .export_settings import ExportSettings, ExportStats
from ...utils.compat import execute_obj_export


class ExportManager:
    """
    Main export manager for QB/TB objects.
    
    Coordinates the complete export workflow including:
    - Object preparation and validation
    - Path and folder management
    - Texture handling
    - Export execution and cleanup
    """
    
    def __init__(self, context):
        """
        Initialize the export manager with Blender context.
        
        Args:
            context: Blender context for accessing scene data
        """
        self.context = context
        self.preprocessor = QB_TB_Preprocessor(context)
        self.validator = ValidationHandler()
        self.texture_handler = TextureHandler()
        self.details_exporter = DetailsExporter()
        
        self.original_active = None
        self.original_selection = []
        self.temp_filepath = None
    
    def _try_create_project_folder(self, base_path, project_name, behavior='INCREMENTAL'):
        """
        Create a project folder for organized exports.
        
        Args:
            base_path: Base directory for the project
            project_name: Name of the project/scene
            behavior: Folder creation strategy ('REPLACE' or 'INCREMENTAL')
            
        Returns:
            str: Path to created project folder, or None if failed
        """
        if behavior == 'REPLACE':
            folder_name = f"{project_name}_replace"
        else:
            folder_name = f"{project_name}_increment"
        
        project_folder = os.path.join(base_path, folder_name)
        
        try:
            os.makedirs(project_folder, exist_ok=True)
            return project_folder
        except Exception as e:
            print(f"Error creating project folder {project_folder}: {e}")
            return None
    
    def _try_create_export_subfolder(self, project_folder, behavior='INCREMENTAL'):
        """
        Create an incremental subfolder within the project folder.
        
        Args:
            project_folder: Parent project folder
            behavior: Subfolder strategy ('REPLACE' or 'INCREMENTAL')
            
        Returns:
            str: Path to created subfolder, or None if failed
        """
        if behavior == 'REPLACE':
            return project_folder
        
        else:
            for i in range(1, 1000):
                subfolder_name = f"{i:03d}"
                subfolder_path = os.path.join(project_folder, subfolder_name)
                
                if not os.path.exists(subfolder_path):
                    try:
                        os.makedirs(subfolder_path, exist_ok=True)
                        return subfolder_path
                    except Exception as e:
                        print(f"Error creating export subfolder {subfolder_path}: {e}")
                        continue
            
            return None
    
    def _get_base_export_path(self, context):
        """
        Get the base export path from context or last export.
        
        Args:
            context: Blender context with scene properties
            
        Returns:
            str: Base directory for exports
        """
        if context.scene.last_export_path and os.path.exists(context.scene.last_export_path):
            last_path = context.scene.last_export_path
            if "_increment" in last_path or "_replace" in last_path:
                return os.path.dirname(last_path)
            return last_path
        elif context.scene.export_default_path:
            return context.scene.export_default_path
        return None
    
    def prepare_objects(self, settings):
        """
        Get initial objects based on export settings.
        
        Args:
            settings: ExportSettings object with user preferences
            
        Returns:
            list: Initial objects to process
        """
        if not settings.export_quadblocks and not settings.export_triblocks:
            return []
            
        if settings.use_selection:
            initial_objects = list(self.context.selected_objects)
        else:
            initial_objects = list(bpy.data.objects)
        
        return initial_objects
    
    def preprocess_objects(self, initial_objects, settings):
        """
        Apply preprocessing steps to objects (modifiers, separation).
        
        Args:
            initial_objects: List of objects to preprocess
            settings: ExportSettings with preprocessing options
            
        Returns:
            list: Processed objects ready for validation
        """
        if not initial_objects:
            return []
            
        print(f"\n Starting export process with {len(initial_objects)} initial objects")
        
        processed_objects = self.preprocessor.preprocess_objects(
            initial_objects,
            apply_modifiers=settings.apply_modifiers,
            separate_loose=settings.separate_loose_parts,
            use_selection=settings.use_selection
        )
        
        return processed_objects
    
    def validate_objects(self, objects, settings):
        """
        Validate objects against QB/TB rules and filter based on settings.
        
        Args:
            objects: List of objects to validate
            settings: ExportSettings with validation filters
            
        Returns:
            tuple: (valid_objects, statistics_dict)
        """
        if not objects:
            return [], {'quadblocks': 0, 'triblocks': 0, 'total_exported': 0, 
                       'exported_with_uv_issues': 0, 'objects_with_uv_issues': [], 
                       'total_quadblocks_found': 0, 'total_triblocks_found': 0}
        
        print(f"\n Validating {len(objects)} processed objects...")
        
        valid_objects, stats = self.validator.filter_valid_objects(objects, settings)
        
        print(f" Found {stats['quadblocks']} Quadblocks and {stats['triblocks']} Triblocks")
        print(f" Total found: {stats['total_quadblocks_found']} Quadblocks, {stats['total_triblocks_found']} Triblocks")
        print(f" {len(valid_objects)} objects ready for export")
        
        return valid_objects, stats
    
    def prepare_export_paths(self, filepath, settings, is_quick_export=False):
        """
        Prepare all file paths for the export operation.
        
        Args:
            filepath: Base file path from user selection
            settings: ExportSettings with folder preferences
            is_quick_export: True if using quick export workflow
            
        Returns:
            dict: Dictionary containing all export paths
        """
        original_filepath = filepath
        
        if is_quick_export:
            base_path = self._get_base_export_path(self.context)
            if not base_path:
                base_path = os.path.dirname(filepath)
        else:
            base_path = os.path.dirname(filepath)
        
        obj_name = os.path.splitext(os.path.basename(filepath))[0]
        
        if settings.export_to_folder:
            project_name = obj_name[:50]
            
            project_folder = self._try_create_project_folder(
                base_path, project_name, settings.folder_behavior
            )
            
            if project_folder is None:
                export_subfolder = base_path
                texture_dir = None
                obj_filepath = original_filepath
            else:
                export_subfolder = self._try_create_export_subfolder(
                    project_folder, settings.folder_behavior
                )
                
                if export_subfolder is None:
                    export_subfolder = project_folder
                
                obj_filepath = os.path.join(export_subfolder, f"{obj_name}.obj")
                texture_dir = os.path.join(export_subfolder, "textures")
                
                try:
                    os.makedirs(texture_dir, exist_ok=True)
                except OSError as e:
                    print(f"Warning: Could not create texture directory: {e}")
                    texture_dir = None
            
            if project_folder:
                self.context.scene.last_export_path = project_folder
        
        else:
            project_folder = None
            export_subfolder = None
            texture_dir = None
            obj_filepath = original_filepath
        
        export_paths = {
            'original_filepath': original_filepath,
            'obj_filepath': obj_filepath,
            'texture_dir': texture_dir,
            'project_folder': project_folder,
            'export_subfolder': export_subfolder
        }
        
        self.temp_filepath = export_paths['obj_filepath']
        return export_paths
    
    def prepare_export_operation(self, valid_objects):
        """
        Set up Blender for export by selecting valid objects.
        
        Args:
            valid_objects: List of objects to export
        """
        self.original_active = self.context.view_layer.objects.active
        self.original_selection = [obj for obj in self.context.selected_objects]
        
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in valid_objects:
            self.preprocessor.ensure_object_in_view_layer(obj)
            obj.select_set(True)
        
        if valid_objects:
            self.context.view_layer.objects.active = valid_objects[0]
    
    def execute_export(self, settings, valid_objects):
        """
        Execute the actual OBJ export using compatibility layer.
        
        Args:
            settings: ExportSettings with export preferences
            valid_objects: List of validated objects to export
            
        Returns:
            dict: Blender operator result
        """
        if not valid_objects:
            return {'CANCELLED'}
            
        class TempExportProps:
            """Temporary properties container for export execution."""
            def __init__(self, settings):
                self.filepath = settings.filepath
                self.use_selection = True
                self.export_colors = settings.export_colors
                self.export_textures = settings.export_textures
                self.export_textures_to_folder = settings.include_textures
                self.apply_modifiers = False
                self.global_scale = settings.global_scale
                self.export_invalid_uvs = settings.export_invalid_uvs
                self.export_degenerated_uvs = settings.export_degenerated_uvs
                self.export_quadblocks = settings.export_quadblocks
                self.export_triblocks = settings.export_triblocks
                self.path_mode = settings.path_mode
        
        temp_props = TempExportProps(settings)
        
        result = execute_obj_export(temp_props, valid_objects)
        
        return result
    
    def restore_state(self):
        """Restore Blender selection and active object to original state."""
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in self.original_selection:
            try:
                if obj and obj.name in bpy.data.objects:
                    obj.select_set(True)
            except:
                pass
        
        if self.original_active:
            try:
                if self.original_active and self.original_active.name in bpy.data.objects:
                    self.context.view_layer.objects.active = self.original_active
            except:
                pass
        
        self.preprocessor.cleanup()
    
    def get_no_objects_error(self, settings, stats):
        """
        Generate user-friendly error message when no objects are exportable.
        
        Args:
            settings: ExportSettings with current configuration
            stats: Dictionary with validation statistics
            
        Returns:
            str: Localized error message explaining why nothing was exported
        """
        if not settings.export_quadblocks and not settings.export_triblocks:
            return "Must select at least one block type (Quadblocks or Triblocks)"
        
        total_quadblocks_found = stats.get('total_quadblocks_found', 0)
        total_triblocks_found = stats.get('total_triblocks_found', 0)
        
        # Handle different scenarios with specific messages
        if total_quadblocks_found == 0 and total_triblocks_found == 0:
            return "No valid Quadblocks or Triblocks found in the selection/scene."
        
        if total_quadblocks_found > 0 and not settings.export_quadblocks and total_triblocks_found == 0:
            return f"Found {total_quadblocks_found} Quadblocks (export disabled) and 0 Triblocks. Enable Quadblocks to export them."
        
        if total_triblocks_found > 0 and not settings.export_triblocks and total_quadblocks_found == 0:
            return f"Found 0 Quadblocks and {total_triblocks_found} Triblocks (export disabled). Enable Triblocks to export them."
        
        if total_quadblocks_found > 0 and not settings.export_quadblocks and total_triblocks_found > 0 and not settings.export_triblocks:
            return f"Found {total_quadblocks_found} Quadblocks (export disabled) and {total_triblocks_found} Triblocks (export disabled). Enable at least one type."
        
        if total_quadblocks_found > 0 and settings.export_quadblocks and total_triblocks_found > 0 and settings.export_triblocks:
            return f"Found {total_quadblocks_found} Quadblocks and {total_triblocks_found} Triblocks but none passed the UV filters (check UV settings)."
        
        if total_quadblocks_found > 0 and settings.export_quadblocks and total_triblocks_found == 0:
            return f"Found {total_quadblocks_found} Quadblocks and 0 Triblocks, but Quadblocks didn't pass UV filters."
        
        if total_triblocks_found > 0 and settings.export_triblocks and total_quadblocks_found == 0:
            return f"Found 0 Quadblocks and {total_triblocks_found} Triblocks, but Triblocks didn't pass UV filters."
        
        if total_quadblocks_found > 0 and settings.export_quadblocks and total_triblocks_found > 0 and not settings.export_triblocks:
            return f"Found {total_quadblocks_found} Quadblocks and {total_triblocks_found} Triblocks (export disabled), but Quadblocks didn't pass UV filters."
        
        if total_triblocks_found > 0 and settings.export_triblocks and total_quadblocks_found > 0 and not settings.export_quadblocks:
            return f"Found {total_quadblocks_found} Quadblocks (export disabled) and {total_triblocks_found} Triblocks, but Triblocks didn't pass UV filters."
        
        return f"Found {total_quadblocks_found} Quadblocks and {total_triblocks_found} Triblocks but none passed the current filters."
    
    def export_details_if_needed(self, valid_objects, stats, settings, filepath, export_details_flag, export_index):
        """
        Export JSON details file if requested by user.
        
        Args:
            valid_objects: List of exported objects
            stats: Export statistics dictionary
            settings: ExportSettings used
            filepath: Path to the exported OBJ file
            export_details_flag: True if details should be exported
            export_index: Sequential export number
            
        Returns:
            str or None: Path to JSON file if exported, None otherwise
        """
        if not valid_objects or not export_details_flag:
            return None
            
        print(f"\n Collecting export details (Export #{export_index})...")
        
        export_data = self.details_exporter.collect_export_details(
            valid_objects, stats, settings, filepath, export_index
        )
        
        json_path = self.details_exporter.export_to_json(filepath, export_data)
        
        if json_path:
            summary = self.details_exporter.get_summary_report(export_data, max_objects_per_list=10)
            print(summary)
            
            return json_path
        
        return None