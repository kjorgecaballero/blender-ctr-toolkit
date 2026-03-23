import bpy

def draw_validator(context, layout):
    scene = context.scene

    main_box = layout.box()

    # Scope selection (Objects / Vertex Groups)
    row = main_box.row(align=True)
    row.prop(scene, "validator_scope", expand=True)

    # Use a column with align=True to remove extra spacing between rows
    col = main_box.column(align=True)

    # First row: Suffix/Issues + Select
    row1 = col.row(align=True)
    if scene.validator_scope == 'OBJECTS':
        row1.operator("qb_tb.object_qb_tb_suffix", text="Suffix", icon='SORTALPHA')
        row1.operator("qb_tb.filter_select_objects", text="Select", icon='RESTRICT_SELECT_OFF')
    else:
        row1.operator("list.validate_vertex_groups", text="Issues", icon='ERROR')
        row1.operator("qb_tb.select_vertex_groups_by_type", text="Select", icon='RESTRICT_SELECT_OFF')

    # Second row: Clean/Clear + Validate
    row2 = col.row(align=True)
    if scene.validator_scope == 'OBJECTS':
        row2.operator("qb_tb.clean_object_suffixes", text="Clean", icon='FILE_REFRESH')
    else:
        row2.operator("qb_tb.clear_vertex_group_issues", text="Clear", icon='TRASH')
    row2.operator("qb_tb.validate", text="Validate", icon='CHECKMARK')

    # Unified dropdown
    main_box.prop(scene, "validator_option", text="")