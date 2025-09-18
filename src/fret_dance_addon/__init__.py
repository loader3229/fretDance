# g:\fretDance\src\blender\__init__.py
import os
import bpy  # type: ignore
from bpy.types import Panel, Operator  # type: ignore
from bpy.props import EnumProperty, StringProperty  # type: ignore
from bpy_extras.io_utils import ImportHelper, ExportHelper  # type: ignore

# 使用相对导入
from .base_states import BaseState, Instruments, BasePositions, LeftHandStates, RightHandStates
from .mmd2blender import mmd2blender

bl_info = {
    "name": "FretDance Controller Setup",
    "author": "BigHippo78",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "location": "3D View > Sidebar > FretDance",
    "description": "Setup and check guitar controller objects for animation",
    "category": "Animation",
}


class FRET_DANCE_OT_setup_objects(Operator):
    """Setup all controller and recorder objects"""
    bl_idname = "fret_dance.setup_objects"
    bl_label = "Setup addons"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))
        base_state.setup_all_objects()
        self.report({'INFO'}, "All objects have been setup")
        return {'FINISHED'}


class FRET_DANCE_OT_check_status(Operator):
    """Check the status of controller and recorder objects"""
    bl_idname = "fret_dance.check_status"
    bl_label = "Check Status"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))
        base_state.check_objects_status()
        self.report({'INFO'}, "Check complete. See console for details.")
        return {'FINISHED'}


class WM_OT_mmd2blender_initialize(bpy.types.Operator):
    """初始化MMD骨骼"""
    bl_idname = "wm.mmd2blender_initialize"
    bl_label = "初始化MMD骨骼"
    bl_description = "初始化MMD骨骼以适配Blender"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            # 调用mmd2blender方法
            mmd2blender()
            self.report({'INFO'}, "MMD骨骼初始化完成")
        except Exception as e:
            self.report({'ERROR'}, f"初始化失败: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class FRET_DANCE_OT_set_state(Operator):
    """Set hand states from controllers to recorders"""
    bl_idname = "fret_dance.set_state"
    bl_label = "Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))

        # 获取左手状态
        base_position = BasePositions(scene.fret_dance_base_positions)
        left_hand_state = LeftHandStates(scene.fret_dance_left_hand_states)

        # 获取右手状态
        right_hand_state = None
        for state in RightHandStates:
            if state.value == scene.fret_dance_right_hand_states:
                right_hand_state = state
                break

        if right_hand_state is None:
            self.report({'ERROR'}, "Invalid right hand state")
            return {'CANCELLED'}

        # 设置左手状态
        base_state.transfer_left_hand_state(
            base_position, left_hand_state, direction="set")

        # 设置右手状态
        base_state.transfer_right_hand_state(right_hand_state, direction="set")

        self.report({'INFO'}, "States have been set")
        return {'FINISHED'}


class FRET_DANCE_OT_load_state(Operator):
    """Load hand states from recorders to controllers"""
    bl_idname = "fret_dance.load_state"
    bl_label = "Load"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))

        # 获取左手状态
        base_position = BasePositions(scene.fret_dance_base_positions)
        left_hand_state = LeftHandStates(scene.fret_dance_left_hand_states)

        # 获取右手状态
        right_hand_state = None
        for state in RightHandStates:
            if state.value == scene.fret_dance_right_hand_states:
                right_hand_state = state
                break

        if right_hand_state is None:
            self.report({'ERROR'}, "Invalid right hand state")
            return {'CANCELLED'}

        # 加载左手状态
        base_state.transfer_left_hand_state(
            base_position, left_hand_state, direction="load")

        # 加载右手状态
        base_state.transfer_right_hand_state(
            right_hand_state, direction="load")

        self.report({'INFO'}, "States have been loaded")
        return {'FINISHED'}


class FRET_DANCE_OT_export_info(Operator, ExportHelper):
    """Export controller information to JSON file"""
    bl_idname = "fret_dance.export_info"
    bl_label = "Export Controller Info"
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    __annotations__ = {
        "filter_glob": StringProperty(
            default="*.json",
            options={'HIDDEN'},
            maxlen=255,
        )
    }

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))

        # 导出控制器信息
        base_state.export_controller_info(self.filepath)

        self.report({'INFO'}, f"Controller info exported to {self.filepath}")
        return {'FINISHED'}

class FRET_DANCE_OT_import_info(Operator, ImportHelper):
    """Import controller information from JSON file"""
    bl_idname = "fret_dance.import_info"
    bl_label = "Import Controller Info"
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    __annotations__ = {
        "filter_glob": StringProperty(
            default="*.json",
            options={'HIDDEN'},
            maxlen=255,
        )
    }

    def execute(self, context):
        scene = context.scene
        base_state = BaseState(Instruments(int(scene.fret_dance_instruments)))
        
        try:
            # 导入控制器信息
            base_state.import_controller_info(self.filepath)
        except:
            self.report({'ERROR'}, "Import Controller Info Error")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Controller info imported from {self.filepath}")
        return {'FINISHED'}


class FRET_DANCE_PT_main_panel(Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "FretDance Controller Setup"
    bl_idname = "FRET_DANCE_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FretDance"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # 第一大块：INIT
        box = layout.box()
        box.label(text="init", icon='TOOL_SETTINGS')
        row = box.row()
        row.prop(scene, "fret_dance_instruments")
        row = box.row(align=True)
        row.operator("fret_dance.check_status")
        row.operator("fret_dance.setup_objects")
        row = box.row()
        row.operator("wm.mmd2blender_initialize", text="初始化mmd骨骼")

        # 第二大块：Choose left hand state
        box = layout.box()
        box.label(text="Choose Left Hand State", icon='HAND')
        row = box.row()
        row.prop(scene, "fret_dance_base_positions")
        row = box.row()
        row.prop(scene, "fret_dance_left_hand_states")

        # 第三大块：Choose right hand state
        box = layout.box()
        box.label(text="Choose Right Hand State", icon='RIGHTARROW_THIN')
        row = box.row()
        row.prop(scene, "fret_dance_right_hand_states")

        # 第四大块：Set and Load
        box = layout.box()
        box.label(text="Set and Load", icon='FILE_REFRESH')
        row = box.row(align=True)
        row.operator("fret_dance.set_state")
        row.operator("fret_dance.load_state")

        # 保存控制信息
        box = layout.box()
        box.label(text="Import and Export Controller Info", icon='EXPORT')
        row = box.row()
        row.operator("fret_dance.import_info", text="Import")
        row.operator("fret_dance.export_info", text="Export")


def register():
    # 注册枚举属性
    bpy.types.Scene.fret_dance_instruments = EnumProperty(
        name="Instrument",
        description="Select instrument type",
        items=[
            ('0', "Finger Style Guitar", "Finger style guitar"),
            ('1', "Electric Guitar", "Electric guitar"),
            ('2', "Bass", "Bass guitar"),
        ],
        default='0'
    )

    bpy.types.Scene.fret_dance_base_positions = EnumProperty(
        name="Position",
        description="Select base position",
        items=[
            ('P0', "P0", "Position 0"),
            ('P1', "P1", "Position 1"),
            ('P2', "P2", "Position 2"),
            ('P3', "P3", "Position 3"),
        ],
        default='P0'
    )

    bpy.types.Scene.fret_dance_left_hand_states = EnumProperty(
        name="State",
        description="Select left hand state",
        items=[
            ('Normal', "Normal", "Normal state"),
            ('Outer', "Outer", "Outer state"),
            ('Inner', "Inner", "Inner state"),
            ('Barre', "Barre", "Barre state"),
        ],
        default='Normal'
    )

    bpy.types.Scene.fret_dance_right_hand_states = EnumProperty(
        name="State",
        description="Select right hand state",
        items=[
            ('0', "Low", "Low position"),
            ('end', "End", "End position"),
            ('3', "High", "High position"),
        ],
        default='0'
    )

    # 注册类
    bpy.utils.register_class(FRET_DANCE_OT_setup_objects)
    bpy.utils.register_class(FRET_DANCE_OT_check_status)
    bpy.utils.register_class(FRET_DANCE_OT_set_state)
    bpy.utils.register_class(FRET_DANCE_OT_load_state)
    bpy.utils.register_class(FRET_DANCE_OT_export_info)
    bpy.utils.register_class(FRET_DANCE_OT_import_info)
    bpy.utils.register_class(WM_OT_mmd2blender_initialize)
    bpy.utils.register_class(FRET_DANCE_PT_main_panel)


def unregister():
    # 注销类
    bpy.utils.unregister_class(FRET_DANCE_PT_main_panel)
    bpy.utils.unregister_class(FRET_DANCE_OT_export_info)
    bpy.utils.unregister_class(FRET_DANCE_OT_import_info)
    bpy.utils.unregister_class(FRET_DANCE_OT_load_state)
    bpy.utils.unregister_class(FRET_DANCE_OT_set_state)
    bpy.utils.unregister_class(FRET_DANCE_OT_check_status)
    bpy.utils.unregister_class(FRET_DANCE_OT_setup_objects)
    bpy.utils.unregister_class(WM_OT_mmd2blender_initialize)

    # 删除属性
    del bpy.types.Scene.fret_dance_instruments
    del bpy.types.Scene.fret_dance_base_positions
    del bpy.types.Scene.fret_dance_left_hand_states
    del bpy.types.Scene.fret_dance_right_hand_states


if __name__ == "__main__":
    register()
