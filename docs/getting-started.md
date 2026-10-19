# 快速开始 / Getting Started

FretDance 把 MIDI 文件转换成吉他/贝斯演奏动画数据（JSON），再由 Blender 插件导入生成关键帧动画。完整流程：**准备素材 → CLI 生成数据 → Blender 插件导入生成动画**。

## 1. 环境准备

- Python 3.10+（推荐用 [uv](https://docs.astral.sh/uv/) 管理依赖）
- Blender 4.5+（仅导入动画数据时需要）

```bash
uv sync    # 按 pyproject.toml 安装依赖
```

不使用 uv 的老用户可用 `pip install -r requirements.txt`（旧版 pinned 清单，更新不及时，推荐上面的方式）。

## 2. 素材准备

| 素材 | 位置 | 说明 |
| --- | --- | --- |
| MIDI 文件 | `asset/midi/*.mid` | 目录被 .gitignore 忽略，需自备 |
| 角色配置 | `asset/controller_infos/<角色名>.json` | 由 Blender 插件"导出人物信息"生成，同样被忽略 |

角色名后缀决定演奏方式：

- `<名>_E` — 电吉他（匹克演奏），需搭配电吉他谱面的 MIDI
- `<名>_B` — 贝斯（4 弦指弹）
- 其余 — 古典吉他/指弹（6 弦）

用 `uv run FretDanceOpenSource.py list` 可查看当前可用的角色及类型。

## 3. 生成动画数据（CLI）

```bash
# 查看 MIDI 文件的轨道、乐器、速度变化
uv run FretDanceOpenSource.py info lemon

# 生成动画数据（角色 asuka，MIDI lemon）
uv run FretDanceOpenSource.py generate -a asuka -m lemon
```

### generate 全部参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `-a, --avatar` | 必填 | 角色名（`asset/controller_infos` 下的 json 文件名，不含后缀） |
| `-m, --midi` | 必填 | MIDI 路径，或 `asset/midi` 下文件名（可省略 `.mid`） |
| `-t, --tracks` | `0` | 使用的 MIDI 轨道编号，多轨逗号分隔（如 `0,1`） |
| `-c, --channel` | `-1` | MIDI 通道编号，`-1` 接受所有通道 |
| `--fps` | `24` | Blender 里的帧率 |
| `-s, --string-notes` | 按角色后缀自动 | 自定义弦音高，从高音弦到低音弦，如 `"e, b, G, D, A, E1"`；贝斯默认 `"G1, D1, A1, E2"` |
| `--capo` | `0` | 原曲变调夹所在品数 |
| `--octave-down` | 关 | 整体降一个八度 |
| `--disable-barre` | 关 | 禁用横按 |
| `--use-harm-note` | 关 | 启用泛音 |

### 输出结果

成功后数据写入 `output/`（详见 [architecture.md](architecture.md#4-输出文件体系)）。最后打印的 `output/animation_config/<角色>_<曲名>_<轨道>_animation_config.json` 是给 Blender 插件用的总配置。

## 4. Gradio 网页界面（可选）

```bash
uv run main.py
```

浏览器自动打开本地页面，功能与 CLI 相同：扫描 MIDI 信息、选角色/轨道/通道/弦音高、提交生成。注意界面默认 FPS 为 **30**（CLI 默认 24）。

## 5. Blender 插件导入

1. 打包插件：把 `src/fret_dance_addon` 整个文件夹压缩成 zip
2. Blender 中 `编辑 > 首选项 > 插件 > 安装`，选择 zip 并启用 **FretDance Controller Setup**
3. 3D 视图右侧边栏打开 **FretDance** 选项卡：
   - 「初始化」区域选乐器类型 → 点「一键初始化」创建控制器与记录器（详细原理见 [one_click_init.md](../src/fret_dance_addon/one_click_init.md)）
   - MMD 模型：选中骨架后点「初始化 mmd 骨骼」绑定手指，再点一次「一键初始化」记录基准状态
4. 「生成动画」区域：选择第 3 步输出的 `animation_config` JSON → 一键生成全部动画

插件面板各功能详见 [插件说明书](../src/fret_dance_addon/readme.md)。

## 6. 常见问题

- **找不到角色**：`asset/controller_infos/` 下没有对应 json。先用插件在 Blender 里为模型导出人物信息。
- **找不到 MIDI**：确认文件在 `asset/midi/` 下，或用完整路径传入。
- **提示没有合适的按法/拨法**：MIDI 谱面超出乐器音域或声部过密，检查角色类型与谱面是否匹配、是否需要 `--octave-down` 或自定义 `-s` 弦音高。
- **FPS 说明**：同一首曲子用不同 FPS 生成两次会得到不同帧数的动画数据，Blender 场景帧率需与生成时一致。

## 7. 运行测试

```bash
python -m unittest tests.testUtils
```

当前测试仅覆盖 `src/utils/utils.py` 的 `verifyValidCombination`（左手按弦合法性校验）。
