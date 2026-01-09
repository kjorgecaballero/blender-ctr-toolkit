import bpy
import time
from bpy.types import Operator
from bpy.props import BoolProperty

# External modules for mesh analysis and naming conventions
from ...utils.qb_tb.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb.qb_tb_naming import build_object_name, clean_object_name


class QB_TB_OT_ObjectQbTbSuffix(Operator):
    """Apply mesh-type suffixes to appropriate objects"""
    bl_idname = "qb_tb.object_qb_tb_suffix"
    bl_label = "Add QB/TB Suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Retrieve current filter setting
        find_option = context.scene.find_option

        # Refresh viewport for visual feedback
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=0)
        start_time = time.time()

        # Process only mesh objects
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        count = 0

        for obj in mesh_objects:
            # Analyze mesh properties
            mesh_type = get_mesh_type(obj)
            issues = get_object_issues(obj)
            
            # Prepare base name without existing suffixes
            base_name = clean_object_name(obj.name)
            
            # Apply suffix only to matching mesh types
            if find_option == 'TRIBLOCK' and mesh_type == 'TRIBLOCK':
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1
            elif find_option == 'QUADBLOCK' and mesh_type == 'QUADBLOCK':
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1

        # Report processing results
        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"Found {count} {find_option.lower()} objects in {elapsed_time:.2f} seconds.")
        return {'FINISHED'}


class QB_TB_OT_ValidateAllObjects(Operator):
    """Comprehensive validation with optional cleanup"""
    bl_idname = "qb_tb.validate_all_objects"
    bl_label = "Validate All Objects"
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

    def invoke(self, context, event):
        # Display settings dialog before execution
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Initialize counters
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0

        # Collections for problematic objects
        invalid_geometry_objects = []
        invalid_uvs_objects = []
        degenerated_uvs_objects = []
        all_invalid_objects = set()
        
        # Process each scene object
        for obj in list(bpy.data.objects):
            # Skip if object no longer exists
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            # Gather object metadata
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            # Apply standardized naming
            base_name = clean_object_name(obj.name)
            new_name = build_object_name(base_name, mesh_type, issues)
            obj.name = new_name
            
            # Categorize geometry issues
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
                # Count valid mesh types
                if mesh_type == 'TRIBLOCK':
                    triblock_count += 1
                elif mesh_type == 'QUADBLOCK':
                    quadblock_count += 1
            
            # Track UV-related issues
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

        # Determine which objects to purge
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

        # Perform cleanup and track results
        removed_count = 0
        removed_geometry = 0
        removed_uvs = 0
        removed_degenerated = 0
        
        for obj in objects_to_remove:
            if obj and obj.name in bpy.data.objects:
                try:
                    issues = get_object_issues(obj)
                    # Classify removal reason
                    if any(issue in issues for issue in ["non_mesh", "ngon", "invalid_geometry"]):
                        removed_geometry += 1
                    if any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"]):
                        removed_uvs += 1
                    if "degenerated_uvs" in issues:
                        removed_degenerated += 1
                        
                    # Remove object from scene
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                except ReferenceError:
                    continue
                except Exception as e:
                    print(f"Error removing object {obj.name}: {e}")

        # Compose summary message
        message_parts = []
        message_parts.append(f"Validated: {triblock_count} triblocks, {quadblock_count} quadblocks.")
        
        if removed_count > 0:
            message_parts.append(f"Removed {removed_count} objects:")
            if removed_geometry > 0:
                message_parts.append(f"- {removed_geometry} invalid geometry")
            if removed_uvs > 0:
                message_parts.append(f"- {removed_uvs} invalid UVs")
            if removed_degenerated > 0:
                message_parts.append(f"- {removed_degenerated} degenerated UVs")
        else:
            total_invalid = non_mesh_count + ngon_count + geometry_invalid_count
            message_parts.append(f"Found {total_invalid} invalid objects:")
            message_parts.append(f"- {non_mesh_count} non-mesh")
            message_parts.append(f"- {ngon_count} NGons")
            message_parts.append(f"- {geometry_invalid_count} invalid geometry")
            message_parts.append(f"- {uvs_invalid_count} invalid UVs")
            message_parts.append(f"- {degenerated_uvs_count} degenerated UVs")

        self.report({'INFO'}, " ".join(message_parts))
        return {'FINISHED'}


class QB_TB_OT_FilterSelectObjects(Operator):
    """Batch selection based on object properties"""
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select Object Types"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Clear existing selection
        for obj in context.selected_objects:
            obj.select_set(False)
        
        select_option = context.scene.select_option
        count = 0
        selected_objects = []
        
        # Evaluate each object against selection criteria
        for obj in list(bpy.data.objects):
            select_this = False
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            # Selection logic based on current filter
            if select_option == 'ALL_INVALID':
                select_this = bool(issues)
            
            elif select_option == 'INVALID_GEOMETRY':
                select_this = any(issue in issues for issue in ["ngon", "invalid_geometry", "non_mesh"])
            
            elif select_option == 'INVALID_UVS':
                select_this = any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"])
            
            elif select_option == 'DEGENERATED_UVS':
                select_this = "degenerated_uvs" in issues
            
            elif select_option == 'INVALID_TRIBLOCK_UVS':
                select_this = "invalid_triblock_uvs" in issues
            
            elif select_option == 'TRIBLOCKS':
                select_this = mesh_type == 'TRIBLOCK'
            
            elif select_option == 'QUADBLOCKS':
                select_this = mesh_type == 'QUADBLOCK'
            
            elif select_option == 'NON_MESH':
                select_this = "non_mesh" in issues
            
            elif select_option == 'NGONS':
                select_this = "ngon" in issues
            
            # Apply selection if criteria met
            if select_this:
                try:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                        count += 1
                except Exception as e:
                    print(f"Selection failed for {obj.name if hasattr(obj, 'name') else 'Unknown object'}: {e}")
        
        # Set active object for convenience
        if selected_objects and context.view_layer.objects.active is None:
            try:
                context.view_layer.objects.active = selected_objects[0]
            except Exception as e:
                print(f"Failed to set active object: {e}")
        
        self.report({'INFO'}, f"Selected {count} objects.")
        return {'FINISHED'}


class QB_TB_OT_CleanObjectSuffixes(Operator):
    """Strip all QB/TB suffixes from object names"""
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Clean Suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        # Remove suffixes from all scene objects
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
    """Register operators with Blender"""
    bpy.utils.register_class(QB_TB_OT_ObjectQbTbSuffix)
    bpy.utils.register_class(QB_TB_OT_ValidateAllObjects)
    bpy.utils.register_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.register_class(QB_TB_OT_CleanObjectSuffixes)


def unregister():
    """Remove operators from Blender"""
    bpy.utils.unregister_class(QB_TB_OT_CleanObjectSuffixes)
    bpy.utils.unregister_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.unregister_class(QB_TB_OT_ValidateAllObjects)
    bpy.utils.unregister_class(QB_TB_OT_ObjectQbTbSuffix)