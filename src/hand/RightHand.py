from typing import List, Dict, Union, Any
import itertools
from numpy import array, linalg
import numpy as np
import json
from src.utils.caculateCrossPoint import get_cross_point
from src.utils.utils import getStringTouchPosition, slerp

RightFingers = {
    "p": 0,
    "i": 1,
    "m": 2,
    "a": 3
}


class RightHand():
    def __init__(self, usedFingers: List[str], rightFingerPositions: List[int], preUsedFingers: List[str], isArpeggio: bool = False):
        self.usedFingers = usedFingers
        self.rightFingerPositions = rightFingerPositions
        self.preUsedFingers = preUsedFingers
        self.isArpeggio = isArpeggio

    def validateRightHand(self, usedFingers=None, rightFingerPositions=None) -> bool:

        if rightFingerPositions == None:
            rightFingerPositions = self.rightFingerPositions
        if usedFingers == None:
            usedFingers = self.usedFingers

        return validateRightHandByFingerPositions(usedFingers, rightFingerPositions, False)

    def caculateDiff(self, otherRightHand: "RightHand") -> float:
        # 重复使用同一根手指的惩罚机制
        repeat_punish = 10
        diff = 0
        # 计算手指改变所在弦位置的情况，每有移动一根弦距就加1单位的diff
        for i in range(4):
            diff += abs(self.rightFingerPositions[i] -
                        otherRightHand.rightFingerPositions[i])

        # 检测两只手的usedFingers相同的元素个数有多少
        common_elements = list(set(self.usedFingers).intersection(
            set(otherRightHand.usedFingers)))
        pre_common_elements = list(set(self.preUsedFingers).intersection(
            set(otherRightHand.usedFingers)))
        same_finger_count = len(common_elements)
        pre_same_finger_count = len(pre_common_elements)

        # 检测重复使用的手指中有没有P指，如果有的话按加repeat_punish来计算重复指惩罚
        if 'p' in common_elements:
            diff += repeat_punish
            same_finger_count -= 1

        if 'p' in pre_common_elements:
            diff += 0.5 * repeat_punish
            pre_same_finger_count -= 1

        # 其它重复使用的手指按双倍repeat_punish来算，也就是非常不鼓励除P指以外的手指重复使用
        diff += 2 * repeat_punish * \
            (same_finger_count + 0.5 * pre_same_finger_count)

        # 不考虑手掌移动，因为手掌是由身体来带动的，它的移动比手指移动要来得轻松
        return diff

    def output(self):
        print("RightHand: ", self.usedFingers, self.rightFingerPositions)


def validateRightHandByFingerPositions(usedFingers, rightFingerPositions: List[int], repeated_fingers_checked: bool) -> bool:
    for i in range(len(rightFingerPositions) - 1):
        # 检测手指的位置是否从左到右递减，如果手指分布不符合科学，判断为错误
        if rightFingerPositions[i] < rightFingerPositions[i+1]:
            return False

    # 如果没有p指，而且其它手指已经预检测掉了重复和可能性，那么就直接返回True
    if 'p' not in usedFingers and repeated_fingers_checked:
        return True

    usedString = []
    used_p_strings = []
    for finger in usedFingers:
        current_string = rightFingerPositions[RightFingers[finger]]
        if finger == 'p':
            used_p_strings.append(current_string)
        elif not repeated_fingers_checked:
            # 如果没有预检测过其它手指是否重复触弦，通过下面的方式来检测
            if current_string not in usedString:
                usedString.append(current_string)
            else:
                return False

    # 如果p指只有1根弦或者没有触弦，那么就直接返回True
    if len(used_p_strings) < 2:
        return True

    # 如果p指触的两根弦并不相邻，那么就直接返回False
    if abs(used_p_strings[0] - used_p_strings[1]) > 1:
        return False

    # 如果p指双拨的弦最高超过了3，那么就直接返回False
    if min(used_p_strings) < 3:
        return False

    return True


def finger_string_map_generator(allFingers: List[str], touchedStrings: List[int], unusedFingers: List[str], allStrings: List[int], prev_finger_string_map: List[Dict[str, Any]] = []):
    if touchedStrings == []:
        for result in rest_finger_string_map_generator(unusedFingers, allStrings, prev_finger_string_map):
            yield result

    for current_finger, touchedString in itertools.product(allFingers, touchedStrings):
        current_pairing_is_legal = True
        current_finger_index = RightFingers[current_finger]

        # 检测当前配对组合是否和之前生成的配对组合有冲突
        for pairing in prev_finger_string_map:
            prev_finger = pairing['finger']
            prev_string = pairing['string']
            prev_index = RightFingers[prev_finger]
            # 这里注意，finger是从pima递增的，但现实中它们拨的弦序号是递减的，所以判断合理性时要留意这一点
            if (current_finger_index > prev_index and touchedString >= prev_string) or (current_finger_index < prev_index and touchedString <= prev_string) or (current_finger_index == prev_index and abs(prev_string-touchedString) > 1):
                current_pairing_is_legal = False

        if current_pairing_is_legal:
            next_allFingers = allFingers[:]
            next_allFingers.remove(current_finger)

            next_touchedStrings = touchedStrings[:]
            next_touchedStrings.remove(touchedString)

            next_unusedFingers = unusedFingers[:]
            next_unusedFingers.remove(current_finger)

            current_pairing = [
                {"finger": current_finger, "string": touchedString}]

            next_finger_string_map = prev_finger_string_map + current_pairing

            for result in finger_string_map_generator(next_allFingers, next_touchedStrings, next_unusedFingers, allStrings, next_finger_string_map):
                yield current_pairing + result


def rest_finger_string_map_generator(unusedFingers: List[str], allStrings: List[int], prev_finger_string_map: List[Dict[Any, Any]] = []):
    """
    这个方法是将剩余的不拨弦的手指与弦进行配对
    """

    if unusedFingers == []:
        yield []
        return

    # 这里每次配对以后，不再移除已经配对的弦，因为不演奏的手指可以放在任一根弦上
    for current_finger, cur_string in itertools.product(unusedFingers, allStrings):
        current_pairing_is_legal = True
        current_finger_index = RightFingers[current_finger]

        # 检测当前配对组合是否和之前生成的配对组合有冲突
        for pairing in prev_finger_string_map:
            prev_finger = pairing['finger']
            prev_string = pairing['string']
            prev_index = RightFingers[prev_finger]
            if (current_finger_index > prev_index and cur_string > prev_string + 1) or (current_finger_index < prev_index and cur_string < prev_string-1):
                current_pairing_is_legal = False

        if current_pairing_is_legal:
            next_allFingers = unusedFingers[:]
            next_allFingers.remove(current_finger)

            current_pairing = [
                {"finger": current_finger, "string": cur_string}]

            updated_finger_string_map = prev_finger_string_map + current_pairing
            for result in rest_finger_string_map_generator(next_allFingers, allStrings, updated_finger_string_map):
                yield current_pairing + result


def generatePossibleRightHands(touchedStrings: List[int], allFingers: List[str], allStrings: List[int]):
    possibleCombinations = []

    if len(touchedStrings) > 4:
        usedFingers = []
        rightFingerPositions = [5, 4, 3, 2]
        possibleCombinations.append({
            'usedFingers': usedFingers,
            'rightFingerPositions': rightFingerPositions
        })
    else:
        unused_fingers = allFingers[:]
        for result in finger_string_map_generator(allFingers, touchedStrings, unused_fingers, allStrings):
            # 输出的结果必须是每个手指都有对应的位置，否则说明配对不合法
            if result == None or len(result) < len(allFingers):
                continue
            rightFingerPositions = sort_fingers(result)
            usedFingers = get_usedFingers(result, touchedStrings)
            possibleCombinations.append({
                'usedFingers': usedFingers,
                'rightFingerPositions': rightFingerPositions
            })
    return possibleCombinations


def sort_fingers(finger_list: List[Any]):
    order = {'p': 0, 'i': 1, 'm': 2, 'a': 3}
    sorted_list = sorted(finger_list, key=lambda x: order[x['finger']])
    return [item['string'] for item in sorted_list]


# 这里把p指的重复演奏进行处理，只留下可能的情况，并只留一个p指数据
def process_p_fingers(result):
    p_fingers = [f for f in result if f['finger'] == 'p']
    strings = [f['string'] for f in p_fingers]
    if abs(strings[0] - strings[1]) != 1:
        return None
    min_string = min(strings)
    result.remove({'finger': 'p', 'string': min_string})
    return result


def get_usedFingers(finger_list: List[Any], usedStrings: List[int]):
    return [item['finger'] for item in finger_list if item['string'] in usedStrings]


def old_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, usedRightFingers: List[str], fingerMoveDistanceWhilePlay: float):
    result = {}
    default_position = {
        "h": 2, "p": 4, "i": 2, "m": 1, "a": 0
    }

    H_default = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'h{default_position["h"]}'])
    T_defalut = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'p{default_position["p"]}'])
    I_default = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'i{default_position["i"]}'])
    M_default = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'm{default_position["m"]}'])
    R_default = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'a{default_position["a"]}'])
    # ch指是总是和a指在同一弦上
    P_default = array(avatar_data['RIGHT_HAND_POSITIONS']
                      [f'ch{default_position["a"]}'])

    # 如果是扫弦，只计算h的位置，然后根据相对位置计算出其它手指的位置
    if isArpeggio:
        if isAfterPlayed:
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['h_end'])
            H_Eulers = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P3'])
            HP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_TP_R'])
        else:
            H_Eulers = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['h0'])
            HP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_TP_R'])

        T_R = array(H_R) + T_defalut - H_default
        I_R = array(H_R) + I_default - H_default
        M_R = array(H_R) + M_default - H_default
        R_R = array(H_R) + R_default - H_default
    else:
        # 根据手掌的位置先计算所有确定手掌和手臂位置的点
        h0 = array(avatar_data['RIGHT_HAND_POSITIONS']['h0'])
        h3 = array(avatar_data['RIGHT_HAND_POSITIONS']['h3'])
        H_R = h0 + hand_position * (h3 - h0) / 3

        h_rotation_0 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
        h_rotation_3 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P3'])
        H_Eulers = h_rotation_0 + hand_position * \
            (h_rotation_3 - h_rotation_0) / 3

        hp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_HP_R'])
        hp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_HP_R'])
        HP_R = hp_0 + hand_position * (hp_3 - hp_0) / 3

        tp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_TP_R'])
        tp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_TP_R'])
        TP_R = tp_0 + hand_position * (tp_3 - tp_0) / 3

        # 接下来计算每个手指的位置
        if "p" in usedRightFingers:
            T_R, t_move = caculateFingerPositionByHandPosition(H_R, h3,
                                                               avatar_data, 0, rightFingerPositions[0])
            if isAfterPlayed:
                T_R += t_move * fingerMoveDistanceWhilePlay * 1.2
        else:
            T_R = H_R + T_defalut - H_default

        # 注意，因为ima指运动方向与p指相反，所以这里的移动方向是相反的
        if "i" in usedRightFingers:
            I_R, i_move = caculateFingerPositionByHandPosition(H_R, h3,
                                                               avatar_data, 1, rightFingerPositions[1])
            if isAfterPlayed:
                I_R -= i_move * fingerMoveDistanceWhilePlay
        else:
            I_R = H_R + I_default - H_default

        if "m" in usedRightFingers:
            M_R, i_move = caculateFingerPositionByHandPosition(H_R, h3,
                                                               avatar_data, 2, rightFingerPositions[2])
            if isAfterPlayed:
                M_R -= i_move * fingerMoveDistanceWhilePlay
        else:
            M_R = H_R + M_default - H_default

        if "a" in usedRightFingers:
            R_R, i_move = caculateFingerPositionByHandPosition(H_R, h3,
                                                               avatar_data, 3, rightFingerPositions[3])
            if isAfterPlayed:
                R_R -= i_move * fingerMoveDistanceWhilePlay
        else:
            R_R = H_R + R_default - H_default

    # ch指是不动的，根据相对位置计算出ch的位置
    P_R = H_R + P_default - H_default

    result.update({
        'H_R': H_R.tolist(),
        'H_rotation_R': H_Eulers.tolist(),
        'HP_R': HP_R.tolist(),
        'TP_R': TP_R.tolist(),
        'T_R': T_R.tolist(),
        'I_R': I_R.tolist(),
        'R_R': R_R.tolist(),
        'M_R': M_R.tolist(),
        'P_R': P_R.tolist()
    })

    return result


def new_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, usedRightFingers: List[str], fingerMoveDistanceWhilePlay: float, max_string_index: int) -> Dict:
    """
    新的定位方法基本上是这样的：
    如果是扫弦，那么直接读取扫弦状态的基准状态，然后结束。
    如果不是扫弦，那么读取h0和h3状态，然后用hand_position计算出插值状态下所有的控件位置。
    接下来，使用计算出来的手掌位置和手指位置，计算出所有在拨弦手指的触弦点。而未使用的手指，需要保留在休息位置，就直接使用上一步计算出来的位置就行了。
    计算出来拨弦手指的触弦点以后，根据当前是否拨弦结束，来决定手指实际应该停留的位置。
    如果拨弦指是IMA指，那么预备点和结束点以及触弦点，都是在手掌->手指的直线上。
    如果拨弦指大拇指指，需要额外读取一个拨弦方向，然后计算出来预备点，结束点的位置。
    """
    result = {}

    if isArpeggio:
        if isAfterPlayed:
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['h_end'])
            H_Eulers = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P4'])
            HP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P4_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P4_TP_R'])
            T_R = array(avatar_data['RIGHT_HAND_POSITIONS']['p_end'])
            I_R = array(avatar_data['RIGHT_HAND_POSITIONS']['i_end'])
            M_R = array(avatar_data['RIGHT_HAND_POSITIONS']['m_end'])
            R_R = array(avatar_data['RIGHT_HAND_POSITIONS']['a_end'])
            P_R = array(avatar_data['RIGHT_HAND_POSITIONS']['ch_end'])
        else:
            H_Eulers = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['h0'])
            HP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_TP_R'])
            T_R = array(avatar_data['RIGHT_HAND_POSITIONS']['p0'])
            I_R = array(avatar_data['RIGHT_HAND_POSITIONS']['i0'])
            M_R = array(avatar_data['RIGHT_HAND_POSITIONS']['m0'])
            R_R = array(avatar_data['RIGHT_HAND_POSITIONS']['a0'])
            P_R = array(avatar_data['RIGHT_HAND_POSITIONS']['ch0'])
    else:
        # 根据手掌的位置先计算所有确定手掌和手臂位置的点
        h0 = array(avatar_data['RIGHT_HAND_POSITIONS']['h0'])
        h3 = array(avatar_data['RIGHT_HAND_POSITIONS']['h3'])
        H_R = h0 + hand_position * (h3 - h0) / 3

        h_rotation_0 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
        h_rotation_3 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P3'])
        H_Eulers = h_rotation_0 + hand_position * \
            (h_rotation_3 - h_rotation_0) / 3

        hp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_HP_R'])
        hp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_HP_R'])
        HP_R = hp_0 + hand_position * (hp_3 - hp_0) / 3

        tp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['P0_TP_R'])
        tp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['P3_TP_R'])
        TP_R = tp_0 + hand_position * (tp_3 - tp_0) / 3

        N_quat_0 = array(avatar_data['RIGHT_HAND_LINES']
                         ['right_hand_normal_p0']['vector'])
        N_quat_3 = array(avatar_data['RIGHT_HAND_LINES']
                         ['right_hand_normal_p3']['vector'])
        N_quat = N_quat_0 + hand_position * (N_quat_3 - N_quat_0) / 3

        P0 = array(avatar_data['LEFT_FINGER_POSITIONS']['P0'])
        P1 = array(avatar_data['LEFT_FINGER_POSITIONS']['P1'])
        P2 = array(avatar_data['LEFT_FINGER_POSITIONS']['P2'])
        P3 = array(avatar_data['LEFT_FINGER_POSITIONS']['P3'])
        string_direction = P2 - P0
        string_direction = string_direction / np.linalg.norm(string_direction)

        t0 = array(avatar_data['RIGHT_HAND_POSITIONS']['p0'])
        t3 = array(avatar_data['RIGHT_HAND_POSITIONS']['p3'])
        t_rest_postion = t0 + hand_position * (t3 - t0) / 3

        thumb_direction_0 = array(
            avatar_data['RIGHT_HAND_LINES']['right_thumb_direct_p0']['vector'])
        thumb_direction_3 = array(
            avatar_data['RIGHT_HAND_LINES']['right_thumb_direct_p3']['vector'])
        thumb_direction = thumb_direction_0 + hand_position * \
            (thumb_direction_3 - thumb_direction_0) / 3

        finger_direct_0 = array(
            avatar_data['RIGHT_HAND_LINES']['right_finger_direct_p0']['vector'])
        finger_direct_3 = array(
            avatar_data['RIGHT_HAND_LINES']['right_finger_direct_p3']['vector'])
        finger_direct = finger_direct_0 + hand_position * \
            (finger_direct_3 - finger_direct_0) / 3

        i0 = array(avatar_data['RIGHT_HAND_POSITIONS']['i0'])
        i3 = array(avatar_data['RIGHT_HAND_POSITIONS']['i3'])
        i_rest_position = i0 + hand_position * (i3 - i0) / 3

        m0 = array(avatar_data['RIGHT_HAND_POSITIONS']['m0'])
        m3 = array(avatar_data['RIGHT_HAND_POSITIONS']['m3'])
        m_rest_position = m0 + (m3 - m0) * hand_position / 3

        a0 = array(avatar_data['RIGHT_HAND_POSITIONS']['a0'])
        a3 = array(avatar_data['RIGHT_HAND_POSITIONS']['a3'])
        a_rest_position = a0 + (a3 - a0) * hand_position / 3

        ch0 = array(avatar_data['RIGHT_HAND_POSITIONS']['ch0'])
        ch3 = array(avatar_data['RIGHT_HAND_POSITIONS']['ch3'])
        ch_rest_position = ch0 + (ch3 - ch0) * hand_position / 3

        # 接下来计算每个手指的位置
        if "p" in usedRightFingers:
            p_current_string_index = rightFingerPositions[0]
            # t_target就是大拇指运动时的目标位置，和其它手指都是向掌心运动不同，大拇指是往弦上运动的
            t_target = t_rest_postion + thumb_direction
            t_touch_position = getStringTouchPosition(
                t_target, t_rest_postion, N_quat, P0, P1, P2, P3, p_current_string_index, max_string_index)
            # 读取大拇指拨弦的方向
            t_move = thumb_direction / np.linalg.norm(thumb_direction)
            if isAfterPlayed:
                T_R = t_touch_position - t_move * fingerMoveDistanceWhilePlay * 1.2
            else:
                T_R = t_touch_position + t_move * fingerMoveDistanceWhilePlay * 1.2
        else:
            T_R = t_rest_postion

        # 处理i, m, a三个手指的计算,有一个小`r`其实就是a指的英文ring
        finger_configs = [
            ('i', 1, i_rest_position),
            ('m', 2, m_rest_position),
            ('r', 3, a_rest_position)
        ]

        finger_results = {}

        # 计算手指的拨弦方向
        t_move = finger_direct / np.linalg.norm(finger_direct)

        # 处理ima三个手指的拨弦，它们的逻辑是相似的
        for finger_char, finger_idx, rest_pos in finger_configs:
            # 小拇指的英文缩写和吉他用语里的左手小拇指不一样，导致这个判断的写法会啰嗦一点
            if finger_char in usedRightFingers or finger_char == 'r' and 'a' in usedRightFingers:
                current_string_index = rightFingerPositions[finger_idx]
                target = rest_pos + finger_direct
                touch_position = getStringTouchPosition(
                    target, rest_pos, N_quat, P0, P1, P2, P3, current_string_index, max_string_index)

                if isAfterPlayed:
                    finger_results[finger_char.upper() + '_R'] = touch_position + \
                        t_move * fingerMoveDistanceWhilePlay
                else:
                    finger_results[finger_char.upper() + '_R'] = touch_position - \
                        t_move * fingerMoveDistanceWhilePlay
            else:
                finger_results[finger_char.upper() + '_R'] = rest_pos

        # 然后分别赋值
        I_R = finger_results['I_R']
        M_R = finger_results['M_R']
        R_R = finger_results['R_R']

        # ch指是不参与演奏的，所以直接使用休息位置
        P_R = ch_rest_position

    result.update({
        'H_R': H_R.tolist(),
        'H_rotation_R': H_Eulers.tolist(),
        'HP_R': HP_R.tolist(),
        'TP_R': TP_R.tolist(),
        'T_R': T_R.tolist(),
        'I_R': I_R.tolist(),
        'M_R': M_R.tolist(),
        'R_R': R_R.tolist(),
        'P_R': P_R.tolist()
    })
    return result


def caculateRightHandFingers(avatar_data: dict, rightFingerPositions: List[int], usedRightFingers: List[str], max_string_index: int = 5, isAfterPlayed: bool = False) -> Dict:

    use_new_finger_position_method = False
    right_hand_normal_data = avatar_data['RIGHT_HAND_LINES'].get(
        'right_hand_normal_p0', None)
    if right_hand_normal_data:
        use_new_finger_position_method = True

    finger_indexs = {
        "p": 0,
        "i": 1,
        "m": 2,
        "a": 3
    }

    isArpeggio = usedRightFingers == []

    hand_position = 0

    if not isArpeggio:
        offsets = 0
        for usedfinger in usedRightFingers:
            current_finger_position = rightFingerPositions[finger_indexs[usedfinger]]
            mutilplier = 3 if usedfinger == 'p' else 1
            offsets += current_finger_position * mutilplier

        total_finger_weights = len(
            usedRightFingers) if 'p' not in usedRightFingers else len(usedRightFingers) + 3
        average_offset = offsets / total_finger_weights
        """
        这一段解释一下：
        我只在blender里调整了h0和h3的两个位置，然后通过这两个位置的average_offset来计算其它手指的位置。 
        所谓 average_offset， 是计量了所有需要弹奏的手指的位置的平均值，然后通过这个平均值来决定手掌的位置，最后面再决定那些没有参与演奏的手指的位置。
        在计算 average_offset时，p指是特殊处理了的，它的权重是3，因为p指是决定手掌位置最重要的手指。 
              
        h0和h3两个极端手型，这两个组合包含了各个手指实际上能触碰的最高和最低弦：
        h0是在{"p": 2, "i": 0, "m": 0, "a": 0}的位置上，它的average_offset是1, 同时h_position=0
        h3是在{"p": 5, "i": 4, "m": 3, "a": 2}的位置上，它的average_offset是6，同时h_position=3
        
        假定h_position都是线性分布，满足：
        h_position = m * average_offset + b
        
        根据上面这两个值，我们可以计算出来线性插值的斜率是：
        m = (3 - 0) / (6 - 1)  = 0.6
        
        最终线性插值的计算公式是：
        h_position = 0.6 * average_offset - 0.6
        
        而这个时间手掌的实际位置是：
        H_R = h0 + h_position * (h3 - h0) / 3
        """
        hand_position = 0.6 * average_offset - 0.6

    fingerMoveDistanceWhilePlay = 0.003

    if use_new_finger_position_method:
        result = new_finger_position_method(
            avatar_data, rightFingerPositions, isArpeggio, isAfterPlayed, hand_position, usedRightFingers, fingerMoveDistanceWhilePlay, max_string_index)
    else:
        result = old_finger_position_method(
            avatar_data, rightFingerPositions, isArpeggio, isAfterPlayed, hand_position, usedRightFingers, fingerMoveDistanceWhilePlay)

    return result


def caculateFingerPositionByHandPosition(H_R: np.ndarray, h3: np.ndarray, avatar_data: Any, finger_index: int, string_index: int) -> Any:
    """
    这是老版本的计算手指位置的方法：
    参数：
    H_R: 手掌位置
    h3: 手掌在position 3 时的位置
    avatar_data: avatar_data
    finger_index: 指的索引，0表示T指，1表示I指，M表示m指，3表示A指
    string_index: 弦的索引，用于定位和读取具体弦的方向向量值


    ------------------------------------------------------------
    这里需要解释一下为什么计算手指的位置需要这些参数：
    计算手指的位置，是根据手掌在position 3 时的几个定位来确定的，这几个定位是：
    h3,手掌在position 3时的位置
    每个手指的方向球，也就是T_ball, I_ball, M_ball, R_ball
    其中，I_ball,M_ball,R_ball与h3的连线，代表了拨弦时i,m,a指的运动方向
    而p5，也就是p指在position 3 时的位置，与T_ball的连线，代表了拨弦时p指的运动方向

    计算方法是：
    通过每个手指的方向连线，以及运动方向的起点（p指起点是p5，其它手指是h3），再加上代表吉它指板normal方向的向量guitar_suface_vector，我们可以得到一个平面
    然后再计算这个平面，与代表弦的直线string_line的交点，就是手指在拨弦时的起点。

    当然，每次计算时，手掌位置不一定还在h3，而是已经实时更新到了H_R，所以我们要更新运动方向的起点，对于i,m,a指来讲，就是H_R。
    对于p指来讲，就是偏移后的p5位置，它可以利用h3和H_R的offset量计算出。

    到这里可以总结一下，如果是用手指演奏，需要以下几个定位来进行计算：
    h0,h3，用来计算插值后的手掌位置H_R
    position 2 时的所有定位，包括{"p": 4, "i": 2, "m": 1, "a": 0}，用来计算非演奏状态下手指的相对位置
    position 3 时四个ball,也就是T_ball, I_ball, M_ball, R_ball，用来计算手指的运动方向

    如果是用pick演奏，则只需要每根弦上p指的位置，H和T则作为pick的子级，不需要另外计算。
    而且pick演奏时，即使是换弦，也不会影响H_P和T_P的位置。
    """
    direction_ball_list = ['T', 'I', 'M', 'R']
    direction_ball_name = f"{direction_ball_list[finger_index]}_ball"
    string_line_name = f"string_line_{string_index}"

    direction_ball_location = array(
        avatar_data['RIGHT_HAND_POSITIONS'][direction_ball_name])
    p5 = array(avatar_data['RIGHT_HAND_POSITIONS']['p5'])
    offset = H_R - h3
    direction_line_location = H_R if finger_index != 0 else p5 + offset
    direction_line_vector = direction_ball_location - \
        h3 if finger_index != 0 else direction_ball_location - p5

    string_line_location = array(
        avatar_data['RIGHT_HAND_LINES'][string_line_name]['location'])
    string_line_vector = array(
        avatar_data['RIGHT_HAND_LINES'][string_line_name]['vector'])
    guitar_suface_vector = array(
        avatar_data['RIGHT_HAND_LINES']['guitar_surface']['vector'])

    cross_point = get_cross_point(
        direction_line_location, direction_line_vector, guitar_suface_vector, string_line_location, string_line_vector)

    direction_line_vector = linalg.norm(direction_line_vector)

    return cross_point, direction_line_vector


def euler_to_rotation_matrix(euler_angles):
    roll, pitch, yaw = euler_angles

    Rx = np.array([[1, 0, 0],
                   [0, np.cos(roll), -np.sin(roll)],
                   [0, np.sin(roll), np.cos(roll)]])

    Ry = np.array([[np.cos(pitch), 0, np.sin(pitch)],
                   [0, 1, 0],
                   [-np.sin(pitch), 0, np.cos(pitch)]])

    Rz = np.array([[np.cos(yaw), -np.sin(yaw), 0],
                   [np.sin(yaw), np.cos(yaw), 0],
                   [0, 0, 1]])

    R = np.dot(np.dot(Rz, Ry), Rx)

    return R


def get_transformation_matrix(position, euler_angles):
    # 将旋转值转换为旋转矩阵
    rotation_matrix = euler_to_rotation_matrix(euler_angles)

    # 创建4x4的变换矩阵
    transformation_matrix = np.eye(4)

    # 将旋转矩阵和位置值填入变换矩阵
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = position

    return transformation_matrix


def calculateRightPick(avatar: str, stringIndex: int, isArpeggio: bool, should_stay_at_lower_position: bool) -> Dict:
    json_file = f'asset/controller_infos/{avatar}.json'
    with open(json_file, 'r') as f:
        data = json.load(f)

    result = {}

    if isArpeggio:
        T_R = data['RIGHT_HAND_POSITIONS']['pend']
        H_R = data['RIGHT_HAND_POSITIONS']['Normal_Pend_H_R']
        HP_R = data['RIGHT_HAND_POSITIONS']['Normal_Pend_HP_R']
        H_rotation_R = data['ROTATIONS']['H_rotation_R']['Normal']['Pend']
        result = {
            'T_R': T_R,
            'H_R': H_R,
            'HP_R': HP_R,
            'H_rotation_R': H_rotation_R
        }
    else:
        tr_high = data['RIGHT_HAND_POSITIONS']['p3']
        tr_low = data['RIGHT_HAND_POSITIONS']['p0']
        h_r_high = data['RIGHT_HAND_POSITIONS']['Normal_P3_H_R']
        h_r_low = data['RIGHT_HAND_POSITIONS']['Normal_P0_H_R']
        hp_r_high = data['RIGHT_HAND_POSITIONS']['Normal_P3_HP_R']
        hp_r_low = data['RIGHT_HAND_POSITIONS']['Normal_P0_HP_R']
        h_rotation_r_high = data['ROTATIONS']['H_rotation_R']['Normal']['P3']
        h_rotation_r_low = data['ROTATIONS']['H_rotation_R']['Normal']['P0']

        tr_diff = np.linalg.norm(np.array(tr_high) - np.array(tr_low))
        fingerMoveDistanceWhilePlay = tr_diff / 20

        move = data['RIGHT_HAND_LINES']["T_line"]['vector']
        thumb_weight = stringIndex / 5

        T_R = np.array(tr_high) * thumb_weight + \
            np.array(tr_low) * (1 - thumb_weight)
        H_R = np.array(h_r_high) * thumb_weight + \
            np.array(h_r_low) * (1 - thumb_weight)
        HP_R = np.array(hp_r_high) * thumb_weight + \
            np.array(hp_r_low) * (1 - thumb_weight)
        H_rotation_R = slerp(h_rotation_r_high, h_rotation_r_low, thumb_weight)

        # 如果当前pick位置在当前弦的位置之下，那么就是在低位置，否则就是在高位置
        multiplier = 1 if should_stay_at_lower_position else -1
        T_R += np.array(move) * fingerMoveDistanceWhilePlay * multiplier

        result = {
            'T_R': T_R.tolist(),
            'H_R': H_R.tolist(),
            'HP_R': HP_R.tolist(),
            'H_rotation_R': H_rotation_R.tolist(),
        }

    return result
