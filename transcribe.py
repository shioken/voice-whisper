#!/usr/bin/env python3
import sys
import os
import json
import math
import time
import platform
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Callable

import click
from rich.console import Console
from tqdm import tqdm


console = Console()


def _format_timestamp(seconds: float, srt: bool = True) -> str:
    if math.isnan(seconds) or math.isinf(seconds):
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    else:
        # WebVTT uses '.' for milliseconds
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _write_txt(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_srt(path: Path, segments: List[dict]) -> None:
    lines: List[str] = []
    for i, seg in enumerate(segments, start=1):
        start = _format_timestamp(seg["start"], srt=True)
        end = _format_timestamp(seg["end"], srt=True)
        text = seg["text"].strip()
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_vtt(path: Path, segments: List[dict]) -> None:
    lines: List[str] = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp(seg["start"], srt=False)
        end = _format_timestamp(seg["end"], srt=False)
        text = seg["text"].strip()
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, segments: List[dict], info: dict) -> None:
    out = {"language": info.get("language"), "duration": info.get("duration"), "segments": segments}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_device() -> str:
    # Favor Apple Silicon Metal when available
    if platform.system() == "Darwin" and platform.machine().startswith("arm"):
        return "metal"
    return "auto"


def _default_compute_type(device: str) -> str:
    # Good defaults: Metal -> float16, else int8_float16 (CPU) for speed vs accuracy
    if device in ("metal", "cuda"):
        return "float16"
    # CPU/auto: int8_float32 is widely supported; int8_float16 may fail
    return "int8_float32"


def _collect_audio_files(paths: List[Path]) -> List[Path]:
    results: List[Path] = []
    exts = {".m4a"}
    for p in paths:
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in exts:
                    results.append(f)
        elif p.is_file() and p.suffix.lower() in exts:
            results.append(p)
        else:
            # allow simple glob patterns
            for f in p.parent.glob(p.name):
                if f.is_file() and f.suffix.lower() in exts:
                    results.append(f)
    # Deduplicate and keep stable order
    seen = set()
    unique: List[Path] = []
    for f in results:
        if f not in seen:
            unique.append(f)
            seen.add(f)
    return unique


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("inputs", nargs=-1, type=click.Path(path_type=Path))
@click.option("--out-dir", type=click.Path(path_type=Path), default=Path("transcripts"), show_default=True, help="Directory to write outputs")
@click.option("--model", "model_name", default="small", show_default=True, help="Model size or local path (tiny/base/small/medium/large-v2)")
@click.option("--device", default=_default_device(), show_default=True, type=click.Choice(["auto", "cpu", "cuda", "metal"]))
@click.option("--compute-type", default=None, help="Compute type override (int8,int8_float16,float16,float32)")
@click.option("--language", default=None, help="Spoken language (auto-detect if omitted)")
@click.option("--task", default="transcribe", show_default=True, type=click.Choice(["transcribe", "translate"]))
@click.option("--beam-size", default=5, show_default=True, help="Beam size for decoding")
@click.option("--vad", "vad_filter", is_flag=True, default=True, show_default=True, help="Enable VAD to reduce hallucinations")
@click.option("--no-vad", "vad_filter", flag_value=False, help="Disable VAD")
@click.option("--threads", default=0, show_default=True, help="Threads (0 = auto)")
@click.option("--format", "out_format", default="all", show_default=True, type=click.Choice(["txt", "srt", "vtt", "json", "all"]))
@click.option("--overwrite/--no-overwrite", default=True, show_default=True, help="Overwrite existing outputs")
def main(
    inputs: Tuple[Path, ...],
    out_dir: Path,
    model_name: str,
    device: str,
    compute_type: Optional[str],
    language: Optional[str],
    task: str,
    beam_size: int,
    vad_filter: bool,
    threads: int,
    out_format: str,
    overwrite: bool,
):
    """Transcribe .m4a files locally using faster-whisper.

    Examples:
      ./transcribe.py audio.m4a
      ./transcribe.py ./data --model small --device metal --format srt
    """

    if not inputs:
        console.print("[bold red]No inputs provided. Pass files, dirs, or globs.[/]")
        sys.exit(1)

    files = _collect_audio_files(list(inputs))
    if not files:
        console.print("[bold yellow]No .m4a files found in given inputs.[/]")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        console.print("[bold red]faster-whisper not installed. Run: pip install -r requirements.txt[/]")
        console.print(str(e))
        sys.exit(1)

    user_set_compute = compute_type is not None
    if compute_type is None:
        compute_type = _default_compute_type(device)

    console.print(
        f"[bold]Loading model[/]: {model_name} (device={device}, compute_type={compute_type})"
    )

    load_kw = dict(device=device, compute_type=compute_type)
    if threads and threads > 0:
        load_kw["cpu_threads"] = threads

    t0 = time.time()
    def _try_load_with_compute_types(first_error: Optional[Exception] = None):
        nonlocal compute_type
        attempts = []
        if user_set_compute:
            attempts = [compute_type]
        else:
            # Choose robust fallbacks for current device/backend
            base_default = _default_compute_type(load_kw.get("device", device))
            attempts = [base_default, "int8_float32", "float32"]
        last_exc: Optional[Exception] = first_error
        for ct in attempts:
            load_kw["compute_type"] = ct
            try:
                return WhisperModel(model_name, **load_kw), ct
            except Exception as e:
                last_exc = e
                continue
        raise last_exc  # type: ignore[misc]

    try:
        model = WhisperModel(model_name, **load_kw)
    except Exception as e:
        msg = str(e).lower()
        if device == "metal" and ("unsupported device" in msg or "metal" in msg or "mps" in msg):
            console.print("[yellow]metal が未対応のようです。CPU/auto にフォールバックします。[/]")
            device = "auto"
            load_kw["device"] = device
            try:
                model, compute_type = _try_load_with_compute_types(e)
            except Exception as e2:
                console.print("[bold red]Failed to load model after fallback.[/]")
                console.print(str(e2))
                sys.exit(1)
        elif "int8_float16" in msg:
            if not user_set_compute:
                console.print("[yellow]int8_float16 が未対応のため compute type を切替えます（int8_float32→float32）。[/]")
                try:
                    model, compute_type = _try_load_with_compute_types(e)
                except Exception as e2:
                    console.print("[bold red]Failed to load model.[/]")
                    console.print(str(e2))
                    sys.exit(1)
            else:
                console.print("[bold red]指定された compute type が未対応です。[/] 別の compute type をお試しください（例: --compute-type int8_float32 もしくは float32）。")
                console.print(str(e))
                sys.exit(1)
        else:
            console.print("[bold red]Failed to load model.[/] Make sure the model is available locally or you have internet for first run.")
            console.print(str(e))
            sys.exit(1)

    console.print(f"Model loaded in {time.time()-t0:.2f}s. Processing {len(files)} file(s)...")

    files_pbar = tqdm(files, desc="Files", unit="file")
    for audio_path in files_pbar:
        # Create per-file progress bar on first progress tick
        file_pbar: Optional[tqdm] = None
        last_completed: float = 0.0

        def on_progress(current: float, total: float) -> None:
            nonlocal file_pbar, last_completed
            if not (isinstance(total, (int, float)) and math.isfinite(total) and total > 0):
                return
            if file_pbar is None:
                file_pbar = tqdm(total=float(total), desc=audio_path.name, unit="s", leave=False)
            # Ensure monotonic progress and update by delta
            current = max(float(current), last_completed)
            delta = current - last_completed
            if delta > 0:
                file_pbar.update(delta)
                last_completed = current

        try:
            segments, info = _transcribe_one(
                model,
                audio_path,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
                on_progress=on_progress,
            )
        except Exception as e:
            console.print(f"[bold red]Error processing {audio_path}:[/] {e}")
            if file_pbar is not None:
                file_pbar.close()
            continue

            # Write outputs
            stem = audio_path.stem
            written = []
            try:
                if out_format in ("txt", "all"):
                    p = out_dir / f"{stem}.txt"
                    if overwrite or not p.exists():
                        _write_txt(p, " ".join(seg["text"].strip() for seg in segments))
                        written.append(p.name)
                if out_format in ("srt", "all"):
                    p = out_dir / f"{stem}.srt"
                    if overwrite or not p.exists():
                        _write_srt(p, segments)
                        written.append(p.name)
                if out_format in ("vtt", "all"):
                    p = out_dir / f"{stem}.vtt"
                    if overwrite or not p.exists():
                        _write_vtt(p, segments)
                        written.append(p.name)
                if out_format in ("json", "all"):
                    p = out_dir / f"{stem}.json"
                    if overwrite or not p.exists():
                        _write_json(p, segments, info)
                        written.append(p.name)
            except Exception as e:
                console.print(f"[bold red]Failed writing outputs for {audio_path}:[/] {e}")

            if file_pbar is not None:
                # Ensure the bar reaches 100% for this file
                if file_pbar.total is not None and file_pbar.n < file_pbar.total:
                    file_pbar.update(file_pbar.total - file_pbar.n)
                file_pbar.close()

            if written:
                console.print(f"[green]Done[/] {audio_path.name} -> {', '.join(written)}")
            else:
                console.print(f"[yellow]Skipped[/] {audio_path.name} (already exists, use --overwrite)")


def _transcribe_one(
    model,
    audio_path: Path,
    *,
    language: Optional[str],
    task: str,
    beam_size: int,
    vad_filter: bool,
    on_progress: Optional[Callable[[float, float], None]] = None,
):
    # Using default VAD parameters generally improves results on real-world audio
    vad_params = {"min_silence_duration_ms": 500}
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters=vad_params if vad_filter else None,
        word_timestamps=False,
    )

    segments: List[dict] = []
    total_duration = getattr(info, "duration", None)
    for seg in segments_iter:
        segments.append(
            {
                "id": seg.id,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "avg_logprob": getattr(seg, "avg_logprob", None),
                "no_speech_prob": getattr(seg, "no_speech_prob", None),
                "temperature": getattr(seg, "temperature", None),
            }
        )
        if on_progress is not None and total_duration is not None and math.isfinite(total_duration):
            try:
                on_progress(seg.end, float(total_duration))
            except Exception:
                pass

    info_dict = {"language": getattr(info, "language", None), "duration": getattr(info, "duration", None)}
    return segments, info_dict


if __name__ == "__main__":
    main()
