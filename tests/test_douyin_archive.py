import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import douyin_archive as dy


class DouyinTests(unittest.TestCase):
    def test_share_text_and_windows_names(self):
        self.assertEqual(dy.share_url('【作者的作品】 [链接](https://v.douyin.com/a\\_b/)'),
                         'https://v.douyin.com/a_b/')
        self.assertEqual(dy.safe_name('../CON'), '_CON')
        self.assertNotIn('/', dy.safe_name('../作者/视频'))
        with self.assertRaises(ValueError):
            dy.share_url('https://v.douyin.com.evil.example/video/123')

    def test_candidates_decode_entities_and_rank(self):
        page = '''分辨率 720 x 1280：
        <a href="https://v.example.douyinvod.com/a?cs=2&amp;br=200">A</a>
        分辨率 1080 x 1920：
        <a href="https://v.example.douyinvod.com/b?cs=0&amp;br=900">B</a>
        <a href="https://v.example.douyinvod.com/mirror?cs=0&amp;br=900">M</a>
        <a href="https://v.example.douyinvod.com/c?cs=9">C</a>
        <a href="https://example.com/douyinvod.com/x?cs=0">bad</a>'''
        choices = dy.candidates(page)
        self.assertEqual(len(choices), 3)
        self.assertEqual([c['width'] for c in choices], [1080, 720, 1080])
        self.assertIn('&br=900', choices[0]['url'])

    def test_lazy_result_id_mismatch_stops(self):
        session = MagicMock()
        check, shell, result = Mock(), Mock(), Mock()
        check.json.return_value = {'error': 0, 'url': '/sph/public/dy-d?url=opaque'}
        shell.text = '''$.get("https://apikr.convry.com/sph/public/dy-r?url=opaque")'''
        result.text = 'video/456'
        session.get.side_effect = [check, shell, result]
        with self.assertRaisesRegex(RuntimeError, 'ID 不匹配'):
            dy.resolve(session, 'https://www.douyin.com/video/123')
        self.assertEqual(session.get.call_count, 3)

    def test_failed_decode_falls_back_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'video.mp4'
            session = MagicMock()
            response = Mock(headers={'Content-Type': 'video/mp4'})
            response.iter_content.side_effect = lambda *_: iter([b'media'])
            session.get.return_value.__enter__.return_value = response
            data = {'candidates': [{'url': 'first'}, {'url': 'second'}]}
            with patch.object(dy, 'probe', return_value={'video_codec': 'h264'}), \
                 patch.object(dy, 'ffmpeg_run', side_effect=[RuntimeError('bad codec'), None]):
                dy.download(session, data, target, 'ffmpeg', 'ffprobe')
            self.assertEqual(target.read_bytes(), b'media')
            self.assertEqual(session.get.call_count, 2)
            with self.assertRaises(FileExistsError):
                dy.download(session, data, target, 'ffmpeg', 'ffprobe')

    def test_failures_leave_no_final_media(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'video.mp4'
            session = MagicMock()
            response = Mock(headers={'Content-Type': 'text/html'})
            session.get.return_value.__enter__.return_value = response
            with self.assertRaises(RuntimeError):
                dy.download(session, {'candidates': [{'url': 'bad'}]}, target, 'ffmpeg', 'ffprobe')
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_archive_preserves_other_entries_and_skips_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'saved.mp4').write_bytes(b'media')
            records = [{'url': 'https://v.douyin.com/saved/', 'file': 'saved.mp4', 'size': 5,
                        'status': '已归档并校验', 'transcript_file': 'saved.md'},
                       {'url': 'https://v.douyin.com/other/', 'title': 'other'}]
            dy.atomic_json(root / '视频清单.json', records)
            with patch.object(dy, 'probe', return_value={}), patch.object(dy, 'resolve') as resolve:
                result = dy.archive([{'url': records[0]['url']}], root, Mock(), SimpleNamespace(ffprobe='ffprobe'))
            self.assertEqual(result, 0)
            resolve.assert_not_called()
            self.assertEqual(dy.json.loads((root / '视频清单.json').read_text(encoding='utf8')), records)


if __name__ == '__main__':
    unittest.main()
