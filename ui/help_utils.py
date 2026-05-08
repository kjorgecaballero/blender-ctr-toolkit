import bpy
from ..addon_updater_ops import updater

class CTR_HelpUtils:
    DOCS_URL = "https://github.com/kjorgecaballero.github.io/blender-ctr-toolkit"
    TUTORIAL_URL = "https://youtube.com/playlist?list=PLvqykQpD5C2LQq1c7pYH5vWBxTlQ0tVXf"
    ISSUES_URL = "https://github.com/kjorgecaballero/blender-ctr-toolkit/issues/new/choose"

    @classmethod
    def draw_help_buttons(cls, layout):
        row = layout.row(align=True)
        row.alignment = 'RIGHT'

        # Documentation button
        doc_op = row.operator("wm.url_open", text="", icon='HELP')
        doc_op.url = cls.DOCS_URL

        # Tutorial button
        tutorial_op = row.operator("wm.url_open", text="", icon='FILE_MOVIE')
        tutorial_op.url = cls.TUTORIAL_URL

        # Update notification button (turns red when update is ready)
        update_ready = False
        if updater and not getattr(updater, 'invalid_updater', True):
            update_ready = updater.update_ready or False

        update_op = row.operator(
            "blender_ctr_toolkit.updater_install_popup",
            text="",
            icon='ERROR' if update_ready else 'INFO',
            emboss=True
        )
        if update_ready:
            update_op.alert = True

        # Report Issue button (GitHub)
        issue_op = row.operator("wm.url_open", text="", icon='URL')
        issue_op.url = cls.ISSUES_URL


def draw_help_buttons(layout):
    CTR_HelpUtils.draw_help_buttons(layout)