---
name: video-link-downloader
description: 下载或解析抖音、微信视频号公开分享链接。支持抖音批量下载、按博主归档、候选清晰度回退与音画校验；用于用户提供分享链接或文本并要求保存视频的任务。
---

# Video Link Downloader

把分享链接保存成经过校验的本地视频。沿用用户指定的目录；批量归档未指定目录时使用工作区 `example`。仅处理用户有权保存的媒体。

## 抖音：验证过的首选方法

使用 `scripts/douyin_archive.py`，需要 Python 3.10+、`requests`、FFmpeg 和 ffprobe。不需要浏览器、登录 Cookie 或 API Key。分享 URL 会发给第三方公开解析站 `sph.miuistore.com`，结果页可能再从 `apikr.convry.com` 加载内容。

```bash
python -m pip install requests
python scripts/douyin_archive.py --share '完整分享文本或链接' -o example
python scripts/douyin_archive.py --input videos.json -o example
python scripts/douyin_archive.py --share '分享链接' --info
```

`--info` 只解析公开元数据，不下载视频。批量输入是 JSON 数组：

```json
[
  {"url": "https://v.douyin.com/EXAMPLE/", "author": "博主名", "title": "视频标题"}
]
```

从用户的分享文本提取博主和标题填入 JSON；不要猜测作者。纯链接未提供博主时存入 `未分类`。可以提供已核对的 `id`，用于短链跳转无法取得视频 ID 的情况。

输出：`example/博主/标题-ID.mp4`、`视频清单.json`、`素材索引.md`。重复执行同一输入会跳过清单中大小及容器信息通过检查的已归档视频；不会覆盖已有同名文件。清单写入每条任务结果，部分失败时命令退出码为 1，可以修复后重跑。

- 清晰度优先选择高分辨率、高码率；默认最多尝试 3 个候选。`cs=0/2` 只是候选筛选条件，实际编码以 ffprobe 和完整 FFmpeg 解码结果为准。
- 完整解码通过才交付。无音轨视频允许保存，并在清单中标注 `audio_codec: null`；有音轨时同时校验。
- 需要剪辑软件兼容时加 `--h264`，将非 H.264 视频转成 H.264/AAC；默认保留已验证的原始编码。
- Windows 可用 `--ffmpeg "C:/tools/ffmpeg.exe" --ffprobe "C:/tools/ffprobe.exe"` 指定路径；其他系统同样支持绝对路径。
- 解析成功不等于下载成功。结果页 ID 不一致、返回 HTML、无法解码时不要交付。验证码、登录或付费要求出现时停止该条，不绕过限制。
- 临时签名地址会过期，重新解析后下载；不把临时地址、Cookie 或完整解析响应写入交付清单或聊天。

页面结构变化、网络失败或需要维护脚本时，读 [references/douyin-method.md](references/douyin-method.md)。不要无上限重试；候选耗尽后保留失败记录并说明原因。

## 视频号与原统一入口

`python scripts/video_dl.py '分享链接' -o output` 保留视频号/抖音单条入口；`-o` 可以是文件或目录。视频号仍需要 `playwright` 和 Chrome，按 `requirements.txt` 安装依赖；抖音已改用上述 HTTP 解析方式。批量按博主归档使用 `douyin_archive.py`。

## 用户另外要求文案时

下载与转写是两个步骤。只有用户要求才继续：从已验证视频提取单声道 16 kHz WAV，使用可用的本地中文 ASR，保存同名 `_文案.md` 和 `_字幕.srt` 到对应博主文件夹。建议保留原始 ASR 结果并校对品牌名、英文名和否定词；不要将宣传观点改写成已核实事实。此 skill 不附带 ASR 模型或转写脚本，不把解析页标题当成完整口播文案。

完成后报告成功/失败数量、绝对文件路径和校验情况。用户只要求本地下载时，不扩展为上传或发布任务。
