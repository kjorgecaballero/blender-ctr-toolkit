import bpy
from .export_operator import QB_TB_OT_ExportQuadTriBlocks, menu_func_export
from .quick_export_operator import QB_TB_OT_QuickExport

def register():
    bpy.utils.register_class(QB_TB_OT_ExportQuadTriBlocks)
    bpy.utils.register_class(QB_TB_OT_QuickExport)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(QB_TB_OT_ExportQuadTriBlocks)
    bpy.utils.unregister_class(QB_TB_OT_QuickExport)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)