---
name: video-link-downloader
description: Download or inspect authorized videos from WeChat Channels (视频号) and Douyin share links with a unified local CLI. Use when the user asks to download, parse, inspect, or batch-save a 视频号/微信视频号/抖音 video link or share text, or asks for a command-line downloader for those platforms.
---

# Video Link Downloader

Use `scripts/video_dl.py` as the deterministic entrypoint. Download only media the user owns or is authorized to save.

## Run

Check dependencies before the first use:

```bash
python3 -c 'import playwright, requests'
command -v yt-dlp
```

Run the requested operation:

```bash
python3 scripts/video_dl.py 'SHARE_LINK_OR_TEXT'
python3 scripts/video_dl.py 'SHARE_LINK_OR_TEXT' -o ~/Downloads
python3 scripts/video_dl.py 'SHARE_LINK_OR_TEXT' --info
```

Interpret `-o` as a file path when it has a suffix and as a directory otherwise. Prefer `--info` when the user asks only to identify or inspect a video.

## Workflow

1. Confirm that the input identifies a 视频号 or 抖音 share URL/text.
2. Run `--info` first when metadata, platform support, or authorization is uncertain.
3. Download to the user-specified path; otherwise use the current directory.
4. Verify the output exists and is non-empty. When `ffprobe` is installed, verify container, duration, video codec, dimensions, and audio codec.
5. Report the resolved title, destination, size, and verification result. Do not call a successful parse a successful download.

## Dependencies and recovery

- Require Python 3, `requests`, Playwright for Python, and Google Chrome.
- Require `yt-dlp` for Douyin. Install missing Python dependencies only when authorized by the user or existing environment policy.
- The 视频号 path uses the public parsing flow exposed by `sph.miuistore.com`; website changes can require script maintenance.
- If parsing succeeds but download fails, do not expose signed media URLs or large decryption payloads in chat. Report the concise error and retry once only when the failure is plausibly transient.
- Never upload, publish, log in, spend credits, bypass access controls, or process private media without explicit authorization.
