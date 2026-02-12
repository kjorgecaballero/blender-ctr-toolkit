"""
Compatibility module for handling Blender version differences
"""

import bpy


def get_blender_version():
    """Return Blender version as tuple (major, minor, patch)"""
    return bpy.app.version


def should_use_wm_obj_export():
    """
    Determine if we should use wm.obj_export (Blender 3.3+) 
    or export_scene.obj (older versions)
    """
    # Blender 3.3.0 and above have wm.obj_export
    return hasattr(bpy.ops.wm, 'obj_export')


def get_export_parameters(export_ops_instance, valid_objects):
    """
    Prepare export parameters based on Blender version
    
    Args:
        export_ops_instance: Instance of QB_TB_OT_ExportQuadTriBlocks
        valid_objects: List of objects to export
        
    Returns:
        dict: Export parameters for current Blender version
    """
    if should_use_wm_obj_export():
        # PARAMETERS FOR wm.obj_export (Blender 3.3.0+)
        params = {
            'filepath': export_ops_instance.filepath,
            'export_selected_objects': True,
            'export_triangulated_mesh': False,  # Or True if triangulation is desired
            'export_normals': True,
            'export_uv': True,
            'export_materials': True,
            'export_colors': export_ops_instance.export_colors,
            # Use the path_mode selected by the user
            'path_mode': export_ops_instance.path_mode,
        }
        
        # Note: wm.obj_export in Blender 3.3.0 does NOT accept global_scale or apply_modifiers
        # Therefore, they are not included. They are handled manually.
        return params
    else:
        # PARAMETERS FOR export_scene.obj (older versions)
        params = {
            'filepath': export_ops_instance.filepath,
            'use_selection': True,
            'use_normals': True,
            'use_uvs': True,
            'use_materials': True,
            'use_triangles': False,
            'use_vertex_colors': export_ops_instance.export_colors,
            'global_scale': export_ops_instance.global_scale,
            # Use the path_mode selected by the user
            'path_mode': export_ops_instance.path_mode,
            'axis_forward': '-Z',
            'axis_up': 'Y',
        }
        
        # Add conditional parameters if they exist in this version
        if hasattr(bpy.ops.export_scene.obj, 'keywords'):
            keywords = bpy.ops.export_scene.obj.keywords
            if 'use_mesh_modifiers' in keywords:
                params['use_mesh_modifiers'] = False  # Already applied modifiers before
            if 'use_textures' in keywords:
                params['use_textures'] = export_ops_instance.export_textures
        
        return params


def apply_scale_to_objects(objects, scale):
    """
    Apply scale to objects manually (for versions that don't support global_scale)
    
    Returns:
        dict: Original scales for restoration
    """
    original_scales = {}
    
    if scale != 1.0:
        for obj in objects:
            if obj and obj.name in bpy.data.objects:
                original_scales[obj] = (obj.scale.x, obj.scale.y, obj.scale.z)
                obj.scale.x *= scale
                obj.scale.y *= scale
                obj.scale.z *= scale
        
        # Update view to apply changes
        bpy.context.view_layer.update()
    
    return original_scales


def restore_scale_to_objects(original_scales):
    """Restore original scales to objects"""
    if original_scales:
        for obj, scale in original_scales.items():
            if obj and obj.name in bpy.data.objects:
                obj.scale.x = scale[0]
                obj.scale.y = scale[1]
                obj.scale.z = scale[2]
        
        bpy.context.view_layer.update()


def execute_obj_export(export_ops_instance, valid_objects):
    """
    Execute OBJ export with version-specific handling
    
    Args:
        export_ops_instance: Instance of QB_TB_OT_ExportQuadTriBlocks
        valid_objects: List of objects to export
        
    Returns:
        Result of the export operation
    """
    try:
        # Save original scales for restoration
        original_scales = {}
        
        # Apply scale manually if needed
        if should_use_wm_obj_export() and export_ops_instance.global_scale != 1.0:
            # wm.obj_export in Blender 3.3.0 doesn't accept global_scale
            # Apply manually
            original_scales = apply_scale_to_objects(
                valid_objects, 
                export_ops_instance.global_scale
            )
        
        # Get export parameters based on version
        export_params = get_export_parameters(export_ops_instance, valid_objects)
        
        # Execute export
        if should_use_wm_obj_export():
            result = bpy.ops.wm.obj_export(**export_params)
        else:
            result = bpy.ops.export_scene.obj(**export_params)
        
        # Restore scales if we changed them
        if original_scales:
            restore_scale_to_objects(original_scales)
        
        return result
        
    except Exception as e:
        # Ensure scale restoration even on error
        if 'original_scales' in locals():
            restore_scale_to_objects(original_scales)
        
        print(f"Error in execute_obj_export: {e}")
        import traceback
        traceback.print_exc()
        return {'CANCELLED'}


def get_export_operator_name():
    """Get the correct export operator name for current Blender version"""
    return 'wm.obj_export' if should_use_wm_obj_export() else 'export_scene.obj'


def has_vertex_colors_support():
    """Check if current Blender version supports vertex colors in OBJ export"""
    if should_use_wm_obj_export():
        return True  # wm.obj_export supports export_colors
    else:
        return hasattr(bpy.ops.export_scene.obj, 'keywords') and \
               'use_vertex_colors' in bpy.ops.export_scene.obj.keywords


def ensure_objects_in_view_layer(objects, context):
    """
    Ensure objects are in the active view layer for selection and operations
    
    Args:
        objects: List of objects to ensure are in view layer
        context: Blender context
    
    Returns:
        list: Objects that were temporarily linked to view layer
    """
    temporarily_linked = []
    
    for obj in objects:
        if obj and obj.name in bpy.data.objects:
            # Check if object is in the active view layer
            if obj.name not in context.view_layer.objects:
                # Link to scene collection if not already linked
                scene_collection_names = [c.name for c in obj.users_collection]
                if context.scene.collection.name not in scene_collection_names:
                    try:
                        context.scene.collection.objects.link(obj)
                        temporarily_linked.append(obj)
                        print(f"Temporarily linked {obj.name} to view layer")
                    except Exception as e:
                        print(f"Could not link {obj.name} to view layer: {e}")
                
                # Make sure object is visible
                obj.hide_viewport = False
                obj.hide_set(False)
                obj.hide_select = False
    
    return temporarily_linked


def cleanup_temporarily_linked_objects(temporarily_linked, context):
    """
    Clean up temporarily linked objects from view layer
    
    Args:
        temporarily_linked: List of objects to unlink
        context: Blender context
    """
    for obj in temporarily_linked:
        if obj and obj.name in bpy.data.objects:
            try:
                # Check if object is in multiple collections
                collections = obj.users_collection
                if len(collections) > 1:
                    # Unlink from scene collection if it's there
                    for coll in collections:
                        if coll.name == context.scene.collection.name:
                            coll.objects.unlink(obj)
                            print(f"Unlinked {obj.name} from temporary view layer")
                            break
            except Exception as e:
                print(f"Error unlinking {obj.name}: {e}")