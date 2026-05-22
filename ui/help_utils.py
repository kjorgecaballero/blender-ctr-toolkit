import bpy
from bpy.types import Operator
from ..icons import get_icon

def _icon(name, fallback):
    ico = get_icon(name)
    return {'icon_value': ico} if ico else {'icon': fallback}


# Operators for help and keymaps

class CTR_OT_open_docs(Operator):
    bl_idname = "ctr.open_docs"
    bl_label = "Documentation"
    bl_description = "Open online documentation in your browser"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://github.com/kjorgecaballero.github.io/blender-ctr-toolkit")
        return {'FINISHED'}

class CTR_OT_open_tutorial(Operator):
    bl_idname = "ctr.open_tutorial"
    bl_label = "Tutorials"
    bl_description = "Watch video tutorials on YouTube"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://youtube.com/playlist?list=PLvqykQpD5C2LQq1c7pYH5vWBxTlQ0tVXf")
        return {'FINISHED'}

class CTR_OT_open_issue(Operator):
    bl_idname = "ctr.open_issue"
    bl_label = "Report Issue"
    bl_description = "Open GitHub issue tracker"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://github.com/kjorgecaballero/blender-ctr-toolkit/issues/new/choose")
        return {'FINISHED'}

class CTR_OT_show_keymaps(Operator):
    bl_idname = "ctr.show_keymaps"
    bl_label = "Keymaps"
    bl_description = "Show default keymap assignments for CTR Toolkit"
    bl_options = {'REGISTER'}

    def execute(self, context):
        def draw(self, context):
            layout = self.layout
            layout.label(text="Ctrl+Shift+E    → Quick Export")
            layout.label(text="Ctrl+L          → Navigate block under cursor")
            layout.label(text="Ctrl+Shift+D    → Duplicate block with constant")
            layout.label(text="Ctrl+Shift+S    → Toggle block seams (Edge menu)")
            layout.separator()
            layout.label(text="You can change these in:")
            layout.label(text="Edit > Preferences > Keymap", icon='PREFERENCES')
        context.window_manager.popup_menu(draw, title="CTR Toolkit Keymaps", icon='KEYINGSET')
        return {'FINISHED'}

class CTR_HelpUtils:
    @classmethod
    def draw_help_buttons_into_row(cls, row):
        # Documentation
        row.operator("ctr.open_docs", text="", icon='INFO')
        # Tutorials
        row.operator("ctr.open_tutorial", text="", **_icon("tutorial_icon", 'FILE_MOVIE'))
        # Report issue
        row.operator("ctr.open_issue", text="", **_icon("report_icon", 'URL'))
        # Keymaps popup
        row.operator("ctr.show_keymaps", text="", icon='KEYINGSET')
        # Update button (from addon_updater_ops)
        try:
            from ..addon_updater_ops import updater
            update_ready = False
            if updater and not getattr(updater, 'invalid_updater', True):
                update_ready = getattr(updater, 'update_ready', False)
            sub_row = row.row(align=True)
            if update_ready:
                sub_row.alert = True
            sub_row.operator("blender_ctr_toolkit.updater_install_popup", text="", icon='BLENDER', emboss=True)
        except Exception:
            pass

    @classmethod
    def draw_help_buttons(cls, layout):
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        cls.draw_help_buttons_into_row(row)

def draw_help_buttons(layout):
    CTR_HelpUtils.draw_help_buttons(layout)

# Register all custom operators
classes = [
    CTR_OT_open_docs,
    CTR_OT_open_tutorial,
    CTR_OT_open_issue,
    CTR_OT_show_keymaps,
]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Error registering {cls.__name__}: {e}")

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {e}")