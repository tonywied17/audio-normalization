# Audio Normalization

![GitHub repo size](https://img.shields.io/github/repo-size/tonywied17/audio-normalization?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/top/tonywied17/audio-normalization?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/tonywied17/audio-normalization?style=for-the-badge)

This project is a simple command-line tool for normalizing and boosting audio tracks in media files. It is designed to help users achieve consistent audio levels across different media files.
The tool calculates the average volume level of the audio track and adjusts it to a target level, making the audio more consistent and balanced. It also supports parallel processing to speed up the normalization process for multiple files.

## Requirements

To run this project, you need the following:

- Python 3.x (tested with Python 3.12)
- FFmpeg (for audio processing)
- The libraries listed in `requirements.txt`

### Install Python and FFmpeg

1. **Install Python**  
   Make sure Python 3.x is installed on your system. You can download it from [here](https://www.python.org/downloads/).

2. **Install FFmpeg**  
   You can download FFmpeg from [FFmpeg.org](https://ffmpeg.org/download.html). After downloading FFmpeg, ensure it's added to your system's PATH:

   - **Windows**: 
     1. Download the FFmpeg zip file from [FFmpeg.org](https://ffmpeg.org/download.html).
     2. Extract the contents and move the folder to a location like `C:\ffmpeg`.
     3. Open the **Start menu** and search for "Environment Variables".
     4. Under "System Properties", click on "Environment Variables".
     5. In the "System variables" section, select the "Path" variable and click "Edit".
     6. Add a new entry with the path to the `bin` folder inside the FFmpeg directory (e.g., `C:\ffmpeg\bin`).
     7. Click "OK" to save and apply.

3. **Install Dependencies**

Once Python and FFmpeg are installed, navigate to the project directory and install the required Python libraries:

```bash
pip install -r requirements.txt
```

This will install the necessary dependencies including `rich` for terminal output and progress bars.

## Alternative Installation Method (Using Scoop)

For an easier installation with automatic environment variable setup, you can use [Scoop](https://scoop.sh/). For detailed instructions, see the [Scoop Installation Guide](scoop_installation_guide.md).


## Usage

### Interactive CLI Menu

You can also launch the interactive CLI menu, which now supports both normalization and boosting for single files and directories, with a modern UI and live per-file progress:

```bash
python main.py
```

#### Main Menu
![Menu](https://molex.cloud/files/an-repo/menu.png)

#### Normalizing Audio Tracks for a Single File or Directory
![Normalize Directory Analyzing](https://molex.cloud/files/an-repo/normalize_directory_1.png)

![Normalize Directory Complete](https://molex.cloud/files/an-repo/normalize_directory_2.png)

#### Applying a Simple Audio Boost to a Single File or Directory
![Audio Boost](https://molex.cloud/files/an-repo/audio_boost.png)

![Audio Boost Complete](https://molex.cloud/files/an-repo/audio_boost_complete.png)

### Command-Line Arguments

You can use the following arguments when running the tool from the command line:

| Argument                | Description                                                                                       | Example Usage                             |
|-------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------|
| `-n`, `--normalize`      | Path to a file or directory for normalization.                                                    | `python main.py -n /path/to/file`         |
| `--I`                   | (Optional, with `--normalize`) Integrated loudness target in LUFS. Default: `-16`.               | `python main.py -n /path/to/file --I -20` |
| `--TP`                  | (Optional, with `--normalize`) True peak target in dBFS. Default: `-1.5`.                        | `python main.py -n /path/to/file --TP -2` |
| `--LRA`                 | (Optional, with `--normalize`) Loudness range target in LU. Default: `11`.                       | `python main.py -n /path/to/file --LRA 10` |
| `-b`, `--boost`          | Path to a file or directory and boost percentage (e.g., 10 for +10%, -10 for -10%).              | `python main.py -b /path/to/file 10` or `python main.py -b /path/to/dir 5` |

#### Notes:
- The `--I`, `--TP`, and `--LRA` arguments are optional and can only be used with `--normalize`.
- If no values are provided for `--I`, `--TP`, or `--LRA`, the tool will use the default normalization parameters specified in `values.py`.
- The `--boost` argument now supports both files and directories. When a directory is provided, all supported files inside will be boosted by the given percentage, with live progress and per-file status.
 - The `--boost` argument now supports both files and directories. When a directory is provided, all supported files inside will be boosted by the given percentage, with live progress and per-file status.
 - `--dry-run`: Build and show FFmpeg commands without executing them. Useful for debugging commands before running.
 - `--workers`: Set maximum parallel worker threads for batch processing. Defaults to auto-detected CPU count.

### Examples

#### Normalize a Single File with Default Parameters:
```bash
python main.py -n /path/to/file.mkv
```

#### Normalize a Directory with Custom Parameters:
```bash
python main.py -n /path/to/directory --I -18 --TP -2 --LRA 9
```

#### Apply Audio Boost to a File:
```bash
python main.py -b /path/to/file.mkv 10
```

#### Apply Audio Boost to All Files in a Directory:
```bash
python main.py -b /path/to/directory 5
```

## How It Works

1. **Normalization**: The tool analyzes the audio track of the specified media file(s) to determine the current loudness levels. It then calculates the necessary adjustments to bring the audio to the target levels defined by the user (or defaults). The tool uses FFmpeg to apply these adjustments and create a new normalized audio track.
2. **Audio Boost**: The tool can also apply a simple audio boost by increasing the volume of the audio track by a specified percentage. This is useful for making quiet audio tracks louder without performing full normalization.
3. **Parallel Processing**: The tool supports parallel processing, allowing multiple files to be processed simultaneously. This significantly speeds up the normalization and boosting process when dealing with large batches of files.
