import bpy
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy.types import Operator
from .export_manager import ExportManager
from .export_settings import ExportSettings, ExportStats
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper
from ...ui.help_utils import draw_help_buttons


class QB_TB_OT_ExportQuadTriBlocks(Operator, ExportHelper):
    """Export Quadblocks and Triblocks to OBJ format."""

    bl_idname = "export_scene.qb_tb_obj"
    bl_label = "Qb/Tb (.obj)"
    bl_description = "Export Quadblocks and Triblocks to OBJ format (Quick Export: Ctrl+Shift+E)"

    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
    )

    use_selection: BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False,
    )

    export_quadblocks: BoolProperty(
        name="Quadblocks",
        description="Export Quadblocks",
        default=True,
    )

    export_triblocks: BoolProperty(
        name="Triblocks",
        description="Export Triblocks",
        default=True,
    )

    export_colors: BoolProperty(
        name="Vertex Colors",
        description="Export Vertex Colors",
        default=True,
    )

    export_to_folder: BoolProperty(
        name="Export to Folder",
        description="Export OBJ to organized folder structure",
        default=False,
    )

    include_textures: BoolProperty(
        name="Include Textures",
        description="Copy textures to texture folder",
        default=False,
    )

    remap_textures: BoolProperty(
        name="Remap Textures",
        description="Remap model to use exported textures in texture folder",
        default=False,
    )

    folder_behavior: EnumProperty(
        name="Behavior",
        description="How to handle existing folders when exporting to folder",
        items=[
            ('REPLACE', 'Replace', 'Replace existing folder'),
            ('INCREMENTAL', 'Numerical Increment', 'Create folder with numerical increment'),
        ],
        default='INCREMENTAL',
    )

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before validating and exporting",
        default=False,
    )

    separate_loose_parts: BoolProperty(
        name="Separate by Loose Parts",
        description="Separate mesh by loose parts before validating",
        default=False,
    )

    export_invalid_uvs: BoolProperty(
        name="Invalid UVs",
        description="Export objects with UVs outside 0-1 range",
        default=False,
    )

    export_invalid_triblock_uvs: BoolProperty(
        name="Invalid Triblock UVs",
        description="Export triblocks with incorrect UV arrangement (shared vertices mismatch)",
        default=False,
    )

    export_degenerated_uvs: BoolProperty(
        name="Degenerated UVs",
        description="Export objects with degenerated UVs",
        default=False,
    )

    path_mode: EnumProperty(
        name="Path Mode",
        description="Texture path handling",
        items=[
            ('AUTO', 'Auto', 'Automatic path handling'),
            ('ABSOLUTE', 'Absolute', 'Use absolute paths'),
            ('RELATIVE', 'Relative', 'Use relative paths'),
            ('COPY', 'Copy', 'Copy textures to export folder'),
            ('STRIP', 'Strip', 'Strip texture paths'),
        ],
        default='ABSOLUTE',
    )

    export_details: BoolProperty(
        name="Export Details (JSON)",
        description="Export a JSON file with export details",
        default=False,
    )

    allow_out_of_range: BoolProperty(
        name="Allow Out of Range",
        description="Export objects outside the 1000x1000x1000 range",
        default=False,
    )

    export_duplicates: BoolProperty(
        name="Export Duplicates",
        description="Export duplicates of detected blocks to a 'Duplicates' subfolder (ignores UV/range filters)",
        default=False,
    )

    export_processed_duplicates: BoolProperty(
        name="Export Processed Duplicates",
        description="After duplication, export the processed objects using current export settings (filters, folder, etc.)",
        default=False,
    )

    global_scale: FloatProperty(
        name="Scale",
        description="Global export scale (forced to 1.0)",
        default=1.0,
        options={'HIDDEN'},
    )

    def draw(self, context):
        layout = self.layout
        draw_help_buttons(layout)

        box = layout.box()
        box.label(text="Selection & Block Types", icon='OBJECT_DATA')
        box.prop(self, "use_selection")
        col = box.column()
        col.prop(self, "export_quadblocks")
        col.prop(self, "export_triblocks")

        box = layout.box()
        box.label(text="UV Issues Handling", icon='UV')
        col = box.column(align=True)
        col.prop(self, "export_invalid_uvs", text="Invalid UVs (out of range)")
        col.prop(self, "export_invalid_triblock_uvs", text="Invalid Triblock UVs (Structure)")
        col.prop(self, "export_degenerated_uvs", text="Degenerated UVs")

        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(self, "export_colors", text="Vertex Colors")
        box.prop(self, "allow_out_of_range", text="Allow Out of Range")
        box.prop(self, "apply_modifiers", text="Apply Modifiers")
        box.prop(self, "separate_loose_parts", text="Separate by Loose Parts")
        box.prop(self, "export_details", text="Export Details (JSON)")
        box.prop(self, "path_mode", text="Path Mode")

        box = layout.box()
        box.label(text="Duplicate Export", icon='DUPLICATE')
        col = box.column(align=True)
        col.prop(self, "export_duplicates", text="Export Duplicates")
        if self.export_duplicates:
            col.prop(self, "export_processed_duplicates", text="Export Processed Duplicates")

        box = layout.box()
        box.label(text="Folder Organization", icon='FILE_FOLDER')
        box.prop(self, "export_to_folder", text="Export to Folder")
        if self.export_to_folder:
            col = box.column(align=True)
            col.prop(self, "folder_behavior")
            col.prop(self, "include_textures", text="Include Textures")
            if self.include_textures:
                col.prop(self, "remap_textures", text="Remap Textures")

        if context.scene.last_export_path:
            layout.separator()
            box = layout.box()
            box.label(text="Quick Export Status", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"Last project: {os.path.basename(context.scene.last_export_path)}")
            col.label(text=f"Location: {context.scene.last_export_path}")
            col.label(text="Quick Export: Ctrl+Shift+E", icon='EVENT_CTRL')

    def invoke(self, context, event):
        self.folder_behavior = context.scene.folder_behavior
        self.use_selection = context.scene.use_selection
        self.export_duplicates = context.scene.export_duplicates
        self.export_processed_duplicates = context.scene.export_processed_duplicates
        self.export_details = context.scene.export_details
        return super().invoke(context, event)

    def _save_export_settings(self, context):
        context.scene.use_selection = self.use_selection
        context.scene.export_quadblocks = self.export_quadblocks
        context.scene.export_triblocks = self.export_triblocks
        context.scene.export_colors = self.export_colors
        context.scene.export_to_folder = self.export_to_folder
        context.scene.include_textures = self.include_textures
        context.scene.remap_textures = self.remap_textures
        context.scene.folder_behavior = self.folder_behavior
        context.scene.apply_modifiers = self.apply_modifiers
        context.scene.separate_loose_parts = self.separate_loose_parts
        context.scene.global_scale = 1.0
        context.scene.export_invalid_uvs = self.export_invalid_uvs
        context.scene.export_invalid_triblock_uvs = self.export_invalid_triblock_uvs
        context.scene.export_degenerated_uvs = self.export_degenerated_uvs
        context.scene.path_mode = self.path_mode
        context.scene.export_details = self.export_details
        context.scene.allow_out_of_range = self.allow_out_of_range
        context.scene.export_duplicates = self.export_duplicates
        context.scene.export_processed_duplicates = self.export_processed_duplicates

    def _export_processed_duplicates(self, context, output_dir, final_filename, main_texture_dir=None):
        processed_collection = bpy.data.collections.get("Processed_Blocks")
        if not processed_collection:
            self.report({'WARNING'}, "No Processed_Blocks collection found.")
            return False

        processed_objs = [obj for obj in processed_collection.objects if obj.type == 'MESH']
        if not processed_objs:
            self.report({'WARNING'}, "No mesh objects found in Processed_Blocks collection.")
            return False

        proc_settings = ExportSettings.from_operator(self)
        proc_settings.export_to_folder = False
        proc_settings.include_textures = self.include_textures
        proc_settings.remap_textures = self.remap_textures
        proc_settings.filepath = os.path.join(output_dir, final_filename)

        if main_texture_dir:
            texture_dir = main_texture_dir
        else:
            texture_dir = os.path.join(output_dir, "textures")

        if proc_settings.include_textures:
            os.makedirs(texture_dir, exist_ok=True)
            texture_handler = TextureHandler()
            texture_handler.copy_textures_to_folder(texture_dir, processed_objs)

        texture_remapper = None
        if proc_settings.remap_textures and proc_settings.include_textures:
            try:
                texture_remapper = TextureRemapper()
                texture_remapper.execute_remapping(
                    proc_settings.filepath,
                    texture_dir,
                    processed_objs,
                    remap_in_blender=True
                )
            except Exception as e:
                self.report({'WARNING'}, f"Texture remapping failed: {e}")
                texture_remapper = None

        temp_manager = ExportManager(context)
        valid_objs, stats = temp_manager.validate_objects(processed_objs, proc_settings)
        if not valid_objs:
            error_msg = temp_manager.get_no_objects_error(proc_settings, stats)
            self.report({'WARNING'}, f"No processed objects passed filters: {error_msg}")
            if texture_remapper:
                texture_remapper.restore_blender_texture_paths()
            return False

        old_sel_names = [obj.name for obj in context.selected_objects if obj.name in bpy.data.objects]
        old_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

        bpy.ops.object.select_all(action='DESELECT')
        for obj in valid_objs:
            obj.select_set(True)
        if valid_objs:
            context.view_layer.objects.active = valid_objs[0]

        temp_manager.prepare_export_operation(valid_objs)
        result = temp_manager.execute_export(proc_settings, valid_objs)

        bpy.ops.object.select_all(action='DESELECT')
        for name in old_sel_names:
            if name in bpy.data.objects:
                bpy.data.objects[name].select_set(True)
        if old_active_name and old_active_name in bpy.data.objects:
            context.view_layer.objects.active = bpy.data.objects[old_active_name]

        if texture_remapper:
            texture_remapper.restore_blender_texture_paths()

        if 'FINISHED' in result:
            if self.export_details:
                export_index = context.scene.export_index
                context.scene.export_index += 1
                temp_manager.export_details_if_needed(
                    valid_objs, stats, proc_settings, proc_settings.filepath,
                    True, export_index
                )
            return True
        else:
            return False

    def _find_block_object(self, context):
        if context.mode == 'EDIT_MESH' and context.edit_object:
            return context.edit_object
        obj = context.object
        if obj and obj.type == 'MESH':
            if "quad_group_members" in obj or "tri_group_members" in obj:
                return obj
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if "quad_group_members" in obj or "tri_group_members" in obj:
                    return obj
        return None

    def _export_duplicates(self, context, export_paths):
        base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
        duplicates_dir = os.path.join(base_dir, "duplicates")
        os.makedirs(duplicates_dir, exist_ok=True)

        main_texture_dir = export_paths.get('texture_dir')

        block_obj = self._find_block_object(context)
        if not block_obj:
            self.report({'WARNING'}, "No object with block data found. Run 'Find Blocks' first.")
            return None, None

        original_mode = context.mode
        original_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

        context.view_layer.objects.active = block_obj
        block_obj.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except Exception as e:
            self.report({'ERROR'}, f"Failed to switch to EDIT mode: {e}")
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            return None, None

        try:
            bpy.ops.navigator.duplicate_all_blocks_by_group(
                'EXEC_DEFAULT',
                directory=base_dir
            )
        except Exception as e:
            self.report({'ERROR'}, f"Duplication operator failed: {e}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            return None, None

        self.report({'INFO'}, f"Duplicates exported to: {duplicates_dir}")

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        if original_active_name and original_active_name in bpy.data.objects:
            context.view_layer.objects.active = bpy.data.objects[original_active_name]
        if original_mode != 'OBJECT' and original_mode != context.mode:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass

        return duplicates_dir, main_texture_dir

    def execute(self, context):
        if not self.export_quadblocks and not self.export_triblocks:
            self.report({'ERROR'}, "Must select at least one block type")
            return {'CANCELLED'}

        settings = ExportSettings.from_operator(self)
        settings.global_scale = 1.0
        self._save_export_settings(context)

        manager = ExportManager(context)
        export_paths = manager.prepare_export_paths(self.filepath, settings, is_quick_export=False)
        settings.filepath = export_paths['obj_filepath']

        # CASE 1: Both duplicate and processed export enabled
        if self.export_duplicates and self.export_processed_duplicates:
            texture_remapper = None
            try:
                duplicates_dir, main_texture_dir = self._export_duplicates(context, export_paths)
                if duplicates_dir is None:
                    return {'CANCELLED'}

                base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
                export_root = base_dir
                final_obj_dir = os.path.join(export_root, "export")
                os.makedirs(final_obj_dir, exist_ok=True)
                final_obj_path = os.path.join(final_obj_dir, os.path.basename(export_paths['obj_filepath']))

                proc_settings = ExportSettings.from_operator(self)
                proc_settings.export_to_folder = False
                proc_settings.include_textures = self.include_textures
                proc_settings.remap_textures = self.remap_textures
                proc_settings.filepath = final_obj_path

                processed_collection = bpy.data.collections.get("Processed_Blocks")
                if not processed_collection:
                    self.report({'WARNING'}, "No Processed_Blocks collection found.")
                    return {'CANCELLED'}
                processed_objs = [obj for obj in processed_collection.objects if obj.type == 'MESH']
                if not processed_objs:
                    self.report({'WARNING'}, "No mesh objects in Processed_Blocks.")
                    return {'CANCELLED'}

                if proc_settings.include_textures:
                    texture_dir = os.path.join(export_root, "export", "textures")
                    os.makedirs(texture_dir, exist_ok=True)
                    if proc_settings.remap_textures:
                        texture_remapper = TextureRemapper()
                        try:
                            texture_remapper.execute_remapping(
                                proc_settings.filepath,
                                texture_dir,
                                processed_objs,
                                remap_in_blender=True
                            )
                        except Exception as e:
                            self.report({'WARNING'}, f"Texture remapping failed: {e}")
                            texture_remapper = None
                    else:
                        texture_handler = TextureHandler()
                        texture_handler.copy_textures_to_folder(texture_dir, processed_objs)

                temp_manager = ExportManager(context)
                valid_objs, stats = temp_manager.validate_objects(processed_objs, proc_settings)
                if not valid_objs:
                    error_msg = temp_manager.get_no_objects_error(proc_settings, stats)
                    self.report({'ERROR'}, error_msg)
                    return {'CANCELLED'}

                old_sel_names = [obj.name for obj in context.selected_objects if obj.name in bpy.data.objects]
                old_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

                bpy.ops.object.select_all(action='DESELECT')
                for obj in valid_objs:
                    obj.select_set(True)
                if valid_objs:
                    context.view_layer.objects.active = valid_objs[0]

                temp_manager.prepare_export_operation(valid_objs)
                export_result = temp_manager.execute_export(proc_settings, valid_objs)

                bpy.ops.object.select_all(action='DESELECT')
                for name in old_sel_names:
                    if name in bpy.data.objects:
                        bpy.data.objects[name].select_set(True)
                if old_active_name and old_active_name in bpy.data.objects:
                    context.view_layer.objects.active = bpy.data.objects[old_active_name]

                if 'FINISHED' not in export_result:
                    self.report({'ERROR'}, "Processed export failed")
                    return {'CANCELLED'}

                # Export JSON details if requested
                if self.export_details:
                    export_index = context.scene.export_index
                    context.scene.export_index += 1
                    temp_manager.export_details_if_needed(
                        valid_objs, stats, proc_settings, proc_settings.filepath,
                        True, export_index
                    )

                self.report({'INFO'}, f"Export completed: final model saved to {proc_settings.filepath}")
                return {'FINISHED'}

            except Exception as e:
                self.report({'ERROR'}, f"Error during duplicate+processed export: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'CANCELLED'}
            finally:
                if texture_remapper:
                    try:
                        texture_remapper.restore_blender_texture_paths()
                    except Exception as e:
                        print(f"Error restoring textures: {e}")
                manager.restore_state()

        # CASE 2: Only duplicate export
        elif self.export_duplicates and not self.export_processed_duplicates:
            try:
                self._export_duplicates(context, export_paths)
                self.report({'INFO'}, "Duplicates exported (no final OBJ saved).")
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f"Error during duplicate export: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'CANCELLED'}
            finally:
                manager.restore_state()

        # CASE 3: Normal export (no duplicates)
        else:
            texture_remapper = None
            try:
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

                if settings.include_textures and export_paths['texture_dir']:
                    if self.remap_textures:
                        texture_remapper = TextureRemapper()
                        try:
                            texture_remapper.execute_remapping(
                                settings.filepath,
                                export_paths['texture_dir'],
                                valid_objects,
                                remap_in_blender=True
                            )
                        except Exception as e:
                            self.report({'WARNING'}, f"Texture remapping failed: {e}")
                            texture_remapper = None
                    else:
                        texture_handler = TextureHandler()
                        texture_handler.copy_textures_to_folder(export_paths['texture_dir'], valid_objects)

                manager.prepare_export_operation(valid_objects)
                export_result = manager.execute_export(settings, valid_objects)

                if 'FINISHED' not in export_result:
                    self.report({'ERROR'}, "Export failed")
                    return {'CANCELLED'}
                else:
                    if self.export_details:
                        export_index = context.scene.export_index
                        context.scene.export_index += 1
                        manager.export_details_if_needed(
                            valid_objects, stats, settings, export_paths['obj_filepath'],
                            True, export_index
                        )
                    stats_obj = ExportStats.from_dict(stats)
                    if settings.export_to_folder and export_paths['export_subfolder']:
                        stats_obj.exported_folder = os.path.basename(export_paths['export_subfolder'])
                    self.report({'INFO'}, stats_obj.get_report_message())
                    return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f"Error during export: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'CANCELLED'}
            finally:
                if texture_remapper:
                    try:
                        texture_remapper.restore_blender_texture_paths()
                    except Exception as e:
                        print(f"Error restoring textures: {e}")
                manager.restore_state()


def menu_func_export(self, context):
    self.layout.operator(QB_TB_OT_ExportQuadTriBlocks.bl_idname, text="Qb/Tb (.obj)")