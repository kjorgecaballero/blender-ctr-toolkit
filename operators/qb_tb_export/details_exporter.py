"""
JSON details exporter for QB/TB export operations (simplified version)
"""

import json
import os
import bpy
from datetime import datetime

try:
    from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
except ImportError:
    def get_mesh_type(obj):
        return 'UNKNOWN'
    def get_object_issues(obj):
        return []


class DetailsExporter:
    """Handles export of simplified JSON details for QB/TB exports"""
    
    def __init__(self):
        self.export_data = {}
    
    def collect_export_details(self, valid_objects, stats, settings, filepath, export_index):
        """Collect simplified export details into a dictionary"""
        
        # Count objects by type and issues (no per-object details)
        type_counts = {}
        issue_counts = {}
        
        for obj in valid_objects:
            if obj and obj.name in bpy.data.objects:
                mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else 'NON_MESH'
                type_counts[mesh_type] = type_counts.get(mesh_type, 0) + 1
                
                issues = get_object_issues(obj)
                if issues:
                    for issue in issues:
                        issue_counts[issue] = issue_counts.get(issue, 0) + 1
                else:
                    issue_counts['valid'] = issue_counts.get('valid', 0) + 1
        
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
                    "include_textures": settings.include_textures,
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
            "objects_summary": {
                "count": len(valid_objects),
                "by_type": type_counts,
                "by_issues": issue_counts
            }
        }
        
        return self.export_data
    
    def export_to_json(self, filepath, data):
        """Export collected data to JSON file inside 'log' folder at project root."""
        try:
            export_folder = os.path.dirname(filepath)      # .../001/export
            project_root = os.path.dirname(export_folder)  # .../001
            log_dir = os.path.join(project_root, "log")
            os.makedirs(log_dir, exist_ok=True)
            
            json_path = os.path.join(log_dir, "Details.json")
            
            print(f"DEBUG: Writing JSON to {json_path}")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f" Export details saved to: {json_path}")
            return json_path
            
        except Exception as e:
            print(f" Error saving export details: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_summary_report(self, data):
        """Generate a short human-readable summary report"""
        stats = data["statistics"]
        export_info = data["export_info"]
        objects_summary = data["objects_summary"]
        
        summary = f"""
========================================
QB/TB EXPORT SUMMARY
========================================
Export #{export_info['export_index']:04d}
Time: {export_info['timestamp']}
File: {export_info['filename']}

Objects exported: {stats['total_objects_exported']}
  Quadblocks: {stats['quadblocks_count']}
  Triblocks: {stats['triblocks_count']}
Objects with UV issues: {stats['objects_with_uv_issues']}

By type:"""
        for t, cnt in objects_summary["by_type"].items():
            summary += f"\n  {t}: {cnt}"
        summary += "\n\nBy issues:"
        for issue, cnt in objects_summary["by_issues"].items():
            summary += f"\n  {issue}: {cnt}"
        summary += "\n========================================\n"
        return summary