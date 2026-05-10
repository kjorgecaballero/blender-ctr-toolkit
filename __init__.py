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
        default=1,      # (daily check)
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

    # 4. Add keymaps and timer ONLY if not running in background mode
    if not bpy.app.background:
        wm = bpy.context.window_manager
        # wm.keyconfigs.addon may be None in some configurations, check it
        if wm and wm.keyconfigs.addon:
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

        # Force an update check right after Blender starts (only in interactive mode)
        def delayed_update_check():
            if not addon_updater_ops.updater.invalid_updater:
                addon_updater_ops.updater.check_for_update(now=False)
                # Refresh UI after the check so the button turns red immediately
                addon_updater_ops.ui_refresh(None)
            return None  # run only once

        bpy.app.timers.register(delayed_update_check, first_interval=2.0)

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} loaded with Block Navigator and Group Management")


def unregister():
    # 1. Remove keymaps only if they were added (i.e., not in background)
    if not bpy.app.background:
        wm = bpy.context.window_manager
        if wm and wm.keyconfigs.addon:
            # Remove from '3D View' keymap
            km = wm.keyconfigs.addon.keymaps.get('3D View')
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == "qb_tb.quick_export":
                        km.keymap_items.remove(kmi)
                        break
            # Remove from 'Mesh' keymap
            km = wm.keyconfigs.addon.keymaps.get('Mesh')
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname in {"navigator.cursor_select_block", "list.duplicate_selection"}:
                        km.keymap_items.remove(kmi)

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