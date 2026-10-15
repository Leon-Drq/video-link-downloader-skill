# Video Link Downloader Skill

[![CI](https://github.com/Leon-Drq/video-link-downloader-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/Leon-Drq/video-link-downloader-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

一个面向 Codex/Agent Skills 的视频下载工具。用同一条命令解析或下载你有权保存的微信视频号与抖音视频。

> 仅用于你拥有、已获授权或法律允许下载的内容。项目不绕过登录、付费、访问控制或平台权限。

## 功能

- 自动识别微信视频号和抖音分享链接/分享文本
- `--info` 仅查看标题、大小等信息
- 支持指定输出文件或目录
- 视频号下载后还原可播放的 MP4 文件
- 抖音通过公开 HTTP 解析流程下载，无需 Cookie、API Key 或浏览器
- 批量按博主归档，记录清单，重复执行跳过已完成文件
- 候选清晰度回退、完整音画解码校验、可选 H.264 转码
- 可作为 Codex Skill 安装，也可单独作为 CLI 使用

## 环境要求

- Windows、macOS 或 Linux（安装 shell 脚本适用于 macOS/Linux）
- Python 3.10+
- 视频号需要 Google Chrome；抖音无需浏览器
- Python 包：`playwright`、`requests`
- 抖音需要 FFmpeg 和 ffprobe，可放入 PATH 或使用参数指定路径

## 安装

### 安装为 Codex Skill 和命令行工具

```bash
git clone https://github.com/Leon-Drq/video-link-downloader-skill.git
cd video-link-downloader-skill
./scripts/install.sh
```

安装脚本会：

1. 创建独立虚拟环境并安装 Python 依赖；
2. 将 Skill 安装到 `${CODEX_HOME:-$HOME/.codex}/skills/video-link-downloader`；
3. 在 `$HOME/.local/bin/video-dl` 创建命令入口。

如果终端找不到 `video-dl`，将以下内容加入 shell 配置：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 仅在仓库中运行

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/video_dl.py --help
```

## 使用

```bash
# 微信视频号
video-dl 'https://weixin.qq.com/sph/VIDEO_ID'

# 抖音链接或完整分享文本
video-dl 'https://v.douyin.com/EXAMPLE/'

# 指定下载目录
video-dl '分享链接' -o ~/Downloads

# 指定文件名
video-dl '分享链接' -o ~/Downloads/video.mp4

# 只解析信息，不下载
video-dl '分享链接' --info
```

## 抖音批量归档（Windows 同样适用）

只使用抖音功能时安装 `requests` 即可；FFmpeg/ffprobe 需另外安装。

```bash
python -m pip install requests
python scripts/douyin_archive.py --share '完整抖音分享文本' -o example
python scripts/douyin_archive.py --input videos.json -o example
python scripts/douyin_archive.py --input videos.json -o example --h264
```

`videos.json` 是包含 `url`、可选 `author`/`title`/`id` 的对象数组，格式见 [SKILL.md](SKILL.md)。每位博主一个目录，生成 `视频清单.json` 和 `素材索引.md`。纯链接无法确定作者时归入“未分类”；可在输入中明确提供博主。不会覆盖同名视频。部分失败返回退出码 1，修复后重跑相同输入即可跳过已完成项。

Windows 可以追加 `--ffmpeg "C:/tools/ffmpeg.exe" --ffprobe "C:/tools/ffprobe.exe"`。下载前只看信息使用 `--info`。默认保留可解码原始编码；`--h264` 用于需要 H.264 兼容版本的情况。

将 `SKILL.md`、`requirements.txt`、`LICENSE`、`scripts/video_dl.py`、`scripts/douyin_archive.py` 和 `references/` 按原目录结构复制到 `~/.codex/skills/video-link-downloader/` 即可安装 skill。也可以用 `python scripts/package_skill.py` 生成 `.skill` 压缩包。

本次工作流已用于 15 条公开视频的归档；站点变化可能导致解析失效。转写文案是另外的可选步骤，仓库不附带语音模型或自动转写脚本。

## Skill 触发方式

安装后，可以直接向 Codex 提出：

- “下载这个视频号链接到 Downloads”
- “看看这个抖音链接对应什么视频，不要下载”
- “把这几个有授权的视频保存下来并检查是否可播放”

智能体工作流定义在 [`SKILL.md`](SKILL.md)。CLI 实现在 [`scripts/video_dl.py`](scripts/video_dl.py)。

## 工作原理

- 视频号：在无头 Chrome 中运行站点公开前端解析流程，取得临时媒体数据，下载并还原文件头。
- 抖音：`dy-check` → 结果页 → 可选 `dy-r` 延迟加载 → 核对 ID → 媒体候选 → 下载与完整解码校验。分享 URL 会发送给第三方公开解析站。详细流程见 [方法说明](references/douyin-method.md)。

解析网站、平台页面或风控规则变化后，功能可能需要更新。不要在 issue 中粘贴临时签名 URL、Cookie、令牌或完整解析响应。

## 开发与测试

```bash
python -m unittest discover -s tests -v
python -m py_compile scripts/video_dl.py
python scripts/validate_skill.py
python scripts/package_skill.py
```

联网端到端测试会访问第三方网站，因此不在默认 CI 中执行。提交修复时，可以在获得授权的测试链接上运行 `--info`，不要把真实私人链接写入仓库。

## 文档

- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [许可证](LICENSE)

## 免责声明

本项目与微信、视频号、抖音、字节跳动及解析网站无隶属或授权关系。使用者需自行遵守适用法律、平台条款和内容版权要求。项目按 MIT License 提供，不保证第三方接口持续可用。

## 上游来源

基于 [kunhai-88/video-link-downloader-skill](https://github.com/kunhai-88/video-link-downloader-skill) 扩展，保留原 MIT 许可；本 fork 增加抖音 HTTP 解析、批量归档与解码校验。
