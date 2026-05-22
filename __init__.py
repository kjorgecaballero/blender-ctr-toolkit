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

from . import addon_updater_ops
from . import icons


class CTRToolkitPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
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
        default=1,
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


def register():
    bpy.utils.register_class(CTRToolkitPreferences)
    addon_updater_ops.register(bl_info)

    from . import properties
    from . import operators
    from . import ui

    properties.register()
    operators.register()
    ui.register()

    icons.register_icons()

    if not bpy.app.background:
        wm = bpy.context.window_manager
        if wm and wm.keyconfigs.addon:
            # 3D View keymap
            km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
            kmi = km.keymap_items.new("qb_tb.quick_export", 'E', 'PRESS', ctrl=True, shift=True)
            kmi.active = True

            # Mesh keymap for navigation and duplicate
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

            # Toggle QB/TB seams with Ctrl+Shift+S
            kmi4 = km2.keymap_items.new(
                "list.toggle_block_seams",
                type='S',
                value='PRESS',
                ctrl=True,
                shift=True,
                alt=False
            )
            kmi4.active = True

        def delayed_update_check():
            if not addon_updater_ops.updater.invalid_updater:
                addon_updater_ops.updater.check_for_update(now=False)
                addon_updater_ops.ui_refresh(None)
            return None

        bpy.app.timers.register(delayed_update_check, first_interval=2.0)

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} loaded with Block Navigator and Group Management")


def unregister():
    if not bpy.app.background:
        wm = bpy.context.window_manager
        if wm and wm.keyconfigs.addon:
            km = wm.keyconfigs.addon.keymaps.get('3D View')
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == "qb_tb.quick_export":
                        km.keymap_items.remove(kmi)
                        break
            km = wm.keyconfigs.addon.keymaps.get('Mesh')
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname in {"navigator.cursor_select_block", "list.duplicate_selection", "list.toggle_block_seams"}:
                        km.keymap_items.remove(kmi)

    from . import ui, operators, properties
    ui.unregister()
    operators.unregister()
    properties.unregister()

    addon_updater_ops.unregister()
    bpy.utils.unregister_class(CTRToolkitPreferences)
    icons.unregister_icons()

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} unloaded")


if __name__ == "__main__":
    register()