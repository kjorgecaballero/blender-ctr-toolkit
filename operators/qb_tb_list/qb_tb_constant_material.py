"""
QB/TB Constant Material Operators
Operators for assigning constant names to blocks via material duplication
Now includes navigation point functionality and invalid material cleanup
Unused operator `LIST_OT_SelectByConstantMaterial` removed.
Added fallback duplication when original material is missing.
"""

import bpy
import bmesh
import time

# Import the utility function needed for clearing invalid navigation points
from ...utils.qb_tb_navigator import get_faces_by_material_name


class LIST_OT_AssignConstantMaterial(bpy.types.Operator):
    """Assign a constant name to the selected block by duplicating its material.
    The base material name is fixed; you can edit only the value after 'ID'.
    The final name will be: base_name_IDvalue (e.g., Dirt_tex01_IDLavaPoint12).
    If the resulting name already exists, a numeric suffix (.001, .002, etc.) is added automatically.
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
        description="Custom value after 'ID' (you can edit this part, e.g., '123' or 'LavaPoint12')",
        default=""
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        # Detect the selected block and generate a default id_value
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

            bm.free()

            const_prop_name = f"constant_name_{block_type}_{block_id}"
            if const_prop_name in obj:
                existing_material_name = obj[const_prop_name]
                self.report({'INFO'}, f"Block {block_type} {block_id} already has constant name '{existing_material_name}'. Constant names do not change.")
                return {'CANCELLED'}

            # Set base name and default id_value
            self.base_name = current_material.name
            self.id_value = str(block_id)  # Default: the block ID as string

        except Exception as e:
            self.report({'ERROR'}, f"Error preparing dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        # Show dialog
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_name}")
        row = layout.row(align=True)
        row.label(text="ID:")
        row.prop(self, "id_value", text="")  # Editable field without extra label
        layout.label(text=f"Final name will be: {self.base_name}_ID{self.id_value}")
        layout.label(text="If the name already exists, a number will be appended automatically.")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            # Re-detect the block (similar to invoke) to get all necessary data
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

            bm.free()

            const_prop_name = f"constant_name_{block_type}_{block_id}"

            if const_prop_name in obj:
                existing_material_name = obj[const_prop_name]
                self.report({'INFO'}, f"Block {block_type} {block_id} already has constant name '{existing_material_name}'. Constant names do not change.")
                return {'FINISHED'}

            # Validate id_value
            if not self.id_value.strip():
                self.report({'ERROR'}, "ID value cannot be empty.")
                return {'CANCELLED'}

            # Build final name
            final_name = f"{self.base_name}_ID{self.id_value.strip()}"

            # Check if the name is already used as a constant material in this object
            if "constant_materials" in obj and final_name in obj["constant_materials"]:
                existing_block_info = obj["constant_materials"][final_name]
                existing_block_type = existing_block_info.get("block_type", "")
                existing_block_id = existing_block_info.get("block_id", 0)
                self.report({'WARNING'}, f"Name '{final_name}' is already used by {existing_block_type} {existing_block_id}.")
                return {'CANCELLED'}

            # Ensure the name is unique across global materials and constant materials in this object
            base_name_for_uniqueness = final_name
            counter = 1
            while True:
                material_exists = final_name in bpy.data.materials
                constant_exists = ("constant_materials" in obj and final_name in obj["constant_materials"])
                if not material_exists and not constant_exists:
                    break
                final_name = f"{base_name_for_uniqueness}.{counter:03d}"
                counter += 1

            if final_name != base_name_for_uniqueness:
                self.report({'INFO'}, f"Name '{base_name_for_uniqueness}' already in use. Using '{final_name}' instead.")

            # Duplicate material with final name
            new_material = current_material.copy()
            new_material.name = final_name

            if final_name not in obj.data.materials:
                obj.data.materials.append(new_material)

            new_mat_index = obj.data.materials.find(final_name)

            # Assign to faces
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
                "original_material": self.base_name,  # store base name, not the possibly renamed one
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

    #  Fallback duplication option
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

            # Clear all option
            row = layout.row()
            row.prop(self, "clear_all")
            if self.clear_all:
                row.label(text="Will clear ALL constant materials", icon='ERROR')

            # Clear invalid only option
            row = layout.row()
            row.prop(self, "clear_invalid_only")
            if self.clear_invalid_only:
                # Simple count of invalid navigation points (materials marked as nav but without exactly 4 faces)
                invalid_count = 0
                if "constant_materials" in obj:
                    constant_materials_dict = dict(obj["constant_materials"])
                    for mat_name, info in constant_materials_dict.items():
                        if info.get("is_navigation_point", False):
                            face_indices = get_faces_by_material_name(obj, mat_name)
                            if len(face_indices) != 4:
                                invalid_count += 1
                row.label(text=f"Will clear {invalid_count} invalid navigation points", icon='ERROR')

            # Fallback duplication option
            row = layout.row()
            row.prop(self, "fallback_duplicate")
            if self.fallback_duplicate:
                row.label(text="Will duplicate missing originals", icon='DUPLICATE')

            # Info about selected block clearing
            row = layout.row()
            if not self.clear_all and not self.clear_invalid_only:
                row.label(text="When unchecked: clears only from selected block", icon='INFO')

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:

            # Helper: create a new base material from a constant material name

            def create_base_material_from_constant(const_mat_name):
                """Create a new base material by duplicating the constant material and stripping '_ID' suffix."""
                # Determine base name: everything before the last '_ID'
                if '_ID' in const_mat_name:
                    base_name = const_mat_name.rsplit('_ID', 1)[0]
                else:
                    base_name = const_mat_name  # fallback

                # Get the constant material object
                const_mat = bpy.data.materials.get(const_mat_name)
                if not const_mat:
                    return None, -1

                # Duplicate it
                new_mat = const_mat.copy()
                new_mat.name = base_name  # Blender will automatically add .001 if needed

                # Ensure it's in the object's material slots
                if new_mat.name not in obj.data.materials:
                    obj.data.materials.append(new_mat)
                new_index = obj.data.materials.find(new_mat.name)

                return new_mat.name, new_index


            # Process according to mode

            if self.clear_invalid_only:
                # Clear only invalid navigation points
                if "constant_materials" not in obj:
                    self.report({'WARNING'}, "No constant materials found on this object.")
                    return {'CANCELLED'}

                # Detect broken navigation points
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
                errors_count = 0

                # Cache for already created fallback materials (base_name -> (new_mat_name, index))
                fallback_cache = {}

                for mat_name in broken_points:
                    block_info = constant_materials_dict[mat_name]
                    block_type = block_info.get("block_type", "")
                    block_id = block_info.get("block_id", 0)
                    original_material_name = block_info.get("original_material", "")

                    # Find original material
                    original_material = None
                    if original_material_name and original_material_name in bpy.data.materials:
                        original_material = bpy.data.materials[original_material_name]

                    if not original_material:
                        if self.fallback_duplicate:
                            # Use fallback duplication
                            const_mat = bpy.data.materials.get(mat_name)
                            if const_mat:
                                base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                                if base_name in fallback_cache:
                                    new_mat_name, new_index = fallback_cache[base_name]
                                else:
                                    new_mat_name, new_index = create_base_material_from_constant(mat_name)
                                    if new_mat_name:
                                        fallback_cache[base_name] = (new_mat_name, new_index)
                                    else:
                                        errors_count += 1
                                        continue

                                # Get faces of this block
                                block_faces = []
                                for i, poly in enumerate(obj.data.polygons):
                                    if poly.material_index < len(obj.material_slots):
                                        slot = obj.material_slots[poly.material_index]
                                        if slot.material and slot.material.name == mat_name:
                                            block_faces.append(i)

                                # Assign new material
                                for face_idx in block_faces:
                                    if face_idx < len(obj.data.polygons):
                                        obj.data.polygons[face_idx].material_index = new_index
                                obj.data.update()
                                restored_with_fallback += 1
                            else:
                                errors_count += 1
                                continue
                        else:
                            # No fallback, just skip restoration (but we will still remove the constant)
                            # Optionally warn later
                            pass

                    else:
                        # Original material exists – restore it
                        block_faces = []
                        for i, poly in enumerate(obj.data.polygons):
                            if poly.material_index < len(obj.material_slots):
                                slot = obj.material_slots[poly.material_index]
                                if slot.material and slot.material.name == mat_name:
                                    block_faces.append(i)

                        if not block_faces:
                            errors_count += 1
                            continue

                        # Ensure original material is in slots
                        if original_material_name not in obj.data.materials:
                            obj.data.materials.append(original_material)
                        original_mat_index = obj.data.materials.find(original_material_name)

                        for face_idx in block_faces:
                            obj.data.polygons[face_idx].material_index = original_mat_index
                        obj.data.update()
                        cleared_count += 1

                    # After (possibly) reassigning, remove the constant material entry and property
                    if mat_name in obj["constant_materials"]:
                        del obj["constant_materials"][mat_name]
                    const_prop_name = f"constant_name_{block_type}_{block_id}"
                    if const_prop_name in obj:
                        del obj[const_prop_name]

                    # Remove the material if it's no longer used
                    if mat_name in bpy.data.materials:
                        material = bpy.data.materials[mat_name]
                        if material.users == 0:
                            bpy.data.materials.remove(material)

                # Remove unused slots
                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception as e:
                    self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

                msg = f"Cleared {len(broken_points)} invalid constant materials. "
                if restored_with_fallback > 0:
                    msg += f"Restored {restored_with_fallback} using fallback."
                if errors_count > 0:
                    msg += f" Errors: {errors_count}."
                self.report({'INFO'}, msg)
                return {'FINISHED'}

            elif self.clear_all:
                # Clear all constant materials
                if "constant_materials" not in obj:
                    self.report({'WARNING'}, "No constant materials found to clear.")
                    return {'CANCELLED'}

                constant_materials_dict = dict(obj["constant_materials"])
                fallback_cache = {}
                restored_with_fallback = 0
                cleared_with_original = 0
                errors = 0

                for mat_name, block_info in constant_materials_dict.items():
                    block_type = block_info.get("block_type", "")
                    block_id = block_info.get("block_id", 0)
                    original_material_name = block_info.get("original_material", "")

                    # Get faces using this constant material
                    block_faces = []
                    for i, poly in enumerate(obj.data.polygons):
                        if poly.material_index < len(obj.material_slots):
                            slot = obj.material_slots[poly.material_index]
                            if slot.material and slot.material.name == mat_name:
                                block_faces.append(i)

                    if not block_faces:
                        errors += 1
                        continue

                    # Find original material
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
                                    new_mat_name, new_index = create_base_material_from_constant(mat_name)
                                    if new_mat_name:
                                        fallback_cache[base_name] = (new_mat_name, new_index)
                                    else:
                                        errors += 1
                                        continue

                                for face_idx in block_faces:
                                    obj.data.polygons[face_idx].material_index = new_index
                                restored_with_fallback += 1
                            else:
                                errors += 1
                                continue
                        else:
                            # No fallback: just skip restoration, but we still remove the constant material later
                            pass
                    else:
                        # Original material exists
                        if original_material_name not in obj.data.materials:
                            obj.data.materials.append(original_material)
                        original_mat_index = obj.data.materials.find(original_material_name)
                        for face_idx in block_faces:
                            obj.data.polygons[face_idx].material_index = original_mat_index
                        cleared_with_original += 1

                    # Remove the constant material entry
                    if mat_name in obj["constant_materials"]:
                        del obj["constant_materials"][mat_name]
                    const_prop_name = f"constant_name_{block_type}_{block_id}"
                    if const_prop_name in obj:
                        del obj[const_prop_name]

                    # Delete the material if no users left
                    if mat_name in bpy.data.materials:
                        mat = bpy.data.materials[mat_name]
                        if mat.users == 0:
                            bpy.data.materials.remove(mat)

                # Also remove any leftover constant_name_* props
                for prop in list(obj.keys()):
                    if prop.startswith("constant_name_"):
                        del obj[prop]

                # Remove unused slots
                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception as e:
                    self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

                msg = f"Cleared all constant materials. "
                msg += f"Restored {cleared_with_original} with original, {restored_with_fallback} with fallback."
                if errors > 0:
                    msg += f" Errors: {errors}."
                self.report({'INFO'}, msg)
                return {'FINISHED'}

            else:
                # Clear only the selected block

                selected_faces_indices = [i for i, poly in enumerate(obj.data.polygons) if poly.select]
                selected_verts_indices = [i for i, vert in enumerate(obj.data.vertices) if vert.select]

                face_to_quadblock = obj.get("face_to_quadblock", {})
                face_to_triblock = obj.get("face_to_triblock", {})

                block_type = None
                block_id = None

                if selected_faces_indices:
                    for face_idx in selected_faces_indices:
                        face_index = str(face_idx)
                        if face_index in face_to_quadblock:
                            block_type = "quadblock"
                            block_id = int(face_to_quadblock[face_index])
                            break
                        elif face_index in face_to_triblock:
                            block_type = "triblock"
                            block_id = int(face_to_triblock[face_index])
                            break

                elif selected_verts_indices and len(selected_verts_indices) == 1:
                    vert_idx = selected_verts_indices[0]
                    if "quadblock_centers" in obj and vert_idx in obj["quadblock_centers"]:
                        block_type = "quadblock"
                        block_id = vert_idx

                if block_type and block_id is not None:
                    const_prop_name = f"constant_name_{block_type}_{block_id}"
                    if const_prop_name not in obj:
                        self.report({'WARNING'}, f"No constant name found for {block_type} {block_id}")
                        return {'CANCELLED'}

                    material_name = obj[const_prop_name]

                    if "constant_materials" not in obj or material_name not in obj["constant_materials"]:
                        self.report({'WARNING'}, f"Constant material '{material_name}' not found in registry.")
                        return {'CANCELLED'}

                    block_info = obj["constant_materials"][material_name]
                    original_material_name = block_info.get("original_material", "")

                    # Find original material
                    original_material = None
                    if original_material_name and original_material_name in bpy.data.materials:
                        original_material = bpy.data.materials[original_material_name]

                    # Get faces of this block
                    block_faces = []
                    for i, poly in enumerate(obj.data.polygons):
                        if poly.material_index < len(obj.material_slots):
                            slot = obj.material_slots[poly.material_index]
                            if slot.material and slot.material.name == material_name:
                                block_faces.append(i)

                    if not block_faces:
                        self.report({'WARNING'}, f"No faces found with material '{material_name}'")
                        return {'CANCELLED'}

                    if not original_material:
                        if self.fallback_duplicate:
                            const_mat = bpy.data.materials.get(material_name)
                            if const_mat:
                                base_name = material_name.rsplit('_ID', 1)[0] if '_ID' in material_name else material_name
                                new_mat_name, new_index = create_base_material_from_constant(material_name)
                                if new_mat_name:
                                    for face_idx in block_faces:
                                        obj.data.polygons[face_idx].material_index = new_index
                                    obj.data.update()
                                    self.report({'INFO'}, f"Restored block using fallback material '{new_mat_name}'")
                                else:
                                    self.report({'ERROR'}, "Failed to create fallback material.")
                                    return {'CANCELLED'}
                            else:
                                self.report({'ERROR'}, f"Constant material '{material_name}' not found in bpy.data.materials.")
                                return {'CANCELLED'}
                        else:
                            self.report({'WARNING'}, f"Original material '{original_material_name}' not found and fallback not enabled.")

                            self.report({'ERROR'}, "Original material missing and fallback disabled. Operation cancelled.")
                            return {'CANCELLED'}
                    else:
                        # Restore original
                        if original_material_name not in obj.data.materials:
                            obj.data.materials.append(original_material)
                        original_mat_index = obj.data.materials.find(original_material_name)
                        for face_idx in block_faces:
                            obj.data.polygons[face_idx].material_index = original_mat_index
                        obj.data.update()

                    # Remove constant material data
                    del obj["constant_materials"][material_name]
                    del obj[const_prop_name]

                    # Delete the constant material if no longer used
                    if material_name in bpy.data.materials:
                        mat = bpy.data.materials[material_name]
                        if mat.users == 0:
                            bpy.data.materials.remove(mat)

                    try:
                        bpy.ops.object.material_slot_remove_unused()
                    except Exception as e:
                        self.report({'WARNING'}, f"Could not remove unused material slots: {e}")

                    self.report({'INFO'}, f"Cleared constant name from {block_type} {block_id}")
                else:
                    self.report({'WARNING'}, "Could not identify a block to clear. Select a block first.")

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