from typing import List, Dict, Any
from ..guitar.Guitar import Guitar
import numpy as np
from numpy import linalg
import itertools
from mathutils import Vector, Quaternion


def convertNotesToChord(notes: List[int], guitar: Guitar) -> Any:
    """
    convert notes to a list of possible positions on the guitar. 将音符转换为吉他上的可能位置列表
    :param notes: notes. 多个音符
    :param guitar: guitar. 吉他
    :return: a list of possible positions on the guitar. 一个吉他上的可能位置列表
    """
    use_harm_notes = guitar.use_harm_notes
    all_harm_notes = guitar.harm_notes if use_harm_notes else []
    notePositions = []
    result = []

    for note in notes:
        possiblePositions = []
        # 从低到高开始计算在每根弦上的位置
        for guitarString in guitar.guitarStrings:
            guitarStringIndex = guitarString._stringIndex
            harm_notes = list(
                filter(lambda x: x["index"] == guitarStringIndex, all_harm_notes)) if use_harm_notes else []
            harm_frets = [harm_note["fret"]
                          for harm_note in harm_notes if harm_note["note"] == note] if use_harm_notes else []
            normal_fret = guitarString.getFretByNote(note)
            has_normal_fret = normal_fret is not False
            if len(harm_frets) == 0 and not has_normal_fret:
                continue
            # 低音弦的超高把位是无法按的
            if guitarStringIndex > 2 and normal_fret > 16 and not has_normal_fret:
                continue
            # 如果当前音符在当前弦上有位置，那么记录下来
            if len(harm_frets) > 0:
                for fret in harm_frets:
                    possiblePositions.append({
                        "index": guitarStringIndex,
                        "fret": fret
                    })
            if has_normal_fret:
                possiblePositions.append({
                    "index": guitarStringIndex,
                    "fret": normal_fret
                })
        notePositions.append(possiblePositions)

    # 对notePositions里所有可能的位置进行组合，确保生成的每个组合都不存在index重复的情况
    combinations = itertools.product(*notePositions)
    for combination in combinations:
        # 如果combination里的元素的index有重复，就跳过
        if len(combination) != len(set([position["index"] for position in combination])):
            continue

        frets = list(filter(bool, [position["fret"]
                     for position in combination]))
        if frets:
            # 如果combination里元素的fret的个数大于4，就跳过，因为四个手指按不下
            if len(set(frets)) > 4:
                continue
            # 如果combination里元素的fret的最小非零值和最大非值的差值大于6，就跳过
            maxFret = max(frets)
            minFret = min(frets)
            outLimitOnLowBar = minFret < 8 and maxFret - minFret > 5
            outLimitOnHighBar = minFret >= 8 and maxFret - minFret > 6
            if outLimitOnLowBar or outLimitOnHighBar:
                continue
            result.append(combination)
        else:
            result.append(combination)

    return result


def convertChordTofingerPositions(chord: List[Any]) -> List[List[Dict[str, int]]]:
    """
    convert chord to a list of possible hands. 将和弦转换为可能的手型列表
    :param chord: chord. 和弦
    :return: a list of possible hands. 一个可能的手型列表
    """
    result = []
    fingerList = [1, 2, 3, 4]

    for combination in generate_combinations_iter(chord, fingerList):
        if verifyValidCombination(combination) and combination not in result:
            result.append(combination)

    return result


def generate_combinations_iter(noteList: List[Dict[str, int]], fingerList: List[int]):
    """
    a iterator to generate all possible combinations of notes and fingers. 生成所有可能的音符与手指组合的迭代器
    :param noteList: a list of notes. 音符列表
    :param fingerList: a list of fingers. 手指列表
    """
    if not noteList:
        yield []
        return

    if noteList[0]["fret"] != 0:
        for finger in fingerList:
            for combination in generate_combinations_iter(noteList[1:], fingerList):
                note = noteList[0].copy()
                note["finger"] = finger
                yield [note] + combination
    else:
        for combination in generate_combinations_iter(noteList[1:], fingerList):
            note = noteList[0].copy()
            yield [note] + combination


def verifyValidCombination(combination: List[Dict[str, int]]) -> bool:
    """
    verify if a combination is valid. 验证组合是否有效
    """
    # 去掉combination里不包含手指的元素
    combination = list(filter(lambda x: "finger" in x, combination))

    if len(combination) < 2:
        return True

    # 将combinations按照finger排序
    combination = sorted(combination, key=lambda x: x["finger"])

    # if finger is smaller and fret is bigger, return false. 如果finger值小的手指，而Fret值反而大，返回false。
    for i in range(len(combination) - 1):
        if "finger" in combination[i+1] and "finger" in combination[i] and combination[i]["finger"] > combination[i + 1]["finger"] and combination[i]["fret"] < combination[i + 1]["fret"]:
            return False
        if "finger" in combination[i+1] and "finger" in combination[i] and combination[i]["finger"] < combination[i + 1]["finger"] and combination[i]["fret"] > combination[i + 1]["fret"]:
            return False
        # 如果出现非食指的跨弦横按，返回false
        if "finger" in combination[i+1] and "finger" in combination[i] and combination[i]["finger"] == combination[i + 1]["finger"] and combination[i]["fret"] == combination[i + 1]["fret"]:
            if combination[i]["finger"] != 1 and abs(combination[i]["index"]-combination[i+1]["index"]) > 1:
                return False

    # 将List转化成对象
    fingerFretDict = {}
    for note in combination:
        if note["finger"] in fingerFretDict:
            # 如果同一个手指按了不同的品，返回false
            if fingerFretDict[note["finger"]]["fret"] != note["fret"]:
                return False
            else:
                fingerFretDict[note["finger"]] = {
                    "fret": note["fret"],
                    "string": note["index"]
                }

    # 如果中指和无名指都在按弦而且两者相差大于1，返回false
    if "2" in fingerFretDict and "3" in fingerFretDict and fingerFretDict["3"]["fret"]-1 > fingerFretDict["2"]["fret"]:
        return False
    # 如果食指和中指都在按弦而且两者相差大于1，返回false
    if "1" in fingerFretDict and "2" in fingerFretDict and fingerFretDict["2"]["fret"]-1 > fingerFretDict["1"]["fret"]:
        return False
    # 如果食指和无名指都在按弦而且两者相差大于1，返回false
    if "3" in fingerFretDict and "4" in fingerFretDict and fingerFretDict["4"]["fret"]-1 > fingerFretDict["3"]["fret"] and abs(fingerFretDict["4"]["string"]-fingerFretDict["3"]["string"]) > 1:
        return False

    # if no above situation, return true. 以上情况都没有发生，返回true.
    return True


def rotate_vector(euler_angles: list):
    vector = np.array([1, 0, 0])
    # 旋转值已经是弧度，无需转换
    a = euler_angles[0]
    b = euler_angles[1]
    c = euler_angles[2]

    # 创建旋转矩阵
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)],
                   [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [
        0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(c), -np.sin(c), 0],
                   [np.sin(c), np.cos(c), 0], [0, 0, 1]])

    # 修改旋转矩阵的计算顺序
    R = np.dot(Rx, np.dot(Ry, Rz))

    # 将旋转矩阵应用到向量上
    rotated_vector = np.dot(R, vector)

    return rotated_vector


def slerp(q1, q2, t_tan):
    """
    四元数球面线性插值 (Spherical Linear Interpolation)
    :param q1: 第一个四元数 [x, y, z, w]
    :param q2: 第二个四元数 [x, y, z, w]
    :param t: 插值参数 [0, 1]
    :return: 插值后的四元数
    """
    # 标准化四元数
    q1 = q1 / linalg.norm(q1)
    q2 = q2 / linalg.norm(q2)

    # 如果两个四元数相同，直接返回
    if np.allclose(q1, q2):
        return q1

    # 计算两个四元数旋转值的夹角
    angel_max = np.arccos(np.dot(q1, q2)) / \
        np.linalg.norm(q1)
    tan_angel_max = np.tan(angel_max)
    current_angel = tan_angel_max * t_tan
    t = current_angel / angel_max

    # 计算点积
    dot = np.dot(q1, q2)

    # 如果点积为负，取反一个四元数以选择较短的路径
    if dot < 0.0:
        q2 = -q2
        dot = -dot

    # 如果四元数非常接近，使用线性插值避免数值不稳定
    if dot > 0.9995:
        result = q1 + t * (q2 - q1)
        return result / linalg.norm(result)

    # 计算角度和插值
    theta_0 = np.arccos(dot)
    theta = theta_0 * t
    sin_theta = np.sin(theta)
    sin_theta_0 = np.sin(theta_0)

    s1 = np.cos(theta) - dot * sin_theta / sin_theta_0
    s2 = sin_theta / sin_theta_0

    return s1 * q1 + s2 * q2


def lerp_by_fret(fret: float, value_1: Any, value_12: Any) -> Any:
    """
    根据品格数计算位置，支持三元位置向量和四元数旋转
    :param fret: 品格数
    :param value_1: 1品位置或旋转
    :param value_12: 12品位置或旋转
    :return: 对应品格的位置或旋转
    """
    # 处理边界情况
    if fret == 1:
        return value_1
    elif fret == 12:
        return value_12

    # 计算各种比率
    ratio_fret = 2**(-fret/12)
    ratio_1 = 2**(-1/12)
    ratio_12 = 2**(-12/12)  # 即 0.5

    # 检查是否为四元数（长度为4）或位置向量（长度为3）
    is_scalar = isinstance(value_1, (int, float)) or isinstance(
        value_12, (int, float))

    is_quaternion = False
    if not is_scalar:
        try:
            is_quaternion = len(value_1) == 4 and len(  # type: ignore
                value_12) == 4  # type: ignore
        except TypeError:
            # 如果无法获取长度，则不是四元数
            is_quaternion = False
            if len(value_1) != len(value_12):  # type: ignore
                print(fret)
                print(value_1)
                print(value_12)
                raise ValueError(
                    "value_1 and value_12 must have the same length.")

    if is_quaternion:
        # 计算插值参数
        t_tan = (ratio_fret - ratio_1) / (ratio_12 - ratio_1)

        # 四元数情况：使用球面线性插值
        return slerp(value_1, value_12, t_tan)
    else:
        # 计算插值参数
        t = (ratio_fret - ratio_1) / (ratio_12 - ratio_1)
        # 三元向量情况：使用线性插值
        return value_1 + (value_12 - value_1) * t


def getStringTouchPosition(H: np.ndarray, F: np.ndarray, N_quat: np.ndarray, P0: np.ndarray, P1: np.ndarray, P2: np.ndarray, P3: np.ndarray,
                           current_string_index: int, max_string_index: int):
    """
    计算吉他弦与手指运动平面的交点

    参数:
    H, F: 手掌和手指位置 (Vector)
    N_quat: 手背法线方向的旋转四元数 (Quaternion) 或 欧拉角 (Euler)
    P0, P2: 最低音弦上的两个端点位置 (Vector)
    P1, P3: 最高音弦上的两个端点位置 (Vector)
    current_string_index: 当前弦的索引
    max_string_index: 最大弦索引

    返回:
    交点位置 (Vector)
    """
    # 将旋转参数转换为方向向量
    # 基准向量为(0,0,1),也就是blender里的z轴方向
    base_vector = Vector((0, 0, 1))

    # 计算插值权重
    if max_string_index == 0:
        weight = 0
    else:
        weight = current_string_index / max_string_index

    # 通过插值计算当前弦的两个端点
    S = P0 + (P1 - P0) * weight  # 当前弦的一个端点
    E = P2 + (P3 - P2) * weight  # 当前弦的另一个端点

    # 计算弦的方向向量
    D_dir = E - S
    D_dir = D_dir / np.linalg.norm(D_dir)

    if len(N_quat) == 4:
        N_dir = Quaternion(N_quat) @ base_vector
        # 确保方向向量单位化
        N_dir = N_dir / np.linalg.norm(N_dir)
    elif len(N_quat) == 3:
        N_dir = N_quat
    else:
        raise ValueError("N_quat参数长度错误")

    # 计算平面内的向量HF = F - H
    HF = F - H

    # 计算平面法向量 M = HF × N_dir
    M = np.cross(HF, N_dir)

    # 检查平面法向量是否有效
    if np.linalg.norm(M) < 1e-5:
        raise ValueError("向量HF与N_dir平行，无法定义平面")

    # 计算弦起点到手指的向量 FS = S - F
    FS = S - F

    # 计算分母：M·D_dir
    denominator = np.dot(M, D_dir)

    # 检查弦是否平行于平面
    if abs(denominator) < 1e-5:
        raise ValueError("弦方向与平面平行，无交点")

    # 计算参数 t = - (M·HS) / (M·D_dir)
    numerator = np.dot(M, FS)
    t = -numerator / denominator

    # 计算交点 P = S + t * D_dir
    return S + t * D_dir
