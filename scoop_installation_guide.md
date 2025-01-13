
# Installation Guide for Scoop Users

This guide will walk you through the installation process for Python and ffmpeg using Scoop on Windows. Scoop simplifies the process of installing and managing software, and it automatically sets up environment variables for easier access.

## Prerequisites
- Windows OS
- Scoop package manager installed

### 1. Install Scoop (if not already installed)
To install Scoop, open PowerShell as Administrator and run the following command:

```powershell
Set-ExecutionPolicy RemoteSigned -scope CurrentUser
iwr -useb get.scoop.sh | iex
```

## Install Python using Scoop
Scoop makes installing Python easy, and it will also set up the necessary environment variables.

1. Open PowerShell or Command Prompt and run:

    ```powershell
    scoop install python
    ```

2. After installation, you can check if Python is successfully installed by running:

    ```bash
    python --version
    ```

    This should output the installed version of Python.

## Install ffmpeg using Scoop
Scoop also makes installing ffmpeg easy, and it automatically adds ffmpeg to your system's `PATH`.

1. To install ffmpeg, run the following command:

    ```powershell
    scoop install ffmpeg
    ```

2. Once installed, you can verify the installation by running:

    ```bash
    ffmpeg -version
    ```

    This should show you the version of `ffmpeg` that was installed.

## Install Dependencies
To run the project, you will also need to install the required Python libraries listed in `requirements.txt`. You can do this by navigating to the project directory and running:

```bash
pip install -r requirements.txt
```