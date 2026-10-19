# 架构说明

FretDance 的核心思想（见根目录 `__init__.py` 的原始注释）：把 MIDI 音符流转成和弦序列，为每个和弦枚举所有可能的左手按法，用**熵（动作消耗）最小化**在数百个候选"手型轨迹"中保留最优的前 N 条，最终导出整只手逐帧的位置数据，交由 Blender 插件映射到角色骨骼。

## 1. 整体管线

```
MIDI 文件 (asset/midi)
   │  src/midi/midiToNote.py
   │    midiToGuitarNotes() → notes_map（音符→(弦,品)候选）+ pitch_wheel_map（推弦）
   │    get_tempo_changes() / calculate_frame() → tick→帧 换算
   ▼
左手求解 (src/hand + src/guitar)
   │  FretDaner.update_recorder_pool()
   │    convertNotesToChord → convertChordTofingerPositions 枚举按法
   │    LeftHand.generateNextHands 生成新手型并计算熵增量
   │    HandPoseRecordPool 只保留熵最小的前 100 条轨迹
   │  最优轨迹 → output/hand_recorder/*_lefthand_recorder.json
   ▼
右手求解
   ├─ 电吉他（角色 _E）：leftHand2ElectronicRightHand
   │    直接由左手记录推导被拨弦列表（匹克，无需搜索）
   └─ 古典吉他/贝斯：update_right_hand_recorder_pool()
        generatePossibleRightHands 枚举 p/i/m/a 分配 → 熵最小化
        → output/hand_recorder/*_righthand_recorder.json
   ▼
动画数据生成 (src/animate/animate.py)
   │  leftHand2Animation / rightHand2Animation / ElectronicRightHand2Animation
   │    读取 asset/controller_infos/<角色>.json 的控制器位置，
   │    把记录器数据插值成逐帧控制器位置（左手用 Fret_P0~P3 四锚点双线性插值）
   │  animated_guitar_string() → 弦振动动画
   │  addPitchwheel() → 推弦关键帧
   ▼
output/hand_animation / string_recorder / animation_config（JSON）
   ▼
Blender 插件 (src/fret_dance_addon)
    读取 animation_config，为控制器批量写入关键帧
```

## 2. 模块职责

| 模块 | 职责 |
| --- | --- |
| `src/midi/midiToNote.py` | MIDI 解析：轨道/通道过滤、降八度、变调夹、音符→吉他位置映射、tick→帧换算 |
| `src/guitar/` | 领域模型：`Guitar`（弦集合、泛音开关）、`GuitarString`（定弦与音域）、`MusicNote`（音名↔MIDI 号）、`GuitarNote` |
| `src/hand/` | 求解核心：`LeftFinger`/`LeftHand`（按弦指型、横按）、`RightHand`（拨指分配与合法性校验） |
| `src/HandPoseRecorder.py` | 轨迹记录池：熵累计、top-N 剪枝、序列化保存（平铺在 `src/` 根，导入路径 `src.HandPoseRecorder`） |
| `src/animate/animate.py` | 记录器数据 → 逐帧控制器位置 JSON（含左手锚点插值、弦动画、推弦） |
| `src/utils/` | 和弦↔指法转换、几何求交、lip sync 信息等工具 |
| `src/fret_dance_addon/` | Blender 插件（独立分发）：控制器初始化、状态 Set/Load、读取动画 JSON 写关键帧。详见插件目录内 `readme.md` / `one_click_init.md` |

## 3. 角色配置（asset/controller_infos/*.json）

由 Blender 插件"导出人物信息"生成，驱动动画端插值，关键字段：

- `LEFT_FINGER_POSITIONS`：左手四锚点 `P0~P3`（对应 Blender 中 `Fret_P0~P3` 记录器，几何含义为 1弦/最低弦 × 1品/12品），动画端按 12 平均律在品方向、按弦序在弦方向做双线性插值（`twiceLerpFingers`）
- `RIGHT_HAND_POSITIONS`：右手各状态（Low/End/High）的控制器与手指位置；新版含 `Normal_P0_H_R`/`Normal_P3_H_R` 键，缺少这两个键的旧版角色由 `is_legacy_avatar()` 自动识别并走旧版计算

## 4. 输出文件体系（output/，均被 .gitignore 忽略）

| 目录 | 文件名格式 | 内容 |
| --- | --- | --- |
| `midi_info/` | `<曲名>_<轨道>_notes_map.json` / `_messages.json` | 音符→位置映射原始数据、MIDI 消息 |
| `hand_recorder/` | `<曲名>_<轨道>_lefthand_recorder.json` / `_righthand_…` | 求解出的最优手型轨迹（与角色无关，只与 MIDI/定弦有关） |
| `hand_animation/` | `<角色>_<曲名>_<轨道>_lefthand_animation.json` / `_righthand_…` | 逐帧控制器位置（与角色绑定） |
| `string_recorder/` | `<曲名>_<轨道>_guitar_string_recorder.json` | 弦振动逐帧数据 |
| `animation_config/` | `<角色>_<曲名>_<轨道>_animation_config.json` | 三个动画文件路径的总配置，供插件"一键生成全部动画" |

注意：`hand_recorder` 与角色无关，同一 MIDI 换角色重跑时左手/右手求解会重复计算；`hand_animation` 才是角色相关产物。

## 5. 设计要点与约束

- **熵最小化搜索**：`HandPoseRecordPool(100)` 表示每一步只保留熵最小的 100 条候选轨迹，是速度/质量的核心权衡；轨迹中断（找不到合法按法）时重复上一手型兜底。
- **左右手解耦**：右手求解读取已落盘的左手记录文件（而非内存传递），因此左手 JSON 是两者的接口。
- **角色差异集中在后缀分支**：`avatar.endswith("_E")` 决定电吉他路径，`_B`/其他走指弹路径，定弦默认值随角色后缀切换。
- **Blender 插件与生成端只通过 JSON 耦合**：插件不依赖 Python 端代码；控制器命名约定（`Fret_P0~P3`、`H_L`/`HP_L`/`T_R` 等）是两端的隐式协议，详见 [one_click_init.md](../src/fret_dance_addon/one_click_init.md) 的"面板与代码对照"一节。
- **已知局限**：测试覆盖薄弱（仅 `verifyValidCombination`）；无 lint/CI 配置；本仓库已停止功能开发。
