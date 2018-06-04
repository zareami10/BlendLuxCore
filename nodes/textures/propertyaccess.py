import bpy
from bpy.props import StringProperty, PointerProperty
from .. import LuxCoreNodeTexture
from ...utils import ui as utils_ui


def is_iterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False


class LuxCoreNodeTexPropertyAccess(LuxCoreNodeTexture):
    bl_label = "PropertyAccess"

    datablock = PointerProperty(name="Datablock", type=bpy.types.Object)
    attribute_path = StringProperty(name="Attribute")
    error = StringProperty(name="Error")

    def init(self, context):
        self.outputs.new("LuxCoreSocketFloatUnbounded", "Value")

    def draw_label(self):
        if self.datablock and self.attribute_path:
            # TODO
            return self.datablock.name + "." + self.attribute_path
        else:
            return self.bl_label

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock")
        layout.prop(self, "attribute_path")
        if self.error:
            row = layout.row()
            row.label(self.error, icon="CANCEL")
            op = row.operator("luxcore.copy_error_to_clipboard", icon="COPYDOWN")
            op.message = self.error

    @staticmethod
    def parse_indices(index_str):
        indices = [int(s) for s in index_str.split(":")]
        len_indices = len(indices)

        if len_indices == 0:
            raise IndexError("No index given")
        elif len_indices == 1:
            start, end, step = indices[0], indices[0] + 1, 1
        elif len_indices == 2:
            start, end, step = indices[0], indices[1], 1
        elif len_indices == 3:
            start, end, step = indices
        else:
            raise IndexError("Too many indices (only start, end, step allowed)")
        return start, end, step, len_indices

    def eval(self):
        if self.datablock and self.attribute_path:
            value = self.datablock
            # Follow the chain of attributes
            for attrib in self.attribute_path.split("."):
                if "[" in attrib:
                    # Indexed access of an iterable
                    iter_attrib, index_str = attrib.split("[")
                    index_str = index_str.replace("]", "")
                    start, end, step, len_indices = self.parse_indices(index_str)

                    iterable = getattr(value, iter_attrib)
                    if not is_iterable(iterable):
                        raise TypeError(iter_attrib + " is not iterable")

                    if len_indices == 1:
                        # Some iterables in Blender don't have slicing support,
                        # so we don't use it if we don't have to
                        value = iterable[start]
                    else:
                        value = iterable[start:end:step]
                else:
                    value = getattr(value, attrib)

            try:
                # Check if it is iterable (Color, Vector etc.)
                return list(value)
            except TypeError:
                # Not iterable
                return [value, value, value]
        return [0, 0, 0]

    def sub_export(self, exporter, props, luxcore_name=None):
        self.error = ""
        utils_ui.tag_region_for_redraw(bpy.context, "NODE_EDITOR", "WINDOW")

        try:
            definitions = {
                "type": "constfloat3",
                "value": self.eval(),
            }

            return self.create_props(props, definitions, luxcore_name)
        except Exception as error:
            import traceback
            traceback.print_exc()

            self.error = str(error)
            utils_ui.tag_region_for_redraw(bpy.context, "NODE_EDITOR", "WINDOW")

            definitions = {
                "type": "constfloat1",
                "value": 0,
            }

            return self.create_props(props, definitions, luxcore_name)

