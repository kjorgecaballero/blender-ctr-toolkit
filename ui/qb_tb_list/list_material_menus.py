"""
Material Selection Menus for Quadblock/Triblock List
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
        else:
            current_filter = scene.list_material_filter_cm

        op = layout.operator("list.set_material_filter", text="All Materials", icon='MATERIAL')
        op.material_name = ""

        layout.separator()

        if not obj:
            return

        materials = set()

        if scene.list_display_type == 'VERTEX_GROUPS':
            for vg in obj.vertex_groups:
                vg_name = vg.name
                if vg_name.startswith("QB_") and scene.list_filter_show_qb:
                    try:
                        block_id = int(vg_name[3:])
                        material = get_block_material_name(obj, 'quadblock', block_id)
                        if material:
                            materials.add(material)
                    except ValueError:
                        continue
                elif vg_name.startswith("TB_") and scene.list_filter_show_tb:
                    try:
                        block_id = int(vg_name[3:])
                        material = get_block_material_name(obj, 'triblock', block_id)
                        if material:
                            materials.add(material)
                    except ValueError:
                        continue
        else:
            # CONSTANT_MATERIALS: read from material slots
            for slot in obj.material_slots:
                mat = slot.material
                if mat and mat.get("ctr_block_type") is not None:
                    materials.add(mat.name)

        for mat_name in sorted(materials):
            mat = bpy.data.materials.get(mat_name)
            icon_id = 0
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        if not hasattr(node.image, 'preview') or not node.image.preview:
                            node.image.preview_ensure()
                        if node.image.preview:
                            icon_id = node.image.preview.icon_id
                            break
            op = layout.operator("list.set_material_filter", text=mat_name, icon_value=icon_id)
            op.material_name = mat_name


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