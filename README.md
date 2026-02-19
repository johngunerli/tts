# 📦 Text-to-Speech

A private, offline desktop app that converts `.txt` files into spoken audio using [Piper TTS](https://github.com/rhasspy/piper) — a fast, neural text-to-speech engine. No internet connection required. No data ever leaves your machine.

---

## Features

- 🎙️ **Neural voice quality** via Piper TTS (ONNX models)
- 🔒 **Fully offline** — no API keys, no cloud, no tracking
- 🎚️ **Adjustable speaking speed** (0.5× – 2.0×)
- ▶️ **Live preview** before saving
- 💾 **Export to MP3**
- 🖥️ Native desktop app (macOS `.app` / Windows `.exe`)

---

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- Python 3.9+ (managed automatically by uv)
- A Piper voice model (see below)

---

## Voice Model Setup

Models live in `audio-model/<lang_code>/`. The app automatically picks up any `.onnx` file it finds there.

**Download the English model:**

```bash
mkdir -p audio-model/en_US
cd audio-model/en_US

# Download model + config
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
```

> Browse all available voices at [huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).
>
> To add another language, create `audio-model/<lang_code>/` and drop the `.onnx` + `.onnx.json` files inside. The app will find them automatically.

---

## Run from Source

```bash
# Install dependencies
uv sync

# Launch the app
uv run python main.py
```

---

## Build a Native App

> ⚠️ PyInstaller builds for the OS it runs on. Run on a Mac to get a `.app`; run on Windows to get a `.exe`. Cross-compilation is not supported.

```bash
chmod +x build_app.sh
./build_app.sh
```

| Platform | Output                                                                      |
| -------- | --------------------------------------------------------------------------- |
| macOS    | `dist/Text-to-Speech.app` — drag to `/Applications`                        |
| Windows  | `dist/Text-to-Speech/Text-to-Speech.exe` — run directly or zip to distribute |

---

## Project Structure

```text
tts/
├── main.py               # App source code
├── pyproject.toml        # uv project & dependencies
├── tts_app.spec          # PyInstaller build spec
├── build_app.sh          # One-command build script
└── audio-model/
    └── en_US/
        ├── en_US-amy-medium.onnx
        └── en_US-amy-medium.onnx.json
```

---

## Dependencies

| Package        | Purpose                                          |
| -------------- | ------------------------------------------------ |
| `piper-tts`    | Neural TTS engine                                |
| `onnxruntime`  | ONNX model inference (pulled in by piper)        |
| `pyinstaller`  | Packages the app into a native executable        |

Audio conversion uses OS-native tools — `afconvert` on macOS, `sox` on Linux — so no extra dependencies are needed.

---

## Privacy

All processing happens locally on your machine. No text, audio, or usage data is ever sent anywhere.
