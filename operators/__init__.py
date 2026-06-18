from .qb_tb_validator import register_qb_tb, unregister_qb_tb
from .qb_tb_export import register as register_qb_tb_export, unregister as unregister_qb_tb_export
from .range_box import register_range_box, unregister_range_box
from .qb_tb_navigator import register as register_qb_tb_navigator, unregister as unregister_qb_tb_navigator
from .qb_tb_list import register as register_qb_tb_list, unregister as unregister_qb_tb_list
from .render import register as register_render_ops, unregister as unregister_render_ops
from .material_manager import register as register_mat_mgr_ops, unregister as unregister_mat_mgr_ops
from .uv_animator import register as register_uv_animator, unregister as unregister_uv_animator

def register():
    register_qb_tb()
    register_qb_tb_export()
    register_range_box()
    register_qb_tb_navigator()
    register_qb_tb_list()
    register_render_ops()
    register_mat_mgr_ops()
    register_uv_animator()

def unregister():
    unregister_uv_animator()
    unregister_mat_mgr_ops()
    unregister_render_ops()
    unregister_qb_tb_list()
    unregister_qb_tb_navigator()
    unregister_range_box()
    unregister_qb_tb_export()
    unregister_qb_tb()