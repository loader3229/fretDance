## FretDance

![pic](asset/img/20240517043331.png)

[中文说明点击这里](readMeCN.md)

Electric Guitar Performance Video: [Furina - Maiden's Capriccio](https://www.bilibili.com/video/BV183t9zXEu6/)

Classical Guitar Performance Video: [Jeht - Bird's Poem](https://www.bilibili.com/video/BV1HmY6zEEwZ/)

For detailed tutorials and documentation, please visit my Zhihu Column (知乎专栏): [fretDance Column](https://www.zhihu.com/column/c_1932748054936684153)

Tutorial in BiliBili: [FretDance Video Tutorial](https://www.bilibili.com/video/BV1jYp8zQEh2/?spm_id_from=333.1387.0.0)

### About Addon

The content in the `src/fret_dance_addon` folder is a Blender add-on. To use it, compress the entire folder into a zip file, then locate and install this zip file through Blender's add-on installation interface.

The add-on is designed to assist with the initialization setup process for character models. See the addon manual: [src/fret_dance_addon/readme.md](src/fret_dance_addon/readme.md) and the one-click init guide: [src/fret_dance_addon/one_click_init.md](src/fret_dance_addon/one_click_init.md).

### Quick Start (CLI)

Requires Python 3.10+. With [uv](https://docs.astral.sh/uv/) installed:

```bash
uv sync
uv run FretDanceOpenSource.py list        # list available avatars (asset/controller_infos)
uv run FretDanceOpenSource.py info lemon  # inspect a MIDI file in asset/midi
uv run FretDanceOpenSource.py generate -a asuka -m lemon   # generate animation data
```

Key `generate` options: `-t` MIDI tracks, `-c` channel, `--fps` (default 24), `-s` custom string notes, `--capo`, `--octave-down`, `--disable-barre`, `--use-harm-note`. Full parameter reference: [docs/getting-started.md](docs/getting-started.md).

There is also a Gradio web UI (`uv run main.py`, default FPS 30) and an original notebook version (`fretDancer.ipynb`).

### Note to English Readers:

Due to the extensive documentation content, I recommend viewing my Zhihu Column for complete information.

As the author is not a native English speaker, this README may contain machine-translated text. For better understanding, I suggest English readers:

1. Visit my Zhihu Column
2. Use browser translation plugins for optimal reading experience

The automatic translation from Chinese to English typically provides more accurate results than my direct machine translation here.

---

## Discontinuation Notice

This repository is no longer maintained. If you are interested in the music doll series, please check out the following repositories:

- **Unreal version**: [highmore9501/MusicDoll](https://github.com/highmore9501/MusicDoll)
- **Blender version**: [highmore9501/music_doll_blender](https://github.com/highmore9501/music_doll_blender)

music doll is a series of projects that generate animations from MIDI, and fret dance (guitar) is just one of the instruments it supports.

Please note that the animation generation part of music doll is **not open source**. The two open-source repositories above are only plugins for data exchange with Unreal and Blender software.

For more music doll related videos and finished works, you can visit the author's personal space on Bilibili: [Author's Bilibili Space](https://space.bilibili.com/1954959)
