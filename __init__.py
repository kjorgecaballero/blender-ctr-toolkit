bl_info = {
    "name": "Blender CTR Toolkit",
    "author": "Jorge Caballero (Siruka)",
    "version": (0, 0, 1),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > CTR",
    "description": "Tools for CTR track development including export functionality.",
    "category": "3D View",
}

import bpy

def register():
    from . import properties
    from . import operators
    from . import ui

    properties.register()
    operators.register()
    ui.register()

    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} loaded")

def unregister():
    from . import ui, operators, properties

    ui.unregister()
    operators.unregister()
    properties.unregister()
    
    print(f"Blender CTR Toolkit v{bl_info['version'][0]}.{bl_info['version'][1]} unloaded")

if __name__ == "__main__":
    register()