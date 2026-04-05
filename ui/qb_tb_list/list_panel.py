"""
Quadblock/Triblock List Panel - Main UI
Main panel class and custom list drawing for the block list system.

Provides the main UI panel with scrollable list, search, sorting,
material filtering, issue filtering (vertex groups), navigation point
filtering (constant materials), pagination, and multi-selection.
"""

import bpy
from bpy.types import Panel

from .list_helpers import get_material_image_icon, get_block_material_name


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

        if not is_edit_mode:
            layout.label(text="Enter Edit Mode to use tools", icon='ERROR')
            return

        if not obj:
            layout.label(text="Select an object in Edit Mode", icon='ERROR')
            return

        # Create a compact column without spacing between rows
        main_col = layout.column(align=True)

        # CALCULATE AND SHOW COUNT FIRST

        display_items = []
        display_counts = {"qb": 0, "tb": 0, "total": 0}
        nav_point_count = 0  # Count of navigation points

        if scene.list_display_type == 'VERTEX_GROUPS':
            # VERTEX GROUPS DISPLAY
            for vg in obj.vertex_groups:
                vg_name = vg.name

                if vg_name.startswith("QB_") and scene.list_filter_show_qb:
                    try:
                        block_id = int(vg_name[3:])
                        display_items.append({
                            'type': 'vertex_group',
                            'name': vg_name,
                            'block_type': 'quadblock',
                            'block_id': block_id,
                            'data': vg
                        })
                        display_counts["qb"] += 1
                        display_counts["total"] += 1
                    except ValueError:
                        continue

                elif vg_name.startswith("TB_") and scene.list_filter_show_tb:
                    try:
                        block_id = int(vg_name[3:])
                        display_items.append({
                            'type': 'vertex_group',
                            'name': vg_name,
                            'block_type': 'triblock',
                            'block_id': block_id,
                            'data': vg
                        })
                        display_counts["tb"] += 1
                        display_counts["total"] += 1
                    except ValueError:
                        continue

            # Show vertex groups count ABOVE the mode selector
            count_row = main_col.row()
            count_row.label(text=f"Vertex Groups - QB: {display_counts['qb']} | TB: {display_counts['tb']} | Total: {display_counts['total']}")

        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            # CONSTANT MATERIALS DISPLAY
            if "constant_materials" in obj and obj["constant_materials"]:
                constant_materials = obj["constant_materials"]

                for mat_name, info in constant_materials.items():
                    block_type = info.get("block_type", "")
                    block_id = info.get("block_id", 0)
                    is_nav_point = info.get("is_navigation_point", False)

                    if (block_type == "quadblock" and scene.list_filter_cm_qb) or \
                       (block_type == "triblock" and scene.list_filter_cm_tb):

                        display_items.append({
                            'type': 'constant_material',
                            'name': mat_name,
                            'block_type': block_type,
                            'block_id': block_id,
                            'original_material': info.get("original_material", "Unknown"),
                            'is_nav_point': is_nav_point,
                            'data': info
                        })

                        if block_type == "quadblock":
                            display_counts["qb"] += 1
                        else:
                            display_counts["tb"] += 1
                        display_counts["total"] += 1

                        if is_nav_point:
                            nav_point_count += 1

            # Show constant materials count ABOVE the mode selector
            count_row = main_col.row()
            if "constant_materials" in obj and obj["constant_materials"]:
                count_text = f"Constant Materials - QB: {display_counts['qb']} | TB: {display_counts['tb']} | Total: {display_counts['total']}"
                if nav_point_count > 0:
                    count_text += f" | Nav Points: {nav_point_count}"
                count_row.label(text=count_text)
            else:
                count_row.label(text="No constant materials assigned to this object", icon='INFO')

        # DISPLAY MODE SELECTION

        mode_row = main_col.row()
        mode_row.prop(scene, "list_display_type", expand=True)

        # Display based on selected type
        if scene.list_display_type == 'VERTEX_GROUPS':
            # VERTEX GROUPS DISPLAY
            has_block_vertex_groups = any(vg.name.startswith(("QB_", "TB_")) for vg in obj.vertex_groups)
            has_detected_blocks = ("quadblock_centers" in obj and obj["quadblock_centers"]) or \
                                 ("triblock_faces" in obj and obj["triblock_faces"])

            # ACTION BUTTONS - Only show if there are vertex groups or blocks detected
            if has_detected_blocks or has_block_vertex_groups:
                # First row: [Create Vertex Groups][Clear Group]
                row1 = main_col.row(align=True)

                # Always show Create Vertex Groups if blocks are detected
                if has_detected_blocks:
                    row1.operator("list.create_block_vertex_groups",
                               text="Vertex Groups",
                               icon='GROUP_VERTEX')

                # Only show Clear Groups if vertex groups exist
                if has_block_vertex_groups:
                    row1.operator("list.clear_block_vertex_groups",
                               text="Clear Group",
                               icon='TRASH')

                # Second row: [Select Group][Select in List]
                row2 = main_col.row(align=True)

                # Direct dropdown menu for selecting vertex groups
                if has_block_vertex_groups:
                    row2.menu("LIST_MT_VertexGroupMenu", text="Select Group", icon='DOWNARROW_HLT')

                # SELECT IN LIST BUTTON - Only show if vertex groups exist
                if has_block_vertex_groups:
                    row2.operator("list.select_list_from_block",
                               text="Select in List",
                               icon='FILE_REFRESH')

            # ALWAYS draw the list (even if empty, so filters are visible)
            self.draw_custom_list(main_col, context, obj, display_items, display_counts,
                                 has_vertex_groups=has_block_vertex_groups,
                                 has_detected_blocks=has_detected_blocks)

        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            # CONSTANT MATERIALS DISPLAY
            has_constant_materials = "constant_materials" in obj and obj["constant_materials"]
            has_detected_blocks = ("quadblock_centers" in obj and obj["quadblock_centers"]) or \
                                 ("triblock_faces" in obj and obj["triblock_faces"])

            # 2x2 BUTTON LAYOUT
            # ROW 1: [Assign Constant][Clear Constant]
            row1 = main_col.row(align=True)

            # Assign Constant button - show if blocks are detected
            if has_detected_blocks:
                row1.operator("list.assign_constant_material",
                            text="Assign Constant",
                            icon='MATERIAL')

            # Clear Constant button - show if constant materials exist
            if has_constant_materials:
                row1.operator("list.clear_constant_material",
                            text="Clear Constant",
                            icon='TRASH')

            # ROW 2: [Select Group][Select in List]
            row2 = main_col.row(align=True)

            # Select Group menu
            if has_constant_materials:
                menu_text = scene.list_active_group if scene.list_active_group else "Select Group"
                row2.menu("LIST_MT_ConstantMaterialGroupMenu", text=menu_text, icon='DOWNARROW_HLT')

            # SELECT IN LIST BUTTON
            if has_constant_materials:
                row2.operator("list.select_list_from_block",
                            text="Select in List",
                            icon='FILE_REFRESH')

            # ALWAYS draw the list (even if empty, so filters are visible)
            self.draw_custom_list(main_col, context, obj, display_items, display_counts,
                                 has_constant_materials=has_constant_materials,
                                 has_detected_blocks=has_detected_blocks,
                                 nav_point_count=nav_point_count)

    def draw_custom_list(self, layout, context, obj, items, display_counts,
                        has_vertex_groups=False, has_constant_materials=False,
                        has_detected_blocks=False, nav_point_count=0):
        """Draw a custom scrollable list with search, sort, material filter, and vertical scrollbar,
        Search bar at top, then filter dropdowns, then action buttons in a single row,
        then list, then pagination at bottom."""
        scene = context.scene
        search_text = scene.list_search_text.lower()

        # USE THE CORRECT MATERIAL FILTER BASED ON DISPLAY MODE
        if scene.list_display_type == 'VERTEX_GROUPS':
            material_filter = scene.list_material_filter_vg
            issue_filter = scene.list_issue_filter   # issue filter
        else:  # CONSTANT_MATERIALS
            material_filter = scene.list_material_filter_cm
            issue_filter = None   # not used in constant materials

        navigation_filter = scene.list_navigation_filter if scene.list_display_type == 'CONSTANT_MATERIALS' else 'ALL'

        # Get stored issues for vertex groups (if any)
        issues_dict = {}
        if scene.list_display_type == 'VERTEX_GROUPS' and "vertex_group_issues" in obj:
            issues_dict = dict(obj["vertex_group_issues"])

        # Apply search and filters
        filtered_items = []
        for item in items:
            # Skip items based on material filter
            if material_filter:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    # For vertex groups, check the block's material
                    block_material = get_block_material_name(obj, item['block_type'], item['block_id'])
                    if block_material != material_filter:
                        continue
                elif scene.list_display_type == 'CONSTANT_MATERIALS':
                    # For constant materials, check the material name directly
                    if item['name'] != material_filter:
                        continue

            # Apply issue filter (only for vertex groups)
            if scene.list_display_type == 'VERTEX_GROUPS' and issue_filter != 'ALL':
                item_issues = issues_dict.get(item['name'], [])
                # Determine if item should be shown based on filter
                if issue_filter == 'VALID':
                    # Valid means has 'quadblock' or 'triblock' and no other issues
                    if not ('quadblock' in item_issues or 'triblock' in item_issues):
                        # Not even a valid block type
                        show = False
                    else:
                        # Check for any issue besides the type
                        other_issues = [i for i in item_issues if i not in ('quadblock', 'triblock')]
                        show = len(other_issues) == 0
                elif issue_filter == 'NO_ISSUES':
                    # No issues at all (including geometry invalid)
                    show = len(item_issues) == 0
                elif issue_filter == 'INVALID_GEOMETRY':
                    show = 'invalid_geometry' in item_issues
                elif issue_filter == 'INVALID_UVS':
                    show = 'invalid_uvs' in item_issues
                elif issue_filter == 'INVALID_TRIBLOCK_UVS':
                    show = 'invalid_triblock_uvs' in item_issues
                elif issue_filter == 'DEGENERATED_UVS':
                    show = 'degenerated_uvs' in item_issues
                else:
                    show = True
                if not show:
                    continue

            # Apply navigation point filter (only for constant materials)
            if scene.list_display_type == 'CONSTANT_MATERIALS':
                is_nav_point = item.get('is_nav_point', False)
                if navigation_filter == 'NAVIGATION_POINTS' and not is_nav_point:
                    continue
                elif navigation_filter == 'NON_NAVIGATION' and is_nav_point:
                    continue

            # Apply text search filter
            if search_text:
                # Search in item name
                if search_text in item['name'].lower():
                    filtered_items.append(item)
                # Search in block type (QB/TB)
                elif search_text in item['block_type'].lower():
                    filtered_items.append(item)
                # Search in block ID
                elif search_text in str(item['block_id']):
                    filtered_items.append(item)
                # Search in material name (for vertex groups)
                elif scene.list_display_type == 'VERTEX_GROUPS':
                    block_material = get_block_material_name(obj, item['block_type'], item['block_id'])
                    if block_material and search_text in block_material.lower():
                        filtered_items.append(item)
                # Search in original material (for constant materials)
                elif scene.list_display_type == 'CONSTANT_MATERIALS':
                    if 'original_material' in item and search_text in item['original_material'].lower():
                        filtered_items.append(item)
            else:
                filtered_items.append(item)

        # Apply group filter (only for constant materials)
        active_group = scene.list_active_group
        if scene.list_display_type == 'CONSTANT_MATERIALS' and active_group:
            # Load groups from scene
            if "constant_material_groups" in scene:
                try:
                    import json
                    groups = json.loads(scene["constant_material_groups"])
                    if active_group in groups:
                        group_materials = set(groups[active_group])
                        # Filter items by group
                        filtered_by_group = []
                        for item in filtered_items:
                            if item['name'] in group_materials:
                                filtered_by_group.append(item)
                        filtered_items = filtered_by_group
                except:
                    pass

        # Apply compound sorting (first by type, then by name)
        reverse_type = (scene.list_sort_type_direction == 'DESC')
        reverse_name = (scene.list_sort_name_direction == 'DESC')

        def sort_key(item):
            # Priority 1: Block type (quadblock/triblock)
            type_order = 0 if item['block_type'] == 'quadblock' else 1
            if reverse_type:
                type_order = 1 - type_order  # Invert if descending

            # Priority 2: Navigation point status (navigation points first) - only for constant mats
            nav_order = 0 if item.get('is_nav_point', False) else 1
            if reverse_name:
                nav_order = 1 - nav_order  # Invert if descending

            # Priority 3: Name
            name_key = item['name'].lower()

            # Priority 4: Block ID (as tiebreaker)
            id_key = item['block_id']

            return (type_order, nav_order, name_key, id_key)

        # Sort items
        filtered_items.sort(key=sort_key)

        # If name sort is descending, reverse the final order
        if reverse_name:
            # Create a copy to avoid modifying the original
            filtered_items = list(reversed(filtered_items))

        total_items = len(filtered_items)

        # Calculate visible range based on scroll position
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total_items - ITEMS_PER_PAGE)

        # Ensure vertical scroll position is valid
        current_scroll = scene.list_vertical_scroll
        if current_scroll > max_scroll:
            current_scroll = max_scroll

        # Get visible items
        start_idx = current_scroll
        end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
        visible_items = filtered_items[start_idx:end_idx]

        # Create ITEM LIST BOX (main container)
        item_list_box = layout.box()

        # 1. SEARCH BAR (at the top) 
        search_row = item_list_box.row(align=True)
        search_row.prop(scene, "list_search_text", text="", icon='VIEWZOOM')

        # 2. FILTER DROPDOWNS (middle) 
        if scene.list_display_type == 'VERTEX_GROUPS':
            filter_row = item_list_box.row()
            filter_row.alignment = 'EXPAND'

            split = filter_row.split(factor=0.5)

            left_col = split.row()
            left_col.alignment = 'EXPAND'
            material_text = scene.list_material_filter_vg if scene.list_material_filter_vg else "All Materials"
            left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')

            right_col = split.row()
            right_col.alignment = 'EXPAND'

            issue_text = {
                'ALL': "All",
                'VALID': "Valid",
                'INVALID_GEOMETRY': "Invalid Geo",
                'INVALID_UVS': "Invalid UVs",
                'INVALID_TRIBLOCK_UVS': "Invalid Triblock UVs",
                'DEGENERATED_UVS': "Degenerated UVs",
                'NO_ISSUES': "No Issues"
            }.get(scene.list_issue_filter, "All")

            right_col.menu("LIST_MT_IssueFilterMenu", text=issue_text, icon='ERROR')

        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            menus_row = item_list_box.row()
            menus_row.alignment = 'EXPAND'

            split = menus_row.split(factor=0.5)

            left_col = split.row()
            left_col.alignment = 'EXPAND'
            material_text = scene.list_material_filter_cm if scene.list_material_filter_cm else "All Materials"
            left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')

            right_col = split.row()
            right_col.alignment = 'EXPAND'
            # nav assignments 
            nav_text = "All"
            if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                nav_text = "Navigation"
            elif scene.list_navigation_filter == 'NON_NAVIGATION':
                nav_text = "Constant"

            right_col.menu("LIST_MT_NavigationFilterMenu", text=nav_text, icon='PIVOT_CURSOR')

        # 3. ACTION BUTTONS (single row below filters, no extra box) 
        action_row = item_list_box.row(align=True)

        if scene.list_display_type == 'VERTEX_GROUPS':
            # All VG action buttons in one row - unified order
            action_row.prop(scene, "list_filter_show_qb", text="", icon='VERTEXSEL', toggle=True)
            action_row.prop(scene, "list_filter_show_tb", text="", icon='FACESEL', toggle=True)
            action_row.operator("list.check_all", text="", icon='CHECKBOX_HLT')
            action_row.operator("list.clear_checks_in_current_list", text="", icon='CHECKBOX_DEHLT')
            action_row.operator("list.toggle_sort_type", text="", icon='VERTEXSEL' if scene.list_sort_type_direction == 'ASC' else 'FACESEL')
            action_row.operator("list.toggle_sort_name", text="", icon='SORTALPHA')

        else:  # CONSTANT_MATERIALS
            # Constant materials action buttons - unified order with VG
            action_row.prop(scene, "list_filter_cm_qb", text="", icon='VERTEXSEL', toggle=True)
            action_row.prop(scene, "list_filter_cm_tb", text="", icon='FACESEL', toggle=True)
            action_row.operator("list.check_all", text="", icon='CHECKBOX_HLT')
            action_row.operator("list.clear_checks_in_current_list", text="", icon='CHECKBOX_DEHLT')
            action_row.operator("list.toggle_sort_type", text="", icon='VERTEXSEL' if scene.list_sort_type_direction == 'ASC' else 'FACESEL')
            action_row.operator("list.toggle_sort_name", text="", icon='SORTALPHA')
            action_row.operator("list.update_derived_from_checked", text="", icon='FILE_REFRESH')
            action_row.operator("list.duplicate_selection", text="", icon='DUPLICATE')

            # Navigation toggle button (dynamic icon)
            if "constant_materials" in obj:
                constant_materials_dict = dict(obj["constant_materials"])
                all_are_nav = True
                any_are_nav = False
                visible_count = 0
                for mat_name, info in constant_materials_dict.items():
                    block_type = info.get("block_type", "")
                    if (block_type == "quadblock" and not scene.list_filter_cm_qb) or \
                       (block_type == "triblock" and not scene.list_filter_cm_tb):
                        continue
                    if scene.list_navigation_filter != 'ALL':
                        is_nav_point = info.get("is_navigation_point", False)
                        if scene.list_navigation_filter == 'NAVIGATION_POINTS' and not is_nav_point:
                            continue
                        elif scene.list_navigation_filter == 'NON_NAVIGATION' and is_nav_point:
                            continue
                    visible_count += 1
                    is_nav = info.get("is_navigation_point", False)
                    if is_nav:
                        any_are_nav = True
                    else:
                        all_are_nav = False
                if visible_count > 0:
                    if all_are_nav:
                        nav_icon = 'PIVOT_CURSOR'
                    elif not any_are_nav:
                        nav_icon = 'PIVOT_ACTIVE'
                    else:
                        nav_icon = 'PIVOT_BOUNDBOX'
                    action_row.operator("list.toggle_all_navigation_points", text="", icon=nav_icon)

            # Add to group button
            add_op = action_row.operator("list.add_to_group", text="", icon='ADD')
            add_op.group_name = scene.list_active_group if scene.list_active_group else ""

            # Remove from group button (also in same row if group is active)
            if scene.list_active_group:
                remove_op = action_row.operator("list.remove_from_group", text="", icon='REMOVE')
                remove_op.group_name = scene.list_active_group

        # 4. SCROLL BOX (contains position text, items, and pagination)
        if visible_items or total_items > 0:
            scroll_box = item_list_box.box()

            # Position text at the top of the scroll box
            if total_items > 0:
                pos_row = scroll_box.row()
                pos_row.alignment = 'CENTER'
                pos_text = f"items {start_idx+1}-{end_idx} of {total_items}"
                pos_row.label(text=pos_text)

            # Items list
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
                                                 text="",
                                                 icon=checkbox_icon)
                    toggle_op.item_name = item['name']

                    icon = 'VERTEXSEL' if item['block_type'] == 'quadblock' else 'FACESEL'
                    left_side.label(text="", icon=icon)

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

                        if item['name'] in issues_dict:
                            item_issues = issues_dict[item['name']]
                            if item_issues:
                                non_type_issues = [iss for iss in item_issues if iss not in ('quadblock', 'triblock')]
                                if non_type_issues:
                                    right_icon = row.row(align=True)
                                    right_icon.alignment = 'RIGHT'
                                    op = right_icon.operator("list.show_vertex_group_issues",
                                                             text="",
                                                             icon='ERROR',
                                                             emboss=False)
                                    op.group_name = item['name']

                    elif item['type'] == 'constant_material':
                        material_name = item['name']
                        material_icon = get_material_image_icon(material_name)
                        display_text = f"{material_name}"
                        if isinstance(material_icon, int) and material_icon != 0:
                            middle.label(text=display_text, icon_value=material_icon)
                        else:
                            middle.label(text=display_text, icon='MATERIAL')

                    if item['type'] == 'constant_material':
                        right_side = row.row(align=True)
                        right_side.alignment = 'RIGHT'

                        nav_icon = 'PIVOT_ACTIVE' if item.get('is_nav_point', False) else 'PIVOT_CURSOR'
                        nav_op = right_side.operator("list.toggle_navigation_point",
                                                   text="",
                                                   icon=nav_icon,
                                                   emboss=False)
                        nav_op.material_name = item['name']

            # Pagination controls inside the scroll box
            if total_items > 0:
                # Pagination buttons
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
            # Show message when no items found (and no items to display)
            message_row = item_list_box.row()
            message_row.alignment = 'CENTER'

            if display_counts["total"] == 0:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    if not has_vertex_groups and not has_detected_blocks:
                        message = "No blocks detected. Run 'Navigate' first."
                    elif not has_vertex_groups and has_detected_blocks:
                        message = "No vertex groups created yet. Click 'Vertex Groups' to create them."
                    else:
                        if not scene.list_filter_show_qb and not scene.list_filter_show_tb:
                            message = "Both QB and TB filters are off"
                        else:
                            message = "No vertex groups found with current filters."
                else:  # CONSTANT_MATERIALS
                    if not has_constant_materials and not has_detected_blocks:
                        message = "No blocks detected. Run 'Navigate' first."
                    elif not has_constant_materials and has_detected_blocks:
                        message = "No constant materials assigned yet. Click 'Assign Constant' to assign one."
                    else:
                        if not scene.list_filter_cm_qb and not scene.list_filter_cm_tb:
                            message = "Both QB and TB filters are off"
                        else:
                            message = "No constant materials found with current filters."
            else:
                if material_filter:
                    message = f"No items match material filter: {material_filter}"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_navigation_filter != 'ALL':
                    if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                        message = "No navigation points found with current filters"
                    else:
                        message = "No constant materials found with current filters"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
                    if "constant_material_groups" in scene:
                        try:
                            import json
                            groups = json.loads(scene["constant_material_groups"])
                            if scene.list_active_group in groups and not groups[scene.list_active_group]:
                                message = f"Group '{scene.list_active_group}' is empty"
                            else:
                                message = f"No items match group filter: {scene.list_active_group}"
                        except:
                            message = f"No items match group filter: {scene.list_active_group}"
                    else:
                        message = f"No items match group filter: {scene.list_active_group}"
                elif scene.list_display_type == 'VERTEX_GROUPS' and issue_filter != 'ALL':
                    message = f"No items match issue filter: {issue_filter}"
                else:
                    message = "No items match current search"

            message_row.label(text=message, icon='INFO')