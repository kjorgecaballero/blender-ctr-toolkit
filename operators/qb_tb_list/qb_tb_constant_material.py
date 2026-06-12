"""
QB/TB Constant Material Operators
Operators for assigning constant names to blocks via material duplication
Includes navigation point functionality and invalid material cleanup
Reindex‑safe selection and clearing using material names only.
"""

import bpy
import bmesh
import time
import random

from ...utils.qb_tb_navigator import get_faces_by_material_name
from ...utils.qb_tb_navigator.constant_material_utils import clear_all_constant_materials
from ...utils.material_utils import is_constant_id_unique


class LIST_OT_AssignConstantMaterial(bpy.types.Operator):
    """Assign a constant name to the selected block(s) by duplicating its material.
    Supports single block (with custom ID) or multiple blocks (with Base ID + unique suffix).
    Multi-assign only allowed if all selected blocks share the same base material.
    """
    bl_idname = "list.assign_constant_material"
    bl_label = "Assign/Set Constant Name"
    bl_description = "Assign a constant name to the selected block(s). Single or multi-assign."
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Material",
        description="Fixed base material name (non-editable)",
        default=""
    )

    id_value: bpy.props.StringProperty(
        name="ID Value",
        description="Custom value after 'ID' (single assign mode)",
        default=""
    )

    multi_assign: bpy.props.BoolProperty(
        name="Multi-Assign",
        description="Assign constant materials to all selected blocks at once",
        default=False
    )
    base_id: bpy.props.StringProperty(
        name="Base ID",
        description="Base identifier used for all selected blocks (will be combined with a unique suffix)",
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
                self.report({'WARNING'}, "No quadblock/triblock selected.")
                bm.free()
                return {'CANCELLED'}

            if not ("face_to_quadblock" in obj and "face_to_triblock" in obj):
                self.report({'WARNING'}, "Run 'Find All Blocks' first.")
                bm.free()
                return {'CANCELLED'}

            face_to_quadblock = obj["face_to_quadblock"]
            face_to_triblock = obj["face_to_triblock"]
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            # Collect all unique blocks in the selection
            found_blocks = set()
            for face in selected_faces_bm:
                face_index = str(face.index)
                if face_index in face_to_quadblock:
                    found_blocks.add(("quadblock", int(face_to_quadblock[face_index])))
                elif face_index in face_to_triblock:
                    found_blocks.add(("triblock", int(face_to_triblock[face_index])))

            for vert in selected_verts_bm:
                if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                    found_blocks.add(("quadblock", vert.index))

            if not found_blocks:
                self.report({'WARNING'}, "Selection contains no valid quadblock/triblock.")
                bm.free()
                return {'CANCELLED'}

            self.blocks_to_assign = list(found_blocks)

            # Pre‑validation: check for existing constant materials
            const_dict = obj.get("constant_materials", {})
            blocks_with_const = []
            for block_type, block_id in self.blocks_to_assign:
                if block_type == "quadblock":
                    face_indices = quadblock_faces_map.get(str(block_id), [])
                else:
                    face_indices = triblock_faces_map.get(str(block_id), [])
                for fidx in face_indices:
                    if fidx < len(mesh.polygons):
                        mat_idx = mesh.polygons[fidx].material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat and mat.name in const_dict:
                                blocks_with_const.append((block_type, block_id))
                                break
            if blocks_with_const:
                self.report({'WARNING'}, "Some selected blocks already have constant materials. Clear them first.")
                bm.free()
                return {'CANCELLED'}

            # For single assign, we need the first block's material for the dialog
            first_block_type, first_block_id = self.blocks_to_assign[0]
            if first_block_type == "quadblock":
                face_indices = quadblock_faces_map.get(str(first_block_id), [])
            else:
                face_indices = triblock_faces_map.get(str(first_block_id), [])
            if face_indices:
                first_face_idx = face_indices[0]
                mat_idx = mesh.polygons[first_face_idx].material_index
                current_material = obj.material_slots[mat_idx].material
                self.base_name = current_material.name
                self.id_value = str(first_block_id)

            bm.free()

        except Exception as e:
            self.report({'ERROR'}, f"Error preparing dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_name}")

        layout.prop(self, "multi_assign", text="Multi-Assign (selected blocks)")

        if self.multi_assign:
            row = layout.row()
            row.prop(self, "base_id", text="Base ID")
            layout.label(text="Final names: <Base>_ID<BaseID><unique suffix>")
            layout.label(text="Example: tree_tex_IDtreemax → tree_tex_IDtreemax5021", icon='INFO')
            if len(self.blocks_to_assign) > 50:
                box = layout.box()
                box.alert = True
                box.label(text=f"Assigning {len(self.blocks_to_assign)} blocks. May be slow.", icon='ERROR')
        else:
            row = layout.row(align=True)
            row.label(text="ID:")
            row.prop(self, "id_value", text="")
            layout.label(text=f"Final name: {self.base_name}_ID{self.id_value}")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            const_dict = obj.get("constant_materials", {})
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            # SINGLE ASSIGN: only allow exactly one block
            if not self.multi_assign:
                if not self.id_value.strip():
                    self.report({'ERROR'}, "ID cannot be empty.")
                    return {'CANCELLED'}
                if len(self.blocks_to_assign) > 1:
                    self.report({'WARNING'}, f"Single assign supports only 1 quadblock/triblock (found {len(self.blocks_to_assign)}). Enable Multi-Assign.")
                    return {'CANCELLED'}
                base_id = self.id_value.strip()

            #  MULTI ASSIGN: validate all blocks share the same base material
            else:
                if not self.base_id.strip():
                    self.report({'ERROR'}, "Base ID cannot be empty.")
                    return {'CANCELLED'}
                base_id = self.base_id.strip()

                # Collect current material for each block
                block_materials = {}
                for block_type, block_id in self.blocks_to_assign:
                    if block_type == "quadblock":
                        face_indices = quadblock_faces_map.get(str(block_id), [])
                    else:
                        face_indices = triblock_faces_map.get(str(block_id), [])
                    if not face_indices:
                        continue
                    first_face_idx = face_indices[0]
                    if first_face_idx >= len(mesh.polygons):
                        continue
                    mat_idx = mesh.polygons[first_face_idx].material_index
                    if mat_idx < len(obj.material_slots):
                        mat = obj.material_slots[mat_idx].material
                        if mat:
                            block_materials[(block_type, block_id)] = mat.name
                unique_materials = set(block_materials.values())
                if len(unique_materials) > 1:
                    self.report({'WARNING'}, f"Multi-assign requires same material for all selected quadblocks/triblocks. Found {len(unique_materials)} different materials. Cancelled.")
                    return {'CANCELLED'}
                # All good

            # Process blocks
            processed = 0
            errors = 0
            quad_processed = 0
            tri_processed = 0

            for block_type, block_id in self.blocks_to_assign:
                # Get faces of the current block
                face_indices = []
                if block_type == "quadblock":
                    if str(block_id) in quadblock_faces_map:
                        face_indices = quadblock_faces_map[str(block_id)]
                else:
                    if str(block_id) in triblock_faces_map:
                        face_indices = triblock_faces_map[str(block_id)]

                if not face_indices:
                    self.report({'WARNING'}, f"Skipping {block_type} {block_id}: no faces.")
                    errors += 1
                    continue

                # Double-check constant material presence
                already_has = False
                for idx in face_indices:
                    if idx < len(mesh.polygons):
                        poly = mesh.polygons[idx]
                        if poly.material_index < len(obj.material_slots):
                            mat = obj.material_slots[poly.material_index].material
                            if mat and mat.name in const_dict:
                                already_has = True
                                break
                if already_has:
                    self.report({'WARNING'}, f"Skipping {block_type} {block_id}: already constant.")
                    errors += 1
                    continue

                # Verify material match
                first_face_idx = face_indices[0]
                if first_face_idx < len(mesh.polygons):
                    mat_idx = mesh.polygons[first_face_idx].material_index
                    if mat_idx < len(obj.material_slots):
                        current_mat = obj.material_slots[mat_idx].material
                        if not current_mat or current_mat.name != self.base_name:
                            self.report({'WARNING'}, f"Skipping {block_type} {block_id}: material mismatch (expected '{self.base_name}').")
                            errors += 1
                            continue

                # Generate final name
                if self.multi_assign:
                    suffix = random.randint(1000, 9999)
                    final_name = f"{self.base_name}_ID{base_id}{suffix}"
                    attempts = 0
                    while (final_name in bpy.data.materials or final_name in const_dict) and attempts < 10:
                        suffix = random.randint(1000, 9999)
                        final_name = f"{self.base_name}_ID{base_id}{suffix}"
                        attempts += 1
                    if final_name in bpy.data.materials or final_name in const_dict:
                        self.report({'ERROR'}, f"Unique name failed for {block_type} {block_id}.")
                        errors += 1
                        continue
                else:
                    final_name = f"{self.base_name}_ID{base_id}"
                    if not is_constant_id_unique(obj, base_id):
                        self.report({'ERROR'}, f"ID '{base_id}' already used.")
                        return {'CANCELLED'}
                    if final_name in bpy.data.materials:
                        self.report({'ERROR'}, f"Material '{final_name}' already exists.")
                        return {'CANCELLED'}

                base_mat = bpy.data.materials.get(self.base_name)
                if not base_mat:
                    self.report({'ERROR'}, f"Base material '{self.base_name}' not found.")
                    return {'CANCELLED'}

                new_material = base_mat.copy()
                new_material.name = final_name

                if final_name not in obj.data.materials:
                    obj.data.materials.append(new_material)

                new_mat_index = obj.data.materials.find(final_name)

                for face_idx in face_indices:
                    if face_idx < len(mesh.polygons):
                        mesh.polygons[face_idx].material_index = new_mat_index

                const_prop_name = f"constant_name_{block_type}_{block_id}"
                obj[const_prop_name] = final_name

                if "constant_materials" not in obj:
                    obj["constant_materials"] = {}
                const_dict = obj["constant_materials"]
                const_dict[final_name] = {
                    "block_type": block_type,
                    "block_id": block_id,
                    "original_material": self.base_name,
                    "assigned_time": time.time(),
                    "is_navigation_point": False
                }
                obj["constant_materials"] = const_dict

                processed += 1
                if block_type == "quadblock":
                    quad_processed += 1
                else:
                    tri_processed += 1

            mesh.update()

            try:
                bpy.ops.object.material_slot_remove_unused()
            except Exception as e:
                self.report({'WARNING'}, f"Could not remove unused slots: {e}")

            if processed > 0:
                if quad_processed > 0 and tri_processed > 0:
                    msg = f"Assigned {quad_processed} quadblock(s) and {tri_processed} triblock(s). Errors: {errors}"
                elif quad_processed > 0:
                    msg = f"Assigned {quad_processed} quadblock(s). Errors: {errors}"
                else:
                    msg = f"Assigned {tri_processed} triblock(s). Errors: {errors}"
                self.report({'INFO'}, msg)
            else:
                self.report({'WARNING'}, "No quadblocks/triblocks assigned (all skipped).")

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
    """Clear constant name from the selected quadblock/triblock, all constant materials, or only invalid navigation points."""
    bl_idname = "list.clear_constant_material"
    bl_label = "Clear Constant Name"
    bl_description = "Clear constant name from selected block, all constants, or invalid nav points"
    bl_options = {'REGISTER', 'UNDO'}

    clear_mode: bpy.props.EnumProperty(
        name="Clear Mode",
        description="What to clear",
        items=[
            ('SELECTED', "Clear Selected", "Clear checked items AND selected blocks"),
            ('ALL', "Clear All", "Clear all constants from this object"),
            ('INVALID_ONLY', "Clear Invalid Only", "Clear broken navigation points only"),
        ],
        default='SELECTED'
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
            self.report({'WARNING'}, "No constant materials found.")
            return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object

        if "constant_materials" in obj:
            constant_materials_dict = dict(obj["constant_materials"])
            count = len(constant_materials_dict)
            layout.label(text=f"This object has {count} constant materials.")

            # Radio buttons for clear mode
            col = layout.column(align=True)
            col.prop(self, "clear_mode", expand=True)

            # Brief info box
            box = layout.box()
            if self.clear_mode == 'SELECTED':
                box.label(text="Clears checked items AND selected blocks.", icon='INFO')
                box.label(text="Combines both selections.")
            elif self.clear_mode == 'ALL':
                box.label(text="Removes ALL constant materials.", icon='ERROR')
                box.label(text="Base materials restored automatically.")
            else:  # INVALID_ONLY
                invalid_count = 0
                if "constant_materials" in obj:
                    constant_materials_dict = dict(obj["constant_materials"])
                    for mat_name, info in constant_materials_dict.items():
                        if info.get("is_navigation_point", False):
                            face_indices = get_faces_by_material_name(obj, mat_name)
                            if len(face_indices) != 4:
                                invalid_count += 1
                box.label(text=f"Clears {invalid_count} invalid nav points.", icon='INFO')
                box.label(text="Only broken navigation points.")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            # 1) Clear only invalid navigation points
            if self.clear_mode == 'INVALID_ONLY':
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
                    self.report({'WARNING'}, f"Could not remove unused slots: {e}")

                msg = f"Cleared {len(broken_points) - len(failed_materials)} invalid constants. "
                if restored_with_fallback > 0:
                    msg += f"Restored {restored_with_fallback} via fallback. "
                if failed_materials:
                    msg += f"Failed: {', '.join(failed_materials)}"
                self.report({'INFO'} if not failed_materials else {'WARNING'}, msg)
                return {'FINISHED'}

            # 2) Clear all constant materials
            elif self.clear_mode == 'ALL':
                cleared_orig, restored_fb, failed = clear_all_constant_materials(obj, fallback_duplicate=True)
                msg = f"Cleared all constants. Restored {cleared_orig} original, {restored_fb} fallback."
                if failed:
                    msg += f" Failed: {', '.join(failed)}"
                    self.report({'WARNING'}, msg)
                else:
                    self.report({'INFO'}, msg)
                # Also clear multi_selected_items
                if "multi_selected_items" in obj:
                    obj["multi_selected_items"].clear()
                return {'FINISHED'}

            # 3) Clear selected: combine checked items AND 3D selection
            else:  # SELECTED
                const_dict = obj.get("constant_materials", {})
                if not const_dict:
                    self.report({'WARNING'}, "No constant materials.")
                    return {'CANCELLED'}

                mats_to_clear = set()

                # Add checked items from the list
                if "multi_selected_items" in obj and obj["multi_selected_items"]:
                    multi = dict(obj["multi_selected_items"])
                    for mat_name in multi.keys():
                        if mat_name in const_dict:
                            mats_to_clear.add(mat_name)
                    if mats_to_clear:
                        self.report({'INFO'}, f"Adding {len(mats_to_clear)} checked material(s) from list.")

                # Add selected blocks from 3D view
                selected_polys = [p for p in obj.data.polygons if p.select]
                if selected_polys:
                    for poly in selected_polys:
                        mat_idx = poly.material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat and mat.name in const_dict:
                                mats_to_clear.add(mat.name)
                    self.report({'INFO'}, f"Adding materials from 3D selected faces.")

                if not mats_to_clear:
                    self.report({'WARNING'}, "No materials to clear (no checked items and no 3D selection).")
                    return {'CANCELLED'}

                # Process clearing
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
                            # Check if the new material has a texture node
                            new_mat = bpy.data.materials.get(new_mat_name)
                            if new_mat and new_mat.use_nodes:
                                has_tex = any(node.type == 'TEX_IMAGE' for node in new_mat.node_tree.nodes)
                                if not has_tex:
                                    self.report({'WARNING'}, f"Fallback material '{new_mat_name}' has no texture. It may appear pink.")
                        else:
                            failed_materials.append(mat_name)
                            continue
                    else:
                        if original_mat_name not in obj.data.materials:
                            obj.data.materials.append(original_mat)
                        orig_idx = obj.data.materials.find(original_mat_name)
                        for idx in face_indices:
                            obj.data.polygons[idx].material_index = orig_idx
                        cleared += 1

                    # Remove from constant_materials dict
                    if mat_name in const_dict:
                        del const_dict[mat_name]
                    # Remove custom properties
                    props_to_delete = [k for k in obj.keys() if k.startswith("constant_name_") and obj[k] == mat_name]
                    for prop in props_to_delete:
                        del obj[prop]
                    # Delete material if unused
                    const_mat = bpy.data.materials.get(mat_name)
                    if const_mat and const_mat.users == 0:
                        bpy.data.materials.remove(const_mat)

                obj["constant_materials"] = const_dict
                # Clear the checked items from multi_selected_items
                if "multi_selected_items" in obj:
                    multi = dict(obj["multi_selected_items"])
                    for mat_name in mats_to_clear:
                        if mat_name in multi:
                            del multi[mat_name]
                    obj["multi_selected_items"] = multi

                obj.data.update()
                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception as e:
                    self.report({'WARNING'}, f"Could not remove unused slots: {e}")

                if failed_materials:
                    self.report({'WARNING'}, f"Failed to clear: {', '.join(failed_materials)}")
                else:
                    msg = f"Cleared {cleared} constant material(s)"
                    if restored_with_fallback > 0:
                        msg += f", restored {restored_with_fallback} via fallback"
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