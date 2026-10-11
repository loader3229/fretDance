import bpy  # type: ignore
from .base_states import BaseState, Instruments, BasePositions, LeftHandStates, RightHandStates

# 12平均律品格位置：弦枕(0品)到12品的距离是弦长的一半，弦枕到1品的距离是弦长的(1 - 2^(-1/12))
# 所以 1品位置 = F0 + (F12 - F0) * 2 * (1 - 2^(-1/12))，与动画端lerp_by_fret的1品/12品锚点定义一致
FRET_1_RATIO = 2 * (1 - 2 ** (-1 / 12))

# 吉他定位点所在的集合名
GUITAR_POINT_COLLECTION = "GuitarPoints"


def get_string_count(instruments: Instruments) -> int:
    """获取乐器的弦数量：bass为4根弦，吉他为6根弦"""
    return 4 if instruments == Instruments.BASS else 6


def guitar_point_name(string: int, fret: int) -> str:
    """获取吉他定位点物体名，string从1开始，1弦为最高音弦"""
    return f"S{string}_F{fret}"


def create_guitar_points() -> tuple[int, int]:
    """
    创建1-6弦在0品和12品的12个定位点空物体，已存在的复用。
    物体名分别为S1_F0、S1_F12 ... S6_F0、S6_F12，创建后需要移动到吉他弦的实际位置。
    返回(新建数量, 已存在数量)
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
    # 默认布局：1弦在+X侧，品沿-Y方向延伸，创建后由用户移动到吉他弦的实际位置
    string_spacing = 0.01
    fret_12_distance = 0.3

    for string in range(1, 7):
        for fret in (0, 12):
            name = guitar_point_name(string, fret)
            if name in bpy.data.objects:
                existed += 1
                continue

            point = bpy.data.objects.new(name, None)
            point.empty_display_type = 'SPHERE'
            point.empty_display_size = 0.01
            point.location = (
                (3.5 - string) * string_spacing,
                -fret_12_distance * fret / 12,
                0,
            )
            collection.objects.link(point)
            created += 1

    return created, existed


def read_guitar_points(string_count: int) -> tuple[dict, list]:
    """
    读取1到string_count弦的0品、12品定位点位置（世界坐标）
    返回({(弦序号, 品数): Vector}, 缺失的物体名列表)
    """
    points = {}
    missing = []
    for string in range(1, string_count + 1):
        for fret in (0, 12):
            name = guitar_point_name(string, fret)
            obj = bpy.data.objects.get(name)
            if obj is None:
                missing.append(name)
            else:
                points[(string, fret)] = obj.matrix_world.translation.copy()
    return points, missing


def record_base_states(base_state: BaseState) -> dict:
    """
    将当前控制器姿态记录为所有左右手基准状态（Set）。
    左手: P0~P4 × Normal/Outer/Inner/Barre（跳过无效组合）
    右手: Low/End/High 三个状态
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
        if base_state.transfer_right_hand_state(state, direction='set'):
            right_count += 1

    return {'left': left_count, 'right': right_count}


def one_click_initialize(instruments: Instruments, record_states: bool = True) -> dict:
    """
    一键初始化：创建所有控制器与记录器，并根据吉他定位点自动计算摆放指板记录器。
    Fret_P0: 1弦1品   Fret_P1: 最低弦1品
    Fret_P2: 1弦12品  Fret_P3: 最低弦12品
    record_states为True时，还会把当前控制器姿态记录为所有左右手基准状态。
    """
    # 创建所有控制器与记录器（已存在的会复用）
    base_state = BaseState(instruments)
    base_state.setup_all_objects()

    string_count = get_string_count(instruments)
    low_string = string_count
    points, missing = read_guitar_points(string_count)

    result = {
        'low_string': low_string,
        'missing': missing,
        'fret_placed': False,
        'positions': {},
        'states_recorded': None,
    }

    # 计算Fret_P0~P3需要1弦和最低弦两端的定位点，其余弦的定位点缺失不影响计算结果
    required = [(1, 0), (1, 12), (low_string, 0), (low_string, 12)]
    if any(key not in points for key in required):
        print("一键初始化: 缺少定位点，跳过Fret_P0~P3摆放")
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

    # 记录所有左右手基准状态
    if record_states:
        result['states_recorded'] = record_base_states(base_state)

    return result
