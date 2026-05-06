from .rename import register as register_rename, unregister as unregister_rename
from .remap import register as register_remap, unregister as unregister_remap
from .assign_select import register as register_assign_select, unregister as unregister_assign_select
from .refresh import register as register_refresh, unregister as unregister_refresh
from .scroll import register as register_scroll, unregister as unregister_scroll
from .toggle_selection import register as register_toggle, unregister as unregister_toggle


def register():
    register_rename()
    register_remap()
    register_assign_select()
    register_refresh()
    register_scroll()
    register_toggle()


def unregister():
    unregister_toggle()
    unregister_scroll()
    unregister_refresh()
    unregister_assign_select()
    unregister_remap()
    unregister_rename()