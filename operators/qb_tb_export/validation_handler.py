import bpy
from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.range_box import get_out_of_range_objects

class ValidationHandler:
    """
    Validates and filters objects based on export settings.
    
    Responsibilities:
    - Filter objects by type (Quadblock/Triblock)
    - Validate UV issues (invalid, degenerated, triblock-specific, missing)
    - Apply range box filtering
    - Collect export statistics for reporting
    """
    
    def filter_valid_objects(self, objects, settings):
        """
        Filter objects based on export settings and validation rules.
        
        Args:
            objects: List of Blender objects to filter
            settings: ExportSettings object with filter preferences
            
        Returns:
            tuple: (filtered_objects, statistics_dict)
        """
        valid_objects = []
        stats = {
            'quadblocks': 0,
            'triblocks': 0,
            'total_exported': 0,
            'exported_with_uv_issues': 0,
            'objects_with_uv_issues': [],
            'total_quadblocks_found': 0,
            'total_triblocks_found': 0,
            'out_of_range_filtered': 0,
            'out_of_range_names': []
        }
        
        for obj in objects:
            if obj.type != 'MESH':
                continue
            
            # Determine mesh type (Quadblock, Triblock, or None)
            mesh_type = get_mesh_type(obj)
            if mesh_type is None:  
                continue
            
            # Count all found objects by type
            if mesh_type == 'QUADBLOCK':
                stats['total_quadblocks_found'] += 1
            elif mesh_type == 'TRIBLOCK':
                stats['total_triblocks_found'] += 1
            
            # Filter by enabled block types
            if mesh_type == 'QUADBLOCK' and not settings.export_quadblocks:
                continue
            if mesh_type == 'TRIBLOCK' and not settings.export_triblocks:
                continue
            
            # Check for issues
            issues = get_object_issues(obj)
            has_uv_issues = any('uv' in issue for issue in issues)
            
            # Apply UV issue filters
            if 'invalid_uvs' in issues and not settings.export_invalid_uvs:
                continue
            if 'invalid_triblock_uvs' in issues and not settings.export_invalid_triblock_uvs:
                continue
            if 'degenerated_uvs' in issues and not settings.export_degenerated_uvs:
                continue
            if 'missing_uvs' in issues and not settings.export_missing_uvs:
                continue
            
            # Apply multiple materials filter
            if 'multiple_materials' in issues and not settings.export_multiple_materials:
                continue
            
            # Object passed all filters
            valid_objects.append(obj)
            stats['total_exported'] += 1
            
            if mesh_type == 'QUADBLOCK':
                stats['quadblocks'] += 1
            elif mesh_type == 'TRIBLOCK':
                stats['triblocks'] += 1
            
            # Track objects with UV issues that were exported
            if has_uv_issues:
                stats['exported_with_uv_issues'] += 1
                stats['objects_with_uv_issues'].append(obj.name)
        
        # Apply range box filtering if enabled
        if not settings.allow_out_of_range:
            in_range_objects, out_of_range_objects = get_out_of_range_objects(valid_objects)
            
            if out_of_range_objects:
                print(f"  Filtered {len(out_of_range_objects)} objects outside Range Box")
                stats['out_of_range_filtered'] = len(out_of_range_objects)
                stats['out_of_range_names'] = [obj.name for obj in out_of_range_objects]
            
            valid_objects = in_range_objects
        
        return valid_objects, stats