from .MusicNote import MusicNote, KEYNOTES
from typing import List, Any


class GuitarString():
    """
    params:
    baseNote: Base note of the string. 弦的基音
    stringIndex: Index of the string, starting with the highest pitch as string 0. 弦的索引,以最高音为0弦开始计算
    """

    def __init__(self, baseNote: MusicNote, stringIndex: int):
        self._baseNote: MusicNote = baseNote
        self._stringIndex = stringIndex

    def getBaseNote(self) -> int:
        return self._baseNote.num

    @property
    def getStringIndex(self) -> int:
        return self._stringIndex

    def getFretByNote(self, note: int) -> int | bool:
        fret = note - self._baseNote.num
        if fret < 0 or fret > 23:
            return False
        return note - self._baseNote.num


def createGuitarStrings(notes: List[str]) -> List[GuitarString]:
    guitar_string_list = []
    for index in range(len(notes)):
        note = notes[index]
        note_num = getKeynoteByValue(note)
        base_note = MusicNote(note_num)
        # 第一弦是高音e弦
        guitar_string_list.append(GuitarString(base_note, index))

    return guitar_string_list


def getKeynoteByValue(value: str) -> Any:
    """
    transform the note to an integer value, C is 48. 将音符转换为一个整数值，C为48
    :param value: keynote such as `C`, `F1`
    :return: an integer value. 一个整数值
    """
    # 如果value在KEYNOTES中，直接返回
    if value in KEYNOTES:
        return KEYNOTES[value]
    # 如果value是单个小写字母，表示为高音
    elif value.upper() in KEYNOTES and value.islower() and len(value) == 1:
        return KEYNOTES[value] + 12
    # 如果value长度大于1，并且最后一个值是一个数字
    elif len(value) > 1 and value[-1].isdigit():
        # 如果第一个值是小写并在KEYNOTES中，说明当前值是高音，数字越大音越高
        if value[0] in KEYNOTES and value[0].islower():
            return KEYNOTES[value[0]] + 12 * int(value[-1])
        # 如果第一个值是大写并在KEYNOTES中，说明当前值是低音，数字越大音越低
        elif value[0:-1].upper() in KEYNOTES and value[0].isupper():
            return KEYNOTES[value[0]] - 12 * int(value[-1])
    # 处理带#号的音符
    elif len(value) > 1 and value[1:-1].isdigit() and value[-1] == "#":
        # 如果第一个值是小写并在KEYNOTES中，说明当前值是高音，数字越大音越高
        if value[0] in KEYNOTES and value[0].islower():
            return KEYNOTES[value[0]] + 12 * int(value[1:-1]) + 1
        # 如果第一个值是大写并在KEYNOTES中，说明当前值是低音，数字越大音越低
        elif value[0].upper() in KEYNOTES and value[0].isupper():
            return KEYNOTES[value[0]] - 12 * int(value[1:-1]) + 1
    # 处理不带数字的大写音符
    elif value.isupper() and value in KEYNOTES:
        return KEYNOTES[value]
    else:
        print("音符格式有误：", value)
        return False
