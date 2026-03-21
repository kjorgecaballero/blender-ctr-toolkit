bl_info = {
    "name": "Blender CTR Toolkit",
    "author": "Jorge Caballero (Siruka)",
    "version": (0, 0, 1),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > CTR",
    "description": "Tools for CTR track development including export functionality, quadblock/triblock navigation, and constant material grouping.",
    "category": "3D View",
}

import bpy

def register():
    from . import properties
    from . import operators
    from . import ui

    properties.register()
    operators.register()
    ui.register()

    # Add keymaps
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new("qb_tb.quick_export", 'E', 'PRESS', ctrl=True, shift=True)
    kmi.active = True

    km2 = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi2 = km2.keymap_items.new(
        "navigator.cursor_select_block",
        type='L',
        value='PRESS',
        ctrl=True,
        shift=False,
        alt=False
    )
    kmi2.active = True

    # Ctrl+Shift+D for duplicate with constant reassignment
    kmi3 = km2.keymap_items.new(
        "list.duplicate_selection",
        type='D',
        value='PRESS',
        ctrl=True,
        shift=True,
        alt=False
    )
    kmi3.active = True

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} loaded with Block Navigator and Group Management")

def unregister():
    from . import ui, operators, properties

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['3D View']
    for kmi in km.keymap_items:
        if kmi.idname == "qb_tb.quick_export":
            km.keymap_items.remove(kmi)
            break

    km2 = wm.keyconfigs.addon.keymaps['Mesh']
    for kmi in km2.keymap_items:
        if kmi.idname == "navigator.cursor_select_block":
            km2.keymap_items.remove(kmi)
            break
    # remove the duplicate shortcut
    for kmi in km2.keymap_items:
        if kmi.idname == "list.duplicate_selection":
            km2.keymap_items.remove(kmi)
            break

    ui.unregister()
    operators.unregister()
    properties.unregister()

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} unloaded")

if __name__ == "__main__":
    register()