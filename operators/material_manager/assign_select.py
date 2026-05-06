import bpy
import bmesh
from bpy.types import Operator


class MATERIAL_OT_AssignSelected(Operator):
    """Assign the selected material to selected faces (whole blocks if any face belongs to a block)"""
    bl_idname = "material.assign_selected"
    bl_label = "Assign"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            self.report({'ERROR'}, f"Material '{mat_name}' not found")
            return {'CANCELLED'}

        if "constant_materials" in obj and mat_name in obj["constant_materials"]:
            self.report({'ERROR'}, "Cannot assign constant/navigation material using this button. Use the 'Assign' button inside the Block List (Constant Materials mode) instead.")
            return {'CANCELLED'}

        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

        has_block_data = ("face_to_quadblock" in obj and "quadblock_faces_map" in obj) or \
                         ("face_to_triblock" in obj and "triblock_faces_map" in obj)

        if not has_block_data:
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if face.select:
                    face.material_index = mat_index
            bmesh.update_edit_mesh(obj.data)
            self.report({'INFO'}, f"Assigned {mat.name} to selected faces")
            return {'FINISHED'}

        bm = bmesh.from_edit_mesh(obj.data)
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        face_to_quad = obj.get("face_to_quadblock", {})
        face_to_tri = obj.get("face_to_triblock", {})
        quad_maps = obj.get("quadblock_faces_map", {})
        tri_maps = obj.get("triblock_faces_map", {})

        blocks_to_assign = set()
        individual_faces = set()

        for face in selected_faces:
            idx_str = str(face.index)
            if idx_str in face_to_quad:
                block_id = int(face_to_quad[idx_str])
                blocks_to_assign.add(('quadblock', block_id))
            elif idx_str in face_to_tri:
                block_id = int(face_to_tri[idx_str])
                blocks_to_assign.add(('triblock', block_id))
            else:
                individual_faces.add(face.index)

        faces_to_assign = set(individual_faces)
        for block_type, block_id in blocks_to_assign:
            if block_type == 'quadblock':
                block_faces = quad_maps.get(str(block_id), [])
            else:
                block_faces = tri_maps.get(str(block_id), [])
            faces_to_assign.update(block_faces)

        for face in bm.faces:
            if face.index in faces_to_assign:
                face.material_index = mat_index

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Assigned {mat.name} to {len(faces_to_assign)} faces ({len(blocks_to_assign)} blocks + {len(individual_faces)} standalone faces)")
        return {'FINISHED'}


class MATERIAL_OT_SelectByMaterial(Operator):
    """Select all faces using the selected material"""
    bl_idname = "material.select_by_material"
    bl_label = "Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            self.report({'WARNING'}, f"Material '{mat_name}' not used by object")
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.select = False
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = True
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected faces with {mat.name}")
        return {'FINISHED'}


class MATERIAL_OT_DeselectByMaterial(Operator):
    """Deselect all faces using the selected material"""
    bl_idname = "material.deselect_by_material"
    bl_label = "Deselect"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = False
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Deselected faces with {mat.name}")
        return {'FINISHED'}


classes = [MATERIAL_OT_AssignSelected, MATERIAL_OT_SelectByMaterial, MATERIAL_OT_DeselectByMaterial]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)