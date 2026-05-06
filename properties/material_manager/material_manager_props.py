import bpy
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty
from bpy.types import PropertyGroup

from ...utils.material_utils import get_material_categories


class CTR_MaterialListItem(PropertyGroup):
    name: StringProperty()


class CTR_MaterialListProps(PropertyGroup):
    filter_type: EnumProperty(
        name="Filter",
        items=[
            ('ALL', "All", "Show all materials in the scene"),
            ('NORMAL', "Normal", "Materials of the active object that are NOT constant/nav points"),
            ('CONSTANT', "Constant", "Constant materials of the active object (not nav points)"),
            ('NAV_POINT', "Nav Point", "Navigation point materials of the active object"),
        ],
        default='ALL',
        update=lambda self, ctx: self._update_items(ctx)
    )
    search_text: StringProperty(
        name="Search", default="",
        update=lambda self, ctx: self._update_items(ctx)
    )
    items: CollectionProperty(type=CTR_MaterialListItem)
    selected_index: IntProperty(default=-1, options={'SKIP_SAVE'})
    scroll: IntProperty(default=0, min=0)

    def _update_items(self, context):
        """Rebuild the items collection from current filter & search."""
        self.items.clear()
        obj = context.active_object
        search = self.search_text.lower()

        if self.filter_type == 'ALL':
            normal, constant, nav_point = get_material_categories()
            raw = normal | constant | nav_point
            for name in sorted(raw):
                if search and search not in name.lower():
                    continue
                item = self.items.add()
                item.name = name
        else:
            if not obj or obj.type != 'MESH':
                self.selected_index = -1
                self.scroll = 0
                return

            const_dict = obj.get("constant_materials", {})
            normal_mats, constant_mats, nav_point_mats = [], [], []

            for slot in obj.material_slots:
                if not slot.material:
                    continue
                mat_name = slot.material.name
                if mat_name in const_dict:
                    if const_dict[mat_name].get("is_navigation_point", False):
                        nav_point_mats.append(mat_name)
                    else:
                        constant_mats.append(mat_name)
                else:
                    normal_mats.append(mat_name)

            normal_mats = list(dict.fromkeys(normal_mats))
            constant_mats = list(dict.fromkeys(constant_mats))
            nav_point_mats = list(dict.fromkeys(nav_point_mats))

            if self.filter_type == 'NORMAL':
                raw = normal_mats
            elif self.filter_type == 'CONSTANT':
                raw = constant_mats
            else:  # NAV_POINT
                raw = nav_point_mats

            for name in sorted(raw):
                if search and search not in name.lower():
                    continue
                item = self.items.add()
                item.name = name

        self.selected_index = -1
        self.scroll = 0


# Registration
classes = [CTR_MaterialListItem, CTR_MaterialListProps]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ctr_material_list = bpy.props.PointerProperty(type=CTR_MaterialListProps)


def unregister():
    del bpy.types.Scene.ctr_material_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)