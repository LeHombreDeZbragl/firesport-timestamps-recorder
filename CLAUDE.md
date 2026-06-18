# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A toolkit for processing firefighter-sport (Czech *požární sport* / fire attack "útok") competition and training footage. The pipeline is: download a video → record frame-accurate timestamps for each attack via a GUI → cut the video into per-attack segments with title + running-timer overlays → join segments into a final video.

There is no application framework — each tool is a standalone Python script driven by `argparse`, orchestrating **FFmpeg** (and `ffprobe`) subprocesses. FFmpeg does all video work; the Python is glue, validation, and overlay-filter construction.

## The five tools (all at repo root)

| Script | Role |
|--------|------|
| `firetimer-ytdownload.py` | Download YouTube video via `yt-dlp`, optionally in time chunks |
| `video_timestamp_recorder.py` | PyQt5 + python-vlc GUI to scrub footage and emit a timestamps file |
| `firetimer-cutvid.py` | Cut by timestamps, draw title + timer overlays per segment, then auto-join (the core/largest tool) |
| `firetimer-joinvids.py` | Concat-join a folder of clips, normalizing codec/resolution mismatches first |
| `add-timer.py` | Add a standalone running-timer overlay to one video |

`firetimer-cutvid.py` calls `firetimer-joinvids.py` to produce its final output, so changes to the joiner affect the cut pipeline too.

## Commands

Everything runs through the project venv. Three equivalent front-ends exist: the `Makefile` (Linux/macOS), `run.bat` (Windows), and direct `python3` invocation. The Makefile uses `venv/bin/python3` explicitly.

```bash
make setup                                   # create venv + install CLI deps
make gui                                      # launch the timestamp recorder
make cut SOURCE=video.mp4 TIMES=timestamps.txt [SORT=1]   # SORT=1 → -z (sort + placement labels)
make join FOLDER=path/to/parts [OUTPUT=final.mp4]
make timer SOURCE=video.mp4 [START=HH:MM:SS.mmm] [END=... | END_REL=...]
make download URL='...' NAME=myvideo [FOLDER=...] [CHUNK=10]
```

`make cut TIMES=` accepts multiple space-separated files; the underlying scripts also accept comma-delimited (`-t a.txt,b.txt`). Pass `--help` to any script for full options.

### Testing

There is **no unit-test suite**. The only test harness is `make testcut`, an integration smoke test that cleans `extraliga-netin/out-parts`, runs `cut -z` against the checked-in `extraliga-netin/extraliga-netin.mp4` + `timestamps.txt` sample, and opens the result in `ffplay`. Use it to verify changes to the cut/overlay/join pipeline end-to-end.

## Dependencies

- **System (not pip):** FFmpeg + ffprobe are required by every tool; VLC is required only by the GUI. Each script calls `check_deps()` at startup to fail fast if these are missing.
- **Python:** `requirements.txt` = CLI only (`yt-dlp`). `requirements_gui.txt` = CLI + `PyQt5` + `python-vlc`. Target Python is 3.13 (`.python-version`); 3.8+ supported.

## The timestamps file format (the contract between GUI and cutter)

This is the central data structure tying the tools together. The recorder writes it; the cutter parses it. Each non-empty, non-`#` line has **12 semicolon-separated fields**:

```
title;začátek;start;koš;voda;kohout;rozdělovač;výstřik_LP;výstřik_PP;LP;PP;konec
```

The Czech field names are fire-attack split points (suction basket, water, valve, divider, left/right spray start, left/right target hit). Field 2 `začátek` and field 12 `konec` bound the cut; the middle fields drive the per-split timer/label overlays. `parse_timestamps_file()` in `firetimer-cutvid.py` strictly requires exactly 12 fields and silently skips malformed lines, so format changes must stay in sync across `video_timestamp_recorder.py` (writer) and `firetimer-cutvid.py` (reader/validator).

## Conventions worth knowing

- **Overlay text** is built as FFmpeg `drawtext` filter strings. Czech diacritics require a real TTF; `find_system_font()` locates one per-OS and text is escaped via `ff_escape_text` / `ff_escape_fontfile`. Font/escaping bugs surface as filter-syntax errors from FFmpeg.
- **Folder convention:** input chunks land in `in-parts/`, processed segments in `out-parts/`; the joined video is written one directory above the parts folder. Cut output goes to an `out-parts/` next to the source video.
- Sample/working data lives in `extraliga/`, `treninky/`, `zl26/`, `extraliga-netin/` (the test fixture). Generated `.mp4` and `.MTS` files are gitignored.
- The `-z` / `SORT=1` flag both sorts segments by final time (max of LP/PP) and adds placement labels (`1.místo`, `2.místo`, …).
</content>
</invoke>
