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


# Updater integration

from . import addon_updater_ops


class CTRToolkitPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_interval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_interval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
    )
    updater_interval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_interval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )

    def draw(self, context):
        layout = self.layout
        addon_updater_ops.update_settings_ui(self, context, layout)



# Original register / unregister functions

def register():
    # 1. Register preferences class
    bpy.utils.register_class(CTRToolkitPreferences)

    # 2. Register updater
    addon_updater_ops.register(bl_info)

    # 3. Register all built-in modules
    from . import properties
    from . import operators
    from . import ui

    properties.register()
    operators.register()
    ui.register()

    # 4. Add keymaps
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
    # 1. Remove keymaps first
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
        if kmi.idname == "list.duplicate_selection":
            km2.keymap_items.remove(kmi)
            break

    # 2. Unregister built-in modules
    from . import ui, operators, properties
    ui.unregister()
    operators.unregister()
    properties.unregister()

    # 3. Unregister updater
    addon_updater_ops.unregister()

    # 4. Unregister preferences class
    bpy.utils.unregister_class(CTRToolkitPreferences)

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} unloaded")


if __name__ == "__main__":
    register()