import unittest

from app.ingestion.extractors.youtube_extractor import extract_video_id_from_url


class YouTubeExtractorTests(unittest.TestCase):
    def test_extracts_video_id_from_watch_url(self):
        self.assertEqual(
            extract_video_id_from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_extracts_video_id_from_short_url(self):
        self.assertEqual(
            extract_video_id_from_url("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )


if __name__ == "__main__":
    unittest.main()
