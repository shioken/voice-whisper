# voice_whisper

A simple local transcription tool for `.m4a` audio files, built with Python. It uses `faster-whisper` backed by CTranslate2 for fast inference, especially on Apple Silicon (M1/M2/M3/M4).

Japanese README is available in `README.md`.

## Setup

Prerequisites:

- Python 3.13 recommended (currently verified)
- `ffmpeg` available on PATH (for audio decoding)
- Internet connection for the first model download (subsequent runs use the local cache)

Installation:

```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Install ffmpeg (macOS/Homebrew):

```
brew install ffmpeg
```

## Usage

Single file:

```
./transcribe.py input.m4a
```

Process all `.m4a` files in a directory and save SRT/VTT/TXT/JSON to `transcripts/`:

```
./transcribe.py ./data --device metal --model small
```

Key options:

- `--model`: `tiny`/`base`/`small`/`medium`/`large-v2` or local CTranslate2 path (default: `small`)
- `--device`: `auto`/`cpu`/`cuda`/`metal` (Apple Silicon recommends `metal`)
- `--compute-type`: precision/quantization. Defaults to `float16` for Metal, otherwise `int8_float16` for speed/quality balance
- `--language`: language code (auto-detected if omitted)
- `--task`: `transcribe` (ASR) or `translate` (to English)
- `--format`: `txt`/`srt`/`vtt`/`json`/`all` (default: `all`)
- `--no-vad`: disable VAD (enabled by default)
- `--threads`: number of CPU threads (0 = auto)

Examples:

```
./transcribe.py ./data --device metal --model small --format srt
./transcribe.py meeting.m4a --language ja --format all
./transcribe.py *.m4a --no-vad --beam-size 3
```

Outputs:

- `transcripts/<basename>.txt`: plain text
- `transcripts/<basename>.srt`: subtitles (SRT)
- `transcripts/<basename>.vtt`: subtitles (WebVTT)
- `transcripts/<basename>.json`: segment-level JSON (start/end, avg log prob, etc.)

## Apple Silicon Tips (M1/M2/M3/M4)

- Use `--device metal` (auto-selected on macOS ARM)
- Default `--compute-type` is `float16` on Metal for a good speed/quality trade-off
- Model `small` works well for many cases; use `medium` for higher accuracy

## Troubleshooting

- ImportError for faster-whisper → `pip install -r requirements.txt`
- `ffmpeg` not found → macOS: `brew install ffmpeg`
- First-time model download fails → check network or pre-download an offline CTranslate2 model and pass its local path via `--model`

## License

This repository is distributed under the MIT License. See `LICENSE` for details.

### Third-party Licenses

This tool depends on the following libraries; their respective licenses apply:

- faster-whisper: MIT (uses CTranslate2: MIT)
- rich: MIT
- click: BSD-3-Clause
- tqdm: MPL-2.0

Notes:

- Models specified via `--model` (Whisper/CTranslate2 formats, etc.) follow their own distribution licenses.
- `ffmpeg` must be installed separately; check whether your build is LGPL/GPL depending on distribution.

## Contributing

Issues/PRs are welcome. Please consider:

- Use Conventional Commits (e.g., `feat: add VTT writer`)
- Keep changes focused; include overview, usage examples, and caveats in the PR
- Do not commit large audio files or `transcripts/`

