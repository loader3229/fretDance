from typing import List, Dict, Union, Any
import itertools
from numpy import array, linalg
import numpy as np
import json
from src.utils.caculateCrossPoint import get_cross_point
from src.utils.utils import getStringTouchPosition, slerp

RIGHT_FINGERS = {
    "p": 0,
    "i": 1,
    "m": 2,
    "a": 3
}


class RightHand():
    def __init__(self, usedFingers: List[str], rightFingerPositions: List[int], preUsedFingers: List[str], isArpeggio: bool = False, is_playing_bass: bool = False):
        self.usedFingers = usedFingers
        self.rightFingerPositions = rightFingerPositions
        self.preUsedFingers = preUsedFingers  # 之所以还要有上一个手型的手指列表，是为了计算diff时，考虑更多一点
        self.isArpeggio = isArpeggio
        self.is_playing_bass = is_playing_bass

    def validateRightHand(self, usedFingers: list[str] = [], rightFingerPositions: list[int] = []) -> bool:

        if len(rightFingerPositions) == 0:
            rightFingerPositions = self.rightFingerPositions
        if len(usedFingers) == 0:
            usedFingers = self.usedFingers

        return self.validateRightHandByFingerPositions(usedFingers, rightFingerPositions, False)

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

    def validateRightHandByFingerPositions(self, usedFingers: list[str], rightFingerPositions: List[int], repeated_fingers_checked: bool) -> bool:
        for i in range(len(rightFingerPositions) - 1):
            # 检测手指的位置是否从左到右递减，如果手指分布不符合科学，判断为错误;bass因为要考虑到会有im指交替拨低音弦的情况，需要另外考虑
            if rightFingerPositions[i] < rightFingerPositions[i+1] and not self.is_playing_bass:
                return False
            if rightFingerPositions[i] < rightFingerPositions[i+1]+1:
                return False

        # 如果没有p指，而且其它手指已经预检测掉了重复和可能性，那么就直接返回True
        if 'p' not in usedFingers and repeated_fingers_checked:
            return True

        usedString = []
        used_p_strings = []
        for finger in usedFingers:
            current_string = rightFingerPositions[RIGHT_FINGERS[finger]]
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
        current_finger_index = RIGHT_FINGERS[current_finger]

        # 检测当前配对组合是否和之前生成的配对组合有冲突
        for pairing in prev_finger_string_map:
            prev_finger = pairing['finger']
            prev_string = pairing['string']
            prev_index = RIGHT_FINGERS[prev_finger]
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
        current_finger_index = RIGHT_FINGERS[current_finger]

        # 检测当前配对组合是否和之前生成的配对组合有冲突
        for pairing in prev_finger_string_map:
            prev_finger = pairing['finger']
            prev_string = pairing['string']
            prev_index = RIGHT_FINGERS[prev_finger]
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


def new_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, used_right_fingers: List[str],  max_string_index: int) -> Dict:
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

    # 根据手掌的位置先计算所有确定手掌和手臂位置的点
    h0 = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P0_H_R'])
    h3 = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P3_H_R'])
    P0 = array(avatar_data['LEFT_FINGER_POSITIONS']['P0'])
    P1 = array(avatar_data['LEFT_FINGER_POSITIONS']['P1'])
    # 大拇指的移动方向以及其它手指的移动方向，一开始设置为None
    t_move = None
    f_move = None
    # 定义手指运动的距离，是P0和P1之间的距离的8分之1，相当于0.725的弦距
    fingerMoveDistanceWhilePlay = 0.725 * \
        np.linalg.norm(P0 - P1) / (max_string_index+1)

    if isArpeggio:
        if isAfterPlayed:
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_Pend_H_R'])
            H_rotation_R = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['Pend'])
            HP_R = array(
                avatar_data['RIGHT_HAND_POSITIONS']['Normal_Pend_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['tpend'])
            T_R = array(avatar_data['RIGHT_HAND_POSITIONS']['pend'])
            I_R = array(avatar_data['RIGHT_HAND_POSITIONS']['iend'])
            M_R = array(avatar_data['RIGHT_HAND_POSITIONS']['mend'])
            R_R = array(avatar_data['RIGHT_HAND_POSITIONS']['aend'])
            P_R = array(avatar_data['RIGHT_HAND_POSITIONS']['chend'])
        else:
            H_rotation_R = array(
                avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
            H_R = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P0_H_R'])
            HP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P0_HP_R'])
            TP_R = array(avatar_data['RIGHT_HAND_POSITIONS']['tp0'])
            T_R = array(avatar_data['RIGHT_HAND_POSITIONS']['p0'])
            I_R = array(avatar_data['RIGHT_HAND_POSITIONS']['i0'])
            M_R = array(avatar_data['RIGHT_HAND_POSITIONS']['m0'])
            R_R = array(avatar_data['RIGHT_HAND_POSITIONS']['a0'])
            P_R = array(avatar_data['RIGHT_HAND_POSITIONS']['ch0'])
    else:
        H_R = h0 + hand_position * (h3 - h0) / 3

        h_rotation_0 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P0'])
        h_rotation_3 = array(
            avatar_data['ROTATIONS']['H_rotation_R']['Normal']['P3'])

        if len(h_rotation_0) == 3:
            H_rotation_R = h_rotation_0 + hand_position * \
                (h_rotation_3 - h_rotation_0) / 3
        elif len(h_rotation_0) == 4:
            hand_weight = hand_position / 3
            H_rotation_R = slerp(h_rotation_0, h_rotation_3, hand_weight)
        else:
            raise Exception("Unknown hand rotation type")

        hp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P0_HP_R'])
        hp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['Normal_P3_HP_R'])
        HP_R = hp_0 + hand_position * (hp_3 - hp_0) / 3

        tp_0 = array(avatar_data['RIGHT_HAND_POSITIONS']['tp0'])
        tp_3 = array(avatar_data['RIGHT_HAND_POSITIONS']['tp3'])
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

        if "p" in used_right_fingers:
            p_current_string_index = rightFingerPositions[0]
            # t_target就是大拇指运动时的目标位置，和其它手指都是向掌心运动不同，大拇指是往弦上运动的
            t_target = t_rest_postion + thumb_direction
            t_touch_position = getStringTouchPosition(
                t_target, t_rest_postion, N_quat, P0, P1, P2, P3, p_current_string_index, max_string_index)
            # 读取大拇指拨弦的方向
            t_move = thumb_direction / np.linalg.norm(thumb_direction)
            if isAfterPlayed:
                T_R = t_touch_position + t_move * fingerMoveDistanceWhilePlay
            else:
                T_R = t_touch_position - t_move * fingerMoveDistanceWhilePlay
        else:
            T_R = t_rest_postion

        # 处理i, m, a三个手指的计算,有一个小`r`其实就是a指的英文ring
        finger_configs = [
            ('i', 1, i_rest_position),
            ('m', 2, m_rest_position),
            ('r', 3, a_rest_position)
        ]

        finger_results = {}

        # 处理ima三个手指的拨弦，它们的逻辑是相似的
        for finger_char, finger_idx, rest_pos in finger_configs:
            # 小拇指的英文缩写和吉他用语里的左手小拇指不一样，导致这个判断的写法会啰嗦一点
            if finger_char in used_right_fingers or finger_char == 'r' and 'a' in used_right_fingers:
                # 计算手指的拨弦方向，这里要注意因为在blender中方向线与手指运动的方式是相反的，所以这里要加负号
                f_move = -finger_direct / np.linalg.norm(finger_direct)
                current_string_index = rightFingerPositions[finger_idx]
                target = rest_pos + finger_direct
                touch_position = getStringTouchPosition(
                    target, rest_pos, N_quat, P0, P1, P2, P3, current_string_index, max_string_index)

                if isAfterPlayed:
                    finger_results[finger_char.upper() + '_R'] = touch_position + \
                        f_move * fingerMoveDistanceWhilePlay
                else:
                    finger_results[finger_char.upper() + '_R'] = touch_position - \
                        f_move * fingerMoveDistanceWhilePlay

            else:
                finger_results[finger_char.upper(
                ) + '_R'] = rest_pos

        # 然后分别赋值
        I_R = finger_results['I_R']
        M_R = finger_results['M_R']
        R_R = finger_results['R_R']

        # ch指是不参与演奏的，所以直接使用休息位置
        P_R = ch_rest_position

        # 给拨弦后的手掌添加一点移动，这个移动适用于所有不参与演奏的手指以及手掌自己
        h_move = f_move if f_move is not None else t_move
        if h_move is not None and isAfterPlayed:
            h_move = h_move * fingerMoveDistanceWhilePlay * 0.25
            H_R = H_R - h_move

            if "p" not in used_right_fingers:
                T_R -= h_move

            # 处理ima三个手指的拨弦，它们的逻辑是相似的
            for finger_char, finger_idx, rest_pos in finger_configs:
                # 小拇指的英文缩写和吉他用语里的左手小拇指不一样，导致这个判断的写法会啰嗦一点
                if finger_char not in used_right_fingers and (finger_char != 'r' or 'a' not in used_right_fingers):
                    finger_results[finger_char.upper(
                    ) + '_R'] -= h_move

    result.update({
        'H_R': H_R.tolist(),
        'H_rotation_R': H_rotation_R.tolist(),
        'HP_R': HP_R.tolist(),
        'TP_R': TP_R.tolist(),
        'T_R': T_R.tolist(),
        'I_R': I_R.tolist(),
        'M_R': M_R.tolist(),
        'R_R': R_R.tolist(),
        'P_R': P_R.tolist()
    })
    return result


def legacy_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, usedRightFingers: List[str], fingerMoveDistanceWhilePlay: float, max_string_index: int) -> Dict:
    """
    这是2025年8月（commit 88b6e66 重写右手动画时期）的定位方法，适用于当时录制的角色数据（如Jeht）。
    它的定位思路与现在的 new_finger_position_method 相同，区别在于读取的键名：
    当时的手掌位置键名是h0/h3（h0为高音弦手位，h3为低音弦手位，与现在Normal_P0/Normal_P3的命名刚好相反），
    扫弦结束状态使用P4后缀（现在的对应键名是Pend后缀）。
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


def old_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, usedRightFingers: List[str], fingerMoveDistanceWhilePlay: float) -> Dict:
    """
    这是2025年8月之前的旧版定位方法，适用于旧版数据（如asuka、Chihiro、mio_B等带有方向球的角色）。
    手指位置通过方向球(T/I/M/R_ball)与弦直线(string_line_N)的几何交点计算得出。
    """
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


def caculateFingerPositionByHandPosition(H_R: np.ndarray, h3: np.ndarray, avatar_data: Any, finger_index: int, string_index: int) -> Any:
    """
    这是老版本的计算手指位置的方法：
    参数：
    H_R: 手掌位置
    h3: 手掌在position 3 时的位置
    avatar_data: avatar_data
    finger_index: 指的索引，0表示T指，1表示I指，M表示m指，3表示A指
    string_index: 弦的索引，用于定位和读取具体弦的方向向量值

    计算方法是：
    通过每个手指的方向连线（方向球与h3的连线），以及运动方向的起点（p指起点是p5，其它手指是h3），
    再加上代表吉它指板normal方向的向量guitar_suface_vector，我们可以得到一个平面
    然后再计算这个平面，与代表弦的直线string_line的交点，就是手指在拨弦时的起点。
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


def legacy_2024_finger_position_method(avatar_data: Any, rightFingerPositions: List[int], isArpeggio: bool, isAfterPlayed: bool, hand_position: float, usedRightFingers: List[str], fingerMoveDistanceWhilePlay: float) -> Dict:
    """
    这是2024年5月版本的定位方法，适用于最早期的角色数据（如rem）。
    这种数据直接记录了每根弦上每个手指的位置（如i0~i5），计算时直接按弦索引取位即可。
    """
    result = {}

    # 这一版数据的手指运动方向是直接的向量值，不是带vector键的字典
    lines = avatar_data['RIGHT_HAND_LINES']

    hand_index = "h_end" if isArpeggio and isAfterPlayed else f"h{round(hand_position)}"
    H_R = array(avatar_data['RIGHT_HAND_POSITIONS'][hand_index])
    # 来一个随机大小为0.001的随机移动，避免出现完全相同的关键帧
    random_move = np.random.rand(3) * 0.001
    H_R = H_R + random_move
    result['H_R'] = H_R.tolist()

    finger_line_names = {
        "p": "T_line",
        "i": "I_line",
        "m": "M_line",
        "a": "P_line",
    }
    # 手指到控制器前缀的映射：p指是T，a指是R，ch指是P
    finger_controller_names = {
        "p": "T",
        "i": "I",
        "m": "M",
        "a": "R",
    }
    for finger, finger_index in RIGHT_FINGERS.items():
        if isArpeggio and isAfterPlayed:
            finger_position = array(
                avatar_data['RIGHT_HAND_POSITIONS'][f"{finger}_end"])
        else:
            finger_position = array(
                avatar_data['RIGHT_HAND_POSITIONS'][f"{finger}{rightFingerPositions[finger_index]}"])
        if isAfterPlayed and finger in usedRightFingers:
            move = array(lines[finger_line_names[finger]])
            finger_position = finger_position + \
                move * fingerMoveDistanceWhilePlay
        result[finger_controller_names[finger] + '_R'] = finger_position.tolist()

    # ch指总是和a指在同一弦上
    if isArpeggio and isAfterPlayed:
        P_R = array(avatar_data['RIGHT_HAND_POSITIONS']['ch_end'])
    else:
        P_R = array(
            avatar_data['RIGHT_HAND_POSITIONS'][f"ch{rightFingerPositions[3]}"])
    result['P_R'] = P_R.tolist()

    return result


def caculateRightHandFingers(avatar_data: dict, rightFingerPositions: List[int], usedRightFingers: List[str], max_string_index: int = 5, isAfterPlayed: bool = False) -> Dict:

    finger_indexs = {
        "p": 0,
        "i": 1,
        "m": 2,
        "a": 3
    }

    isArpeggio = usedRightFingers == []

    # 根据角色数据的格式，选择对应版本的计算方法（兼容历史多个版本的数据格式）
    right_hand_positions = avatar_data['RIGHT_HAND_POSITIONS']
    if 'Normal_P0_H_R' in right_hand_positions:
        # 新格式（如1-ToyamaKasumi_E、2-HanazonoTae_E）
        finger_method = new_finger_position_method
        hand_position_reversed = True
    elif avatar_data['RIGHT_HAND_LINES'].get('right_hand_normal_p0', None):
        # 2025年8月的中间格式（如Jeht），键名为h0/h3/P4后缀
        finger_method = legacy_finger_position_method
        hand_position_reversed = False
    elif 'T_ball' in right_hand_positions:
        # 旧格式（如asuka、Chihiro、mio_B），带有方向球和弦直线数据
        finger_method = old_finger_position_method
        hand_position_reversed = False
    else:
        # 2024年的早期格式（如rem），直接记录了每根弦上的手指位置
        finger_method = legacy_2024_finger_position_method
        hand_position_reversed = False

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
        h3是在{"p": 2, "i": 0, "m": 0, "a": 0}的位置上，它的average_offset是1, 同时h_position=3
        h0是在{"p": 5, "i": 4, "m": 3, "a": 2}的位置上，它的average_offset是6，同时h_position=0
        
        假定h_position都是线性分布，满足：
        h_position = m * average_offset + b
        
        根据上面这两个值，我们可以计算出来线性插值的斜率是：
        m = -0.6
        
        最终线性插值的计算公式是：
        h_position = -0.6 * average_offset + 3.6
        
        而这个时间手掌的实际位置是：
        H_R = h0 + h_position * (h3 - h0) / 3
        
        注意：新格式的数据（Normal_P0_H_R为低音弦手位，Normal_P3_H_R为高音弦手位）使用上面的公式；
        而历史格式的数据（h0为高音弦手位，h3为低音弦手位）的插值方向刚好相反，
        使用h_position = 0.6 * average_offset - 0.6。
        """
        if hand_position_reversed:
            hand_position = -0.6 * average_offset + 3.6
        else:
            hand_position = 0.6 * average_offset - 0.6

    if finger_method is new_finger_position_method:
        # 新方法内部会根据实际弦距自行计算拨弦幅度
        result = finger_method(
            avatar_data, rightFingerPositions, isArpeggio, isAfterPlayed, hand_position, usedRightFingers, max_string_index)
    else:
        # 历史格式的拨弦幅度是按6根弦的弦距标定的，弦更少的乐器（如4弦bass）需要按弦数放大
        fingerMoveDistanceWhilePlay = 0.003 * 6 / (max_string_index + 1)
        if finger_method is legacy_finger_position_method:
            result = finger_method(
                avatar_data, rightFingerPositions, isArpeggio, isAfterPlayed, hand_position, usedRightFingers, fingerMoveDistanceWhilePlay, max_string_index)
        else:
            result = finger_method(
                avatar_data, rightFingerPositions, isArpeggio, isAfterPlayed, hand_position, usedRightFingers, fingerMoveDistanceWhilePlay)

    return result


def calculateRightPick(avatar: str, stringIndex: int, isArpeggio: bool, should_stay_at_lower_position: bool, guitar_max_string_index: int = 5) -> Dict:
    json_file = f'asset/controller_infos/{avatar}.json'
    with open(json_file, 'r') as f:
        data = json.load(f)

    result = {}

    if 'Normal_P3_H_R' not in data['RIGHT_HAND_POSITIONS']:
        # 旧格式的电吉他角色（如Furina_E、miku_E）只记录了每根弦上p指的位置，
        # 拨片演奏时手掌和手臂作为子级不需要单独计算，只输出拇指位置即可
        fingerMoveDistanceWhilePlay = 0.009
        thumb_index = "p_end" if isArpeggio else f"p{stringIndex}"
        T_R = data['RIGHT_HAND_POSITIONS'][thumb_index][:]
        if not isArpeggio:
            t_line = data['RIGHT_HAND_LINES']["T_line"]
            # 早期数据（如yui_E）的T_line是直接的向量值，没有vector键
            move = t_line['vector'] if isinstance(t_line, dict) else t_line
            # 如果当前pick位置在当前弦的位置之下，那么就是在低位置，否则就是在高位置
            multiplier = 1 if should_stay_at_lower_position else -1
            T_R[0] += move[0] * fingerMoveDistanceWhilePlay * multiplier
            T_R[1] += move[1] * fingerMoveDistanceWhilePlay * multiplier
            T_R[2] += move[2] * fingerMoveDistanceWhilePlay * multiplier
        result['T_R'] = T_R

        return result

    if isArpeggio and should_stay_at_lower_position:
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
        # 这里的后缀high和low分别表示高音和低音，它刚刚好和stringIndex顺序相反
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
        # 因为相反，所以这里的权重应该是用1减一下
        thumb_weight = 1-(stringIndex / (guitar_max_string_index + 1))

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
