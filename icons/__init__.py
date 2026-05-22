import bpy
import os

_previews = None

def register_icons():
    global _previews
    try:
        from bpy.utils import previews
        _previews = previews.new()
    except (ImportError, AttributeError):
        _previews = None
        return

    addon_dir = os.path.dirname(os.path.dirname(__file__))
    icons_dir = os.path.join(addon_dir, "icons")

    icon_files = {
        "clear_icon": "clear_icon.png",
        "reset_icon": "reset_icon.png",
        "duplicate_icon": "duplicate_icon.png",
        "invalid_icon": "invalid_icon.png",
        "navigate_icon": "navigate_icon.png",
        "quadblock_icon": "quadblock_icon.png",
        "triblock_icon": "triblock_icon.png",
        "doc_icon": "doc_icon.png",
        "tutorial_icon": "tutorial_icon.png",
        "update_icon": "update_icon.png",
        "report_icon": "report_icon.png",
        "typeqb_icon": "typeqb_icon.png",
        "typetb_icon": "typetb_icon.png",
        "check_all_icon": "check_all_icon.png",
        "uncheck_all_icon": "uncheck_all_icon.png",
        "nav_point_icon": "nav_point_icon.png",
        "constant_mat_icon": "constant_mat_icon.png",
        "psx_icon": "psx_icon.png",
        "resolution_icon": "resolution_icon.png",
        "split_screen_icon": "split_screen_icon.png",
        "seams_icon": "seams_icon.png",
        "duplicate_constant_icon": "duplicate_constant_icon.png",
        "remove_group_icon": "remove_group_icon.png",
        "quadblock_cache_icon": "quadblock_cache_icon.png",
    }

    for name, filename in icon_files.items():
        path = os.path.join(icons_dir, filename)
        if os.path.exists(path):
            try:
                _previews.load(name, path, 'IMAGE')
            except Exception:
                pass

def unregister_icons():
    global _previews
    if _previews:
        try:
            from bpy.utils import previews
            previews.remove(_previews)
        except:
            pass
        _previews = None

def get_icon(name):
    if _previews and name in _previews:
        return _previews[name].icon_id
    return 0