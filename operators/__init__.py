from .qb_tb_validator.qb_tb_ops import register as register_qb_tb, unregister as unregister_qb_tb
from .qb_tb_export import register as register_qb_tb_export, unregister as unregister_qb_tb_export
from .range_box import register_range_box, unregister_range_box


def register():
    register_qb_tb()
    register_qb_tb_export()
    register_range_box()


def unregister():
    unregister_range_box()
    unregister_qb_tb_export()
    unregister_qb_tb()