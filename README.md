
# Audio Normalization

![GitHub repo size](https://img.shields.io/github/repo-size/tonywied17/audio-normalization?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/top/tonywied17/audio-normalization?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/tonywied17/audio-normalization?style=for-the-badge)

This project is a simple command-line tool for normalizing audio tracks in media files. It uses FFmpeg to process audio files and provides options to normalize the audio track for a single media file, normalize audio tracks for all media files in a directory, and apply a simple audio boost to a media file.
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

### Command-Line Arguments

You can use the following arguments when running the tool from the command line:

| Argument                | Description                                                                                       | Example Usage                             |
|-------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------|
| `-n`, `--normalize`      | Path to a file or directory for normalization.                                                    | `python main.py -n /path/to/file`         |
| `--I`                   | (Optional, with `--normalize`) Integrated loudness target in LUFS. Default: `-16`.               | `python main.py -n /path/to/file --I -20` |
| `--TP`                  | (Optional, with `--normalize`) True peak target in dBFS. Default: `-1.5`.                        | `python main.py -n /path/to/file --TP -2` |
| `--LRA`                 | (Optional, with `--normalize`) Loudness range target in LU. Default: `11`.                       | `python main.py -n /path/to/file --LRA 10` |
| `-b`, `--boost`          | Path to a file and boost percentage (e.g., +6 for 6% increase, or -6 for 6% decrease).           | `python main.py -b /path/to/file 6`       |

#### Notes:
- The `--I`, `--TP`, and `--LRA` arguments are optional and can only be used with `--normalize`.
- If no values are provided for `--I`, `--TP`, or `--LRA`, the tool will use the default normalization parameters specified in `values.py`.

### Examples

#### Normalize a Single File with Default Parameters:
```bash
python main.py -n /path/to/file
```

#### Normalize a Directory with Custom Parameters:
```bash
python main.py -n /path/to/directory --I -18 --TP -2 --LRA 9
```

#### Apply Audio Boost to a File:
```bash
python main.py -b /path/to/file 10
```

### Normalization Parameters

In the file `util/values.py`, you can adjust the following parameters manually (if desired):

| Parameter               | Description                                                                   | Default Value |
|-------------------------|-------------------------------------------------------------------------------|---------------|
| Integrated Loudness (I) | The target integrated loudness level in LUFS (Loudness Units Full Scale).     | `-16 LUFS`    |
| True Peak (TP)          | The target true peak level in dBFS (decibels relative to full scale).         | `-1.5 dBFS`   |
| Loudness Range (LRA)    | The target loudness range in LU (Loudness Units).                            | `11 LU`       |

For a more detailed explanation of these parameters, refer to the [EBU R 128 Loudness Standard](r128.pdf).

### Launching the Interactive CLI Menu

Run the following command to start the interactive command-line interface (CLI):

```bash
python main.py
```

#### Main Menu
![Menu](https://molex.cloud/files/an-repo/menu.png)

#### Normalizing an Audio Track for a Media File
![Normalize File](https://molex.cloud/files/an-repo/normalize_file.png)
![Normalize File Complete](https://molex.cloud/files/an-repo/normalize_file_complete.png)

#### Normalizing Audio Tracks for All Media Files in a Directory
![Normalize Directory](https://molex.cloud/files/an-repo/normalize_directory.png)
![Normalize Directory Table](https://molex.cloud/files/an-repo/normalize_directory_table.png)

#### Applying a Simple Audio Boost to a Media File
![Audio Boost](https://molex.cloud/files/an-repo/audio_boost.png)


## How It Works

1. **Normalization**: The tool normalizes the audio track of a media file by calculating the average volume level and adjusting the audio to a target level. This helps to balance the audio and make it more consistent across different tracks.
2. **Audio Boost**: The tool can also apply a simple audio boost to increase (or decrease) the volume level of a media file. This is useful when the audio is too low and needs to be amplified.
3. **Parallel Processing**: The tool uses parallel processing to speed up the normalization process for multiple files. This allows it to process multiple files simultaneously, making the normalization faster and more efficient.

## Development

If you want to contribute or modify the code, clone the repository and install the dependencies as described above. You can also add new features or improvements as needed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
