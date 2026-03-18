import bpy

def draw_validator(context, layout):
    scene = context.scene

    # Main box containing the unified dropdown and the 2x2 button grid
    main_box = layout.box()

    # Unified options dropdown (full width)
    main_box.prop(scene, "validator_option", text="")

    # 2x2 button grid
    grid = main_box.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)

    # Button 1: Suffix
    find_icon = get_icon(scene.validator_option)
    grid.operator("qb_tb.object_qb_tb_suffix", text="Suffix", icon=find_icon)

    # Button 2: Validate
    grid.operator("qb_tb.validate_all_objects", text="Validate", icon='ERROR')

    # Button 3: Select
    select_icon = get_icon(scene.validator_option)
    grid.operator("qb_tb.filter_select_objects", text="Select", icon=select_icon)

    # Button 4: Clean
    grid.operator("qb_tb.clean_object_suffixes", text="Clean", icon='FILE_REFRESH')


def get_icon(option):
    """Return icon for a given validator option."""
    icon_mapping = {
        'QUADBLOCK': 'MESH_CUBE',
        'TRIBLOCK': 'MESH_CONE',
        'INVALID_GEOMETRY': 'MESH_DATA',
        'INVALID_UVS': 'UV',
        'INVALID_TRIBLOCK_UVS': 'MESH_CONE',
        'DEGENERATED_UVS': 'GROUP_UVS',
        'NGONS': 'MESH_CYLINDER',
        'NON_MESH': 'OUTLINER_OB_EMPTY',
        'OUT_OF_RANGE': 'CUBE',
        'ALL_INVALID': 'ERROR'
    }
    return icon_mapping.get(option, 'VIEWZOOM')