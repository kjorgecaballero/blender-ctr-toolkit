"""
Material Selection Menus for Quadblock/Triblock List
Issue Filter Menu with individual operators.
"""

import bpy
from bpy.props import StringProperty
from .list_helpers import get_block_material_name


class LIST_MT_MaterialFilterMenu(bpy.types.Menu):
    bl_label = "Select Material"

    def draw(self, layout):
        layout = self.layout
        scene = bpy.context.scene
        obj = bpy.context.edit_object

        if scene.list_display_type == 'VERTEX_GROUPS':
            current_filter = scene.list_material_filter_vg
            menu_title = "Filter by Material (Vertex Groups)"
        else:
            current_filter = scene.list_material_filter_cm
            menu_title = "Filter by Material (Const. Mat)"

        op = layout.operator("list.set_material_filter", text="All Materials", icon='MATERIAL')
        op.material_name = ""

        layout.separator()

        if obj and scene.list_display_type in ['VERTEX_GROUPS', 'CONSTANT_MATERIALS']:
            materials = set()
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

            for item in display_items:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    material_name = get_block_material_name(obj, item['block_type'], item['block_id'])
                    if material_name:
                        materials.add(material_name)
                else:
                    materials.add(item['name'])

            for mat in sorted(materials):
                if mat:
                    material_obj = bpy.data.materials.get(mat)
                    icon_id = 0
                    if material_obj and material_obj.use_nodes:
                        for node in material_obj.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                image = node.image
                                if not hasattr(image, 'preview') or not image.preview:
                                    image.preview_ensure()
                                if image.preview:
                                    icon_id = image.preview.icon_id
                                    break
                    op = layout.operator("list.set_material_filter", text=mat, icon_value=icon_id)
                    op.material_name = mat


class LIST_MT_VertexGroupMenu(bpy.types.Menu):
    bl_label = "Select Vertex Group"

    def draw(self, layout):
        layout = self.layout
        scene = bpy.context.scene
        obj = bpy.context.edit_object

        if not obj:
            return

        vertex_groups = []
        for vg in obj.vertex_groups:
            vg_name = vg.name
            if vg_name.startswith("QB_") and scene.list_filter_show_qb:
                vertex_groups.append(vg_name)
            elif vg_name.startswith("TB_") and scene.list_filter_show_tb:
                vertex_groups.append(vg_name)

        def sort_key(vg_name):
            try:
                return (vg_name[:2], int(vg_name[3:]))
            except ValueError:
                return (vg_name[:2], vg_name)

        vertex_groups.sort(key=sort_key)

        for vg_name in vertex_groups:
            op = layout.operator("list.select_block_by_vertex_group", text=vg_name)
            op.vertex_group_name = vg_name


class LIST_MT_IssueFilterMenu(bpy.types.Menu):
    bl_label = "Filter by Issue"

    def draw(self, layout):
        layout = self.layout
        scene = bpy.context.scene
        current = scene.list_issue_filter

        def draw_item(op_id, text, icon, filter_value):
            icon_disp = 'CHECKBOX_HLT' if current == filter_value else 'CHECKBOX_DEHLT'
            layout.operator(op_id, text=text, icon=icon_disp)

        draw_item("list.set_issue_filter_all", "All", 'FILTER', 'ALL')
        draw_item("list.set_issue_filter_valid", "Valid", 'CHECKBOX_HLT', 'VALID')
        draw_item("list.set_issue_filter_invalid", "Invalid", 'ERROR', 'INVALID')
        layout.separator()
        draw_item("list.set_issue_filter_invalid_geometry", "Invalid Geometry", 'ERROR', 'INVALID_GEOMETRY')
        draw_item("list.set_issue_filter_invalid_uvs", "Invalid UVs", 'UV', 'INVALID_UVS')
        draw_item("list.set_issue_filter_invalid_triblock_uvs", "Invalid Triblock UVs", 'MESH_CONE', 'INVALID_TRIBLOCK_UVS')
        draw_item("list.set_issue_filter_degenerated_uvs", "Degenerated UVs", 'GROUP_UVS', 'DEGENERATED_UVS')
        draw_item("list.set_issue_filter_missing_uvs", "Missing UVs", 'UV', 'MISSING_UVS')
        draw_item("list.set_issue_filter_out_of_range", "Out of Range", 'BOUNDS', 'OUT_OF_RANGE')
        draw_item("list.set_issue_filter_multiple_materials", "Multiple Materials", 'MATERIAL', 'MULTIPLE_MATERIALS')


classes = [
    LIST_MT_MaterialFilterMenu,
    LIST_MT_VertexGroupMenu,
    LIST_MT_IssueFilterMenu,
]