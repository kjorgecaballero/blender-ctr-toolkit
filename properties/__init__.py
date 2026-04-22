from .ctr_main_props import register as register_ctr_main_props, unregister as unregister_ctr_main_props
from .qb_tb_validator.qb_tb_props import register as register_qb_tb_props, unregister as unregister_qb_tb_props
from .qb_tb_export.qb_tb_export_props import register as register_qb_tb_export_props, unregister as unregister_qb_tb_export_props
from .qb_tb_navigator import register as register_qb_tb_navigator_props, unregister as unregister_qb_tb_navigator_props
from .qb_tb_list import register as register_qb_tb_list_props, unregister as unregister_qb_tb_list_props
from .render import register as register_render_props, unregister as unregister_render_props   

def register():
    register_ctr_main_props()
    register_qb_tb_props()
    register_qb_tb_export_props()
    register_qb_tb_navigator_props()
    register_qb_tb_list_props()
    register_render_props()     

def unregister():
    unregister_render_props()   
    unregister_qb_tb_list_props()
    unregister_qb_tb_navigator_props()
    unregister_qb_tb_export_props()
    unregister_qb_tb_props()
    unregister_ctr_main_props()