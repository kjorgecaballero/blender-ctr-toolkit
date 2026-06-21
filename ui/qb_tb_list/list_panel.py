"""
Quadblock/Triblock List Panel - Main UI
"""

import bpy
from bpy.types import Panel

from .list_helpers import get_material_image_icon, get_block_material_name
from ...addon_updater_ops import updater
from ..help_utils import draw_help_buttons
from ...icons import get_icon

def _icon(name, fallback):
    ico = get_icon(name)
    return {'icon_value': ico} if ico else {'icon': fallback}


class LIST_PT_BlockListPanel(Panel):
    bl_label = "Navigation List"
    bl_idname = "LIST_PT_block_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CTR'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.edit_object

        is_edit_mode = (context.mode == 'EDIT_MESH')
        if not is_edit_mode or not obj:
            layout.label(text="Enter Edit Mode to use tools", icon='ERROR')
            return

        main_col = layout.column(align=True)

        display_items = []
        display_counts = {"qb": 0, "tb": 0, "total": 0}
        nav_point_count = 0

        if scene.list_display_type == 'VERTEX_GROUPS':
            for vg in obj.vertex_groups:
                if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                    try:
                        block_id = int(vg.name[3:])
                        display_items.append({
                            'type': 'vertex_group',
                            'name': vg.name,
                            'block_type': 'quadblock',
                            'block_id': block_id,
                            'data': vg
                        })
                        display_counts["qb"] += 1
                        display_counts["total"] += 1
                    except ValueError:
                        continue
                elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                    try:
                        block_id = int(vg.name[3:])
                        display_items.append({
                            'type': 'vertex_group',
                            'name': vg.name,
                            'block_type': 'triblock',
                            'block_id': block_id,
                            'data': vg
                        })
                        display_counts["tb"] += 1
                        display_counts["total"] += 1
                    except ValueError:
                        continue

        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            # scan material slots for constant materials
            for slot in obj.material_slots:
                mat = slot.material
                if not mat:
                    continue
                block_type = mat.get("ctr_block_type")
                if block_type is None:
                    continue
                block_id = mat.get("ctr_block_id", 0)
                original_material = mat.get("ctr_original_material", "Unknown")
                is_nav_point = mat.get("ctr_is_navigation_point", False)

                if (block_type == "quadblock" and scene.list_filter_cm_qb) or \
                   (block_type == "triblock" and scene.list_filter_cm_tb):
                    display_items.append({
                        'type': 'constant_material',
                        'name': mat.name,
                        'block_type': block_type,
                        'block_id': block_id,
                        'original_material': original_material,
                        'is_nav_point': is_nav_point,
                        'data': mat
                    })
                    if block_type == "quadblock":
                        display_counts["qb"] += 1
                    else:
                        display_counts["tb"] += 1
                    display_counts["total"] += 1
                    if is_nav_point:
                        nav_point_count += 1

        # Mode selector
        mode_row = main_col.row()
        mode_row.prop(scene, "list_display_type", expand=True)

        if scene.list_display_type == 'VERTEX_GROUPS':
            has_block_vg = any(vg.name.startswith(("QB_", "TB_")) for vg in obj.vertex_groups)
            has_detected = ("quadblock_centers" in obj and obj["quadblock_centers"]) or \
                           ("triblock_faces" in obj and obj["triblock_faces"])

            if has_detected or has_block_vg:
                row1 = main_col.row(align=True)
                if has_detected:
                    row1.operator("list.create_block_vertex_groups", text="Generate", **_icon("vertex_group_icon", 'GROUP_VERTEX'))
                if has_block_vg:
                    row1.operator("list.clear_block_vertex_groups", text="Clear", **_icon("clear_icon", 'TRASH'))

                row2 = main_col.row(align=True)
                if has_block_vg:
                    row2.menu("LIST_MT_VertexGroupMenu", text="Groups", icon='GROUP')
                    row2.operator("list.select_list_from_block", text="Check", **_icon("check_icon", 'CHECKBOX_HLT'))

            self.draw_custom_list(main_col, context, obj, display_items, display_counts,
                                 has_vertex_groups=has_block_vg, has_detected_blocks=has_detected)

        else:  # CONSTANT_MATERIALS
            has_const = any(slot.material and slot.material.get("ctr_block_type") is not None for slot in obj.material_slots)
            has_detected = ("quadblock_centers" in obj and obj["quadblock_centers"]) or \
                           ("triblock_faces" in obj and obj["triblock_faces"])

            row1 = main_col.row(align=True)
            if has_detected:
                row1.operator("list.assign_constant_material", text="Assign", **_icon("material_icon", 'MATERIAL'))
            if has_const:
                row1.operator("list.clear_constant_material", text="Clear", **_icon("clear_icon", 'TRASH'))

            row2 = main_col.row(align=True)
            if has_const:
                group_text = scene.list_active_group if scene.list_active_group else "Groups"
                row2.operator("list.group_management_dialog", text=group_text, icon='GROUP')
                row2.operator("list.select_list_from_block", text="Check", **_icon("check_icon", 'CHECKBOX_HLT'))

            self.draw_custom_list(main_col, context, obj, display_items, display_counts,
                                 has_constant_materials=has_const,
                                 has_detected_blocks=has_detected,
                                 nav_point_count=nav_point_count)

    def draw_custom_list(self, layout, context, obj, display_items, display_counts,
                        has_vertex_groups=False, has_constant_materials=False,
                        has_detected_blocks=False, nav_point_count=0):
        scene = context.scene

        list_box = layout.box()
        header_row = list_box.row(align=True)
        header_row.prop(scene, "list_show_items",
                        icon="TRIA_DOWN" if scene.list_show_items else "TRIA_RIGHT",
                        icon_only=True, emboss=False)
        header_row.label(text="Item List")

        help_row = header_row.row(align=True)
        help_row.alignment = 'RIGHT'
        draw_help_buttons(help_row)

        if not scene.list_show_items:
            return

        # Search
        search_row = list_box.row(align=True)
        search_row.prop(scene, "list_search_text", text="", icon='VIEWZOOM')

        # Filter menus (only visual, the actual filtering is done below)
        if scene.list_display_type == 'VERTEX_GROUPS':
            filter_row = list_box.row()
            filter_row.alignment = 'EXPAND'
            split = filter_row.split(factor=0.5)
            left_col = split.row()
            left_col.alignment = 'EXPAND'
            material_text = scene.list_material_filter_vg if scene.list_material_filter_vg else "All"
            vg_icon = get_icon("vertex_group_icon")
            if vg_icon:
                left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon_value=vg_icon)
            else:
                left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')
            right_col = split.row()
            right_col.alignment = 'EXPAND'
            issue_text = {
                'ALL': "All",
                'VALID': "Valid",
                'INVALID': "Invalid",
                'INVALID_GEOMETRY': "Invalid Geo",
                'INVALID_UVS': "Invalid UVs",
                'INVALID_TRIBLOCK_UVS': "Invalid Triblock UVs",
                'DEGENERATED_UVS': "Degenerated UVs",
                'OUT_OF_RANGE': "Out of Range",
                'MULTIPLE_MATERIALS': "Multiple Mats",
                'MISSING_UVS': "Missing UVs",
            }.get(scene.list_issue_filter, "All")
            right_col.menu("LIST_MT_IssueFilterMenu", text=issue_text, icon='ERROR')

        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            menus_row = list_box.row()
            menus_row.alignment = 'EXPAND'
            split = menus_row.split(factor=0.5)
            left_col = split.row()
            left_col.alignment = 'EXPAND'
            material_text = scene.list_material_filter_cm if scene.list_material_filter_cm else "All"
            const_icon = get_icon("constant_mat_icon")
            if const_icon:
                left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon_value=const_icon)
            else:
                left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')
            right_col = split.row()
            right_col.alignment = 'EXPAND'
            nav_text = "All"
            if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                nav_text = "Navigation"
            elif scene.list_navigation_filter == 'NON_NAVIGATION':
                nav_text = "Constant"
            nav_icon = get_icon("nav_point_icon")
            if nav_icon:
                right_col.menu("LIST_MT_NavigationFilterMenu", text=nav_text, icon_value=nav_icon)
            else:
                right_col.menu("LIST_MT_NavigationFilterMenu", text=nav_text, icon='PIVOT_CURSOR')

        # Action row (QB/TB toggles, check/uncheck, sort)
        if scene.list_display_type == 'VERTEX_GROUPS':
            action_row = list_box.row(align=True)
            action_row.alignment = 'CENTER'
            qb_icon = get_icon("quadblock_icon")
            tb_icon = get_icon("triblock_icon")
            check_all_icon = get_icon("check_all_icon")
            uncheck_all_icon = get_icon("uncheck_all_icon")
            if qb_icon:
                action_row.prop(scene, "list_filter_show_qb", text="", icon_value=qb_icon, toggle=True)
            else:
                action_row.prop(scene, "list_filter_show_qb", text="", icon='VERTEXSEL', toggle=True)
            if tb_icon:
                action_row.prop(scene, "list_filter_show_tb", text="", icon_value=tb_icon, toggle=True)
            else:
                action_row.prop(scene, "list_filter_show_tb", text="", icon='FACESEL', toggle=True)
            if check_all_icon:
                action_row.operator("list.check_all", text="", icon_value=check_all_icon)
            else:
                action_row.operator("list.check_all", text="", icon='CHECKBOX_HLT')
            if uncheck_all_icon:
                action_row.operator("list.clear_checks_in_current_list", text="", icon_value=uncheck_all_icon)
            else:
                action_row.operator("list.clear_checks_in_current_list", text="", icon='CHECKBOX_DEHLT')
            typeqb_icon = get_icon("typeqb_icon")
            typetb_icon = get_icon("typetb_icon")
            if scene.list_sort_type_direction == 'ASC' and typeqb_icon:
                action_row.operator("list.toggle_sort_type", text="", icon_value=typeqb_icon)
            elif scene.list_sort_type_direction == 'DESC' and typetb_icon:
                action_row.operator("list.toggle_sort_type", text="", icon_value=typetb_icon)
            else:
                fallback = 'VERTEXSEL' if scene.list_sort_type_direction == 'ASC' else 'FACESEL'
                action_row.operator("list.toggle_sort_type", text="", icon=fallback)
            action_row.operator("list.toggle_sort_name", text="", icon='SORTALPHA')

        else:  # CONSTANT_MATERIALS
            action_row = list_box.row(align=True)
            action_row.alignment = 'CENTER'
            qb_icon = get_icon("quadblock_icon")
            tb_icon = get_icon("triblock_icon")
            check_all_icon = get_icon("check_all_icon")
            uncheck_all_icon = get_icon("uncheck_all_icon")
            if qb_icon:
                action_row.prop(scene, "list_filter_cm_qb", text="", icon_value=qb_icon, toggle=True)
            else:
                action_row.prop(scene, "list_filter_cm_qb", text="", icon='VERTEXSEL', toggle=True)
            if tb_icon:
                action_row.prop(scene, "list_filter_cm_tb", text="", icon_value=tb_icon, toggle=True)
            else:
                action_row.prop(scene, "list_filter_cm_tb", text="", icon='FACESEL', toggle=True)
            if check_all_icon:
                action_row.operator("list.check_all", text="", icon_value=check_all_icon)
            else:
                action_row.operator("list.check_all", text="", icon='CHECKBOX_HLT')
            if uncheck_all_icon:
                action_row.operator("list.clear_checks_in_current_list", text="", icon_value=uncheck_all_icon)
            else:
                action_row.operator("list.clear_checks_in_current_list", text="", icon='CHECKBOX_DEHLT')
            typeqb_icon = get_icon("typeqb_icon")
            typetb_icon = get_icon("typetb_icon")
            if scene.list_sort_type_direction == 'ASC' and typeqb_icon:
                action_row.operator("list.toggle_sort_type", text="", icon_value=typeqb_icon)
            elif scene.list_sort_type_direction == 'DESC' and typetb_icon:
                action_row.operator("list.toggle_sort_type", text="", icon_value=typetb_icon)
            else:
                fallback = 'VERTEXSEL' if scene.list_sort_type_direction == 'ASC' else 'FACESEL'
                action_row.operator("list.toggle_sort_type", text="", icon=fallback)
            action_row.operator("list.toggle_sort_name", text="", icon='SORTALPHA')

        # BUILD FILTERED LIST FROM display_items
        # Apply all filters (material, navigation, group, search, issue) to display_items
        filtered_items = list(display_items)

        # Material filter
        if scene.list_display_type == 'VERTEX_GROUPS':
            mat_filter = scene.list_material_filter_vg
            if mat_filter:
                filtered_items = [it for it in filtered_items if it.get('material') == mat_filter]
        else:
            mat_filter = scene.list_material_filter_cm
            if mat_filter:
                filtered_items = [it for it in filtered_items if it['name'] == mat_filter]

        # Navigation filter (only for CONSTANT_MATERIALS)
        if scene.list_display_type == 'CONSTANT_MATERIALS':
            nav_filter = scene.list_navigation_filter
            if nav_filter == 'NAVIGATION_POINTS':
                filtered_items = [it for it in filtered_items if it.get('is_nav_point', False)]
            elif nav_filter == 'NON_NAVIGATION':
                filtered_items = [it for it in filtered_items if not it.get('is_nav_point', False)]

        # Group filter (only for CONSTANT_MATERIALS)
        if scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
            if "constant_material_groups" in scene:
                try:
                    import json
                    groups = json.loads(scene["constant_material_groups"])
                    group_name = scene.list_active_group
                    if group_name in groups:
                        group_set = set(groups[group_name])
                        filtered_items = [it for it in filtered_items if it['name'] in group_set]
                except:
                    pass

        # Search filter
        search_text = scene.list_search_text.lower()
        if search_text:
            new_filtered = []
            for it in filtered_items:
                name_match = search_text in it['name'].lower()
                type_match = search_text in it['block_type'].lower()
                id_match = search_text in str(it['block_id'])
                material_match = False
                if scene.list_display_type == 'VERTEX_GROUPS' and it.get('material'):
                    material_match = search_text in it['material'].lower()
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and it.get('original_material'):
                    material_match = search_text in it['original_material'].lower()
                if name_match or type_match or id_match or material_match:
                    new_filtered.append(it)
            filtered_items = new_filtered

        # Issue filter (only for VERTEX_GROUPS)
        if scene.list_display_type == 'VERTEX_GROUPS':
            issues_dict = {}
            if "vertex_group_issues" in obj:
                issues_dict = dict(obj["vertex_group_issues"])
            issue_filter = scene.list_issue_filter
            if issue_filter != 'ALL':
                new_filtered = []
                for it in filtered_items:
                    item_issues = issues_dict.get(it['name'], [])
                    real_issues = [i for i in item_issues if i not in ('quadblock', 'triblock')]
                    if issue_filter == 'VALID':
                        if ('quadblock' in item_issues or 'triblock' in item_issues) and len(real_issues) == 0:
                            new_filtered.append(it)
                    elif issue_filter == 'INVALID':
                        if len(real_issues) > 0:
                            new_filtered.append(it)
                    elif issue_filter == 'INVALID_GEOMETRY':
                        if 'invalid_geometry' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'INVALID_UVS':
                        if 'invalid_uvs' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'INVALID_TRIBLOCK_UVS':
                        if 'invalid_triblock_uvs' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'DEGENERATED_UVS':
                        if 'degenerated_uvs' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'OUT_OF_RANGE':
                        if 'out_of_range' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'MULTIPLE_MATERIALS':
                        if 'multiple_materials' in item_issues:
                            new_filtered.append(it)
                    elif issue_filter == 'MISSING_UVS':
                        if 'missing_uvs' in item_issues:
                            new_filtered.append(it)
                filtered_items = new_filtered

        # SORT
        reverse_type = (scene.list_sort_type_direction == 'DESC')
        reverse_name = (scene.list_sort_name_direction == 'DESC')

        def sort_key(item):
            type_order = 0 if item['block_type'] == 'quadblock' else 1
            if reverse_type:
                type_order = 1 - type_order
            nav_order = 0 if item.get('is_nav_point', False) else 1
            if reverse_name:
                nav_order = 1 - nav_order
            name_key = item['name'].lower()
            id_key = item['block_id']
            return (type_order, nav_order, name_key, id_key)

        filtered_items.sort(key=sort_key)
        if reverse_name:
            filtered_items.reverse()

        # PAGINATION
        total_items = len(filtered_items)
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total_items - ITEMS_PER_PAGE)
        current_scroll = scene.list_vertical_scroll
        if current_scroll > max_scroll:
            current_scroll = max_scroll
        start_idx = current_scroll
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
        visible_items = filtered_items[start_idx:end_idx]

        # DRAW THE LIST
        if visible_items or total_items > 0:
            scroll_box = list_box.box()
            info_col = scroll_box.column(align=True)
            count_row = info_col.row()
            count_row.alignment = 'CENTER'
            if scene.list_display_type == 'CONSTANT_MATERIALS':
                count_text = f"QB: {display_counts['qb']} | TB: {display_counts['tb']} | NAV: {nav_point_count}"
            else:
                count_text = f"QB: {display_counts['qb']} | TB: {display_counts['tb']}"
            count_row.label(text=count_text)

            if total_items > 0:
                pos_row = info_col.row()
                pos_row.alignment = 'CENTER'
                pos_text = f"items {start_idx+1}-{end_idx} of {total_items}"
                pos_row.label(text=pos_text)

            if visible_items:
                multi_selected = {}
                if "multi_selected_items" in obj:
                    multi_selected = dict(obj["multi_selected_items"])

                for i, item in enumerate(visible_items):
                    idx = start_idx + i
                    row = scroll_box.row()
                    row.alignment = 'EXPAND'

                    left_side = row.row(align=True)
                    left_side.alignment = 'LEFT'

                    is_selected = item['name'] in multi_selected
                    checkbox_icon = 'CHECKBOX_HLT' if is_selected else 'CHECKBOX_DEHLT'
                    toggle_op = left_side.operator("list.toggle_multi_selection",
                                                   text="", icon=checkbox_icon, emboss=False)
                    toggle_op.item_name = item['name']

                    if item['block_type'] == 'quadblock':
                        qb_icon = get_icon("quadblock_icon")
                        if qb_icon:
                            left_side.label(text="", icon_value=qb_icon)
                        else:
                            left_side.label(text="", icon='MESH_CUBE')
                    else:
                        tb_icon = get_icon("triblock_icon")
                        if tb_icon:
                            left_side.label(text="", icon_value=tb_icon)
                        else:
                            left_side.label(text="", icon='MESH_CONE')

                    middle = row.row()
                    middle.alignment = 'EXPAND'

                    if item['type'] == 'vertex_group':
                        material_name = get_block_material_name(obj, item['block_type'], item['block_id'])
                        if material_name:
                            block_prefix = "QB" if item['block_type'] == 'quadblock' else "TB"
                            display_text = f"{block_prefix}_{material_name}_{item['block_id']}"
                            material_icon = get_material_image_icon(material_name)
                            if isinstance(material_icon, int) and material_icon != 0:
                                middle.label(text=display_text, icon_value=material_icon)
                            else:
                                middle.label(text=display_text, icon='MATERIAL')
                        else:
                            block_prefix = "QB" if item['block_type'] == 'quadblock' else "TB"
                            middle.label(text=f"{block_prefix}_Block_{item['block_id']}", icon='MATERIAL')

                        if "vertex_group_issues" in obj:
                            issues_dict = dict(obj["vertex_group_issues"])
                            item_issues = issues_dict.get(item['name'], [])
                            if item_issues:
                                non_type = [iss for iss in item_issues if iss not in ('quadblock', 'triblock')]
                                if non_type:
                                    right_icon = row.row(align=True)
                                    right_icon.alignment = 'RIGHT'
                                    warn_icon = get_icon("warning_icon")
                                    if warn_icon:
                                        op = right_icon.operator("list.show_vertex_group_issues",
                                                                 text="", icon_value=warn_icon, emboss=False)
                                    else:
                                        op = right_icon.operator("list.show_vertex_group_issues",
                                                                 text="", icon='ERROR', emboss=False)
                                    op.group_name = item['name']

                    elif item['type'] == 'constant_material':
                        material_name = item['name']
                        display_text = material_name
                        material_icon = get_material_image_icon(material_name)
                        if isinstance(material_icon, int) and material_icon != 0:
                            middle.label(text=display_text, icon_value=material_icon)
                        else:
                            const_icon = get_icon("constant_mat_icon")
                            if const_icon:
                                middle.label(text=display_text, icon_value=const_icon)
                            else:
                                middle.label(text=display_text, icon='MATERIAL')

                    # Toggle navigation button for constant materials
                    if item['type'] == 'constant_material':
                        right_side = row.row(align=True)
                        right_side.alignment = 'RIGHT'
                        is_nav = item.get('is_nav_point', False)
                        nav_icon_val = get_icon("nav_point_icon") if is_nav else get_icon("constant_mat_icon")
                        if nav_icon_val:
                            nav_op = right_side.operator("list.toggle_navigation_point",
                                                         text="", icon_value=nav_icon_val, emboss=False)
                        else:
                            fallback = 'PIVOT_ACTIVE' if is_nav else 'PIVOT_CURSOR'
                            nav_op = right_side.operator("list.toggle_navigation_point",
                                                         text="", icon=fallback, emboss=False)
                        nav_op.material_name = item['name']

            # Navigation buttons
            if total_items > 0:
                nav_row = scroll_box.row(align=True)
                nav_row.alignment = 'CENTER'

                current_page = (current_scroll // ITEMS_PER_PAGE) + 1
                total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

                nav_row.enabled = current_scroll > 0
                up_op = nav_row.operator("list.vertical_scroll", text="", icon='TRIA_UP')
                up_op.direction = 'UP'

                nav_row.enabled = current_page > 1
                first_op = nav_row.operator("list.jump_to_page", text="<<", icon='REW')
                first_op.page_number = 1

                nav_row.enabled = current_page > 1
                prev_op = nav_row.operator("list.jump_to_page", text="<", icon='PREV_KEYFRAME')
                prev_op.page_number = current_page - 1

                indicator_row = nav_row.row()
                indicator_row.alignment = 'CENTER'
                indicator_row.enabled = True
                indicator_row.label(text=f"[{current_page}/{total_pages}]")

                nav_row.enabled = current_page < total_pages
                next_op = nav_row.operator("list.jump_to_page", text=">", icon='NEXT_KEYFRAME')
                next_op.page_number = current_page + 1

                nav_row.enabled = current_page < total_pages
                last_op = nav_row.operator("list.jump_to_page", text=">>", icon='FF')
                last_op.page_number = total_pages

                nav_row.enabled = current_scroll < max_scroll
                down_op = nav_row.operator("list.vertical_scroll", text="", icon='TRIA_DOWN')
                down_op.direction = 'DOWN'

                nav_row.enabled = True
        else:
            message_row = list_box.row()
            message_row.alignment = 'CENTER'

            if display_counts["total"] == 0:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    if not has_vertex_groups and not has_detected_blocks:
                        message = "No blocks detected. Run 'Navigate' first."
                    elif not has_vertex_groups and has_detected_blocks:
                        message = "No vertex groups created yet. Click 'Generate'."
                    else:
                        if not scene.list_filter_show_qb and not scene.list_filter_show_tb:
                            message = "Both QB and TB filters are off"
                        else:
                            message = "No vertex groups found with current filters."
                else:
                    if not has_constant_materials and not has_detected_blocks:
                        message = "No blocks detected. Run 'Navigate' first."
                    elif not has_constant_materials and has_detected_blocks:
                        message = "No constant materials assigned yet. Click 'Assign'."
                    else:
                        if not scene.list_filter_cm_qb and not scene.list_filter_cm_tb:
                            message = "Both QB and TB filters are off"
                        else:
                            message = "No constant materials found with current filters."
            else:
                if scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_material_filter_cm:
                    message = f"No items match material filter: {scene.list_material_filter_cm}"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_navigation_filter != 'ALL':
                    if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                        message = "No navigation points found with current filters"
                    else:
                        message = "No constant materials found with current filters"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
                    message = f"No items match group filter: {scene.list_active_group}"
                elif scene.list_display_type == 'VERTEX_GROUPS' and scene.list_issue_filter != 'ALL':
                    message = f"No items match issue filter: {scene.list_issue_filter}"
                else:
                    message = "No items match current search"

            message_row.label(text=message, icon='INFO')