from .qb_tb.qb_tb_props import register as register_qb_tb_props, unregister as unregister_qb_tb_props
from .qb_tb_export.qb_tb_export_props import register as register_qb_tb_export_props, unregister as unregister_qb_tb_export_props

def register():
    register_qb_tb_props()
    register_qb_tb_export_props()

def unregister():
    unregister_qb_tb_export_props()
    unregister_qb_tb_props()