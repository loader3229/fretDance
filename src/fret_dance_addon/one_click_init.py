import bpy  # type: ignore
from collections import defaultdict
from mathutils import Vector  # type: ignore
from .base_states import BaseState, Instruments, BasePositions, LeftHandStates, RightHandStates

# 12平均律品格位置：弦枕(0品)到12品的距离是弦长的一半，弦枕到1品的距离是弦长的(1 - 2^(-1/12))
# 所以 1品位置 = F0 + (F12 - F0) * 2 * (1 - 2^(-1/12))，与动画端lerp_by_fret的1品/12品锚点定义一致
FRET_1_RATIO = 2 * (1 - 2 ** (-1 / 12))

# 吉他定位点所在的集合名
GUITAR_POINT_COLLECTION = "GuitarPoints"

# 右手默认摆放参数（单位：米），之后可以摆好姿势重新Set覆盖
DEFAULT_PICK_RATIO = 1.25  # 新建右手定位点时的默认位置：距琴枕0品~12品距离的倍数（约音孔上方）
FINGER_SPREAD = 0.008    # 多根手指落在同一根弦上时，沿弦方向互相错开的间距
RIGHT_HAND_BACK = 0.18   # 手掌控制器H_R位于指尖质心后方（朝琴头方向）的距离
RIGHT_HAND_UP = 0.04     # 手掌控制器H_R高于弦平面的距离
RIGHT_ARM_UP = 0.24      # 手臂IK轴心HP_R高于手掌控制器的距离
RIGHT_ARM_BACK = 0.08    # 手臂IK轴心HP_R朝琴头方向偏移的距离
THUMB_PIVOT_UP = 0.14    # 拇指IK轴心TP_R高于拇指触弦点的距离


def get_string_count(instruments: Instruments) -> int:
    """获取乐器的弦数量：bass为4根弦，吉他为6根弦"""
    return 4 if instruments == Instruments.BASS else 6


def guitar_point_name(string: int, fret: int) -> str:
    """获取吉他定位点物体名，string从1开始，1弦为最高音弦"""
    return f"S{string}_F{fret}"


def right_point_name(string: int) -> str:
    """获取右手定位点物体名，表示第string根弦上右手放置的基准位置（约拨弦处）"""
    return f"S{string}_Right"


def create_guitar_points(string_count: int = 6) -> tuple[int, int]:
    """
    创建1弦和最低弦所需的6个定位点空物体，已存在的复用：
    - 品定位点：S1_F0、S1_F12、S{最低弦}_F0、S{最低弦}_F12（吉他为S6，贝斯为S4）
    - 右手定位点：S1_Right、S{最低弦}_Right（对应弦上右手放置的基准位置）
    其余弦的位置与右手各状态的摆放位置均可由这6个点计算得到。
    创建后需要移动到吉他的实际位置。返回(新建数量, 已存在数量)
    """
    # 确保在对象模式下操作
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 获取或创建定位点集合，并确保它链接在场景中（否则其中的物体不可见）
    scene_collection = bpy.context.scene.collection
    if GUITAR_POINT_COLLECTION in bpy.data.collections:
        collection = bpy.data.collections[GUITAR_POINT_COLLECTION]
        if collection not in scene_collection.children_recursive and collection not in scene_collection.children:
            scene_collection.children.link(collection)
    else:
        collection = bpy.data.collections.new(GUITAR_POINT_COLLECTION)
        scene_collection.children.link(collection)

    created = 0
    existed = 0
    low_string = string_count
    # 默认布局：1弦在+X侧，品沿-Y方向延伸，创建后由用户移动到吉他的实际位置
    string_spacing = 0.01
    fret_12_distance = 0.3
    # 右手定位点默认放在约音孔上方（0品~12品距离的DEFAULT_PICK_RATIO倍处）
    pick_distance = fret_12_distance * DEFAULT_PICK_RATIO

    # (物体名, 默认位置)
    defaults = [
        (guitar_point_name(1, 0), ((low_string - 1) / 2 * string_spacing, 0, 0)),
        (guitar_point_name(1, 12), ((low_string - 1) / 2 * string_spacing, -fret_12_distance, 0)),
        (guitar_point_name(low_string, 0), (-(low_string - 1) / 2 * string_spacing, 0, 0)),
        (guitar_point_name(low_string, 12), (-(low_string - 1) / 2 * string_spacing, -fret_12_distance, 0)),
        (right_point_name(1), ((low_string - 1) / 2 * string_spacing, -pick_distance, 0)),
        (right_point_name(low_string), (-(low_string - 1) / 2 * string_spacing, -pick_distance, 0)),
    ]

    for name, location in defaults:
        if name in bpy.data.objects:
            existed += 1
            continue

        point = bpy.data.objects.new(name, None)
        point.empty_display_type = 'SPHERE'
        point.empty_display_size = 0.01
        point.location = location
        collection.objects.link(point)
        created += 1

    return created, existed


def read_guitar_points(string_count: int) -> tuple[dict, dict, list]:
    """
    读取1弦与最低弦的0品、12品定位点及右手定位点位置（世界坐标）
    返回(品定位点{(弦序号, 品数): Vector}, 右手定位点{弦序号: Vector}, 缺失的物体名列表)
    """
    points = {}
    right_points = {}
    missing = []
    for string in (1, string_count):
        for fret in (0, 12):
            name = guitar_point_name(string, fret)
            obj = bpy.data.objects.get(name)
            if obj is None:
                missing.append(name)
            else:
                points[(string, fret)] = obj.matrix_world.translation.copy()
        name = right_point_name(string)
        obj = bpy.data.objects.get(name)
        if obj is None:
            missing.append(name)
        else:
            right_points[string] = obj.matrix_world.translation.copy()
    return points, right_points, missing


def finger_strings_for_state(base_state: BaseState, low_string: int, state: RightHandStates) -> dict:
    """
    获取右手某个状态下各手指对应的弦序号（1=1弦最高音弦，小于1表示扫过1弦后越过的位置）
    Low: 拇指在最低弦（吉他6弦/bass4弦），i/m/a依次移向高音弦
    High: i/m/a捏在1弦，ch在2弦，拇指在3弦
    End: 扫弦结束，整只手越过1弦
    电吉他只有匹克（拇指）一个拨弦点：Low在最低弦，High在1弦，End越过1弦
    """
    if base_state.instruments == Instruments.ELECTRIC_GUITAR:
        return {'p': {RightHandStates.LOW: low_string,
                      RightHandStates.HIGH: 1,
                      RightHandStates.END: 0}[state]}
    return {
        RightHandStates.LOW: {'p': low_string, 'i': low_string - 1, 'm': low_string - 2,
                              'a': low_string - 3, 'ch': low_string - 4},
        RightHandStates.HIGH: {'p': 3, 'ch': 2, 'i': 1, 'm': 1, 'a': 1},
        RightHandStates.END: {'p': 0, 'i': 0, 'm': 0, 'a': 0, 'ch': 0},
    }[state]


def string_pick_point(right_points: dict, low_string: int, string: float) -> Vector:
    """
    计算第string根弦上右手基准点（世界坐标）：由1弦与最低弦的右手定位点沿弦方向线性插值
    string允许小于1或大于low_string：按相同弦间距外推的位置
    """
    t = (string - 1) / (low_string - 1)
    return right_points[1].lerp(right_points[low_string], t)


def right_hand_state_locations(base_state: BaseState, points: dict, right_points: dict,
                               low_string: int, state: RightHandStates) -> dict:
    """
    计算右手某个状态下所有位置记录器在吉他上的期望摆放位置
    返回{记录器物体名: Vector}，物体名与base_states中的记录器命名一致
    """
    finger_strings = finger_strings_for_state(base_state, low_string, state)

    # 弦坐标系：u沿弦指向琴桥，v从1弦指向最低弦，n为弦平面法线（朝上）
    f0_mid = points[(1, 0)].lerp(points[(low_string, 0)], 0.5)
    f12_mid = points[(1, 12)].lerp(points[(low_string, 12)], 0.5)
    u = (f12_mid - f0_mid).normalized()
    v = (points[(low_string, 0)] - points[(1, 0)]).normalized()
    n = v.cross(u).normalized()

    # 计算各手指触弦点，落在同一根弦上的手指沿弦方向依次错开
    contacts = {}
    groups = defaultdict(list)
    for finger, string in finger_strings.items():
        groups[string].append(finger)
    for fingers in groups.values():
        count = len(fingers)
        for index, finger in enumerate(fingers):
            string = finger_strings[finger]
            contacts[finger] = string_pick_point(right_points, low_string, string) + \
                u * (index - (count - 1) / 2) * FINGER_SPREAD

    recorder_names = base_state.right_hand_position_recorders

    def recorder(suffix: str):
        return recorder_names.get(f'{state}_{suffix}')

    locations = {}
    for finger, contact in contacts.items():
        name = recorder(finger)
        if name is not None:
            locations[name] = contact

    # 拇指IK轴心在拇指触弦点正上方
    name = recorder('tp')
    if name is not None:
        locations[name] = contacts['p'] + n * THUMB_PIVOT_UP

    # 手掌控制器在指尖质心后方（朝琴头）并抬高；手臂IK轴心再向后上方
    centroid = Vector()
    for contact in contacts.values():
        centroid += contact
    centroid /= len(contacts)
    hand = centroid - u * RIGHT_HAND_BACK + n * RIGHT_HAND_UP
    name = recorder('h')
    if name is not None:
        locations[name] = hand
    name = recorder('hp')
    if name is not None:
        locations[name] = hand - u * RIGHT_ARM_BACK + n * RIGHT_ARM_UP

    return locations


def move_right_hand_controllers(base_state: BaseState, locations: dict,
                                state: RightHandStates) -> None:
    """把右手控制器摆到指定状态对应的期望位置，使Set记录与期望位置一致"""
    recorder_names = base_state.right_hand_position_recorders
    controller_to_suffix = {
        'H_R': 'h', 'HP_R': 'hp', 'T_R': 'p', 'TP_R': 'tp',
        'I_R': 'i', 'M_R': 'm', 'R_R': 'a', 'P_R': 'ch',
    }
    for controller_obj_name, suffix in controller_to_suffix.items():
        recorder_obj_name = recorder_names.get(f'{state}_{suffix}')
        if recorder_obj_name is None or recorder_obj_name not in locations:
            continue
        controller = bpy.data.objects.get(controller_obj_name)
        if controller is not None:
            controller.location = locations[recorder_obj_name]


def record_base_states(base_state: BaseState, right_hand_locations: dict = None) -> dict:
    """
    将当前控制器姿态记录为所有左右手基准状态（Set）。
    左手: P0~P4 × Normal/Outer/Inner/Barre（跳过无效组合）
    右手: Low/End/High 三个状态；提供right_hand_locations时先把右手控制器摆到对应期望位置再记录
    返回{'left': 成功记录的左手组合数, 'right': 成功记录的右手状态数}
    """
    left_count = 0
    for position in BasePositions:
        for state in LeftHandStates:
            # 跳过无效的组合
            if position in base_state.invalid_combinations and state in base_state.invalid_combinations[position]:
                continue
            if base_state.transfer_left_hand_state(position, state, direction='set'):
                left_count += 1

    right_count = 0
    for state in RightHandStates:
        if right_hand_locations and state in right_hand_locations:
            move_right_hand_controllers(
                base_state, right_hand_locations[state], state)
        if base_state.transfer_right_hand_state(state, direction='set'):
            right_count += 1

    return {'left': left_count, 'right': right_count}


def one_click_initialize(instruments: Instruments, record_states: bool = True) -> dict:
    """
    一键初始化：创建所有控制器与记录器，并根据吉他定位点自动计算摆放指板记录器。
    Fret_P0: 1弦1品   Fret_P1: 最低弦1品
    Fret_P2: 1弦12品  Fret_P3: 最低弦12品
    同时把右手Low/End/High三个状态的记录器摆到吉他上的期望位置（由右手定位点决定，约拨弦处）。
    record_states为True时，还会把当前控制器姿态记录为所有左右手基准状态，
    右手会先摆到期望位置再记录。
    """
    # 创建所有控制器与记录器（已存在的会复用）
    base_state = BaseState(instruments)
    base_state.setup_all_objects()

    string_count = get_string_count(instruments)
    low_string = string_count
    points, right_points, missing = read_guitar_points(string_count)

    result = {
        'low_string': low_string,
        'missing': missing,
        'fret_placed': False,
        'right_hand_placed': False,
        'positions': {},
        'states_recorded': None,
    }

    # 计算Fret_P0~P3与右手期望位置需要1弦和最低弦两端的定位点及两个右手定位点，
    # 缺少任何一个都无法完成计算
    required = [(1, 0), (1, 12), (low_string, 0), (low_string, 12)]
    right_hand_locations = None
    if any(key not in points for key in required) or len(right_points) < 2:
        print("一键初始化: 缺少定位点，跳过Fret_P0~P3与右手状态的摆放")
    else:
        positions = {
            'Fret_P0': points[(1, 0)] + (points[(1, 12)] - points[(1, 0)]) * FRET_1_RATIO,
            'Fret_P1': points[(low_string, 0)] + (points[(low_string, 12)] - points[(low_string, 0)]) * FRET_1_RATIO,
            'Fret_P2': points[(1, 12)],
            'Fret_P3': points[(low_string, 12)],
        }

        for recorder_name, location in positions.items():
            obj = bpy.data.objects.get(recorder_name)
            if obj is not None:
                obj.lock_location = (False, False, False)
                obj.location = location

        result['fret_placed'] = True
        result['positions'] = {name: location.copy()
                               for name, location in positions.items()}

        # 右手三个状态：把记录器直接摆到吉他上的期望位置
        right_hand_locations = {}
        for state in RightHandStates:
            locations = right_hand_state_locations(
                base_state, points, right_points, low_string, state)
            right_hand_locations[state] = locations
            for recorder_obj_name, location in locations.items():
                obj = bpy.data.objects.get(recorder_obj_name)
                if obj is not None:
                    obj.lock_location = (False, False, False)
                    obj.location = location
        result['right_hand_placed'] = True

    # 记录所有左右手基准状态（右手先摆到期望位置再记录）
    if record_states:
        result['states_recorded'] = record_base_states(
            base_state, right_hand_locations)

    return result
