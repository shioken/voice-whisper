# voice_whisper

English README is available in `README.en.md`.

ローカルで `.m4a` を文字起こしするシンプルな Python ツールです。Apple Silicon (M1/M2/M3/M4) で高速に動作するよう、`faster-whisper` + CTranslate2 を利用します。

## セットアップ

前提:

- Python 3.13 推奨（現在の環境で動作確認）
- ffmpeg が必要（音声読み込みのため）
- 初回モデルダウンロードにインターネット接続が必要（以降はローカルキャッシュ利用）

インストール:

```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

ffmpeg（macOS/Homebrew）:

```
brew install ffmpeg
```

## 使い方

単一ファイル:

```
./transcribe.py input.m4a
```

ディレクトリ内の全 `.m4a` を処理し、SRT/VTT/TXT/JSON を `transcripts/` に保存:

```
./transcribe.py ./data --device metal --model small
```

主なオプション:

- `--model`: `tiny`/`base`/`small`/`medium`/`large-v2` またはローカルモデルパス（既定: `small`）
- `--device`: `auto`/`cpu`/`cuda`/`metal`（Apple Silicon は `metal` 推奨）
- `--compute-type`: 量子化/精度（既定: `metal` の場合 `float16`、それ以外は `int8_float16`）
- `--language`: 言語（省略で自動判定）
- `--task`: `transcribe`（書き起こし） or `translate`（英訳）
- `--format`: `txt`/`srt`/`vtt`/`json`/`all`（既定: `all`）
- `--no-vad`: VAD 無効化（既定は有効）
- `--threads`: CPU スレッド数（0で自動）

例:

```
./transcribe.py ./data --device metal --model small --format srt
./transcribe.py meeting.m4a --language ja --format all
./transcribe.py *.m4a --no-vad --beam-size 3
```

出力:

- `transcripts/<元ファイル名>.txt`: プレーンテキスト
- `transcripts/<元ファイル名>.srt`: 字幕 (SRT)
- `transcripts/<元ファイル名>.vtt`: 字幕 (WebVTT)
- `transcripts/<元ファイル名>.json`: セグメント情報を含む JSON（開始/終了時刻、平均対数尤度など）

## Apple Silicon 最適化（M1/M2/M3/M4）

- `--device metal` を指定（既定でも macOS ARM の場合は `metal` を選択します）
- 既定の `--compute-type` は `float16`（Metal）で高速・高品質のバランスが良いです
- モデルは `small` が多くのケースで実用的（より高精度なら `medium`）

## よくある問題

- ImportError: faster-whisper が見つからない → `pip install -r requirements.txt`
- ffmpeg が見つからない → macOS: `brew install ffmpeg`
- 初回実行でモデルダウンロードに失敗 → ネットワーク接続を確認するか、あらかじめオフライン用にモデルをダウンロードして `--model` にローカルパスを指定してください（CTranslate2 形式）。

## ライセンス

本リポジトリは MIT License の下で配布されています。詳細は `LICENSE` をご参照ください。

### サードパーティライセンス

本ツールは以下のライブラリに依存しており、各ライブラリのライセンスが適用されます。

- faster-whisper: MIT（内部で CTranslate2: MIT を利用）
- rich: MIT
- click: BSD-3-Clause
- tqdm: MPL-2.0

補足:

- モデル（`--model` に指定する Whisper/CTranslate2 形式など）は配布元のライセンスに従います。
- ffmpeg は別途インストールが必要であり、配布形態によって LGPL/GPL 構成の確認が必要です。

## 貢献ガイド

Issue/PR は歓迎です。以下を参考にお願いします。

- コミットメッセージは Conventional Commits を推奨（例: `feat: add VTT writer`）
- 変更は小さく焦点を絞り、概要・使用例・注意点を PR に記載
- 大きな音声ファイルや `transcripts/` はコミットしない
