# 贡献指南

感谢参与改进 Video Link Downloader Skill。

## 开始开发

1. Fork 仓库并创建功能分支。
2. 创建 Python 3.10+ 虚拟环境。
3. 安装 `requirements.txt`。
4. 修改代码和文档。
5. 运行全部本地检查。

```bash
python -m unittest discover -s tests -v
python -m py_compile scripts/video_dl.py
python scripts/validate_skill.py
```

## 提交要求

- 保持 `SKILL.md` 精简，只放智能体执行任务必需的流程。
- 面向用户的安装、使用和维护说明放在 `README.md` 或项目文档中。
- 新增平台或参数时补充离线单元测试和使用示例。
- 不要提交 Cookie、令牌、签名地址、解析响应、私人分享链接或下载的视频。
- 不要添加绕过登录、付费、访问控制、验证码或数字版权保护的功能。

## Issue 与 Pull Request

Bug 报告请包含：

- 操作系统与 Python 版本；
- 执行的命令（隐藏私人链接和令牌）；
- 精简后的错误信息；
- 是否可以稳定复现。

Pull Request 请说明修改目的、用户影响和验证方式。涉及第三方网页变化时，描述页面行为，不要公开临时凭据或完整响应。

