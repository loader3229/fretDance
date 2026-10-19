## FretDance

电吉他演奏视频: [芙宁娜-少女绮想曲](https://www.bilibili.com/video/BV183t9zXEu6/)

古典吉他演奏视频: [婕德-鸟之诗](https://www.bilibili.com/video/BV1HmY6zEEwZ/)

具体使用方法和介绍，请看知乎专栏：[fretDance 专栏](https://www.zhihu.com/column/c_1932748054936684153)

B 站上的系列视频教程：[fretDance 教程](https://www.bilibili.com/video/BV1jYp8zQEh2/?spm_id_from=333.1387.0.0)

### 插件说明

`src/fret_dance_addon` 文件夹下的内容是 blender 插件，使用方法是将整个文件夹压缩成一个 zip 文件，然后在 blender 的 addon 添加界面里找到这个 zip 文件并且添加即可。

插件的功能是为人物的初始化设置过程提供辅助。详见插件说明书：[src/fret_dance_addon/readme.md](src/fret_dance_addon/readme.md) 与一键初始化说明：[src/fret_dance_addon/one_click_init.md](src/fret_dance_addon/one_click_init.md)。

### 快速开始（命令行）

需要 Python 3.10+。安装 [uv](https://docs.astral.sh/uv/) 后：

```bash
uv sync
uv run FretDanceOpenSource.py list        # 列出可用角色（asset/controller_infos）
uv run FretDanceOpenSource.py info lemon  # 查看 asset/midi 下 MIDI 文件信息
uv run FretDanceOpenSource.py generate -a asuka -m lemon   # 生成动画数据
```

`generate` 常用参数：`-t` 轨道编号、`-c` 通道、`--fps`（默认 24）、`-s` 自定义弦音高、`--capo` 变调夹品数、`--octave-down` 降八度、`--disable-barre` 禁用横按、`--use-harm-note` 启用泛音。完整参数见 [docs/getting-started.md](docs/getting-started.md)。

另有 Gradio 网页界面（`uv run main.py`，默认 FPS 30）与最初的 notebook 版本（`fretDancer.ipynb`）。

---

## 停止更新说明

本仓库已停止更新。如果您对 music doll 系列项目感兴趣，可以前往以下仓库：

- **Unreal 版本**：[highmore9501/MusicDoll](https://github.com/highmore9501/MusicDoll)
- **Blender 版本**：[highmore9501/music_doll_blender](https://github.com/highmore9501/music_doll_blender)

music doll 是一个通过 MIDI 生成动画的系列项目，fret dance（吉他）只是其中一种乐器。

需要说明的是，music doll 中负责生成动画的部分并不开源；上面两个开源库，只是用于与 Unreal 和 Blender 软件进行数据交换的插件。

更多 music doll 相关的视频和成品，可以前往 B 站作者的个人空间查看：[作者个人空间](https://space.bilibili.com/1954959)
