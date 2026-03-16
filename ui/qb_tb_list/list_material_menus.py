"""
Material Selection Menus for Quadblock/Triblock List
Menus for selecting materials and constant materials
Now includes Vertex Group selection menu
Now with separate material filters for each display mode
"""

import bpy
from bpy.props import StringProperty

from .list_helpers import get_block_material_name


class LIST_MT_MaterialFilterMenu(bpy.types.Menu):
    """Menu for selecting materials from current list only with material image icons
    Now with separate filters for each display mode"""
    bl_label = "Select Material"
    
    def draw(self, layout):
        layout = self.layout
        scene = bpy.context.scene
        obj = bpy.context.edit_object
        
        # Determine which filter to show based on current display mode
        if scene.list_display_type == 'VERTEX_GROUPS':
            current_filter = scene.list_material_filter_vg
            menu_title = "Filter by Material (Vertex Groups)"
        else:  # CONSTANT_MATERIALS
            current_filter = scene.list_material_filter_cm
            menu_title = "Filter by Material (Constant Materials)"
        
        # Option to clear the filter
        op = layout.operator("list.set_material_filter", text="All", icon='MATERIAL')
        op.material_name = ""
        
        layout.separator()
        
        # Get materials from current items
        if obj and scene.list_display_type in ['VERTEX_GROUPS', 'CONSTANT_MATERIALS']:
            materials = set()
            
            # Get display items based on current filters
            display_items = []
            
            if scene.list_display_type == 'VERTEX_GROUPS':
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
                        except ValueError:
                            continue
            
            elif scene.list_display_type == 'CONSTANT_MATERIALS':
                if "constant_materials" in obj and obj["constant_materials"]:
                    constant_materials = obj["constant_materials"]
                    for mat_name, info in constant_materials.items():
                        block_type = info.get("block_type", "")
                        block_id = info.get("block_id", 0)
                        
                        if (block_type == "quadblock" and scene.list_filter_cm_qb) or \
                           (block_type == "triblock" and scene.list_filter_cm_tb):
                            
                            display_items.append({
                                'type': 'constant_material',
                                'name': mat_name,
                                'block_type': block_type,
                                'block_id': block_id,
                                'original_material': info.get("original_material", "Unknown"),
                                'data': info
                            })
            
            # Get materials from display items
            for item in display_items:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    material_name = get_block_material_name(obj, item['block_type'], item['block_id'])
                    if material_name:
                        materials.add(material_name)
                elif scene.list_display_type == 'CONSTANT_MATERIALS':
                    # In constant materials, the item name is the material name
                    materials.add(item['name'])
            
            # Show materials in menu with icons
            for mat in sorted(materials):
                if mat:  # Skip empty strings
                    # Get the material object
                    material_obj = None
                    if mat in bpy.data.materials:
                        material_obj = bpy.data.materials[mat]
                    
                    # Get icon for this material
                    icon_id = 0  # Default
                    if material_obj and material_obj.use_nodes:
                        for node in material_obj.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                image = node.image
                                if not hasattr(image, 'preview') or not image.preview:
                                    image.preview_ensure()
                                
                                if hasattr(image, 'preview') and image.preview:
                                    icon_id = image.preview.icon_id
                                    break
                    
                    # Create operator with icon
                    op = layout.operator("list.set_material_filter", text=mat, icon_value=icon_id)
                    op.material_name = mat


class LIST_MT_VertexGroupMenu(bpy.types.Menu):
    """Menu for selecting vertex groups directly (dropdown style)"""
    bl_label = "Select Vertex Group"
    
    def draw(self, layout):
        layout = self.layout
        scene = bpy.context.scene
        obj = bpy.context.edit_object
        
        if not obj:
            return
        
        # Get vertex groups filtered by current display settings
        vertex_groups = []
        for vg in obj.vertex_groups:
            vg_name = vg.name
            if vg_name.startswith("QB_") and scene.list_filter_show_qb:
                vertex_groups.append(vg_name)
            elif vg_name.startswith("TB_") and scene.list_filter_show_tb:
                vertex_groups.append(vg_name)
        
        # Sort vertex groups (numerically by ID when possible)
        def sort_key(vg_name):
            try:
                # Extract number from QB_XXX or TB_XXX
                return (vg_name[:2], int(vg_name[3:]))
            except ValueError:
                return (vg_name[:2], vg_name)
        
        vertex_groups.sort(key=sort_key)
        
        # Add to menu - use existing operator without dialog
        for vg_name in vertex_groups:
            # Use the existing operator but pass the group name directly
            op = layout.operator("list.select_block_by_vertex_group", text=vg_name)
            op.vertex_group_name = vg_name


classes = [
    LIST_MT_MaterialFilterMenu,
    LIST_MT_VertexGroupMenu, 
]