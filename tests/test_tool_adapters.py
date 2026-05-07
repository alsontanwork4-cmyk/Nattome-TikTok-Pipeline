import tempfile
import unittest
from pathlib import Path

from batch_analysis.tool_adapters import copy_or_download_video, source_video_filename


class ToolAdaptersTest(unittest.TestCase):
    def test_local_video_source_is_copied_and_recorded_as_downloaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.mov"
            destination = temp_path / source_video_filename(str(source))
            source.write_bytes(b"video bytes")

            status = copy_or_download_video(str(source), destination)

            self.assertEqual(status["status"], "downloaded")
            self.assertEqual(status["source"], str(source))
            self.assertEqual(status["artifact"], "source_video.mov")
            self.assertEqual(status["bytes"], len(b"video bytes"))
            self.assertEqual(destination.read_bytes(), b"video bytes")
