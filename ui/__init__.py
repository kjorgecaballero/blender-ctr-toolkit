from .ctr_main_panel import register as register_main_panel, unregister as unregister_main_panel
from .qb_tb_list import register as register_qb_tb_list_ui, unregister as unregister_qb_tb_list_ui
from .render import register as register_render_ui, unregister as unregister_render_ui
from . import qb_tb_navigator
from . import qb_tb_validator
from . import mesh_menus
from .material_manager import register as register_mat_mgr_ui, unregister as unregister_mat_mgr_ui
from . import help_utils
from .uv_animator import register as register_uv_animator_ui, unregister as unregister_uv_animator_ui

def register():
    register_main_panel()
    register_qb_tb_list_ui()
    register_render_ui()
    mesh_menus.register()
    register_mat_mgr_ui()
    help_utils.register()
    register_uv_animator_ui()

def unregister():
    unregister_uv_animator_ui()
    help_utils.unregister()
    unregister_mat_mgr_ui()
    mesh_menus.unregister()
    unregister_render_ui()
    unregister_qb_tb_list_ui()
    unregister_main_panel()