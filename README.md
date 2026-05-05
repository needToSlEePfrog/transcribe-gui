[transcribe_README_EN.md](https://github.com/user-attachments/files/27385745/transcribe_README_EN.md)
# Transcribe GUI

A local audio/video-to-text transcription tool with a graphical interface, powered by the [Groq](https://groq.com/) Whisper API and ffmpeg. Handles large files automatically by splitting them into chunks.

[中文说明](README_CN.md)

## Features

- **Multi-format support** — mp3, mp4, wav, m4a, mkv, webm, avi, mov, flac, ogg, and more
- **Auto chunking** — Files over 20MB are automatically split and transcribed segment by segment, bypassing API upload limits
- **Multi-language** — Chinese, English, Japanese, Korean, French, German, Spanish, or auto-detect
- **Persistent settings** — API key, output directory, and language preference saved locally across sessions
- **Real-time logging** — Live progress updates for tracking long transcriptions
- **Local processing** — Audio extraction happens locally; only the transcription request is sent to Groq

## Prerequisites

1. **Python 3.7+**
2. **Groq API Key** — Get one for free at [console.groq.com/keys](https://console.groq.com/keys)
3. **ffmpeg** — Must be in your system PATH
4. Install dependencies:

```bash
pip install groq
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/transcribe-gui.git
cd transcribe-gui

# Install dependencies
pip install groq

# Run
python transcribe_gui.py
```

## Usage

1. Launch the app and enter your Groq API Key (click "Save Settings" after the first time)
2. Select an audio or video file
3. Choose a language (or leave on auto-detect)
4. Click **Start Transcription**
5. The transcript is saved as a `.txt` file in the output directory

## How It Works

```
Input file → ffmpeg extracts audio (16kHz mono mp3)
           → Check size; auto-split if over 20MB
           → Transcribe each chunk via Groq Whisper API
           → Merge results and save as .txt
```

## Project Structure

```
transcribe-gui/
├── transcribe_gui.py    # Main application (single file)
├── README_CN.md            # 中文说明
├── README.md         # This file
└── LICENSE              # MIT License
```

## License

[MIT License](LICENSE)

## Acknowledgements

- [Groq](https://groq.com/) — High-speed Whisper inference API
- [OpenAI Whisper](https://github.com/openai/whisper) — Speech recognition model
