"""
Quadblock/Triblock List Panel - Main UI
Main panel class and custom list drawing for QB/TB Block List
Now with Navigation Points support
Now with intelligent toggle for all navigation points
Now with separate material filters for each display mode
Now with issue filter and validation button for vertex groups
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
            count_row = layout.row()
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
            count_row = layout.row()
            if "constant_materials" in obj and obj["constant_materials"]:
                count_text = f"Constant Materials - QB: {display_counts['qb']} | TB: {display_counts['tb']} | Total: {display_counts['total']}"
                if nav_point_count > 0:
                    count_text += f" | Nav Points: {nav_point_count}"
                count_row.label(text=count_text)
            else:
                count_row.label(text="No constant materials assigned to this object", icon='INFO')
        

        # DISPLAY MODE SELECTION

        mode_row = layout.row()
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
                row1 = layout.row(align=True)
                
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
                row2 = layout.row(align=True)
                
                # Direct dropdown menu for selecting vertex groups
                if has_block_vertex_groups:
                    row2.menu("LIST_MT_VertexGroupMenu", text="Select Group", icon='DOWNARROW_HLT')
                
                # SELECT IN LIST BUTTON - Only show if vertex groups exist
                if has_block_vertex_groups:
                    row2.operator("list.select_list_from_block", 
                               text="Select in List", 
                               icon='FILE_REFRESH')
            
            # ALWAYS draw the list (even if empty, so filters are visible)
            self.draw_custom_list(layout, context, obj, display_items, display_counts,
                                 has_vertex_groups=has_block_vertex_groups,
                                 has_detected_blocks=has_detected_blocks)
            
        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            # CONSTANT MATERIALS DISPLAY
            has_constant_materials = "constant_materials" in obj and obj["constant_materials"]
            has_detected_blocks = ("quadblock_centers" in obj and obj["quadblock_centers"]) or \
                                 ("triblock_faces" in obj and obj["triblock_faces"])
            

            # 2x2 BUTTON LAYOUT       
            # ROW 1: [Assign Constant][Clear Constant]
            row1 = layout.row(align=True)
            
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
            row2 = layout.row(align=True)
            
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
            self.draw_custom_list(layout, context, obj, display_items, display_counts,
                                 has_constant_materials=has_constant_materials,
                                 has_detected_blocks=has_detected_blocks,
                                 nav_point_count=nav_point_count)
    
    def draw_custom_list(self, layout, context, obj, items, display_counts,
                        has_vertex_groups=False, has_constant_materials=False,
                        has_detected_blocks=False, nav_point_count=0):
        """Draw a custom scrollable list with search, sort, material filter, and vertical scrollbar
        Now includes navigation point toggles, separate material filters for each display mode,
        and issue filter for vertex groups."""
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
        
        #  Get stored issues for vertex groups (if any)
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
        
        # If name sort is descending, we need to reverse the final order
        if reverse_name:
            # Create a copy to avoid modifying the original
            filtered_items = list(reversed(filtered_items))
        
        total_items = len(filtered_items)
        
        # Calculate visible range based on scroll position
        items_per_page = scene.list_items_per_page
        max_scroll = max(0, total_items - items_per_page)
        
        # Ensure vertical scroll position is valid
        current_scroll = scene.list_vertical_scroll
        if current_scroll > max_scroll:
            current_scroll = max_scroll
        
        # Get visible items
        start_idx = current_scroll
        end_idx = min(start_idx + items_per_page, total_items)
        visible_items = filtered_items[start_idx:end_idx]
        
        # Create ITEM LIST BOX (inside the main list_box)
        item_list_box = layout.box()
        

        # SEARCH ROW 

        search_row = item_list_box.row(align=True)
        search_row.prop(scene, "list_search_text", text="", icon='VIEWZOOM')
        

        # CONTROLS ROW 

        # ROW 1: FILTER ICONS 
        icons_row = item_list_box.row()
        icons_row.alignment = 'EXPAND'
        
        # Create a container for icons that will expand
        icons_container = icons_row.row(align=True)
        icons_container.alignment = 'EXPAND'
        
        # QB and TB filter buttons as icons
        if scene.list_display_type == 'VERTEX_GROUPS':
            icons_container.prop(scene, "list_filter_show_qb", text="", icon='VERTEXSEL', toggle=True)
            icons_container.prop(scene, "list_filter_show_tb", text="", icon='FACESEL', toggle=True)
        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            icons_container.prop(scene, "list_filter_cm_qb", text="", icon='VERTEXSEL', toggle=True)
            icons_container.prop(scene, "list_filter_cm_tb", text="", icon='FACESEL', toggle=True)
        
        # Check All button (icon only)
        icons_container.operator("list.check_all", text="", icon='CHECKBOX_HLT')
        
        # Clear All button (icon only)
        icons_container.operator("list.clear_checks_in_current_list", text="", icon='CHECKBOX_DEHLT')
        
        # Sort buttons
        name_icon = 'SORTALPHA'
        icons_container.operator("list.toggle_sort_name", text="", icon=name_icon)
        
        type_icon = 'VERTEXSEL' if scene.list_sort_type_direction == 'ASC' else 'FACESEL'
        icons_container.operator("list.toggle_sort_type", text="", icon=type_icon)
        
        # Navigation toggle button (only for constant materials)
        if scene.list_display_type == 'CONSTANT_MATERIALS':
            # Calculate the state to decide the icon
            if "constant_materials" in obj:
                constant_materials_dict = dict(obj["constant_materials"])
                
                all_are_nav = True
                any_are_nav = False
                visible_count = 0
                
                for mat_name, info in constant_materials_dict.items():
                    block_type = info.get("block_type", "")
                    
                    # Apply QB/TB filter
                    if (block_type == "quadblock" and not scene.list_filter_cm_qb) or \
                       (block_type == "triblock" and not scene.list_filter_cm_tb):
                        continue
                    
                    # Apply navigation filter if active
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
                        nav_icon = 'PIVOT_CURSOR'  # All are nav points, will unmark
                    elif not any_are_nav:
                        nav_icon = 'PIVOT_ACTIVE'  # None are nav points, will mark
                    else:
                        nav_icon = 'PIVOT_BOUNDBOX'  # Mixed, will toggle
                    
                    icons_container.operator("list.toggle_all_navigation_points", 
                                           text="", 
                                           icon=nav_icon)
        
        # Group management buttons (only for constant materials)
        if scene.list_display_type == 'CONSTANT_MATERIALS':
            # Add to group button (always shown)
            add_op = icons_container.operator("list.add_to_group", text="", icon='ADD')
            # If there's an active group, use it as default, otherwise empty string
            add_op.group_name = scene.list_active_group if scene.list_active_group else ""
            
            # Remove from group button (only shown when there's an active group)
            if scene.list_active_group:
                remove_op = icons_container.operator("list.remove_from_group", text="", icon='REMOVE')
                remove_op.group_name = scene.list_active_group
        

        # ROW 2: FILTER DROPDOWNS (Material and Issue for Vertex Groups; Navigation and Material for Constant Materials)

        if scene.list_display_type == 'VERTEX_GROUPS':
            # Row for two dropdowns: Material Filter and Issue Filter
            filter_row = item_list_box.row()
            filter_row.alignment = 'EXPAND'
            
            # Split into two columns
            split = filter_row.split(factor=0.5)
            
            # Left: Material Filter
            left_col = split.row()
            left_col.alignment = 'EXPAND'
            material_text = scene.list_material_filter_vg if scene.list_material_filter_vg else "All Materials"
            left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')
            
            # Right: Issue Filter
            right_col = split.row()
            right_col.alignment = 'EXPAND'
            
            # Determine display text for issue filter
            issue_text = {
                'ALL': "All",
                'VALID': "Valid",
                'INVALID_GEOMETRY': "Invalid Geo",
                'INVALID_UVS': "Invalid UVs",
                'INVALID_TRIBLOCK_UVS': "Invalid Triblock UVs",
                'DEGENERATED_UVS': "Degenerated UVs",
                'NO_ISSUES': "No Issues"
            }.get(scene.list_issue_filter, "All")
            
            # Create a menu for issue filter
            right_col.menu("LIST_MT_IssueFilterMenu", text=issue_text, icon='ERROR')
        
        elif scene.list_display_type == 'CONSTANT_MATERIALS':
            menus_row = item_list_box.row()
            menus_row.alignment = 'EXPAND'
            
            # Split row into two columns that expand properly
            split = menus_row.split(factor=0.5)
            
            # Left column: Material filter (moved from right to left)
            left_col = split.row()
            left_col.alignment = 'EXPAND'
            
            material_text = scene.list_material_filter_cm if scene.list_material_filter_cm else "All Materials"
            # Material filter with proper expansion
            left_col.menu("LIST_MT_MaterialFilterMenu", text=material_text, icon='MATERIAL')
            
            # Right column: Navigation filter
            right_col = split.row()
            right_col.alignment = 'EXPAND'
            
            nav_text = "All"
            if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                nav_text = "Nav Points"
            elif scene.list_navigation_filter == 'NON_NAVIGATION':
                nav_text = "Non-Nav"
            
            # Navigation filter with proper expansion
            right_col.menu("LIST_MT_NavigationFilterMenu", text=nav_text, icon='PIVOT_CURSOR')
        
        # POSITION AND PAGINATION CONTROLS 

        if total_items > 0:
            # Create a row for position info and items per page
            info_row = item_list_box.row()
            info_row.alignment = 'EXPAND'
            
            # Split into three sections
            split = info_row.split(factor=0.33)
            
            # Left: Position information
            left_col = split.row()
            left_col.alignment = 'LEFT'
            pos_text = f"{start_idx+1}-{end_idx} of {total_items}"
            left_col.label(text=pos_text)
            
            # Middle: Split for center content
            middle_split = split.split(factor=0.5)
            
            # Center left: Filter status indicators
            center_left = middle_split.row()
            center_left.alignment = 'CENTER'
            
            # Show navigation filter status if active
            if scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_navigation_filter != 'ALL':
                if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                    center_left.label(text="Nav Points", icon='PIVOT_CURSOR')
                else:
                    center_left.label(text="Non-Nav", icon='PIVOT_ACTIVE')
            
            # Center right: Group filter status if active
            center_right = middle_split.row()
            center_right.alignment = 'CENTER'
            
            if scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
                # Show count of materials in the active group
                if "constant_material_groups" in scene:
                    try:
                        import json
                        groups = json.loads(scene["constant_material_groups"])
                        if scene.list_active_group in groups:
                            group_size = len(groups[scene.list_active_group])
                            center_right.label(text=f"Group: {scene.list_active_group} ({group_size})", icon='GROUP')
                        else:
                            center_right.label(text=f"Group: {scene.list_active_group} (0)", icon='GROUP')
                    except:
                        center_right.label(text=f"Group: {scene.list_active_group}", icon='GROUP')
            
            # Right: Items per page control
            right_col = split.row()
            right_col.alignment = 'RIGHT'
            
            items_row = right_col.row(align=True)
            items_row.prop(scene, "list_items_per_page", text="")
        

        # ITEM LIST CONTENT 

        if visible_items:
            # Get current multi-selection state (if exists)
            multi_selected = {}
            if "multi_selected_items" in obj:
                # Convert IDPropertyGroup to dict
                multi_selected = dict(obj["multi_selected_items"])
            
            # Create a scrollable area for items
            scroll_box = item_list_box.box()
            
            for i, item in enumerate(visible_items):
                idx = start_idx + i
                
                row = scroll_box.row()
                row.alignment = 'EXPAND'
                
                # Left side: Checkbox and type icon
                left_side = row.row(align=True)
                left_side.alignment = 'LEFT'
                
                # Checkbox for multi-selection
                is_selected = item['name'] in multi_selected
                checkbox_icon = 'CHECKBOX_HLT' if is_selected else 'CHECKBOX_DEHLT'
                
                # Toggle selection operator
                toggle_op = left_side.operator("list.toggle_multi_selection", 
                                             text="", 
                                             icon=checkbox_icon)
                toggle_op.item_name = item['name']
                
                # Icon for block type (QB/TB) only - no text
                icon = 'VERTEXSEL' if item['block_type'] == 'quadblock' else 'FACESEL'
                left_side.label(text="", icon=icon)
                
                # Middle: Item name with material icon and possibly issue icon
                middle = row.row()
                middle.alignment = 'EXPAND'
                
                # Display block type prefix with material name
                if item['type'] == 'vertex_group':
                    # Get the block's material name
                    material_name = get_block_material_name(obj, item['block_type'], item['block_id'])
                    
                    if material_name:
                        # Format: QB/TB MaterialName_BlockID
                        block_prefix = "QB" if item['block_type'] == 'quadblock' else "TB"
                        display_text = f"{block_prefix}_{material_name}_{item['block_id']}"
                        
                        # Get the actual image icon from the material
                        material_icon = get_material_image_icon(material_name)
                        
                        # Display with material icon if available
                        if isinstance(material_icon, int) and material_icon != 0:
                            middle.label(text=display_text, icon_value=material_icon)
                        else:
                            middle.label(text=display_text, icon='MATERIAL')
                    else:
                        # If no material, show just the block ID with QB/TB prefix
                        block_prefix = "QB" if item['block_type'] == 'quadblock' else "TB"
                        middle.label(text=f"{block_prefix}_Block_{item['block_id']}", icon='MATERIAL')
                    
                    # Add issue indicator icon if this group has issues
                    if item['name'] in issues_dict:
                        item_issues = issues_dict[item['name']]
                        if item_issues:
                            # If there are any issues besides valid type, show error icon
                            non_type_issues = [iss for iss in item_issues if iss not in ('quadblock', 'triblock')]
                            if non_type_issues:
                                # Use a small icon at the end
                                right_icon = row.row(align=True)
                                right_icon.alignment = 'RIGHT'
                                right_icon.label(text="", icon='ERROR')
                            # Could also show specific icons for each issue, but we keep it simple
                    
                elif item['type'] == 'constant_material':
                    # Show only the constant material name (not QB/TB_ prefix)
                    material_name = item['name']
                    
                    # Get the actual image icon from the material
                    material_icon = get_material_image_icon(material_name)
                    
                    # Display with material icon if available
                    display_text = f"{material_name}"
                    if isinstance(material_icon, int) and material_icon != 0:
                        middle.label(text=display_text, icon_value=material_icon)
                    else:
                        middle.label(text=display_text, icon='MATERIAL')
                
                # Right side: Navigation point toggle (only for constant materials)
                if item['type'] == 'constant_material':
                    right_side = row.row(align=True)
                    right_side.alignment = 'RIGHT'
                    
                    nav_icon = 'PIVOT_ACTIVE' if item.get('is_nav_point', False) else 'PIVOT_CURSOR'
                    nav_op = right_side.operator("list.toggle_navigation_point", 
                                               text="", 
                                               icon=nav_icon, 
                                               emboss=False)
                    nav_op.material_name = item['name']
            

            # NAVIGATION CONTROLS 
 
            if total_items > 0:
                # Calculate how many pages there are
                current_page = (current_scroll // items_per_page) + 1
                total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
                
                # Create a box for navigation controls
                nav_box = item_list_box.box()
                nav_row = nav_box.row(align=True)
                nav_row.alignment = 'CENTER'
                
                # Up button
                nav_row.enabled = current_scroll > 0
                up_op = nav_row.operator("list.vertical_scroll", text="", icon='TRIA_UP')
                up_op.direction = 'UP'
                
                # First Page button
                nav_row.enabled = current_page > 1
                first_op = nav_row.operator("list.jump_to_page", text="<<", icon='REW')
                first_op.page_number = 1
                
                # Previous Page button
                nav_row.enabled = current_page > 1
                prev_op = nav_row.operator("list.jump_to_page", text="<", icon='PREV_KEYFRAME')
                prev_op.page_number = current_page - 1
                
                # Current Page indicator - separate row to avoid inheriting enabled state
                indicator_row = nav_row.row()
                indicator_row.alignment = 'CENTER'
                indicator_row.enabled = True
                indicator_row.label(text=f"[{current_page}/{total_pages}]")
                
                # Next Page button
                nav_row.enabled = current_page < total_pages
                next_op = nav_row.operator("list.jump_to_page", text=">", icon='NEXT_KEYFRAME')
                next_op.page_number = current_page + 1
                
                # Last Page button
                nav_row.enabled = current_page < total_pages
                last_op = nav_row.operator("list.jump_to_page", text=">>", icon='FF')
                last_op.page_number = total_pages
                
                # Down button
                nav_row.enabled = current_scroll < max_scroll
                down_op = nav_row.operator("list.vertical_scroll", text="", icon='TRIA_DOWN')
                down_op.direction = 'DOWN'
                
                # Reset enabled state to avoid affecting subsequent UI elements
                nav_row.enabled = True
        else:
            # Show message when no items found
            message_row = item_list_box.row()
            message_row.alignment = 'CENTER'
            
            if display_counts["total"] == 0:
                # No items at all (likely both filters are off or no data)
                if scene.list_display_type == 'VERTEX_GROUPS':
                    if not has_vertex_groups and not has_detected_blocks:
                        message = "No blocks detected. Run 'Navigate' first."
                    elif not has_vertex_groups and has_detected_blocks:
                        message = "No vertex groups created yet. Click 'Vertex Groups' to create them."
                    else:
                        # This case is when there are vertex groups but both QB and TB filters are off
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
                        # This case is when there are constant materials but both QB and TB filters are off
                        if not scene.list_filter_cm_qb and not scene.list_filter_cm_tb:
                            message = "Both QB and TB filters are off"
                        else:
                            message = "No constant materials found with current filters."
            else:
                # Items exist but filtered out by search or material filter
                if material_filter:
                    message = f"No items match material filter: {material_filter}"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_navigation_filter != 'ALL':
                    if scene.list_navigation_filter == 'NAVIGATION_POINTS':
                        message = "No navigation points found with current filters"
                    else:
                        message = "No non-navigation materials found with current filters"
                elif scene.list_display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
                    # Check if group exists but is empty
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