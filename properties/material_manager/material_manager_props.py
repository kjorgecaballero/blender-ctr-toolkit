import bpy
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty
from bpy.types import PropertyGroup


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
        """Rebuild the items collection from current filter & search,
        using material custom properties (ctr_block_type, ctr_is_navigation_point)."""
        self.items.clear()
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.selected_index = -1
            self.scroll = 0
            return

        search = self.search_text.lower()

        # Build lists from material slots
        normal_names = []
        constant_names = []
        nav_names = []

        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            if mat.get("ctr_block_type") is not None:
                if mat.get("ctr_is_navigation_point", False):
                    nav_names.append(mat.name)
                else:
                    constant_names.append(mat.name)
            else:
                normal_names.append(mat.name)

        # Remove duplicates (just in case)
        normal_names = list(dict.fromkeys(normal_names))
        constant_names = list(dict.fromkeys(constant_names))
        nav_names = list(dict.fromkeys(nav_names))

        if self.filter_type == 'ALL':
            raw = normal_names + constant_names + nav_names
        elif self.filter_type == 'NORMAL':
            raw = normal_names
        elif self.filter_type == 'CONSTANT':
            raw = constant_names
        else:  # NAV_POINT
            raw = nav_names

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
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.ctr_material_list = bpy.props.PointerProperty(type=CTR_MaterialListProps)


def unregister():
    del bpy.types.Scene.ctr_material_list
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass