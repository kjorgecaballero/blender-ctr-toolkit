import bpy
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy.types import Operator
from .export_manager import ExportManager
from .export_settings import ExportSettings, ExportStats
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper
from .duplicate_export_helper import DuplicateExportHelper
from ...ui.help_utils import draw_help_buttons
from ...utils.export_helpers import (
    temporary_disable_ps1_render,
    restore_ps1_render,
    get_vertex_snap_modifiers,
    disable_vertex_snap_modifiers,
    restore_vertex_snap_modifiers
)


class QB_TB_OT_ExportQuadTriBlocks(Operator, ExportHelper):
    """Export Quadblocks and Triblocks to OBJ format."""

    bl_idname = "export_scene.qb_tb_obj"
    bl_label = "Qb/Tb (.obj)"
    bl_description = "Export Quadblocks and Triblocks to OBJ format"

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
        name="Copy Textures",
        description="Copy textures to texture folder",
        default=False,
    )

    remap_textures: BoolProperty(
        name="Remap Textures",
        description="Remap model to use exported textures in texture folder",
        default=False,
    )

    folder_behavior: EnumProperty(
        name="Folder Behavior",
        description="How to handle existing folders when exporting to folder",
        items=[
            ('REPLACE', 'Replace', 'Replace existing folder'),
            ('INCREMENTAL', 'Incremental', 'Create folder with numerical increment'),
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

    export_multiple_materials: BoolProperty(
        name="Multiple Materials",
        description="Export objects with more than one material on the block",
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
        name="Out of Range",
        description="Export objects outside the 1000x1000x1000 range",
        default=False,
    )

    export_duplicates: BoolProperty(
        name="Export Duplicates",
        description="Export duplicates of detected blocks to a 'Duplicates' subfolder (ignores UV/range filters)",
        default=False,
    )

    export_processed_duplicates: BoolProperty(
        name="Export Processed",
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

        # Export Scope
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Export Scope", icon='OBJECT_DATA')
        box.prop(self, "use_selection")

        # Types
        box = layout.box()
        box.label(text="Types", icon='CUBE')
        box.prop(self, "export_quadblocks")
        box.prop(self, "export_triblocks")

        # Preprocessing
        box = layout.box()
        box.label(text="Preprocessing", icon='MODIFIER')
        box.prop(self, "export_colors")
        box.prop(self, "apply_modifiers")
        box.prop(self, "separate_loose_parts")

        # Issue Filtering
        box = layout.box()
        box.label(text="Issue Filtering", icon='FILTER')
        box.prop(self, "allow_out_of_range", text="Out of Range")
        box.prop(self, "export_invalid_uvs", text="Invalid UVs")
        box.prop(self, "export_invalid_triblock_uvs", text="Invalid Triblock UVs")
        box.prop(self, "export_degenerated_uvs", text="Degenerated UVs")
        box.prop(self, "export_multiple_materials", text="Multiple Materials")

        # Duplicates
        box = layout.box()
        box.label(text="Duplicates", icon='DUPLICATE')
        box.prop(self, "export_duplicates", text="Export Duplicates")
        if self.export_duplicates:
            box.prop(self, "export_processed_duplicates", text="Export Processed")

        # Output
        box = layout.box()
        box.label(text="Output", icon='FILE_FOLDER')
        box.prop(self, "export_to_folder", text="Export to Folder")

        if self.export_to_folder:
            box.prop(self, "folder_behavior", text="Behavior")
            box.prop(self, "path_mode", text="Path Mode")

            tex_box = box.box()
            tex_box.label(text="Textures", icon='TEXTURE')
            tex_box.prop(self, "include_textures", text="Copy Textures")
            if self.include_textures:
                tex_box.prop(self, "remap_textures", text="Remap Textures")
        else:
            box.prop(self, "path_mode", text="Path Mode")

        # Metadata
        box = layout.box()
        box.label(text="Metadata", icon='INFO')
        box.prop(self, "export_details", text="Export Details (JSON)")

        # Last export info
        if context.scene.last_export_path:
            layout.separator()
            box = layout.box()
            box.label(text="Last export", icon='TIME')
            box.label(text=f"  {os.path.basename(context.scene.last_export_path)}")
            box.label(text=f"  {context.scene.last_export_path}")

    def invoke(self, context, event):
        self.folder_behavior = context.scene.folder_behavior
        self.use_selection = context.scene.use_selection
        self.export_duplicates = context.scene.export_duplicates
        self.export_processed_duplicates = context.scene.export_processed_duplicates
        self.export_details = context.scene.export_details
        self.export_multiple_materials = context.scene.export_multiple_materials
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
        context.scene.export_multiple_materials = self.export_multiple_materials
        context.scene.path_mode = self.path_mode
        context.scene.export_details = self.export_details
        context.scene.allow_out_of_range = self.allow_out_of_range
        context.scene.export_duplicates = self.export_duplicates
        context.scene.export_processed_duplicates = self.export_processed_duplicates

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

        # DUPLICATE EXPORT LOGIC (if enabled)
        if self.export_duplicates and self.export_processed_duplicates:
            success = DuplicateExportHelper.export_duplicates_and_processed(
                context, export_paths, settings, report_func=self.report
            )
            if success:
                return {'FINISHED'}
            else:
                return {'CANCELLED'}

        elif self.export_duplicates and not self.export_processed_duplicates:
            DuplicateExportHelper.export_duplicates_only(context, export_paths, report_func=self.report)
            self.report({'INFO'}, "Duplicates exported (no final OBJ saved).")
            return {'FINISHED'}

        # NORMAL EXPORT (no duplicates)
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

                ps1_was_active = temporary_disable_ps1_render(context)
                snap_mods = get_vertex_snap_modifiers(valid_objects)
                snap_states = disable_vertex_snap_modifiers(snap_mods)

                try:
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
                finally:
                    restore_vertex_snap_modifiers(snap_states)
                    restore_ps1_render(context, ps1_was_active)

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