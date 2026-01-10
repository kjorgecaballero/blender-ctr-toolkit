import bpy


class CTR_HelpUtils:
    DOCS_URL = "https://github.com/kjorgecaballero.github.io/blender-ctr-toolkit"
    TUTORIAL_URL = "https://youtube.com/playlist?list=PLvqykQpD5C2LQq1c7pYH5vWBxTlQ0tVXf"
    
    @classmethod
    def draw_help_buttons(cls, layout):
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        
        doc_op = row.operator(
            "wm.url_open", 
            text="", 
            icon='HELP'
        )
        doc_op.url = cls.DOCS_URL
        
        tutorial_op = row.operator(
            "wm.url_open", 
            text="", 
            icon='FILE_MOVIE'
        )
        tutorial_op.url = cls.TUTORIAL_URL


def draw_help_buttons(layout):
    CTR_HelpUtils.draw_help_buttons(layout)