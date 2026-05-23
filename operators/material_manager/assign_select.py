import bpy
import bmesh
from bpy.types import Operator
from bpy.props import EnumProperty


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
    """Select faces using the selected material family (popup to choose scope)"""
    bl_idname = "material.select_by_material"
    bl_label = "Select Materials"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Selection Scope",
        description="Which materials to select",
        items=[
            ('FULL', "Full Family", "Base + all constants (including nav points)"),
            ('CONSTANTS', "Constants Only", "All constant materials (excluding base and nav points)"),
            ('NAV', "Nav Points Only", "Only navigation point constants"),
        ],
        default='FULL'
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "scope", expand=True)

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        const_dict = obj.get("constant_materials", {})

        # Build the set of material names to select based on scope
        material_names = set()
        if mat_name in const_dict:
            # Selected is a constant
            base_name = const_dict[mat_name].get("original_material")
            if base_name:
                if self.scope == 'FULL':
                    material_names.add(base_name)
                # Always include constants matching the scope
                for cname, cinfo in const_dict.items():
                    if cinfo.get("original_material") == base_name:
                        is_nav = cinfo.get("is_navigation_point", False)
                        if self.scope == 'FULL':
                            material_names.add(cname)
                        elif self.scope == 'CONSTANTS' and not is_nav:
                            material_names.add(cname)
                        elif self.scope == 'NAV' and is_nav:
                            material_names.add(cname)
        else:
            # Selected is a normal material (possibly a base)
            base_name = mat_name
            has_constants = any(cinfo.get("original_material") == base_name for cinfo in const_dict.values())
            if has_constants:
                if self.scope == 'FULL':
                    material_names.add(base_name)
                for cname, cinfo in const_dict.items():
                    if cinfo.get("original_material") == base_name:
                        is_nav = cinfo.get("is_navigation_point", False)
                        if self.scope == 'FULL':
                            material_names.add(cname)
                        elif self.scope == 'CONSTANTS' and not is_nav:
                            material_names.add(cname)
                        elif self.scope == 'NAV' and is_nav:
                            material_names.add(cname)
            else:
                # No constants, just the material itself (scope irrelevant)
                material_names.add(mat_name)

        # Get material indices in the object
        mat_indices = set()
        for mname in material_names:
            mat = bpy.data.materials.get(mname)
            if mat and mat.name in obj.data.materials:
                mat_indices.add(obj.data.materials.find(mat.name))

        if not mat_indices:
            self.report({'WARNING'}, f"None of the materials in the family are used by this object")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.select = False
        for face in bm.faces:
            if face.material_index in mat_indices:
                face.select = True
        bmesh.update_edit_mesh(obj.data)

        scope_name = {'FULL': 'full family', 'CONSTANTS': 'constants only', 'NAV': 'nav points only'}[self.scope]
        self.report({'INFO'}, f"Selected {scope_name} for '{mat_name}'")
        return {'FINISHED'}


class MATERIAL_OT_DeselectByMaterial(Operator):
    """Deselect faces using the selected material family (popup to choose scope)"""
    bl_idname = "material.deselect_by_material"
    bl_label = "Deselect Materials"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Deselection Scope",
        description="Which materials to deselect",
        items=[
            ('FULL', "Full Family", "Base + all constants (including nav points)"),
            ('CONSTANTS', "Constants Only", "All constant materials (excluding base and nav points)"),
            ('NAV', "Nav Points Only", "Only navigation point constants"),
        ],
        default='FULL'
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "scope", expand=True)

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        const_dict = obj.get("constant_materials", {})

        # Same logic as Select
        material_names = set()
        if mat_name in const_dict:
            base_name = const_dict[mat_name].get("original_material")
            if base_name:
                if self.scope == 'FULL':
                    material_names.add(base_name)
                for cname, cinfo in const_dict.items():
                    if cinfo.get("original_material") == base_name:
                        is_nav = cinfo.get("is_navigation_point", False)
                        if self.scope == 'FULL':
                            material_names.add(cname)
                        elif self.scope == 'CONSTANTS' and not is_nav:
                            material_names.add(cname)
                        elif self.scope == 'NAV' and is_nav:
                            material_names.add(cname)
        else:
            base_name = mat_name
            has_constants = any(cinfo.get("original_material") == base_name for cinfo in const_dict.values())
            if has_constants:
                if self.scope == 'FULL':
                    material_names.add(base_name)
                for cname, cinfo in const_dict.items():
                    if cinfo.get("original_material") == base_name:
                        is_nav = cinfo.get("is_navigation_point", False)
                        if self.scope == 'FULL':
                            material_names.add(cname)
                        elif self.scope == 'CONSTANTS' and not is_nav:
                            material_names.add(cname)
                        elif self.scope == 'NAV' and is_nav:
                            material_names.add(cname)
            else:
                material_names.add(mat_name)

        mat_indices = set()
        for mname in material_names:
            mat = bpy.data.materials.get(mname)
            if mat and mat.name in obj.data.materials:
                mat_indices.add(obj.data.materials.find(mat.name))

        if not mat_indices:
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.material_index in mat_indices:
                face.select = False
        bmesh.update_edit_mesh(obj.data)

        scope_name = {'FULL': 'full family', 'CONSTANTS': 'constants only', 'NAV': 'nav points only'}[self.scope]
        self.report({'INFO'}, f"Deselected {scope_name} for '{mat_name}'")
        return {'FINISHED'}


classes = [MATERIAL_OT_AssignSelected, MATERIAL_OT_SelectByMaterial, MATERIAL_OT_DeselectByMaterial]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)