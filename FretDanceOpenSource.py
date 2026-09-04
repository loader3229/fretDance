# FretDance-OpenSource CLI
# 以 fretDancer.ipynb 为蓝本制作的命令行工具
import argparse
import json
import os

from src.HandPoseRecorder import HandPoseRecordPool, HandPoseRecorder, RightHandRecorder
from src.guitar.Guitar import Guitar
from src.guitar.GuitarString import createGuitarStrings, getKeynoteByValue
from src.hand.LeftFinger import LeftFinger
from src.hand.LeftHand import LeftHand
from src.hand.RightHand import RightHand
from src.midi.midiToNote import calculate_frame, export_midi_info, get_tempo_changes, midiToGuitarNotes
from src.animate.animate import (ElectronicRightHand2Animation, addPitchwheel,
                                 animated_guitar_string, leftHand2Animation,
                                 rightHand2Animation)
from FretDaner import (leftHand2ElectronicRightHand, update_recorder_pool,
                       update_right_hand_recorder_pool)

VERSION = "2609"

CONTROLLER_DIR = os.path.join("asset", "controller_infos")
MIDI_DIR = os.path.join("asset", "midi")
OUTPUT_DIRS = [
    os.path.join("output", "midi_info"),
    os.path.join("output", "hand_recorder"),
    os.path.join("output", "hand_animation"),
    os.path.join("output", "string_recorder"),
    os.path.join("output", "animation_config"),
]

# 各吉他类型的默认弦音高（从高音弦到低音弦排列）
GUITAR_TYPE_OPTIONS = {
    "guitar": ["e", "b", "G", "D", "A", "E1"],
    "bass": ["G1", "D1", "A1", "E2"],
}


def is_legacy_avatar(avatar: str) -> bool:
    """判断角色数据是否为旧版本格式（缺少新版右手键名 Normal_P0_H_R / Normal_P3_H_R）"""
    with open(os.path.join(CONTROLLER_DIR, avatar + ".json"), encoding="utf-8") as f:
        data = json.load(f)
    positions = data.get("RIGHT_HAND_POSITIONS", {})
    return "Normal_P0_H_R" not in positions and "Normal_P3_H_R" not in positions


def list_avatars():
    """列出所有可用的角色配置"""
    files = sorted(f[:-5] for f in os.listdir(CONTROLLER_DIR) if f.endswith(".json"))
    print("可用角色（asset/controller_infos 目录下）：")
    for name in files:
        tag = "电吉他" if name.endswith("_E") else "古典吉他/指弹"
        display_name = f"{name}（旧版本）" if is_legacy_avatar(name) else name
        print(f"  {display_name}  ({tag})")
    print("\n提示：以 _E 结尾的角色使用电吉他（匹克演奏），请确保 MIDI 也是电吉他的谱子。")
    print("旧版本角色使用历史数据格式，会自动选择对应版本的动画计算方法，无需额外操作。")
    return files


def resolve_midi_path(midi_arg: str) -> str:
    """解析 MIDI 路径，支持完整路径或 asset/midi 下的文件名（可省略 .mid 后缀）"""
    candidates = [
        midi_arg,
        os.path.join(MIDI_DIR, midi_arg),
        os.path.join(MIDI_DIR, midi_arg + ".mid"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        f"找不到 MIDI 文件：{midi_arg}\n"
        f"尝试过的路径：{candidates}\n"
        f"提示：可以把 MIDI 文件放到 {MIDI_DIR} 目录下，然后用文件名（不含后缀）来引用。"
    )


def parse_string_notes(notes_str: str) -> list:
    """解析自定义弦音高字符串，如 "e, b, G, D, A, E1\""""
    notes = [n.strip() for n in notes_str.replace("，", ",").split(",") if n.strip()]
    for note in notes:
        if getKeynoteByValue(note) is False:
            raise ValueError(f"无效的弦音高：{note}")
    return notes


def parse_tracks(tracks_str: str) -> list:
    """解析轨道编号字符串，如 "0,1\""""
    try:
        return [int(t.strip()) for t in tracks_str.split(",") if t.strip()]
    except ValueError:
        raise ValueError(f"无效的轨道编号：{tracks_str}（多个轨道请用逗号分隔，如 0,1）")


def cmd_info(args):
    """查看 MIDI 文件信息（对应 ipynb 第一步中的 export_midi_info）"""
    midi_path = resolve_midi_path(args.midi)
    os.makedirs("output", exist_ok=True)

    midi_name = os.path.splitext(os.path.basename(midi_path))[0]
    if os.path.dirname(os.path.abspath(midi_path)) == os.path.abspath(MIDI_DIR):
        print(export_midi_info(midi_name))
    else:
        print(f"MIDI 文件：{midi_path}")
        print("提示：完整曲目信息（各轨道乐器）仅支持 asset/midi 目录下的文件。")

    tempo_changes, ticks_per_beat = get_tempo_changes(midi_path)
    print("全曲的速度变化是:")
    for track, tempo, tick in tempo_changes:
        print(f"在{track}轨，tick为{tick}时，速度变为{tempo}")
    print(f"\n全曲的每拍tick数是:{ticks_per_beat}")


def cmd_generate(args):
    """执行完整的动画生成流水线（对应 ipynb 的九个步骤）"""
    # ---------- 前置检查 ----------
    avatar = args.avatar
    if not os.path.isfile(os.path.join(CONTROLLER_DIR, avatar + ".json")):
        print(f"错误：找不到角色配置文件 asset/controller_infos/{avatar}.json\n")
        list_avatars()
        return

    midi_path = resolve_midi_path(args.midi)

    if args.string_notes:
        guitar_string_notes = parse_string_notes(args.string_notes)
    else:
        guitar_string_notes = GUITAR_TYPE_OPTIONS[args.guitar_type]

    track_number = parse_tracks(args.tracks)

    FPS = args.fps
    channel_number = args.channel
    octave_down_checkbox = args.octave_down
    capo_number = args.capo
    disable_barre = args.disable_barre
    use_harm_note = args.use_harm_note

    for d in OUTPUT_DIRS:
        os.makedirs(d, exist_ok=True)

    # ---------- 第一步：解析 MIDI ----------
    filename = os.path.splitext(os.path.basename(midi_path))[0]
    track_number_string = "_".join([str(i) for i in track_number])
    notes_map_file = f"output/midi_info/{filename}_{track_number_string}_notes_map.json"
    messages_file = f"output/midi_info/{filename}_{track_number_string}_messages.json"
    left_hand_recorder_file = f"output/hand_recorder/{filename}_{track_number_string}_lefthand_recorder.json"
    left_hand_animation_file = f"output/hand_animation/{avatar}_{filename}_{track_number_string}_lefthand_animation.json"
    right_hand_recorder_file = f"output/hand_recorder/{filename}_{track_number_string}_righthand_recorder.json"
    right_hand_animation_file = f"output/hand_animation/{avatar}_{filename}_{track_number_string}_righthand_animation.json"
    guitar_string_recorder_file = f"output/string_recorder/{filename}_{track_number_string}_guitar_string_recorder.json"
    animation_config_file = f"output/animation_config/{avatar}_{filename}_{track_number_string}_animation_config.json"

    print("文件路径已初始化:")
    print(f"  音符映射文件: {notes_map_file}")
    print(f"  消息文件: {messages_file}")
    print(f"  左手记录文件: {left_hand_recorder_file}")
    print(f"  左手动画文件: {left_hand_animation_file}")
    print(f"  右手记录文件: {right_hand_recorder_file}")
    print(f"  右手动画文件: {right_hand_animation_file}")
    print(f"  吉他弦动画文件: {guitar_string_recorder_file}")

    tempo_changes, ticks_per_beat = get_tempo_changes(midi_path)
    notes_map, pitch_wheel_map, messages = midiToGuitarNotes(
        midi_path, useTracks=track_number, useChannel=channel_number,
        octave_down_checkbox=octave_down_checkbox, capo_number=capo_number)

    with open(notes_map_file, "w") as f:
        json.dump(notes_map, f, indent=4)
    with open(messages_file, "w") as f:
        json.dump(messages, f, indent=4)

    if os.path.dirname(os.path.abspath(midi_path)) == os.path.abspath(MIDI_DIR):
        print(export_midi_info(filename))

    print("全曲的速度变化是:")
    for track, tempo, tick in tempo_changes:
        print(f"在{track}轨，tick为{tick}时，速度变为{tempo}")
    print(f"\n全曲的每拍tick数是:{ticks_per_beat}\n")

    # 计算总时长
    total_tick = notes_map[-1]["real_tick"]
    total_frame = calculate_frame(tempo_changes, ticks_per_beat, FPS, total_tick)
    total_time = total_frame / FPS
    print(f"如果以{FPS}的fps做成动画，一共是{total_tick} ticks, 合计{total_frame}帧, 约{total_time}秒")

    # ---------- 第二步：初始化吉他和左手 ----------
    guitar_string_list = createGuitarStrings(guitar_string_notes)
    max_string_index = len(guitar_string_list) - 1

    for i, string in enumerate(guitar_string_list):
        print(f"弦{i}的音符范围是: {string.getBaseNote()} ~ {string.getBaseNote() + 12}")

    guitar = Guitar(guitar_string_list, use_harm_note)

    leftFingers = [
        LeftFinger(1, guitar_string_list[1], 5),
        LeftFinger(2, guitar_string_list[1], 6),
        LeftFinger(3, guitar_string_list[1], 7),
        LeftFinger(4, guitar_string_list[1], 8)
    ]
    initLeftHand = LeftHand(leftFingers)

    handPoseRecord = HandPoseRecorder()
    handPoseRecord.addHandPose(initLeftHand, 0, 0)

    handPoseRecordPool = HandPoseRecordPool(100)
    handPoseRecordPool.insert_new_hand_pose_recorder(handPoseRecord, 0)

    print("吉他和左手初始化完成")
    print(f"最大弦索引: {max_string_index}")
    print(f"初始手指位置: {[f'手指{f._fingerIndex}在{f.stringIndex}弦{f.fret}品' for f in leftFingers]}")

    # ---------- 第三步：生成左手按弦数据 ----------
    current_recoreder_num = 0
    previous_recoreder_num = 0
    total_steps = len(notes_map)

    print("开始生成左手按弦数据")
    update_recorder_pool(total_steps, guitar, handPoseRecordPool, notes_map,
                         current_recoreder_num, previous_recoreder_num)

    bestHandPoseRecord = handPoseRecordPool.curHandPoseRecordPool[0]
    bestEntropy = bestHandPoseRecord.currentEntropy
    print(f"最小消耗熵为：{bestEntropy}")
    bestHandPoseRecord.save(left_hand_recorder_file, tempo_changes, ticks_per_beat, FPS)
    print(f"总音符数应该为{total_steps}")
    print(f"实际输出音符数为{len(bestHandPoseRecord.handPoseList)}")

    # ---------- 第四步：处理推弦动作 ----------
    if len(pitch_wheel_map) > 0:
        print("检测到推弦动作，正在处理...")
        for item in pitch_wheel_map:
            frame = calculate_frame(tempo_changes, ticks_per_beat, FPS, item["real_tick"])
            item["frame"] = frame
        addPitchwheel(left_hand_recorder_file, pitch_wheel_map)
        print(f"已处理{len(pitch_wheel_map)}个推弦动作")
    else:
        print("未检测到推弦动作")

    # ---------- 第五步：生成左手动画数据 ----------
    print("正在生成左手动画数据...")
    leftHand2Animation(avatar, left_hand_recorder_file,
                       left_hand_animation_file, FPS, max_string_index,
                       disable_barre=disable_barre)
    print("左手动画数据生成完成")

    # ---------- 第六、七步：生成右手演奏数据 ----------
    print("开始生成右手演奏数据")
    if avatar.endswith("_E"):
        print("检测到电吉他角色，使用电吉他右手处理...")
        leftHand2ElectronicRightHand(left_hand_recorder_file, right_hand_recorder_file)
        ElectronicRightHand2Animation(avatar, right_hand_recorder_file,
                                      right_hand_animation_file, FPS, max_string_index)
        print("电吉他右手动画数据生成完成")
    else:
        is_playing_bass = max_string_index < 5
        print("使用古典吉他/finger bass右手处理...")
        initRightHand = RightHand(
            usedFingers=[], rightFingerPositions=[max_string_index, 2, 1, 0],
            preUsedFingers=[], is_playing_bass=is_playing_bass)

        initRightHandRecorder = RightHandRecorder()
        initRightHandRecorder.addHandPose(initRightHand, 0, 0)

        rightHandRecordPool = HandPoseRecordPool(100)
        rightHandRecordPool.insert_new_hand_pose_recorder(initRightHandRecorder, 0)

        current_recoreder_num = 0
        previous_recoreder_num = current_recoreder_num

        update_right_hand_recorder_pool(
            left_hand_recorder_file, rightHandRecordPool,
            current_recoreder_num, previous_recoreder_num, max_string_index)

        bestHandPoseRecord = rightHandRecordPool.curHandPoseRecordPool[0]
        bestEntropy = bestHandPoseRecord.currentEntropy
        print(f"最小消耗熵为：{bestEntropy}")
        bestHandPoseRecord.save(right_hand_recorder_file, tempo_changes, ticks_per_beat, FPS)

        print("正在生成古典吉他右手动画数据...")
        rightHand2Animation(avatar, right_hand_recorder_file,
                            right_hand_animation_file, FPS, max_string_index)
        print("古典吉他右手动画数据生成完成")

    # ---------- 第八步：生成吉他弦动画数据 ----------
    print("开始生成吉他弦动画数据...")
    animated_guitar_string(left_hand_recorder_file, guitar_string_recorder_file, FPS)
    print("吉他弦动画数据生成完成")

    # ---------- 第九步：输出结果与 Blender 插件动画配置 ----------
    animation_config = {
        "guitar_string_recorder_file": guitar_string_recorder_file,
        "left_hand_animation_file": left_hand_animation_file,
        "right_hand_animation_file": right_hand_animation_file,
    }
    with open(animation_config_file, "w") as f:
        json.dump(animation_config, f, indent=4)

    print(f'''全部执行完毕:
recorder文件被保存到了:
  - {left_hand_recorder_file}
  - {right_hand_recorder_file}
动画文件被保存到了:
  - {left_hand_animation_file}
  - {right_hand_animation_file}
吉他弦动画文件被保存到了:
  - {guitar_string_recorder_file}
Blender 插件动画配置文件（在插件"生成动画"中选择此文件即可一键生成全部动画）:
  - {animation_config_file}''')


def main():
    parser = argparse.ArgumentParser(
        prog="FretDanceOpenSource",
        description="FretDance-OpenSource CLI：把 MIDI 文件转换为吉他演奏动画数据（以 fretDancer.ipynb 为蓝本）",
    )
    parser.add_argument("--version", action="version", version=f"FretDance-OpenSource v{VERSION}")
    subparsers = parser.add_subparsers(dest="command")

    # list 子命令：列出所有可用角色
    subparsers.add_parser("list", help="列出所有可用的角色配置")

    # info 子命令：查看 MIDI 文件信息
    parser_info = subparsers.add_parser("info", help="查看 MIDI 文件信息（速度变化、轨道乐器等）")
    parser_info.add_argument("midi", help="MIDI 文件路径，或 asset/midi 目录下的文件名（可省略 .mid 后缀）")

    # generate 子命令：生成动画
    parser_generate = subparsers.add_parser("generate", help="生成吉他演奏动画数据")
    parser_generate.add_argument("-a", "--avatar", required=True,
                                 help="角色名称，为 asset/controller_infos 目录下的 json 文件名（不含后缀），如 1-ToyamaKasumi_E")
    parser_generate.add_argument("-m", "--midi", required=True,
                                 help="MIDI 文件路径，或 asset/midi 目录下的文件名（可省略 .mid 后缀）")
    parser_generate.add_argument("-t", "--tracks", default="0",
                                 help="要使用的 MIDI 轨道编号，多个轨道用逗号分隔（默认: 0）")
    parser_generate.add_argument("-c", "--channel", type=int, default=-1,
                                 help="MIDI 通道编号，-1 表示接受所有通道（默认: -1）")
    parser_generate.add_argument("--fps", type=int, default=24,
                                 help="Blender 中的 FPS（默认: 24）")
    parser_generate.add_argument("-g", "--guitar-type", choices=GUITAR_TYPE_OPTIONS.keys(), default="guitar",
                                 help="吉他类型（默认: guitar）")
    parser_generate.add_argument("-s", "--string-notes", default=None,
                                 help='自定义弦音高，用逗号分隔，如 "e, b, G, D, A, E1"。设置后吉他类型选项失效')
    parser_generate.add_argument("--octave-down", action="store_true",
                                 help="整体降一个八度")
    parser_generate.add_argument("--capo", type=int, default=0,
                                 help="原曲变调夹所在的品数（默认: 0）")
    parser_generate.add_argument("--disable-barre", action="store_true",
                                 help="禁用横按")
    parser_generate.add_argument("--use-harm-note", action="store_true",
                                 help="启用泛音")

    args = parser.parse_args()

    if args.command == "list":
        list_avatars()
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "generate":
        cmd_generate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
