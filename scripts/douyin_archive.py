#!/usr/bin/env python3
"""Download public Douyin share links and keep a resumable creator archive."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests

SITE = "https://sph.miuistore.com"
UA = "Mozilla/5.0"


def safe_name(value: str, fallback: str = "video") -> str:
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', value).strip(' ._')[:80].rstrip(' .')
    value = value or fallback
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value):
        value = '_' + value
    return value


def share_url(text: str) -> str:
    # Markdown-escaped underscores occur in pasted share messages.
    text = text.replace('\\_', '_')
    for url in re.findall(r'https?://[^\s<>"\[\]]+', text):
        url = url.rstrip(').,，。；;')
        host = (urlparse(url).hostname or '').lower()
        if host in {'v.douyin.com', 'www.douyin.com', 'douyin.com', 'www.iesdouyin.com'}:
            return url
    raise ValueError('没有找到抖音分享链接')


def video_id(text: str) -> str | None:
    match = re.search(r'/(?:video|share/video)/(\d+)', text)
    return match[1] if match else None


def candidates(page: str) -> list[dict]:
    choices = {}
    groups = re.split(r'分辨率\s*(\d+)\s*[x×]\s*(\d+)\s*[：:]', page)
    for n in range(1, len(groups), 3):
        width, height = int(groups[n]), int(groups[n + 1])
        for raw in re.findall(r'href=["\']([^"\']+)', groups[n + 2]):
            url = html.unescape(raw)
            parsed = urlparse(url)
            host = (parsed.hostname or '').lower()
            if parsed.scheme not in {'http', 'https'} or not host.endswith('.douyinvod.com'):
                continue
            query = parse_qs(parsed.query)
            # Observed cs=0/2 are useful candidates, not a codec guarantee.
            if query.get('cs', [''])[0] not in {'0', '2'}:
                continue
            rate = query.get('br', ['0'])[0]
            choices[url] = dict(url=url, width=width, height=height,
                                bitrate=int(rate) if rate.isdigit() else 0)
    ranked = sorted(choices.values(), key=lambda c: (c['width'] * c['height'], c['bitrate']), reverse=True)
    # Try a lower resolution before spending the whole budget on mirror URLs.
    primary, mirrors, seen = [], [], set()
    for choice in ranked:
        key = (choice['width'], choice['height'])
        (mirrors if key in seen else primary).append(choice)
        seen.add(key)
    return primary + mirrors


def resolve(session: requests.Session, text: str, expected_id: str | None = None) -> dict:
    url = share_url(text)
    known_id = video_id(url)
    if expected_id and known_id and expected_id != known_id:
        raise ValueError('输入 ID 与链接不一致')
    known_id = expected_id or known_id
    if not known_id:
        response = session.head(url, allow_redirects=True, timeout=30)
        known_id = next((video_id(r.url) or video_id(r.headers.get('Location', ''))
                         for r in [*response.history, response]
                         if video_id(r.url) or video_id(r.headers.get('Location', ''))), None)
    if not known_id or not re.fullmatch(r'\d+', known_id):
        raise RuntimeError('无法确认视频 ID；请提供抖音完整视频链接或 JSON 中的 id')
    response = session.get(SITE + '/sph/public/dy-check', params={'data': url}, timeout=45)
    response.raise_for_status()
    result = response.json()
    if result.get('error') != 0 or not result.get('url'):
        raise RuntimeError('公开解析服务未返回结果页')
    page_url = urljoin(SITE, result['url'])
    if urlparse(page_url).hostname != 'sph.miuistore.com':
        raise RuntimeError('解析结果页域名变化，请检查服务')
    page = session.get(page_url, timeout=45)
    page.raise_for_status()
    content = page.text
    shell_title = re.search(r'<title>(.*?)</title>', content, re.S | re.I)
    lazy = re.search(r'\$\.get\(\s*["\'](https://apikr\.convry\.com/sph/public/dy-r\?[^"\'\s]+)["\']', content)
    if lazy:
        page = session.get(html.unescape(lazy[1]), timeout=60)
        page.raise_for_status()
        content = page.text
    if not re.search(r'(?<!\d)' + re.escape(known_id) + r'(?!\d)', content):
        raise RuntimeError('结果页视频 ID 不匹配，未下载')
    options = candidates(content)
    if not options:
        raise RuntimeError('结果页未找到兼容候选地址；可能是页面结构变化')
    title = re.search(r'<title>(.*?)</title>', content, re.S | re.I) or shell_title
    author = re.search(r'【(.+?)的作品】', text)
    share_title = re.search(r'【.+?的作品】\s*(.*?)(?:https?://|$)', text, re.S)
    return dict(id=known_id, url=url, title=(share_title[1].strip(' []') if share_title and share_title[1].strip(' []') else html.unescape(title[1]).strip() if title else known_id),
                author=author[1] if author else '未分类', candidates=options)


def public_info(data: dict) -> dict:
    return {**{k: data[k] for k in ('id', 'url', 'title', 'author')},
            'candidates': [{k: c[k] for k in ('width', 'height', 'bitrate')} for c in data['candidates']]}


def probe(path: Path, ffprobe: str) -> dict:
    result = subprocess.run([ffprobe, '-v', 'error', '-show_entries',
                             'format=duration,size:stream=codec_type,codec_name,width,height',
                             '-of', 'json', str(path)], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('媒体容器读取失败')
    data = json.loads(result.stdout)
    videos = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    if not videos or not videos[0].get('codec_name') or float(data['format'].get('duration', 0)) <= 0:
        raise RuntimeError('缺少有效视频流或时长')
    audio = next((s for s in data['streams'] if s.get('codec_type') == 'audio'), {})
    return dict(duration=float(data['format']['duration']), size=path.stat().st_size,
                width=videos[0]['width'], height=videos[0]['height'],
                video_codec=videos[0]['codec_name'], audio_codec=audio.get('codec_name'))


def ffmpeg_run(ffmpeg: str, args: list[str]) -> None:
    result = subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-xerror', *args],
                            capture_output=True, timeout=3600)
    if result.returncode:
        raise RuntimeError('音画解码或转换失败')


def download(session: requests.Session, data: dict, target: Path, ffmpeg: str,
             ffprobe: str, h264: bool = False, max_candidates: int = 3) -> dict:
    if target.exists():
        raise FileExistsError('目标文件已存在，未覆盖')
    target.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    with tempfile.TemporaryDirectory(prefix='.douyin-', dir=target.parent) as tmp:
        raw, ready = Path(tmp) / 'source.mp4', Path(tmp) / 'ready.mp4'
        for candidate in data['candidates'][:max_candidates]:
            try:
                with session.get(candidate['url'], stream=True, timeout=(20, 90)) as response:
                    response.raise_for_status()
                    if 'text/html' in response.headers.get('Content-Type', '').lower():
                        raise RuntimeError('下载地址返回 HTML')
                    with raw.open('wb') as output:
                        for chunk in response.iter_content(1024 * 1024):
                            output.write(chunk)
                metadata = probe(raw, ffprobe)
                ffmpeg_run(ffmpeg, ['-i', str(raw), '-map', '0:v:0', '-map', '0:a:0?', '-f', 'null', '-'])
                if h264 and metadata['video_codec'] != 'h264':
                    ffmpeg_run(ffmpeg, ['-y', '-i', str(raw), '-map', '0:v:0', '-map', '0:a:0?',
                                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
                                       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(ready)])
                    metadata = probe(ready, ffprobe)
                    ffmpeg_run(ffmpeg, ['-i', str(ready), '-map', '0:v:0', '-map', '0:a:0?', '-f', 'null', '-'])
                else:
                    shutil.copyfile(raw, ready)
                # Exclusive creation avoids overwriting an unrelated file, even on retry.
                created = False
                try:
                    with target.open('xb') as output, ready.open('rb') as source:
                        created = True
                        shutil.copyfileobj(source, output)
                except BaseException:
                    if created:
                        target.unlink(missing_ok=True)
                    raise
                return metadata
            except FileExistsError:
                raise
            except (requests.RequestException, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                failures.append(type(exc).__name__)
        raise RuntimeError(f'尝试 {len(failures)} 个候选均失败：' + ', '.join(failures))


def atomic_json(path: Path, data: list[dict]) -> None:
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    tmp.replace(path)


def archive(items: list[dict], root: Path, session: requests.Session, args) -> int:
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / '视频清单.json'
    records = json.loads(manifest.read_text(encoding='utf-8-sig')) if manifest.exists() else []
    failures = 0
    for item in items:
        source = item.get('url') or item.get('text', '')
        row = dict(item)
        try:
            url = share_url(source)
            previous = next((r for r in records if r.get('url') == url or
                             (item.get('id') and r.get('id') == item['id'])), None)
            if previous and previous.get('status') == '已归档并校验' and previous.get('file'):
                local = (root / previous['file']).resolve()
                if not local.is_relative_to(root.resolve()):
                    raise ValueError('清单文件路径越出输出目录')
                if local.is_file() and local.stat().st_size == previous.get('size'):
                    probe(local, args.ffprobe)
                    print('跳过已归档：' + previous.get('title', local.name), flush=True)
                    continue
            data = resolve(session, source, item.get('id'))
            data['author'] = item.get('author') or data['author']
            data['title'] = item.get('title') or data['title']
            row = {k: v for k, v in data.items() if k != 'candidates'}
            target = root / safe_name(data['author']) / (safe_name(data['title']) + '-' + data['id'] + '.mp4')
            row.update(download(session, data, target, args.ffmpeg, args.ffprobe, args.h264, args.max_candidates))
            row.update(file=target.relative_to(root).as_posix(), status='已归档并校验')
            print('完成：' + str(target), flush=True)
        except Exception as exc:
            failures += 1
            row.update(status='待处理', error=re.sub(r'https?://\S+', '[URL omitted]', str(exc))[:200])
            print('待处理：' + row['error'], file=sys.stderr, flush=True)
        # Merge this source only; preserve other videos and their transcript metadata.
        index = next((i for i, r in enumerate(records) if r.get('url') == row.get('url') or
                      (row.get('id') and r.get('id') == row['id'])), None)
        if index is None:
            records.append(row)
        else:
            records[index] = {**records[index], **row}
            if row['status'] == '已归档并校验':
                records[index].pop('error', None)
        atomic_json(manifest, records)
    lines = ['# 抖音视频素材索引', '']
    for row in records:
        title = row.get('title') or row.get('url', '未知视频')
        label = title.replace('[', '（').replace(']', '）').replace('\n', ' ')
        link = f'[{label}]({quote(row["file"])})' if row.get('file') else label
        lines.append(f'- {row.get("author", "未分类")}：{link} — {row.get("status", "待处理")}')
    (root / '素材索引.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='抖音公开分享链接下载、按博主归档与校验')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--share', help='单条分享文本或链接')
    source.add_argument('--input', type=Path, help='JSON 数组：每项包含 url，可选 author/title/id')
    parser.add_argument('-o', '--output', type=Path, default=Path('example'), help='输出目录')
    parser.add_argument('--info', action='store_true', help='仅解析，不下载媒体，不写归档')
    parser.add_argument('--h264', action='store_true', help='需要兼容剪辑软件时转成 H.264/AAC')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--max-candidates', type=int, choices=range(1, 6), default=3)
    args = parser.parse_args(argv)
    try:
        items = json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else [{'text': args.share}]
        if not isinstance(items, list) or not items or not all(isinstance(i, dict) and (i.get('url') or i.get('text')) for i in items):
            raise ValueError('输入必须是包含 url 或 text 的非空 JSON 对象数组')
        if not args.info and (not shutil.which(args.ffmpeg) or not shutil.which(args.ffprobe)):
            raise RuntimeError('需要 FFmpeg 和 ffprobe；安装后加入 PATH 或用参数指定路径')
        with requests.Session() as session:
            session.headers['User-Agent'] = UA
            if args.info:
                for item in items:
                    print(json.dumps(public_info(resolve(session, item.get('url') or item['text'], item.get('id'))), ensure_ascii=False, indent=2))
                return 0
            return archive(items, args.output.expanduser(), session, args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print('错误：' + re.sub(r'https?://\S+', '[URL omitted]', str(exc))[:250], file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
