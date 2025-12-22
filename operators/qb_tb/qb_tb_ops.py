import bpy
import time
from bpy.types import Operator
from bpy.props import BoolProperty

from ...utils.qb_tb.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb.qb_tb_naming import build_object_name, clean_object_name


class QB_TB_OT_ObjectQbTbSuffix(Operator):
    """Operator to find and label QuadBlocks or TriBlocks based on selection"""
    bl_idname = "qb_tb.object_qb_tb_suffix"
    bl_label = "Add QB/TB Suffix"
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
    """Validate all objects and optionally remove invalid ones by category"""
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
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0

        invalid_geometry_objects = []
        invalid_uvs_objects = []
        degenerated_uvs_objects = []
        all_invalid_objects = set()
        
        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
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

        objects_to_remove = set()
        
        if self.remove_invalid_geometry:
            for obj in invalid_geometry_objects:
                if obj and obj.name in bpy.data.objects:
                    objects_to_remove.add(obj)
                    
        if self.remove_invalid_uvs:
            for obj in invalid_uvs_objects:
                if obj and obj.name in bpy.data.objects:
                    objects_to_remove.add(obj)
                    
        if self.remove_degenerated_uvs:
            for obj in degenerated_uvs_objects:
                if obj and obj.name in bpy.data.objects:
                    objects_to_remove.add(obj)

        removed_count = 0
        removed_geometry = 0
        removed_uvs = 0
        removed_degenerated = 0
        
        for obj in objects_to_remove:
            if obj and obj.name in bpy.data.objects:
                try:
                    issues = get_object_issues(obj)
                    if "non_mesh" in issues or "ngon" in issues or "invalid_geometry" in issues:
                        removed_geometry += 1
                    if "invalid_uvs" in issues:
                        removed_uvs += 1
                    if "degenerated_uvs" in issues:
                        removed_degenerated += 1
                        
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                except ReferenceError:
                    continue
                except Exception as e:
                    print(f"Error removing object {obj.name}: {e}")
            else:
                continue

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
    """Select objects based on various QB/TB criteria and validation issues"""
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select Object Types"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        select_option = context.scene.select_option
        
        bpy.ops.object.select_all(action='DESELECT')
        
        count = 0
        selected_objects = []
        
        for obj in list(bpy.data.objects):
            select_this = False
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            if select_option == 'ALL_INVALID':
                if issues:
                    select_this = True
            
            elif select_option == 'INVALID_GEOMETRY':
                if "ngon" in issues or "invalid_geometry" in issues or "non_mesh" in issues:
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
            
            if select_this:
                try:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                        count += 1
                except Exception as e:
                    print(f"Could not select {obj.name if hasattr(obj, 'name') else 'Unknown object'}: {e}")
        
        if selected_objects:
            for obj in selected_objects:
                try:
                    if obj and obj.name in bpy.data.objects:
                        context.view_layer.objects.active = obj
                        break
                except Exception as e:
                    print(f"Could not set active object {obj.name if hasattr(obj, 'name') else 'Unknown object'}: {e}")
                    continue
        
        self.report({'INFO'}, f"Selected {count} objects.")
        return {'FINISHED'}


class QB_TB_OT_CleanObjectSuffixes(Operator):
    """Reset all object names by removing QB/TB suffixes and validation markers"""
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Clean Suffix"
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