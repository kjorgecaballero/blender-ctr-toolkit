import bpy
import time
from bpy.types import Operator
from bpy.props import BoolProperty

from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb_validator.qb_tb_naming import build_object_name, clean_object_name


class QB_TB_OT_ObjectQbTbSuffix(Operator):
    bl_idname = "qb_tb.object_qb_tb_suffix"
    bl_label = "Add Suffix"
    bl_description = "Add suffix to objects based on their type (uses current validator option)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        option = context.scene.validator_option  # Unified option

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=0)
        start_time = time.time()

        all_objects = bpy.data.objects
        count = 0

        for obj in all_objects:
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            base_name = clean_object_name(obj.name)
            
            match = False
            if option == 'QUADBLOCK':
                match = (mesh_type == 'QUADBLOCK')
            elif option == 'TRIBLOCK':
                match = (mesh_type == 'TRIBLOCK')
            elif option == 'INVALID_GEOMETRY':
                match = any(issue in issues for issue in ["ngon", "invalid_geometry", "non_mesh"])
            elif option == 'INVALID_UVS':
                match = any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"])
            elif option == 'INVALID_TRIBLOCK_UVS':
                match = "invalid_triblock_uvs" in issues
            elif option == 'DEGENERATED_UVS':
                match = "degenerated_uvs" in issues
            elif option == 'NGONS':
                match = "ngon" in issues
            elif option == 'NON_MESH':
                match = "non_mesh" in issues
            elif option == 'OUT_OF_RANGE':
                match = "out_of_range" in issues
            elif option == 'ALL_INVALID':
                match = bool(issues)
            
            if match:
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1

        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"Found {count} objects matching '{option}' in {elapsed_time:.2f} seconds.")
        return {'FINISHED'}


class QB_TB_OT_ValidateAllObjects(Operator):
    bl_idname = "qb_tb.validate_all_objects"
    bl_label = "Validate All Objects"
    bl_description = "Validate all objects and optionally remove invalid ones"
    bl_options = {'REGISTER', 'UNDO'}

    remove_invalid_geometry: BoolProperty(
        name="Remove Invalid Geometry Objects",
        description="Remove non-mesh, NGons and invalid geometry objects",
        default=False
    )

    remove_invalid_uvs: BoolProperty(
        name="Remove Invalid UVs Objects",
        description="Remove objects with invalid UVs",
        default=False
    )

    remove_degenerated_uvs: BoolProperty(
        name="Remove Degenerated UVs Objects",
        description="Remove objects with degenerated UVs",
        default=False
    )

    remove_out_of_range: BoolProperty(
        name="Remove Out of Range Objects",
        description="Remove objects that are outside the 1000x1000x1000 range box",
        default=False
    )

    add_suffixes: BoolProperty(
        name="Add Suffixes to Objects",
        description="Add suffixes to object names based on their type and issues",
        default=True
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0
        out_of_range_count = 0

        invalid_geometry_objects = []
        invalid_uvs_objects = []
        degenerated_uvs_objects = []
        out_of_range_objects = []
        all_invalid_objects = set()
        
        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            if self.add_suffixes:
                base_name = clean_object_name(obj.name)
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
            
            if "non_mesh" in issues:
                non_mesh_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            elif "ngon" in issues:
                ngon_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            elif "invalid_geometry" in issues:
                geometry_invalid_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            else:
                if mesh_type == 'TRIBLOCK':
                    triblock_count += 1
                elif mesh_type == 'QUADBLOCK':
                    quadblock_count += 1
            
            if "invalid_uvs" in issues:
                uvs_invalid_count += 1
                invalid_uvs_objects.append(obj)
                all_invalid_objects.add(obj)
                
            if "degenerated_uvs" in issues:
                degenerated_uvs_count += 1
                degenerated_uvs_objects.append(obj)
                all_invalid_objects.add(obj)
                
            if "invalid_triblock_uvs" in issues:
                uvs_invalid_count += 1
                invalid_uvs_objects.append(obj)
                all_invalid_objects.add(obj)
                
            if "out_of_range" in issues:
                out_of_range_count += 1
                out_of_range_objects.append(obj)
                all_invalid_objects.add(obj)

        objects_to_remove = set()
        
        if self.remove_invalid_geometry:
            objects_to_remove.update(obj for obj in invalid_geometry_objects 
                                   if obj and obj.name in bpy.data.objects)
                    
        if self.remove_invalid_uvs:
            objects_to_remove.update(obj for obj in invalid_uvs_objects 
                                   if obj and obj.name in bpy.data.objects)
                    
        if self.remove_degenerated_uvs:
            objects_to_remove.update(obj for obj in degenerated_uvs_objects 
                                   if obj and obj.name in bpy.data.objects)

        if self.remove_out_of_range:
            objects_to_remove.update(obj for obj in out_of_range_objects 
                                   if obj and obj.name in bpy.data.objects)

        removed_count = 0
        removed_geometry = 0
        removed_uvs = 0
        removed_degenerated = 0
        removed_out_of_range = 0
        
        for obj in objects_to_remove:
            if obj and obj.name in bpy.data.objects:
                try:
                    issues = get_object_issues(obj)
                    if any(issue in issues for issue in ["non_mesh", "ngon", "invalid_geometry"]):
                        removed_geometry += 1
                    if any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"]):
                        removed_uvs += 1
                    if "degenerated_uvs" in issues:
                        removed_degenerated += 1
                    if "out_of_range" in issues:
                        removed_out_of_range += 1
                        
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                except ReferenceError:
                    continue
                except Exception as e:
                    print(f"Error removing object {obj.name}: {e}")

        message_parts = []
        suffix_status = "renamed" if self.add_suffixes else "validated"
        message_parts.append(f"{suffix_status.capitalize()}: {triblock_count} triblocks, {quadblock_count} quadblocks.")
        
        if removed_count > 0:
            message_parts.append(f"Removed {removed_count} objects:")
            if removed_geometry > 0:
                message_parts.append(f"- {removed_geometry} invalid geometry")
            if removed_uvs > 0:
                message_parts.append(f"- {removed_uvs} invalid UVs")
            if removed_degenerated > 0:
                message_parts.append(f"- {removed_degenerated} degenerated UVs")
            if removed_out_of_range > 0:
                message_parts.append(f"- {removed_out_of_range} out of range")
        else:
            total_invalid = non_mesh_count + ngon_count + geometry_invalid_count
            message_parts.append(f"Found {total_invalid} invalid objects:")
            message_parts.append(f"- {non_mesh_count} non-mesh")
            message_parts.append(f"- {ngon_count} NGons")
            message_parts.append(f"- {geometry_invalid_count} invalid geometry")
            message_parts.append(f"- {uvs_invalid_count} invalid UVs")
            message_parts.append(f"- {degenerated_uvs_count} degenerated UVs")
            message_parts.append(f"- {out_of_range_count} out of range")

        self.report({'INFO'}, " ".join(message_parts))
        return {'FINISHED'}


class QB_TB_OT_FilterSelectObjects(Operator):
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select Object Types"
    bl_description = "Select objects based on their type (uses current validator option)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        option = context.scene.validator_option  # Unified option

        # Deselect all
        for obj in context.selected_objects:
            obj.select_set(False)
        
        count = 0
        selected_objects = []
        
        for obj in list(bpy.data.objects):
            select_this = False
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            if option == 'ALL_INVALID':
                select_this = bool(issues)
            elif option == 'INVALID_GEOMETRY':
                select_this = any(issue in issues for issue in ["ngon", "invalid_geometry", "non_mesh"])
            elif option == 'INVALID_UVS':
                select_this = any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"])
            elif option == 'DEGENERATED_UVS':
                select_this = "degenerated_uvs" in issues
            elif option == 'INVALID_TRIBLOCK_UVS':
                select_this = "invalid_triblock_uvs" in issues
            elif option == 'TRIBLOCK':  
                select_this = mesh_type == 'TRIBLOCK'
            elif option == 'QUADBLOCK':
                select_this = mesh_type == 'QUADBLOCK'
            elif option == 'NON_MESH':
                select_this = "non_mesh" in issues
            elif option == 'NGONS':
                select_this = "ngon" in issues
            elif option == 'OUT_OF_RANGE':
                select_this = "out_of_range" in issues
            
            if select_this:
                try:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                        count += 1
                except Exception as e:
                    print(f"Selection failed for {obj.name if hasattr(obj, 'name') else 'Unknown object'}: {e}")
        
        if selected_objects and context.view_layer.objects.active is None:
            try:
                context.view_layer.objects.active = selected_objects[0]
            except Exception as e:
                print(f"Failed to set active object: {e}")
        
        self.report({'INFO'}, f"Selected {count} objects.")
        return {'FINISHED'}


class QB_TB_OT_CleanObjectSuffixes(Operator):
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Clean Suffix"
    bl_description = "Clean all suffixes from object names"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            original_name = obj.name
            obj.name = clean_object_name(obj.name)
            if original_name != obj.name:
                count += 1
                
        self.report({'INFO'}, f"Reset {count} object names.")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(QB_TB_OT_ObjectQbTbSuffix)
    bpy.utils.register_class(QB_TB_OT_ValidateAllObjects)
    bpy.utils.register_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.register_class(QB_TB_OT_CleanObjectSuffixes)


def unregister():
    bpy.utils.unregister_class(QB_TB_OT_CleanObjectSuffixes)
    bpy.utils.unregister_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.unregister_class(QB_TB_OT_ValidateAllObjects)
    bpy.utils.unregister_class(QB_TB_OT_ObjectQbTbSuffix)