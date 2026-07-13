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
    """
    
    def __init__(self, context):
        self.context = context
        self.preprocessor = QB_TB_Preprocessor(context)
        self.validator = ValidationHandler()
        self.texture_handler = TextureHandler()
        self.details_exporter = DetailsExporter()
        
        self.original_active = None
        self.original_selection = []
        self.temp_filepath = None
    
    def _get_base_export_path(self, context):
        """
        Determine the base export path from the last_export_path scene property.
        If last_export_path is a .obj file, return its directory.
        If it is a folder, return it directly.
        Returns None if no valid last_export_path exists.
        """
        last = context.scene.last_export_path
        if last and os.path.exists(last):
            if last.lower().endswith('.obj'):
                return os.path.dirname(last)
            else:
                return last
        return None
    
    def _try_create_project_folder(self, base_path, project_name, behavior='INCREMENTAL'):
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
    
    def prepare_objects(self, settings):
        if not settings.export_quadblocks and not settings.export_triblocks:
            return []
        if settings.use_selection:
            initial_objects = list(self.context.selected_objects)
        else:
            initial_objects = list(bpy.data.objects)
        return initial_objects
    
    def preprocess_objects(self, initial_objects, settings):
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
        Prepare all export paths (OBJ file, texture directory, folders).
        
        For quick export, if the stored last_export_path points to a direct .obj file,
        we use that exact path and ignore the "Export to Folder" setting.
        Otherwise, we behave normally (creating project folders etc.).
        """
        original_filepath = filepath
        
        # Determine base directory
        if is_quick_export:
            base_path = self._get_base_export_path(self.context)
            if not base_path:
                base_path = os.path.dirname(filepath)
        else:
            base_path = os.path.dirname(filepath)
        
        obj_name = os.path.splitext(os.path.basename(filepath))[0]
        
        # Check if we should force direct export (when last export was a single .obj)
        force_direct = False
        if is_quick_export and self.context.scene.last_export_path:
            last = self.context.scene.last_export_path
            if last.lower().endswith('.obj'):
                force_direct = True
        
        if settings.export_to_folder and not force_direct:
            # Normal folder-based export
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
                
                # Create 'export' subfolder inside the export_subfolder
                export_folder = os.path.join(export_subfolder, "export")
                os.makedirs(export_folder, exist_ok=True)
                obj_filepath = os.path.join(export_folder, f"{obj_name}.obj")
                
                # Only create textures folder if include_textures is True
                if settings.include_textures:
                    texture_dir = os.path.join(export_folder, "textures")
                    try:
                        os.makedirs(texture_dir, exist_ok=True)
                    except OSError as e:
                        print(f"Warning: Could not create texture directory: {e}")
                        texture_dir = None
                else:
                    texture_dir = None
            
            # Store base_path
            if project_folder:
                self.context.scene.last_export_path = base_path
            else:
                self.context.scene.last_export_path = obj_filepath
        else:
            # Direct file export (no folder structure)
            project_folder = None
            export_subfolder = None
            texture_dir = None
            obj_filepath = original_filepath
            # Store the actual .obj filepath for future quick exports
            self.context.scene.last_export_path = obj_filepath
        
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
        self.original_active = self.context.view_layer.objects.active
        self.original_selection = [obj for obj in self.context.selected_objects]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in valid_objects:
            self.preprocessor.ensure_object_in_view_layer(obj)
            obj.select_set(True)
        if valid_objects:
            self.context.view_layer.objects.active = valid_objects[0]
    
    def execute_export(self, settings, valid_objects):
        if not valid_objects:
            return {'CANCELLED'}
            
        class TempExportProps:
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
        for obj in bpy.data.objects:
            obj.select_set(False)
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
        if not settings.export_quadblocks and not settings.export_triblocks:
            return "Must select at least one block type (Quadblocks or Triblocks)"
        
        total_quadblocks_found = stats.get('total_quadblocks_found', 0)
        total_triblocks_found = stats.get('total_triblocks_found', 0)
        
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
        if not valid_objects or not export_details_flag:
            print(f"DEBUG: Not exporting details - valid_objects={len(valid_objects) if valid_objects else 0}, flag={export_details_flag}")
            return None
        print(f"\n Collecting export details (Export #{export_index})...")
        export_data = self.details_exporter.collect_export_details(
            valid_objects, stats, settings, filepath, export_index
        )
        json_path = self.details_exporter.export_to_json(filepath, export_data)
        if json_path:
            summary = self.details_exporter.get_summary_report(export_data)
            print(summary)
            return json_path
        else:
            print("ERROR: Failed to export JSON details")
            return None