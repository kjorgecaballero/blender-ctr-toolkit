import bpy

def draw_validator(context, layout):
    scene = context.scene

    main_box = layout.box()

    col = main_box.column(align=True)

    row_scope = col.row(align=True)
    row_scope.prop(scene, "validator_scope", expand=True)

    row1 = col.row(align=True)
    if scene.validator_scope == 'OBJECTS':
        row1.operator("qb_tb.object_qb_tb_suffix", text="Issues", icon='ERROR')
        row1.operator("qb_tb.filter_select_objects", text="Select", icon='RESTRICT_SELECT_OFF')
    else:
        row1.operator("list.validate_vertex_groups", text="Issues", icon='ERROR')
        row1.operator("qb_tb.select_vertex_groups_by_type", text="Select", icon='RESTRICT_SELECT_OFF')

    row2 = col.row(align=True)
    if scene.validator_scope == 'OBJECTS':
        row2.operator("qb_tb.clean_object_suffixes", text="Clear", icon='BRUSH_DATA')
    else:
        row2.operator("qb_tb.clear_vertex_group_issues", text="Clear", icon='BRUSH_DATA')
    row2.operator("qb_tb.validate", text="Remove", icon='CANCEL')

    if scene.validator_scope == 'OBJECTS':
        col.prop(scene, "validator_object_option", text="")
    else:
        col.prop(scene, "validator_vertex_group_option", text="")