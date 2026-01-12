from .qb_tb.qb_tb_ops import register as register_qb_tb, unregister as unregister_qb_tb
from .range_box.range_box_operator import register as register_range_box, unregister as unregister_range_box

def register():
    register_qb_tb()
    register_range_box()

def unregister():
    unregister_range_box()
    unregister_qb_tb()