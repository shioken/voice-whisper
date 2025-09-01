# Contributing Guide

ありがとうございます！このプロジェクトへの貢献を歓迎します。以下のガイドラインに沿って PR / Issue をお願いします。

## 開発環境のセットアップ

1. Python 仮想環境を作成し依存をインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. ffmpeg を導入（例: macOS/Homebrew）:
   ```bash
   brew install ffmpeg
   ```
3. 動作確認:
   ```bash
   python main.py
   ./transcribe.py --help
   ```

## コーディング規約

- PEP8 / 4スペースインデント、可能な範囲で型ヒント
- 命名: 関数/変数 `snake_case`、クラス `CapWords`、定数 `UPPER_CASE`
- CLI は `click` の型付きオプションを使用し、`--help` を明確に
- I/O は `pathlib.Path` を使用、絶対パスのハードコードは避ける
- 推奨ツール: `black` / `ruff` / `isort`（任意・現状未導入）

## テスト

- 既存テストは未整備です。`tests/` 配下に `test_*.py` を作成して `pytest` で実行できます。
  ```bash
  pip install pytest
  pytest -q
  ```
- モデル呼び出しはスタブ化し、小さく再現可能なサンプルで検証してください。

## コミットと PR

- Conventional Commits を推奨（例: `feat: add VTT writer`, `fix: handle empty segments`）
- 変更は小さく焦点を絞り、必要に応じて使用例や出力サンプル、性能/破壊的変更の注意点を記載
- 大きな音声ファイルや `transcripts/` はコミットしない

## Issue

- バグ報告には再現手順、期待/実際の振る舞い、ログ、サンプルを添付してください。
- 機能要望はユースケースを明確にし、互換性/性能への影響を記載してください。

## 行動規範

当プロジェクトは [Contributor Covenant v2.1](./CODE_OF_CONDUCT.md) に従います。

