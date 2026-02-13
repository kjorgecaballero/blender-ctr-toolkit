"""
JSON details exporter for QB/TB export operations
"""

import json
import os
import bpy
from datetime import datetime
from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues


class DetailsExporter:
    """Handles export of JSON details for QB/TB exports"""
    
    def __init__(self):
        self.export_data = {}
    
    def collect_export_details(self, valid_objects, stats, settings, filepath, export_index):
        """Collect all export details into a dictionary"""
        
        # Basic export information with export index
        self.export_data = {
            "export_info": {
                "export_index": export_index,
                "timestamp": datetime.now().isoformat(),
                "blender_version": f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}",
                "ctr_toolkit_version": "0.0.2",
                "export_path": filepath,
                "filename": os.path.basename(filepath),
                "export_settings": {
                    "export_quadblocks": settings.export_quadblocks,
                    "export_triblocks": settings.export_triblocks,
                    "export_colors": settings.export_colors,
                    "export_textures": settings.export_textures,
                    "export_textures_to_folder": settings.export_textures_to_folder,
                    "apply_modifiers": settings.apply_modifiers,
                    "separate_loose_parts": settings.separate_loose_parts,
                    "global_scale": settings.global_scale,
                    "export_invalid_uvs": settings.export_invalid_uvs,
                    "export_degenerated_uvs": settings.export_degenerated_uvs,
                    "path_mode": settings.path_mode
                }
            },
            "statistics": {
                "total_objects_exported": stats['total_exported'],
                "quadblocks_count": stats['quadblocks'],
                "triblocks_count": stats['triblocks'],
                "objects_with_uv_issues": stats['exported_with_uv_issues'],
                "exported_folder": stats.get('exported_folder', None)
            },
            "objects_summary": self._get_objects_summary(valid_objects)
        }
        
        return self.export_data
    
    def _get_objects_summary(self, objects):
        """Get a detailed summary of objects with their issues"""
        summary = {
            "count": len(objects),
            "by_type": {},
            "by_issues": {},
            "objects_by_issue_type": {},
            "object_details": [],
            "object_names": []
        }
        
        # Initialize issue type categories
        all_issue_types = ["valid", "invalid_uvs", "degenerated_uvs", 
                          "invalid_triblock_uvs", "invalid_geometry", 
                          "ngon", "non_mesh"]
        for issue_type in all_issue_types:
            summary["objects_by_issue_type"][issue_type] = []
        
        for obj in objects:
            if obj and obj.name in bpy.data.objects:
                # Add object name to simple list
                summary["object_names"].append(obj.name)
                
                # Get object details
                mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else 'NON_MESH'
                issues = get_object_issues(obj)
                
                # Object details
                obj_detail = {
                    "name": obj.name,
                    "type": mesh_type,
                    "issues": issues,
                    "has_uv_issues": any('uv' in issue for issue in issues)
                }
                summary["object_details"].append(obj_detail)
                
                # Classify by issue type
                if not issues:
                    summary["objects_by_issue_type"]["valid"].append(obj.name)
                else:
                    for issue in issues:
                        if issue in summary["objects_by_issue_type"]:
                            summary["objects_by_issue_type"][issue].append(obj.name)
                
                # Count by type
                if mesh_type not in summary["by_type"]:
                    summary["by_type"][mesh_type] = 0
                summary["by_type"][mesh_type] += 1
                
                # Count by issues (compatibility with existing code)
                if issues:
                    for issue in issues:
                        if issue not in summary["by_issues"]:
                            summary["by_issues"][issue] = 0
                        summary["by_issues"][issue] += 1
                else:
                    if "valid" not in summary["by_issues"]:
                        summary["by_issues"]["valid"] = 0
                    summary["by_issues"]["valid"] += 1
        
        return summary
    
    def export_to_json(self, filepath, data):
        """Export collected data to JSON file"""
        
        # Create JSON filename based on OBJ filename
        obj_filename = os.path.basename(filepath)
        json_filename = os.path.splitext(obj_filename)[0] + f"_export_{data['export_info']['export_index']:04d}.json"
        json_path = os.path.join(os.path.dirname(filepath), json_filename)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f" Export details saved to: {json_path}")
            return json_path
            
        except Exception as e:
            print(f" Error saving export details: {e}")
            return None
    
    def get_summary_report(self, data, max_objects_per_list=5):
        """Generate a human-readable summary report"""
        
        stats = data["statistics"]
        export_info = data["export_info"]
        objects_summary = data["objects_summary"]
        
        summary = f"""
========================================
QB/TB EXPORT DETAILS SUMMARY
========================================
Export #{export_info['export_index']:04d}
Export Time: {export_info['timestamp']}
File: {export_info['filename']}
Path: {export_info['export_path']}

STATISTICS:
===========
Total Objects Exported: {stats['total_objects_exported']}
Quadblocks: {stats['quadblocks_count']}
Triblocks: {stats['triblocks_count']}
Objects with UV Issues: {stats['objects_with_uv_issues']}

OBJECTS BY ISSUE TYPE:
======================"""
        
        # Show objects grouped by issue type
        objects_by_issue = objects_summary.get("objects_by_issue_type", {})
        for issue_type, obj_list in objects_by_issue.items():
            if obj_list:
                summary += f"\n\n{issue_type.upper()} ({len(obj_list)} objects):"
                # Show first N objects
                display_list = obj_list[:max_objects_per_list]
                for obj_name in display_list:
                    summary += f"\n  - {obj_name}"
                if len(obj_list) > max_objects_per_list:
                    summary += f"\n  ... and {len(obj_list) - max_objects_per_list} more"
        
        summary += f"""

OBJECTS BREAKDOWN:
==================
Total: {objects_summary['count']} objects

By Type:"""
        
        for obj_type, count in objects_summary["by_type"].items():
            summary += f"\n  - {obj_type}: {count}"
        
        summary += "\n\nBy Issues:"
        for issue, count in objects_summary["by_issues"].items():
            summary += f"\n  - {issue}: {count}"
        
        # Show first 20 object names only (for backward compatibility)
        object_names = objects_summary['object_names']
        summary += f"\n\nObject Names (first 20 of {len(object_names)}):\n"
        for i in range(0, min(20, len(object_names)), 5):
            chunk = object_names[i:i+5]
            summary += "  " + ", ".join(chunk) + "\n"
        
        if len(object_names) > 20:
            summary += f"  ... and {len(object_names) - 20} more\n"
        
        return summary