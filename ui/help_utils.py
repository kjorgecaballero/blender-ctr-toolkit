import bpy

class CTR_HelpUtils:
    DOCS_URL = "https://github.com/kjorgecaballero.github.io/blender-ctr-toolkit"
    TUTORIAL_URL = "https://youtube.com/playlist?list=PLvqykQpD5C2LQq1c7pYH5vWBxTlQ0tVXf"
    ISSUES_URL = "https://github.com/kjorgecaballero/blender-ctr-toolkit/issues/new/choose"

    @classmethod
    def draw_help_buttons_into_row(cls, row):
        """Draw help buttons directly into an existing row (robust version)."""
        # Documentation button
        doc = row.operator("wm.url_open", text="", icon='HELP')
        doc.url = cls.DOCS_URL

        # Tutorial button 
        tutorial = row.operator("wm.url_open", text="", icon='FILE_MOVIE')
        tutorial.url = cls.TUTORIAL_URL

        # Update button - The row must be red, not the operator
        try:
            from ..addon_updater_ops import updater
            update_ready = False
            if updater and not getattr(updater, 'invalid_updater', True):
                update_ready = getattr(updater, 'update_ready', False)
            
            # Insert the operator inside a temporary sub-layout
            sub_row = row.row(align=True)
            if update_ready:
                sub_row.alert = True  # Make the entire sub-layout red
            
            update_op = sub_row.operator(
                "blender_ctr_toolkit.updater_install_popup",
                text="",
                icon='INFO',
                emboss=True
            )
        except Exception:
            pass

        # Report Issue button 
        issue = row.operator("wm.url_open", text="", icon='URL')
        issue.url = cls.ISSUES_URL

    @classmethod
    def draw_help_buttons(cls, layout):
        """Legacy method that creates its own row (kept for compatibility)."""
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        cls.draw_help_buttons_into_row(row)


def draw_help_buttons(layout):
    CTR_HelpUtils.draw_help_buttons(layout)