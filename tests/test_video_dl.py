from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "video_dl.py"
SPEC = importlib.util.spec_from_file_location("video_dl", MODULE_PATH)
video_dl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(video_dl)


class VideoDlTests(unittest.TestCase):
    def test_detects_weixin(self):
        self.assertEqual(video_dl.platform_for("https://weixin.qq.com/sph/example"), "weixin")

    def test_detects_channels_preview(self):
        url = "https://channels.weixin.qq.com/finder-preview/pages/sph?id=example"
        self.assertEqual(video_dl.platform_for(url), "weixin")

    def test_detects_douyin_in_share_text(self):
        text = "复制打开抖音 https://v.douyin.com/example/ 看视频"
        self.assertEqual(video_dl.platform_for(text), "douyin")

    def test_rejects_unknown_platform(self):
        with self.assertRaises(ValueError):
            video_dl.platform_for("https://example.com/video")

    def test_sanitizes_filename(self):
        self.assertEqual(video_dl.safe_name('a/b:c*?"<>|'), "a_b_c")


if __name__ == "__main__":
    unittest.main()

