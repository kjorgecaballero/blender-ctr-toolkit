import bpy

def draw_section_header(layout, label, icon='NONE'):
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    row.label(text=label, icon=icon)
    return row

def draw_toggle_button(layout, prop_name, text, icon, context):
    row = layout.row(align=True)
    row.prop(context.scene, prop_name, text=text, icon=icon, toggle=True)
    return row

def draw_button_row(layout, operators, icons, texts):
    row = layout.row(align=True)
    for i, (op, icon, text) in enumerate(zip(operators, icons, texts)):
        row.operator(op, text=text, icon=icon)
    return row