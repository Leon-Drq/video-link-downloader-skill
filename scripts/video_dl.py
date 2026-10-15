#!/usr/bin/env python3
"""Unified CLI downloader for WeChat Channels and Douyin share links.

Use only for media you own or are authorized to download.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests


SITE = "https://sph.miuistore.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/138 Safari/537.36"


def platform_for(text: str) -> str:
    value = text.lower()
    if "weixin.qq.com/sph/" in value or "channels.weixin.qq.com/" in value:
        return "weixin"
    if any(x in value for x in ("douyin.com", "iesdouyin.com")):
        return "douyin"
    raise ValueError("无法识别链接：目前支持视频号和抖音分享链接")


def safe_name(value: str, fallback: str = "video") -> str:
    value = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", value).strip(" ._")
    return value[:120] or fallback


def choose_path(out: str | None, title: str, suffix: str = ".mp4") -> Path:
    if out:
        target = Path(out).expanduser()
        if target.exists() and target.is_dir():
            target = target / f"{safe_name(title)}{suffix}"
        elif not target.suffix:
            target.mkdir(parents=True, exist_ok=True)
            target = target / f"{safe_name(title)}{suffix}"
    else:
        target = Path.cwd() / f"{safe_name(title)}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def browser() -> tuple:
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    instance = pw.chromium.launch(channel="chrome", headless=True)
    page = instance.new_page(user_agent=UA)
    page.add_init_script("Object.defineProperty(window, 'showSaveFilePicker', {value: undefined})")
    return pw, instance, page


def resolve_weixin(link: str) -> dict:
    pw, instance, page = browser()
    try:
        page.goto(SITE + "/", wait_until="domcontentloaded", timeout=60_000)
        page.locator("input.search-input").fill(link)
        with page.expect_response(lambda r: "/sph/public/quick?" in r.url, timeout=90_000) as event:
            page.locator("button.btn-go").click(force=True)
        data = event.value.json()
        if data.get("error") != 0:
            raise RuntimeError(data.get("message") or f"解析失败：{data}")
        return data
    finally:
        instance.close()
        pw.stop()


def download_weixin(data: dict, target: Path) -> None:
    media_url = data["url"]
    headers = {"User-Agent": UA, "Referer": SITE + "/"}
    with requests.get(media_url, headers=headers, stream=True, timeout=(20, 120)) as response:
        response.raise_for_status()
        key = base64.b64decode(data.get("_data", ""))
        first = True
        with target.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                if first and key:
                    mutable = bytearray(chunk)
                    limit = min(len(key), len(mutable))
                    for i in range(limit):
                        mutable[i] ^= key[i]
                    chunk = bytes(mutable)
                    first = False
                output.write(chunk)


def download_douyin(text: str, out: str | None, info_only: bool) -> Path | None:
    # Sibling module import also works when this file is loaded through importlib.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import douyin_archive as dy

    with requests.Session() as session:
        session.headers['User-Agent'] = UA
        data = dy.resolve(session, text)
        print(json.dumps(dy.public_info(data), ensure_ascii=False, indent=2))
        if info_only:
            return None
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            raise RuntimeError('抖音下载需要 FFmpeg 和 ffprobe；可通过 douyin_archive.py 指定路径')
        target = choose_path(out, dy.safe_name(data['title']) + '-' + data['id'])
        metadata = dy.download(session, data, target, 'ffmpeg', 'ffprobe')
        print(json.dumps(metadata, ensure_ascii=False))
        print(f'已下载并校验：{target.resolve()}')
        return target


def main() -> int:
    parser = argparse.ArgumentParser(prog="video-dl", description="视频号/抖音统一下载命令")
    parser.add_argument("link", help="视频号或抖音分享链接/分享文本")
    parser.add_argument("-o", "--output", help="输出文件或目录，默认当前目录")
    parser.add_argument("--info", action="store_true", help="只解析并显示信息，不下载")
    args = parser.parse_args()
    try:
        platform = platform_for(args.link)
        if platform == "douyin":
            download_douyin(args.link, args.output, args.info)
            return 0
        data = resolve_weixin(args.link)
        media = data.get("media", {})
        public = {
            "platform": "weixin",
            "title": media.get("title"),
            "short_title": media.get("short_title"),
            "file_size": media.get("file_size"),
            "is_live": media.get("is_live"),
        }
        print(json.dumps(public, ensure_ascii=False, indent=2))
        if args.info:
            return 0
        target = choose_path(args.output, media.get("title") or "weixin-video")
        download_weixin(data, target)
        print(f"已下载：{target.resolve()}")
        return 0
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
