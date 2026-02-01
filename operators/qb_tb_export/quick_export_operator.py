import bpy
import os
from bpy.types import Operator
from .export_manager import ExportManager
from .export_settings import ExportSettings, ExportStats
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper


class QB_TB_OT_QuickExport(Operator):
    bl_idname = "qb_tb.quick_export"
    bl_label = "Quick Export Qb/Tb"
    bl_description = "Quick export using last export location (Ctrl+Shift+E)"
    
    @classmethod
    def poll(cls, context):
        return context.scene.last_export_path

    def execute(self, context):
        if not context.scene.export_quadblocks and not context.scene.export_triblocks:
            self.report({'ERROR'}, "Must select at least one block type (Quadblocks or Triblocks)")
            return {'CANCELLED'}
        
        if not context.scene.last_export_path:
            self.report({'ERROR'}, "No export location saved. Please do a regular export first.")
            return {'CANCELLED'}
            
        try:
            settings = ExportSettings.from_scene_props(context)
            
            if bpy.data.filepath:
                scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            else:
                scene_name = "untitled"
            
            filename = f"{scene_name}.obj"
            
            manager = ExportManager(context)
            
            initial_objects = manager.prepare_objects(settings)
            
            if not initial_objects:
                self.report({'ERROR'}, "No objects to export")
                return {'CANCELLED'}
            
            processed_objects = manager.preprocess_objects(initial_objects, settings)
            
            valid_objects, stats = manager.validate_objects(processed_objects, settings)
            
            if not valid_objects:
                error_msg = manager.get_no_objects_error(settings, stats)
                self.report({'ERROR'}, error_msg)
                return {'CANCELLED'}
            
            export_paths = manager.prepare_export_paths(filename, settings, is_quick_export=True)
            settings.filepath = export_paths['obj_filepath']
            
            os.makedirs(os.path.dirname(settings.filepath), exist_ok=True)
            
            if settings.include_textures and not export_paths['texture_dir']:
                self.report({'WARNING'}, "Could not create texture directory. Textures will not be copied.")
            
            texture_remapper = None
            if settings.include_textures and export_paths['texture_dir']:
                try:
                    os.makedirs(export_paths['texture_dir'], exist_ok=True)
                except OSError:
                    self.report({'WARNING'}, "Could not create texture directory. Textures will not be copied.")
                    export_paths['texture_dir'] = None
            
            if settings.include_textures and export_paths['texture_dir']:
                if context.scene.remap_textures:
                    texture_remapper = TextureRemapper()
                    success = texture_remapper.execute_remapping(
                        settings.filepath,
                        export_paths['texture_dir'],
                        valid_objects,
                        remap_in_blender=True
                    )
                    
                    if not success:
                        self.report({'WARNING'}, "Texture remapping encountered issues")
            
            manager.prepare_export_operation(valid_objects)
            
            export_result = manager.execute_export(settings, valid_objects)
            
            if texture_remapper:
                texture_remapper.restore_blender_texture_paths()
            
            if 'FINISHED' not in export_result:
                self.report({'ERROR'}, "Export failed")
                manager.restore_state()
                return {'CANCELLED'}
            
            if hasattr(context.scene, 'export_details') and context.scene.export_details:
                export_index = context.scene.export_index
                context.scene.export_index += 1
                
                json_path = manager.export_details_if_needed(
                    valid_objects, stats, settings, export_paths['obj_filepath'], 
                    True, export_index
                )
            
            obj_dir = os.path.dirname(settings.filepath)
            obj_name = os.path.splitext(os.path.basename(settings.filepath))[0]
            mtl_path = os.path.join(obj_dir, f"{obj_name}.mtl")
            
            if settings.include_textures and export_paths['texture_dir']:
                if not context.scene.remap_textures:
                    texture_handler = TextureHandler()
                    texture_handler.copy_textures_to_folder(export_paths['texture_dir'], valid_objects)
            
            manager.restore_state()
            
            stats_obj = ExportStats()
            stats_obj.quadblocks = stats['quadblocks']
            stats_obj.triblocks = stats['triblocks']
            stats_obj.total_exported = stats['total_exported']
            stats_obj.exported_with_uv_issues = stats['exported_with_uv_issues']
            
            if settings.export_to_folder and export_paths['export_subfolder']:
                stats_obj.exported_folder = os.path.basename(export_paths['export_subfolder'])
            
            self.report({'INFO'}, f"Quick export completed: {stats_obj.get_report_message()}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error during quick export: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}