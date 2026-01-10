from .qb_tb.qb_tb_props import register as register_qb_tb_props, unregister as unregister_qb_tb_props


def register():
    register_qb_tb_props()

def unregister():
    unregister_qb_tb_props()