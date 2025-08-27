
from enum import IntEnum, Enum
import bpy  # type: ignore


class Instruments(IntEnum):
    FINGER_STYLE_GUITAR = 0
    ELECTRIC_GUITAR = 1
    BASS = 2


class BasePositions(Enum):
    P0 = 'P0'
    P1 = 'P1'
    P2 = 'P2'
    P3 = 'P3'


class LeftHandStates(Enum):
    NORMAL = "Normal"
    OUTER = "Outer"
    INNER = "Inner"
    BARRE = "Barre"


class BaseState():
    def __init__(self, instruments: Instruments):
        # 控制左手手掌位置和手臂ik的控制器,因为左手大拇指不参与演奏，所以也被归到这一类里
        self.left_hand_controllers = {
            "left_hand_controller": "H_L",
            "left_hand_ik_pivot_controller": "HP_L",
            "left_thumb_controller": "T_L",
            "left_thumb_ik_pivot_controller": "TP_L",
        }
        # 控制右手手掌位置和手臂ik的控制器，因为右手大拇指要参与演奏，所以不被归到这一类里
        self.right_hand_controllers = {
            "right_hand_controller": "H_R",
            "right_hand_ik_pivot_controller": "HP_R",
        }
        # 控制手掌旋转
        self.hand_rotation_controllers = {
            "left_hand_rotation_controller": "H_rotation_L",
            "right_hand_rotation_controller": "H_rotation_R"
        }
        # 控制左手手指位置
        self.left_finger_controllers = {
            "left_index_controller": "I_L",
            "left_middle_controller": "M_L",
            "left_ring_controller": "R_L",
            "left_little_controller": "P_L",
        }
        # 控制右手手指位置
        self.right_finger_controllers = {
            "right_thumb_controller": "T_R",
            "right_index_controller": "I_R",
            "right_middle_controller": "M_R",
            "right_ring_controller": "R_R",
            "right_little_controller": "P_R",
        } if instruments != Instruments.ELECTRIC_GUITAR else {
            "right_thumb_controller": "T_R",
        }

        # 用于记录指板位置的四个基本点
        self.guitar_fret_positions = {}
        for position in BasePositions:
            self.guitar_fret_positions[position] = f'Fret_{position.value}'

        # 用于记录左手位置的点
        self.left_hand_position_recorders = {}
        # 添加用于计算横按状态时食指位置的点
        for position in BasePositions:
            self.left_hand_position_recorders[f'barre_{position.value}'] = f'Fret_Barre_{position.value}'

        # 定义无效的组合
        invalid_combinations = {
            BasePositions.P0: [LeftHandStates.INNER],
            BasePositions.P2: [LeftHandStates.INNER],
            BasePositions.P1: [LeftHandStates.OUTER],
            BasePositions.P3: [LeftHandStates.OUTER]}

        # 添加用于记录不同状态下左手位置的点
        for position in BasePositions:
            for state in LeftHandStates:
                for left_controller in self.left_hand_controllers:
                    controller_name = self.left_hand_controllers[left_controller]
                    # 跳过无效的组合
                    if position in invalid_combinations and state in invalid_combinations[position]:
                        continue

                    # 为每种有效的组合创建记录器
                    key = f'{state.name}_{position.value}_{controller_name}'.lower()
                    value = f'{state.value}_{position.value}_{controller_name}'
                    self.left_hand_position_recorders[key] = value

        # 添加用于记录不同状态下左手旋转值的旋转记录器
        for position in BasePositions:
            for state in LeftHandStates:
                for hand_rotation_controller in self.hand_rotation_controllers:
                    hand_rotation_controller_name = self.hand_rotation_controllers[
                        hand_rotation_controller]
                    if hand_rotation_controller_name == 'H_rotation_R':
                        continue
                    # 跳过无效的组合
                    if position in invalid_combinations and state in invalid_combinations[position]:
                        continue

                    # 为每种有效的组合创建记录器
                    key = f'{state.name}_{position.value}_{hand_rotation_controller_name}'.lower(
                    )
                    value = f'{state.value}_{position.value}_{hand_rotation_controller_name}'
                    self.left_hand_position_recorders[key] = value

        # 用于记录右手位置的点
        self.right_hand_position_recorders = {}

        if instruments == Instruments.ELECTRIC_GUITAR:
            # 电吉他只需要记录三个点，分别是最高弦的拨奏点，最低弦的拨奏点，和最底部的扫弦结束时的休息点
            self.right_hand_position_recorders['high'] = 'p5'
            self.right_hand_position_recorders['low'] = 'p0'
            self.right_hand_position_recorders['end'] = 'p_end'
        else:
            # 这里是用西班牙吉他的缩写代表手指，指弹吉他和bass需要记录所有五个手指在三种状态下的位置
            # 为什么是使用的状态是3和0，这都是历史遗留问题
            for finger in ['p', 'i', 'm', 'a', 'ch']:
                self.right_hand_position_recorders[f'high_{finger}'] = f'{finger}3'
                self.right_hand_position_recorders[f'low_{finger}'] = f'{finger}0'
                self.right_hand_position_recorders[f'end_{finger}'] = f'{finger}_end'

        # 用于记录右手旋转值的旋转记录器
        self.right_hand_rotation_recorders = {}
        # 电吉他不需要记录右手旋转值
        if instruments != Instruments.ELECTRIC_GUITAR:
            self.right_hand_rotation_recorders['high'] = 'Normal_P3_H_rotation_R'
            self.right_hand_rotation_recorders['low'] = 'Normal_P0_H_rotation_R'
            self.right_hand_rotation_recorders['end'] = 'Normal_P_end_H_rotation_R'

        # 接下来是一些辅助线
        self.guidelines = {}

        # 吉他弦的振动方向
        self.guidelines['string_move_direction'] = 'string_move_direction'

        # 右手运动的辅助线
        if instruments == Instruments.ELECTRIC_GUITAR:
            # 电吉他演奏时的拨弦方向
            self.guidelines['left_thumb_move_direction'] = 'T_line'
        else:
            # 指弹吉它和bass演奏时要记录手背的朝向
            self.guidelines['left_hand_high_normal'] = 'right_hand_normal_p3'
            self.guidelines['left_hand_low_normal'] = 'right_hand_normal_p0'

    def add_controllers(self):
        """
        添加控制器对象到Blender场景中
        位置控制器使用立方体，旋转控制器使用正四面体
        """
        # 确保在对象模式下操作
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # 创建或获取主集合
        main_collection = self.get_or_create_collection("addons")

        # 创建控制器集合
        controllers_collection = self.get_or_create_collection(
            "Controllers", main_collection)

        # 创建左右手子集合
        left_hand_collection = self.get_or_create_collection(
            "Left_Hand_Controllers", controllers_collection)
        right_hand_collection = self.get_or_create_collection(
            "Right_Hand_Controllers", controllers_collection)

        # 添加左手控制器
        for controller_name, obj_name in self.left_hand_controllers.items():
            if obj_name not in bpy.data.objects:
                if 'rotation' in controller_name:
                    # 旋转控制器使用圆锥体
                    bpy.ops.mesh.primitive_cone_add(
                        enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(0.1, 0.1, 0.1))

                else:
                    # 位置控制器使用立方体
                    bpy.ops.mesh.primitive_cube_add(
                        size=0.2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))

                # 重命名对象
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到左手集合
                self.move_object_to_collection(obj, left_hand_collection)

        # 添加右手控制器
        for controller_name, obj_name in self.right_hand_controllers.items():
            if obj_name not in bpy.data.objects:
                if 'rotation' in controller_name:
                    # 旋转控制器使用圆锥体
                    bpy.ops.mesh.primitive_cone_add(
                        enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(0.1, 0.1, 0.1))
                else:
                    # 位置控制器使用立方体
                    bpy.ops.mesh.primitive_cube_add(
                        size=0.2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))

                # 重命名对象
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到右手集合
                self.move_object_to_collection(obj, right_hand_collection)

        # 添加左手手指控制器
        for controller_name, obj_name in self.left_finger_controllers.items():
            if obj_name not in bpy.data.objects:
                # 手指控制器使用立方体
                bpy.ops.mesh.primitive_cube_add(
                    size=0.2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到左手集合
                self.move_object_to_collection(obj, left_hand_collection)

        # 添加右手手指控制器
        for controller_name, obj_name in self.right_finger_controllers.items():
            if obj_name not in bpy.data.objects:
                # 手指控制器使用立方体
                bpy.ops.mesh.primitive_cube_add(
                    size=0.2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到右手集合
                self.move_object_to_collection(obj, right_hand_collection)

        # 添加手部旋转控制器
        for controller_name, obj_name in self.hand_rotation_controllers.items():
            if obj_name not in bpy.data.objects:
                # 旋转控制器使用圆锥体
                bpy.ops.mesh.primitive_cone_add(
                    enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(0.1, 0.1, 0.1))
                obj = bpy.context.active_object
                obj.name = obj_name

                # 根据名称判断是左手还是右手
                if '_L' in obj_name:
                    self.move_object_to_collection(obj, left_hand_collection)
                else:
                    self.move_object_to_collection(obj, right_hand_collection)

    def add_recorders(self):
        """
        添加记录器对象到Blender场景中
        位置记录器使用球体空物体，旋转记录器使用圆锥体空物体
        """
        # 确保在对象模式下操作
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # 创建或获取主集合
        main_collection = self.get_or_create_collection("addons")

        # 创建记录器集合
        recorders_collection = self.get_or_create_collection(
            "Recorders", main_collection)

        # 创建左右手子集合
        left_hand_collection = self.get_or_create_collection(
            "Left_Hand_Recorders", recorders_collection)
        right_hand_collection = self.get_or_create_collection(
            "Right_Hand_Recorders", recorders_collection)

        # 创建辅助线子集合
        guidelines_collection = self.get_or_create_collection(
            "Guidelines", recorders_collection)

        # 添加指板位置记录器
        for recorder_name, obj_name in self.guitar_fret_positions.items():
            if isinstance(recorder_name, Enum):
                obj_name_actual = obj_name
            else:
                obj_name_actual = recorder_name

            if obj_name_actual not in bpy.data.objects:
                # 位置记录器使用球体空物体
                bpy.ops.object.empty_add(type='SPHERE', radius=0.1)
                obj = bpy.context.active_object
                obj.name = obj_name_actual

                # 指板位置记录器放入左手集合
                self.move_object_to_collection(obj, left_hand_collection)

        # 添加左手位置记录器
        for recorder_name, obj_name in self.left_hand_position_recorders.items():
            if obj_name not in bpy.data.objects:
                if 'rotation' in recorder_name:
                    # 旋转记录器使用圆锥体空物体
                    bpy.ops.object.empty_add(type='CONE', radius=0.1)
                else:
                    # 位置记录器使用球体空物体
                    bpy.ops.object.empty_add(type='SPHERE', radius=0.1)

                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到左手集合
                self.move_object_to_collection(obj, left_hand_collection)

        # 添加右手位置记录器
        for recorder_name, obj_name in self.right_hand_position_recorders.items():
            if obj_name not in bpy.data.objects:
                # 右手位置记录器使用球体空物体
                bpy.ops.object.empty_add(type='SPHERE', radius=0.1)
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到右手集合
                self.move_object_to_collection(obj, right_hand_collection)

        # 添加右手旋转记录器
        for recorder_name, obj_name in self.right_hand_rotation_recorders.items():
            if obj_name not in bpy.data.objects:
                # 右手旋转记录器使用圆锥体空物体
                bpy.ops.object.empty_add(type='CONE', radius=0.1)
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到右手集合
                self.move_object_to_collection(obj, right_hand_collection)

        # 添加辅助线对象
        for guideline_name, obj_name in self.guidelines.items():
            if obj_name not in bpy.data.objects:
                # 辅助线使用球体空物体
                bpy.ops.object.empty_add(type='SINGLE_ARROW', radius=1.0)
                obj = bpy.context.active_object
                obj.name = obj_name

                # 将对象移动到辅助线集合
                self.move_object_to_collection(obj, guidelines_collection)

    def get_or_create_collection(self, name, parent_collection=None):
        """
        获取或创建集合
        """
        if name in bpy.data.collections:
            collection = bpy.data.collections[name]
        else:
            collection = bpy.data.collections.new(name)
            if parent_collection:
                parent_collection.children.link(collection)
            else:
                # 如果没有指定父集合，链接到场景主集合
                bpy.context.scene.collection.children.link(collection)

        # 如果指定了父集合，则确保该集合在父集合中
        if parent_collection and collection.name not in [c.name for c in parent_collection.children]:
            parent_collection.children.link(collection)

        return collection

    def move_object_to_collection(self, obj, collection):
        """
        将对象移动到指定集合
        """
        # 从所有现有集合中移除对象
        for coll in obj.users_collection:
            coll.objects.unlink(obj)

        # 将对象链接到目标集合
        collection.objects.link(obj)

    def setup_all_objects(self):
        """
        一次性设置所有控制器和记录器
        """
        self.add_controllers()
        self.add_recorders()


if __name__ == '__main__':
    # 创建一个实例
    base_state = BaseState(Instruments.FINGER_STYLE_GUITAR)

    base_state.setup_all_objects()
