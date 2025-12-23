bl_info = {
    "name": "Blender CTR Toolkit",
    "author": "Jorge Caballero (Siruka)",
    "version": (0, 1, 0),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > CTR",
    "description": "Tools for CTR track development.",
    "category": "3D View",
}

import bpy

def register():
    """Register the entire addon"""
    from . import properties
    from . import operators
    from . import ui

    properties.register()
    operators.register()
    ui.register()

    print(f"Blender CTR Toolkit loaded")

def unregister():
    """Unregister the entire addon"""
    from . import ui,operators, properties

    ui.unregister()
    operators.unregister()
    properties.unregister()
    
    print(f"Blender CTR Toolkit unloaded")

if __name__ == "__main__":
    register()