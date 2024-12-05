# Audio Normalization

![GitHub repo size](https://img.shields.io/github/repo-size/tonywied17/audio-normalization?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/top/tonywied17/audio-normalization?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/tonywied17/audio-normalization?style=for-the-badge)

This project allows you to normalize or boost the audio tracks of media files. Many movie soundtracks, particularly surround sound mixes, often have inconsistencies in volume levels. This tool helps to address that by normalizing or boosting the audio to make it more balanced and clear.

## Features

- **Normalize Audio Track for a Media File**
- **Normalize Audio Tracks for All Media Files in a Directory**
- **Apply Simple Audio Boost to a Media File**

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

## Usage

### Launch the Interactive CLI

Run the following command to start the interactive command-line interface (CLI):

```bash
python main.py
```

The application will present a menu with the following options:

1. **Normalize Audio Track for a Media File**  
   Prompts for the path to a media file and normalizes its audio.

2. **Normalize Audio Tracks for All Media Files in a Directory**  
   Prompts for a directory path and processes all media files in that directory.

3. **Apply Simple Audio Boost to a Media File**  
   Prompts for the path to a media file and applies a simple audio boost.

4. **Exit**  
   Exit the program.

### Example Flow

After running `python main.py`, you will see a menu. Here's an example interaction:

```
Option  Description
------  ------------------------------------------------------------
1       Normalize Audio Track for a Media File
2       Normalize Audio Tracks for All Media Files in a Directory
3       Apply Simple Audio Boost to Media File
4       Exit

Enter your choice: 1
Enter the path to the media file (e.g., E:\Movies\media.mkv): E:\Movies\my_media.mkv
Processing media for Normalization...
```

## Alternative Installation Method (Using Scoop)

For an easier installation with automatic environment variable setup, you can use [Scoop](https://scoop.sh/). For detailed instructions, see the [Scoop Installation Guide](scoop_installation_guide.md).

## How It Works

1. **Normalization**: This tool uses FFmpeg to normalize the audio tracks of the media files. It adjusts the volume levels of the audio to bring them to a standard level without clipping.
2. **Audio Boost**: The tool applies a simple boost to the audio, increasing the volume by the specified percentage.
3. **Parallel Processing**: The tool supports parallel processing, which speeds up the task when processing multiple files.

## Development

If you want to contribute or modify the code, clone the repository and install the dependencies as described above. You can also add new features or improvements as needed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.