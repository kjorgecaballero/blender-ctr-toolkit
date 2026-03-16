from .qb_tb_validator.qb_tb_panel import register as register_qb_tb_ui, unregister as unregister_qb_tb_ui
from .qb_tb_navigator import register as register_qb_tb_navigator_ui, unregister as unregister_qb_tb_navigator_ui
from .qb_tb_list import register as register_qb_tb_list_ui, unregister as unregister_qb_tb_list_ui

def register():
    register_qb_tb_ui()
    register_qb_tb_navigator_ui()
    register_qb_tb_list_ui()

def unregister():
    unregister_qb_tb_list_ui()
    unregister_qb_tb_navigator_ui()
    unregister_qb_tb_ui()