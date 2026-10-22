# AGENTS.md — FretDance AI 协作手册

MIDI → 吉他/贝斯演奏动画数据生成器（Python 3.10+，uv 管理）。核心算法：左手按弦熵最小化求解 + 右手拨法搜索，输出 JSON 动画数据，由 Blender 插件导入生成关键帧。**本仓库原作者已停止更新**（继任者：MusicDoll 系列），改动以保持兼容为主，不做大重构。

## 入口文件（注意拼写，不要"纠正"）

| 文件 | 作用 |
| --- | --- |
| `FretDaner.py` | 核心管线库（注意：**没有 c**，与 `fretDancer.ipynb` 拼写不一致是历史产物） |
| `FretDanceOpenSource.py` | CLI 入口（argparse，子命令 `list` / `info` / `generate`） |
| `main.py` | Gradio Web UI 入口 |
| `fretDancer.ipynb` | 最初的 notebook 版本 |
| `__init__.py`（根目录） | 只是算法思路注释，不是包入口 |

## 常用命令

```bash
uv sync                                          # 安装依赖
uv run FretDanceOpenSource.py list               # 列出角色
uv run FretDanceOpenSource.py info <midi名>      # 查看 MIDI 信息
uv run FretDanceOpenSource.py generate -a <角色> -m <midi名>
uv run main.py                                   # Gradio 界面
python -m unittest tests.testUtils               # 运行测试
```

`generate` 默认 FPS=24；Gradio 界面默认 FPS=30。两处默认值不同是有意为之，改其中一处需检查另一处的文档。

## 目录约定

- `src/animate` 动画数据生成；`src/guitar` 吉他/弦/音符模型；`src/hand` 左右手求解；`src/midi` MIDI 解析；`src/utils` 工具
- `src/HandPoseRecorder.py` 平铺在 `src/` 根（不在子包内），导入路径为 `src.HandPoseRecorder`
- `src/fret_dance_addon/` 是 Blender 插件（打包为 zip 安装，目标 Blender 4.5），其中的 `readme.md` / `one_click_init.md` 随插件分发，**不要移到 docs/**。用 Blender MCP 实测插件时，先把改动文件复制到已安装目录 `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\fret_dance_addon\` 再重载插件，否则测试的是旧代码
- `asset/controller_infos/*.json` 角色配置（已被 .gitignore 忽略，仓库里可能看不到）；`asset/midi/` 存放 MIDI（同样被忽略）
- `output/` 全部为生成产物，勿手改、勿提交

## 关键规则

1. **角色名后缀决定演奏方式**：`_E` 结尾 = 电吉他（匹克，右手由左手直接推导）；`_B` 结尾 = 贝斯（4 弦，默认定弦 `G1,D1,A1,E2`）；其余 = 古典吉他/指弹。MIDI 谱面必须与角色类型匹配。
2. **弦音高表示**：如 `"e, b, G, D, A, E1"`，从高音弦到低音弦；大小写与数字后缀表示八度，解析见 `FretDanceOpenSource.py` 的 `parse_string_notes`。
3. **依赖以 pyproject.toml 为准**（uv.lock 同步）；`requirements.txt` 是旧版 pinned 清单，仅老用户使用，新增依赖不加进去。
4. 代码注释、日志、CLI 输出均为中文（部分双语），保持风格一致。
5. 输出文件名格式固定为 `{midi名}_{轨道号}_{用途}.json`（动画文件带 `{角色}_` 前缀），路径拼接逻辑在 `FretDaner.py` 的 `main()` 与 `FretDanceOpenSource.py` 的 `cmd_generate()`，改动需两处同步。

## 深入文档

| 文档 | 内容 |
| --- | --- |
| [docs/getting-started.md](docs/getting-started.md) | 安装、CLI 全参数、Gradio 用法、Blender 插件安装与完整工作流 |
| [docs/architecture.md](docs/architecture.md) | 管线架构、数据流、输出文件体系、角色配置格式 |
| [src/fret_dance_addon/readme.md](src/fret_dance_addon/readme.md) | 插件面板功能说明书 |
| [src/fret_dance_addon/one_click_init.md](src/fret_dance_addon/one_click_init.md) | 一键初始化原理（Fret 锚点插值、12 平均律推导） |

<!-- neat-freak: initialized at 2026-10-19 -->
