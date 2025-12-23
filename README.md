# [molexAudio] Normalization and Boosting Tool
[![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/tonywied17/6b1ae8d34f5a48d54593e829bdc66849/raw/molex-audio-cobertura-coverage.json&style=for-the-badge)](https://gist.github.com/tonywied17/6b1ae8d34f5a48d54593e829bdc66849)
[![tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/tonywied17/6b1ae8d34f5a48d54593e829bdc66849/raw/molex-audio-junit-tests.json&style=for-the-badge)](https://gist.github.com/tonywied17/6b1ae8d34f5a48d54593e829bdc66849)
<br>
![Tests (workflow)](https://img.shields.io/github/actions/workflow/status/tonywied17/audio-normalization/ci.yml?branch=main&label=workflow%20tests&style=for-the-badge)
![GitHub repo size](https://img.shields.io/github/repo-size/tonywied17/audio-normalization?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/top/tonywied17/audio-normalization?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/tonywied17/audio-normalization?style=for-the-badge)

This project is a command-line tool for normalizing and boosting audio tracks in media files. It helps you achieve consistent audio levels across files by analyzing loudness and applying fixes using FFmpeg. It also supports parallel processing to speed up batch operations.

## Windows Releases
A standalone executable and an optional Windows installer are available on the project's [Releases](https://github.com/tonywied17/audio-normalization/releases) page.

## Requirements

To run this project, you need the following:

- Python 3.x (tested with Python 3.12)
- FFmpeg (for audio processing)
- The libraries listed in `requirements.txt`

The CLI now auto-detects `ffmpeg` on your PATH. If FFmpeg is missing the interactive menu will offer a guided "Setup FFmpeg" flow (Windows/Scoop) to install Scoop and FFmpeg.

### Install Python and FFmpeg

1. **Install Python**
   - Make sure Python 3.x is installed on your system (the project is tested with Python 3.12). Download from https://www.python.org/downloads/.

2. **Install Dependencies**
   Once Python is installed, install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**
   - The simplest cross-platform way is to download from https://ffmpeg.org/download.html and add the `ffmpeg` executable to your PATH.
   - Alternatively, the application can auto-install FFmpeg on Windows: when `ffmpeg` is not detected the interactive menu offers a "Setup FFmpeg" option that will bootstrap Scoop and install FFmpeg for you. If you are having trouble with this flow, you can manually trigger it with the debug flag:

```bash
python -m audio_tool --debug-no-ffmpeg
```
Choose the "Setup FFmpeg" option from the menu to run the guided installer.

## Alternative Installation Method (Using Scoop)

For an easier installation with automatic environment variable setup, you can use [Scoop](https://scoop.sh/). For detailed instructions, see the [Scoop Installation Guide](/.github/readme/scoop_installation_guide.md).


## Usage

### Interactive CLI Menu

The interactive menu auto-detects FFmpeg. The recommended launcher is the top-level `audio_tool.py` which ensures the `src/` package is importable; run from the project root:

```bash
# run as a module from project root (recommended)
python -m audio_tool

# or run directly from project root
python audio_tool.py
```


#### CLI Screenshot
![Audio Tool 2.2](https://raw.githubusercontent.com/tonywied17/molex-audio/refs/heads/main/.github/readme/audio-tool-menu.gif)

### Command-Line Arguments

You can use the following arguments when running the tool from the command line:

| Argument                | Description                                                                                       | Example Usage                             |
|-------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------|
| `-n`, `--normalize`      | Path to a file or directory for normalization.                                                    | `python -m audio_tool -n "/path/to/fileOrDir"`         |
| `--I`                   | (Optional, with `--normalize`) Integrated loudness target in LUFS. Default: `-16`.               | `python -m audio_tool -n "/path/to/fileOrDir" --I -20` |
| `--TP`                  | (Optional, with `--normalize`) True peak target in dBFS. Default: `-1.5`.                        | `python -m audio_tool -n "/path/to/fileOrDir" --TP -2` |
| `--LRA`                 | (Optional, with `--normalize`) Loudness range target in LU. Default: `11`.                       | `python -m audio_tool -n "/path/to/fileOrDir" --LRA 10` |
| `-b`, `--boost`          | Path to a file or directory and boost percentage (e.g., 10 for +10%, -10 for -10%).              | `python -m audio_tool -b "/path/to/fileOrDir" 10` |
#### Notes:
- The `--I`, `--TP`, and `--LRA` arguments are optional and can only be used with `--normalize`.
- If no values are provided for `--I`, `--TP`, or `--LRA`, the tool will use the default normalization parameters specified in `src/core/config.py`.
- The `--boost` argument now supports both files and directories. When a directory is provided, all supported files inside will be boosted by the given percentage, with live progress and per-file status.
 - `--dry-run`: Build and show FFmpeg commands without executing them. Useful for debugging commands before running.
 - `--workers`: Set maximum parallel worker threads for batch processing. Defaults to auto-detected CPU count.
 - `--debug-no-ffmpeg`: Debug flag to simulate missing FFmpeg and exercise the setup flow.

## How It Works

1. **Normalization**: The tool analyzes the audio track of the specified media file(s) to determine the current loudness levels. It then calculates the necessary adjustments to bring the audio to the target levels defined by the user (or defaults). The tool uses FFmpeg to apply these adjustments and create a new normalized audio track.
2. **Audio Boost**: The tool can also apply a simple audio boost by increasing the volume of the audio track by a specified percentage. This is useful for making quiet audio tracks louder without performing full normalization.
3. **Parallel Processing**: The tool supports parallel processing, allowing multiple files to be processed simultaneously. This significantly speeds up the normalization and boosting process when dealing with large batches of files.
4. **Logging**: Detailed logs of the operations are maintained in the `logs/` directory, including FFmpeg command outputs for troubleshooting.
5. **Configuration**: Default settings such as target loudness levels and audio codecs can be adjusted in the `config.json` file.
6. **Auto-FFmpeg Setup (Windows/Scoop)**: If FFmpeg is not detected, the interactive menu offers a guided setup flow that installs Scoop (if needed) and then installs FFmpeg, simplifying the installation process for Windows users.

### Configuration via config.json

The application now supports a `config.json` file (created automatically in the project root on first run) which can be used to persist and override default settings. When present, values in `config.json` are merged with the built-in defaults at startup.

Common keys you can set in `config.json`:
- `NORMALIZATION_PARAMS`: an object with `I`, `TP`, and `LRA` (e.g. integrated loudness, true peak, loudness range).
- `AUDIO_CODEC`: the default output audio codec (e.g. `ac3`).
- `AUDIO_BITRATE`: default audio bitrate (e.g. `256k`).
- `SUPPORTED_EXTENSIONS`: array of file extensions the tool should consider.
- `LOG_DIR`, `LOG_FILE`, `LOG_FFMPEG_DEBUG`: logging paths and filenames.

Example `config.json` (project root):

```json
{
  "VERSION": "2.2",
  "NORMALIZATION_PARAMS": {
    "I": -16.0,
    "TP": -1.5,
    "LRA": 11.0
  },
  "SUPPORTED_EXTENSIONS": [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".m4a",
    ".wma",
    ".aac"
  ],
  "AUDIO_CODEC": "inherit",
  "AUDIO_BITRATE": "256k",
  "FALLBACK_AUDIO_CODEC": "ac3",
  "LOG_DIR": "logs/",
  "LOG_FILE": "app.log",
  "LOG_FFMPEG_DEBUG": "ffmpeg_debug.log",
  "TEMP_SUFFIX": "_temp_processing"
}
```

## Audio codec options

When the tool re-encodes audio it uses the codec specified in `AUDIO_CODEC` (or `inherit`). Common values and when to use them:

- `ac3`: Broadly compatible (Plex, many TVs/receivers). Good default for device compatibility.
- `aac`: Common inside MP4/M4V containers and streaming; good quality at moderate bitrates.
- `opus`: High quality at low bitrates; typically used in WebM/OGG.
- `flac`: Lossless; use when you want to preserve original quality (large files).
- `dts`, `eac3`: Consumer surround formats; usually preserved for passthrough to receivers rather than re-encoding.
- `pcm_s16le`: Uncompressed PCM — highest fidelity but very large files.
- `inherit`: Special value (the default). Re-encode each audio stream using the original codec reported by `ffprobe` (`codec_name`). If the original codec cannot be determined or is unsupported for the target container, the `FALLBACK_AUDIO_CODEC` setting (in `config.json`) will be used instead.

Tradeoffs: choosing a fixed codec like `ac3` gives predictable compatibility but changes the original codec (and may alter filesize/quality). `inherit` aims to preserve the original codec per-stream while still applying normalization.

How to use:
- Start the tool once to generate a default `config.json` (if missing), or create the file manually in the project root.
- Edit values and save; restart the tool for changes to take effect.

Note: `config.json` is intended for user-level defaults. Runtime precedence is:

1. Command-line arguments (highest precedence)
2. `config.json` values
3. Built-in defaults in `src/core/config.py` (lowest precedence)

So command-line arguments (e.g. `--I`, `--TP`, `--LRA`) will override values from the `config.json` file.