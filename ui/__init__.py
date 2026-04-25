from .ctr_main_panel import register as register_main_panel, unregister as unregister_main_panel
from .qb_tb_list import register as register_qb_tb_list_ui, unregister as unregister_qb_tb_list_ui
from .render import register as register_render_ui, unregister as unregister_render_ui

from . import qb_tb_navigator
from . import qb_tb_validator

def register():
    register_main_panel()
    register_qb_tb_list_ui()
    register_render_ui()

def unregister():
    unregister_render_ui()
    unregister_qb_tb_list_ui()
    unregister_main_panel()