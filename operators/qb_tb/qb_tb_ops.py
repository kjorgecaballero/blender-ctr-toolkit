import bpy
import time
from bpy.types import Operator
from bpy.props import BoolProperty

# Import from utils with correct relative path
from ...utils.qb_tb.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb.qb_tb_naming import build_object_name, clean_object_name

class QB_TB_OT_ObjectQbTbSuffix(Operator):
    """Find objects based on the selected option."""
    bl_idname = "qb_tb.object_qb_tb_suffix"
    bl_label = "Find QB/TB"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        find_option = context.scene.find_option

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=0)
        start_time = time.time()

        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        count = 0

        for obj in mesh_objects:
            mesh_type = get_mesh_type(obj)
            issues = get_object_issues(obj)
            
            # Clean base name
            base_name = clean_object_name(obj.name)
            
            if find_option == 'TRIBLOCK' and mesh_type == 'TRIBLOCK':
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1
            elif find_option == 'QUADBLOCK' and mesh_type == 'QUADBLOCK':
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1

        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"Found {count} {find_option.lower()} objects in {elapsed_time:.2f} seconds.")
        return {'FINISHED'}

class QB_TB_OT_ValidateAllObjects(Operator):
    """Validate all objects for correct geometry and UVs."""
    bl_idname = "qb_tb.validate_all_objects"
    bl_label = "Validate QB/TB"
    bl_options = {'REGISTER', 'UNDO'}

    remove_invalid: BoolProperty(
        name="Remove Invalid Objects Automatically",
        description="If enabled, invalid objects will be automatically deleted after validation",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Counters
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0
        mixed_issues_count = 0

        # List to store invalid objects that might be removed
        invalid_objects = []

        for obj in bpy.data.objects:
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            # Clean base name
            base_name = clean_object_name(obj.name)
            
            # Build new name with all problems
            new_name = build_object_name(base_name, mesh_type, issues)
            obj.name = new_name
            
            # Count statistics
            if "non_mesh" in issues:
                non_mesh_count += 1
                invalid_objects.append(obj)
            elif "ngon" in issues:
                ngon_count += 1
                invalid_objects.append(obj)
            elif "invalid_geometry" in issues:
                geometry_invalid_count += 1
                invalid_objects.append(obj)
            else:
                # Valid geometry
                if mesh_type == 'TRIBLOCK':
                    triblock_count += 1
                elif mesh_type == 'QUADBLOCK':
                    quadblock_count += 1
            
            # Count UV problems
            if "invalid_uvs" in issues:
                uvs_invalid_count += 1
            if "degenerated_uvs" in issues:
                degenerated_uvs_count += 1
            
            # Count objects with multiple problems
            if len(issues) > 1:
                mixed_issues_count += 1

        # If auto-remove option is enabled, delete invalid objects
        removed_count = 0
        if self.remove_invalid and invalid_objects:
            removed_count = len(invalid_objects)
            for obj in invalid_objects:
                bpy.data.objects.remove(obj, do_unlink=True)

        # Report message
        if self.remove_invalid:
            self.report({'INFO'}, f"Validated: {triblock_count} triblocks, {quadblock_count} quadblocks. Removed {removed_count} invalid objects.")
        else:
            total_invalid = non_mesh_count + ngon_count + geometry_invalid_count
            self.report({'INFO'}, f"Found {triblock_count} triblocks, {quadblock_count} quadblocks. {total_invalid} invalid ({non_mesh_count} non-mesh, {ngon_count} NGons, {geometry_invalid_count} invalid geometry), {uvs_invalid_count} bad UVs, {degenerated_uvs_count} degenerated UVs, {mixed_issues_count} mixed issues.")

        return {'FINISHED'}

class QB_TB_OT_FilterSelectObjects(Operator):
    """Select objects based on the selected option."""
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select QB/TB"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        select_option = context.scene.select_option
        
        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')
        
        count = 0
        selected_objects = []
        
        for obj in bpy.data.objects:
            select_this = False
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            if select_option == 'ALL_INVALID':
                #  will select all objects with ANY issues
                if issues:
                    select_this = True
            
            elif select_option == 'INVALID_GEOMETRY':
                if "ngon" in issues or "invalid_geometry" in issues:
                    select_this = True
            
            elif select_option == 'INVALID_UVS':
                if "invalid_uvs" in issues:
                    select_this = True
            
            elif select_option == 'DEGENERATED_UVS':
                if "degenerated_uvs" in issues:
                    select_this = True
            
            elif select_option == 'TRIBLOCKS':
                if mesh_type == 'TRIBLOCK':
                    select_this = True
            
            elif select_option == 'QUADBLOCKS':
                if mesh_type == 'QUADBLOCK':
                    select_this = True
            
            elif select_option == 'NON_MESH':
                if "non_mesh" in issues:
                    select_this = True
            
            elif select_option == 'NGONS':
                if "ngon" in issues:
                    select_this = True
            
            elif select_option == 'MIXED_ISSUES':
                if len(issues) > 1:
                    select_this = True
            
            if select_this:
                try:
                    obj.select_set(True)
                    selected_objects.append(obj)
                    count += 1
                except Exception as e:
                    print(f"Could not select {obj.name}: {e}")
        
        # Set the active object if any objects are selected
        if selected_objects:
            try:
                context.view_layer.objects.active = selected_objects[0]
            except Exception as e:
                print(f"Could not set active object: {e}")
                for obj in selected_objects:
                    try:
                        context.view_layer.objects.active = obj
                        break
                    except:
                        continue
        
        self.report({'INFO'}, f"Selected {count} objects.")
        return {'FINISHED'}

class QB_TB_OT_CleanObjectSuffixes(Operator):
    """Remove suffixes from all objects."""
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Reset QB/TB Names"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in bpy.data.objects:
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