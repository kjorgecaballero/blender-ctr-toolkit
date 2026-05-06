"""
QB/TB Constant Material Operators
Operators for assigning constant names to blocks via material duplication
Includes navigation point functionality and invalid material cleanup
Added reindex‑safe selection and clearing using material names only.
"""

import bpy
import bmesh
import time

from ...utils.qb_tb_navigator import get_faces_by_material_name
from ...utils.qb_tb_navigator.constant_material_utils import clear_all_constant_materials
from ...utils.material_utils import is_constant_id_unique


class LIST_OT_AssignConstantMaterial(bpy.types.Operator):
    """Assign a constant name to the selected block by duplicating its material.
    The base material name is fixed; you can edit only the value after 'ID'.
    The final name will be: base_name_IDvalue (e.g., Dirt_tex01_IDCustomName).
    If the resulting name already exists, the operation is cancelled.
    All IDs must be unique across all constant materials on the object.
    """
    bl_idname = "list.assign_constant_material"
    bl_label = "Assign/Set Constant Name"
    bl_description = "Assign a constant name to the selected block. The base material is fixed; you can edit the value after 'ID'."
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Material",
        description="Fixed base material name (non-editable)",
        default=""
    )

    id_value: bpy.props.StringProperty(
        name="ID Value",
        description="Custom value after 'ID' (you can edit this part, e.g., '123' or 'CustomName')",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        obj = context.edit_object
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_faces_bm = [f for f in bm.faces if f.select]
            selected_verts_bm = [v for v in bm.verts if v.select]

            if not selected_faces_bm and not selected_verts_bm:
                self.report({'WARNING'}, "No block selected. Select exactly one quadblock or triblock.")
                bm.free()
                return {'CANCELLED'}

            if not ("face_to_quadblock" in obj and "face_to_triblock" in obj):
                self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
                bm.free()
                return {'CANCELLED'}

            face_to_quadblock = obj["face_to_quadblock"]
            face_to_triblock = obj["face_to_triblock"]
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            block_type = None
            block_id = None

            if selected_faces_bm:
                found_blocks = set()
                for face in selected_faces_bm:
                    face_index = str(face.index)
                    if face_index in face_to_quadblock:
                        found_blocks.add(("quadblock", int(face_to_quadblock[face_index])))
                    elif face_index in face_to_triblock:
                        found_blocks.add(("triblock", int(face_to_triblock[face_index])))

                if len(found_blocks) == 0:
                    self.report({'WARNING'}, "No block found in selection.")
                    bm.free()
                    return {'CANCELLED'}
                elif len(found_blocks) > 1:
                    self.report({'WARNING'}, "Multiple blocks selected. Select only ONE block at a time.")
                    bm.free()
                    return {'CANCELLED'}

                block_type, block_id = list(found_blocks)[0]

            elif selected_verts_bm and len(selected_verts_bm) == 1:
                vert = selected_verts_bm[0]
                if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                    block_type = "quadblock"
                    block_id = vert.index

            if not block_type:
                self.report({'WARNING'}, "Could not identify a valid block from selection.")
                bm.free()
                return {'CANCELLED'}

            face_indices = []
            if block_type == "quadblock":
                if str(block_id) in quadblock_faces_map:
                    face_indices = quadblock_faces_map[str(block_id)]
            else:
                if str(block_id) in triblock_faces_map:
                    face_indices = triblock_faces_map[str(block_id)]

            if not face_indices:
                self.report({'WARNING'}, f"No faces found for {block_type} {block_id}")
                bm.free()
                return {'CANCELLED'}

            first_face_idx = face_indices[0]
            if first_face_idx >= len(mesh.polygons):
                self.report({'WARNING'}, f"Face index {first_face_idx} out of range")
                bm.free()
                return {'CANCELLED'}

            first_face_material_index = mesh.polygons[first_face_idx].material_index
            if first_face_material_index >= len(obj.material_slots):
                self.report({'WARNING'}, f"Selected block has no material assigned. Assign a material first.")
                bm.free()
                return {'CANCELLED'}

            current_material = obj.material_slots[first_face_material_index].material
            if not current_material:
                self.report({'WARNING'}, "Selected block has no material assigned.")
                bm.free()
                return {'CANCELLED'}

            # REINDEX‑SAFE CHECK, does this block already have a constant material? 
            const_dict = obj.get("constant_materials", {})
            for idx in face_indices:
                poly = mesh.polygons[idx]
                if poly.material_index < len(obj.material_slots):
                    mat = obj.material_slots[poly.material_index].material
                    if mat and mat.name in const_dict:
                        self.report({'WARNING'}, f"Block already has constant material '{mat.name}'. Clear it first.")
                        bm.free()
                        return {'CANCELLED'}

            bm.free()

            const_prop_name = f"constant_name_{block_type}_{block_id}"
            if const_prop_name in obj:
                existing_material_name = obj[const_prop_name]
                self.report({'INFO'}, f"Block {block_type} {block_id} already has constant name '{existing_material_name}'. Constant names do not change.")
                return {'CANCELLED'}

            self.base_name = current_material.name
            self.id_value = str(block_id)

        except Exception as e:
            self.report({'ERROR'}, f"Error preparing dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_name}")
        row = layout.row(align=True)
        row.label(text="ID:")
        row.prop(self, "id_value", text="")
        layout.label(text=f"Final name will be: {self.base_name}_ID{self.id_value}")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_faces_bm = [f for f in bm.faces if f.select]
            selected_verts_bm = [v for v in bm.verts if v.select]

            if not selected_faces_bm and not selected_verts_bm:
                self.report({'WARNING'}, "No block selected.")
                bm.free()
                return {'CANCELLED'}

            if not ("face_to_quadblock" in obj and "face_to_triblock" in obj):
                self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
                bm.free()
                return {'CANCELLED'}

            face_to_quadblock = obj["face_to_quadblock"]
            face_to_triblock = obj["face_to_triblock"]
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            block_type = None
            block_id = None

            if selected_faces_bm:
                found_blocks = set()
                for face in selected_faces_bm:
                    face_index = str(face.index)
                    if face_index in face_to_quadblock:
                        found_blocks.add(("quadblock", int(face_to_quadblock[face_index])))
                    elif face_index in face_to_triblock:
                        found_blocks.add(("triblock", int(face_to_triblock[face_index])))

                if len(found_blocks) == 0:
                    self.report({'WARNING'}, "No block found in selection.")
                    bm.free()
                    return {'CANCELLED'}
                elif len(found_blocks) > 1:
                    self.report({'WARNING'}, "Multiple blocks selected. Select only ONE block.")
                    bm.free()
                    return {'CANCELLED'}

                block_type, block_id = list(found_blocks)[0]

            elif selected_verts_bm and len(selected_verts_bm) == 1:
                vert = selected_verts_bm[0]
                if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                    block_type = "quadblock"
                    block_id = vert.index

            if not block_type:
                self.report({'WARNING'}, "Could not identify a valid block.")
                bm.free()
                return {'CANCELLED'}

            face_indices = []
            if block_type == "quadblock":
                if str(block_id) in quadblock_faces_map:
                    face_indices = quadblock_faces_map[str(block_id)]
            else:
                if str(block_id) in triblock_faces_map:
                    face_indices = triblock_faces_map[str(block_id)]

            if not face_indices:
                self.report({'WARNING'}, f"No faces found for {block_type} {block_id}")
                bm.free()
                return {'CANCELLED'}

            first_face_idx = face_indices[0]
            if first_face_idx >= len(mesh.polygons):
                self.report({'WARNING'}, f"Face index {first_face_idx} out of range")
                bm.free()
                return {'CANCELLED'}

            first_face_material_index = mesh.polygons[first_face_idx].material_index
            if first_face_material_index >= len(obj.material_slots):
                self.report({'WARNING'}, "Selected block has no material assigned.")
                bm.free()
                return {'CANCELLED'}

            current_material = obj.material_slots[first_face_material_index].material
            if not current_material:
                self.report({'WARNING'}, "Selected block has no material.")
                bm.free()
                return {'CANCELLED'}

            # Re‑check constant material (in case selection changed)
            const_dict = obj.get("constant_materials", {})
            for idx in face_indices:
                poly = mesh.polygons[idx]
                if poly.material_index < len(obj.material_slots):
                    mat = obj.material_slots[poly.material_index].material
                    if mat and mat.name in const_dict:
                        self.report({'WARNING'}, f"Block already has constant material '{mat.name}'. Clear it first.")
                        bm.free()
                        return {'CANCELLED'}

            bm.free()

            const_prop_name = f"constant_name_{block_type}_{block_id}"
            if const_prop_name in obj:
                existing_material_name = obj[const_prop_name]
                self.report({'INFO'}, f"Block already has constant name '{existing_material_name}'.")
                return {'FINISHED'}

            if not self.id_value.strip():
                self.report({'ERROR'}, "ID value cannot be empty.")
                return {'CANCELLED'}

            id_value = self.id_value.strip()
            final_name = f"{self.base_name}_ID{id_value}"

            # Check ID uniqueness across all constant materials
            if not is_constant_id_unique(obj, id_value):
                self.report({'ERROR'}, f"ID '{id_value}' is already used by another constant material. Please choose a unique ID.")
                return {'CANCELLED'}

            # Check if the full name already exists (global materials or constant materials)
            if final_name in bpy.data.materials:
                self.report({'ERROR'}, f"Material name '{final_name}' already exists. Choose a different base or ID.")
                return {'CANCELLED'}

            if "constant_materials" in obj and final_name in obj["constant_materials"]:
                existing_block_info = obj["constant_materials"][final_name]
                existing_block_type = existing_block_info.get("block_type", "")
                existing_block_id = existing_block_info.get("block_id", 0)
                self.report({'ERROR'}, f"Name '{final_name}' is already assigned to {existing_block_type} {existing_block_id}. Cannot reuse.")
                return {'CANCELLED'}

            # Create new material
            new_material = current_material.copy()
            new_material.name = final_name

            if final_name not in obj.data.materials:
                obj.data.materials.append(new_material)

            new_mat_index = obj.data.materials.find(final_name)

            for face_idx in face_indices:
                if face_idx < len(mesh.polygons):
                    mesh.polygons[face_idx].material_index = new_mat_index

            mesh.update()

            obj[const_prop_name] = final_name

            if "constant_materials" not in obj:
                obj["constant_materials"] = {}

            constant_materials = obj["constant_materials"]
            constant_materials[final_name] = {
                "block_type": block_type,
                "block_id": block_id,
                "original_material": self.base_name,
                "assigned_time": time.time(),
                "is_navigation_point": False
            }

            self.report({'INFO'}, f"Assigned constant name '{final_name}' to {block_type} {block_id} (based on '{self.base_name}')")

            try:
                bpy.ops.object.material_slot_remove_unused()
            except Exception as e:
                self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


class LIST_OT_ClearConstantMaterial(bpy.types.Operator):
    """Clear constant name from the selected quadblock/triblock, all constant materials, or only invalid navigation points.
    When the original material is missing and 'Duplicate as fallback' is enabled, a new base material is created from the
    constant material (by stripping the '_ID' suffix) and all blocks sharing the same base are reassigned to it.
    """
    bl_idname = "list.clear_constant_material"
    bl_label = "Clear Constant Name"
    bl_description = "Clear constant name from selected block, all constant materials, or only invalid navigation points"
    bl_options = {'REGISTER', 'UNDO'}

    clear_all: bpy.props.BoolProperty(
        name="Clear All",
        description="Clear all constant materials from this object",
        default=False,
        update=lambda self, context: setattr(self, 'clear_invalid_only', False) if self.clear_all else None
    )

    clear_invalid_only: bpy.props.BoolProperty(
        name="Clear Invalid Only",
        description="Clear only invalid constant materials (navigation points that are broken)",
        default=False,
        update=lambda self, context: setattr(self, 'clear_all', False) if self.clear_invalid_only else None
    )

    fallback_duplicate: bpy.props.BoolProperty(
        name="Duplicate if missing",
        description="If original material is missing, duplicate constant material as new base (stripping '_ID' suffix)",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None)

    def invoke(self, context, event):
        obj = context.edit_object
        if "constant_materials" in obj and obj["constant_materials"]:
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=350)
        else:
            self.report({'WARNING'}, "No constant materials found on this object.")
            return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object

        if "constant_materials" in obj:
            constant_materials_dict = dict(obj["constant_materials"])
            count = len(constant_materials_dict)
            layout.label(text=f"This object has {count} constant materials.")

            row = layout.row()
            row.prop(self, "clear_all")
            if self.clear_all:
                row.label(text="Will clear ALL constant materials", icon='ERROR')

            row = layout.row()
            row.prop(self, "clear_invalid_only")
            if self.clear_invalid_only:
                invalid_count = 0
                if "constant_materials" in obj:
                    constant_materials_dict = dict(obj["constant_materials"])
                    for mat_name, info in constant_materials_dict.items():
                        if info.get("is_navigation_point", False):
                            face_indices = get_faces_by_material_name(obj, mat_name)
                            if len(face_indices) != 4:
                                invalid_count += 1
                row.label(text=f"Will clear {invalid_count} invalid navigation points", icon='ERROR')

            row = layout.row()
            row.prop(self, "fallback_duplicate")
            if self.fallback_duplicate:
                row.label(text="Will duplicate missing originals", icon='DUPLICATE')

            row = layout.row()
            if not self.clear_all and not self.clear_invalid_only:
                row.label(text="When unchecked: clears only from selected block", icon='INFO')

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:

            # 1) Clear only invalid navigation points (unchanged)
            if self.clear_invalid_only:
                if "constant_materials" not in obj:
                    self.report({'WARNING'}, "No constant materials found.")
                    return {'CANCELLED'}

                broken_points = []
                constant_materials_dict = dict(obj["constant_materials"])
                for mat_name, block_info in constant_materials_dict.items():
                    if block_info.get("is_navigation_point", False):
                        face_indices = get_faces_by_material_name(obj, mat_name)
                        if len(face_indices) != 4:
                            broken_points.append(mat_name)

                if not broken_points:
                    self.report({'INFO'}, "No invalid constant materials found.")
                    return {'FINISHED'}

                cleared_count = 0
                restored_with_fallback = 0
                failed_materials = []
                fallback_cache = {}

                for mat_name in broken_points:
                    block_info = constant_materials_dict[mat_name]
                    block_type = block_info.get("block_type", "")
                    block_id = block_info.get("block_id", 0)
                    original_material_name = block_info.get("original_material", "")

                    original_material = None
                    if original_material_name and original_material_name in bpy.data.materials:
                        original_material = bpy.data.materials[original_material_name]

                    if not original_material:
                        if self.fallback_duplicate:
                            const_mat = bpy.data.materials.get(mat_name)
                            if const_mat:
                                base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                                if base_name in fallback_cache:
                                    new_mat_name, new_index = fallback_cache[base_name]
                                else:
                                    from ...utils.qb_tb_navigator.constant_material_utils import _create_base_material_from_constant
                                    new_mat_name, new_index = _create_base_material_from_constant(obj, mat_name)
                                    if new_mat_name:
                                        fallback_cache[base_name] = (new_mat_name, new_index)
                                    else:
                                        failed_materials.append(mat_name)
                                        continue

                                block_faces = get_faces_by_material_name(obj, mat_name)
                                for face_idx in block_faces:
                                    if face_idx < len(obj.data.polygons):
                                        obj.data.polygons[face_idx].material_index = new_index
                                obj.data.update()
                                restored_with_fallback += 1
                            else:
                                failed_materials.append(mat_name)
                                continue
                        else:
                            # No fallback, cannot restore -> keep constant material untouched
                            failed_materials.append(mat_name)
                            continue
                    else:
                        block_faces = get_faces_by_material_name(obj, mat_name)
                        if not block_faces:
                            failed_materials.append(mat_name)
                            continue

                        if original_material_name not in obj.data.materials:
                            obj.data.materials.append(original_material)
                        original_mat_index = obj.data.materials.find(original_material_name)
                        for face_idx in block_faces:
                            obj.data.polygons[face_idx].material_index = original_mat_index
                        obj.data.update()
                        cleared_count += 1

                    # Only if restoration succeeded do we delete the constant material
                    if mat_name in obj["constant_materials"]:
                        del obj["constant_materials"][mat_name]
                    const_prop_name = f"constant_name_{block_type}_{block_id}"
                    if const_prop_name in obj:
                        del obj[const_prop_name]

                    if mat_name in bpy.data.materials:
                        material = bpy.data.materials[mat_name]
                        if material.users == 0:
                            bpy.data.materials.remove(material)

                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception as e:
                    self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

                msg = f"Cleared {len(broken_points) - len(failed_materials)} invalid constant materials. "
                if restored_with_fallback > 0:
                    msg += f"Restored {restored_with_fallback} using fallback. "
                if failed_materials:
                    msg += f"Could NOT restore (missing original & fallback off): {', '.join(failed_materials)}"
                self.report({'INFO'} if not failed_materials else {'WARNING'}, msg)
                return {'FINISHED'}

            # 2) Clear all constant materials (unchanged)
            elif self.clear_all:
                cleared_orig, restored_fb, failed = clear_all_constant_materials(obj, self.fallback_duplicate)
                msg = f"Cleared all constant materials. Restored {cleared_orig} with original, {restored_fb} with fallback."
                if failed:
                    msg += f" Could NOT restore (missing original & fallback off): {', '.join(failed)}"
                    self.report({'WARNING'}, msg)
                else:
                    self.report({'INFO'}, msg)
                return {'FINISHED'}

            # 3) Clear only from the selected block (unchanged)
            else:
                selected_polys = [p for p in obj.data.polygons if p.select]
                if not selected_polys:
                    self.report({'WARNING'}, "No faces selected. Select a block to clear its constant material.")
                    return {'CANCELLED'}

                const_dict = obj.get("constant_materials", {})
                if not const_dict:
                    self.report({'WARNING'}, "No constant materials on this object.")
                    return {'CANCELLED'}

                mats_to_clear = set()
                for poly in selected_polys:
                    mat_idx = poly.material_index
                    if mat_idx < len(obj.material_slots):
                        mat = obj.material_slots[mat_idx].material
                        if mat and mat.name in const_dict:
                            mats_to_clear.add(mat.name)

                if not mats_to_clear:
                    self.report({'WARNING'}, "Selected faces have no constant material.")
                    return {'CANCELLED'}

                cleared = 0
                restored_with_fallback = 0
                failed_materials = []
                fallback_cache = {}

                for mat_name in mats_to_clear:
                    block_info = const_dict[mat_name]
                    original_mat_name = block_info.get("original_material", "")
                    original_mat = bpy.data.materials.get(original_mat_name)

                    face_indices = get_faces_by_material_name(obj, mat_name)
                    if not face_indices:
                        failed_materials.append(mat_name)
                        continue

                    if not original_mat:
                        if self.fallback_duplicate:
                            const_mat = bpy.data.materials.get(mat_name)
                            if const_mat:
                                base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                                if base_name in fallback_cache:
                                    new_mat_name, new_index = fallback_cache[base_name]
                                else:
                                    from ...utils.qb_tb_navigator.constant_material_utils import _create_base_material_from_constant
                                    new_mat_name, new_index = _create_base_material_from_constant(obj, mat_name)
                                    if new_mat_name:
                                        fallback_cache[base_name] = (new_mat_name, new_index)
                                    else:
                                        failed_materials.append(mat_name)
                                        continue

                                for idx in face_indices:
                                    if idx < len(obj.data.polygons):
                                        obj.data.polygons[idx].material_index = new_index
                                restored_with_fallback += 1
                            else:
                                failed_materials.append(mat_name)
                                continue
                        else:
                            self.report({'ERROR'}, f"Original material '{original_mat_name}' missing and fallback disabled for '{mat_name}'.")
                            return {'CANCELLED'}
                    else:
                        if original_mat_name not in obj.data.materials:
                            obj.data.materials.append(original_mat)
                        orig_idx = obj.data.materials.find(original_mat_name)
                        for idx in face_indices:
                            obj.data.polygons[idx].material_index = orig_idx
                        cleared += 1

                    if mat_name in const_dict:
                        del const_dict[mat_name]

                    props_to_delete = [k for k in obj.keys() if k.startswith("constant_name_") and obj[k] == mat_name]
                    for prop in props_to_delete:
                        del obj[prop]

                    const_mat = bpy.data.materials.get(mat_name)
                    if const_mat and const_mat.users == 0:
                        bpy.data.materials.remove(const_mat)

                obj["constant_materials"] = const_dict
                obj.data.update()
                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception as e:
                    self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

                if failed_materials:
                    self.report({'WARNING'}, f"Some materials could not be cleared (missing original & fallback off): {', '.join(failed_materials)}")
                else:
                    msg = f"Cleared {cleared} constant material(s)"
                    if restored_with_fallback > 0:
                        msg += f", restored {restored_with_fallback} with fallback"
                    self.report({'INFO'}, msg)

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


classes = [
    LIST_OT_AssignConstantMaterial,
    LIST_OT_ClearConstantMaterial,
]