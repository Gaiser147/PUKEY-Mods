import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from manager.media import compose_image, video_targets


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.png"
        self.target = {"width": 20, "height": 20, "background": "transparent"}

    def compose(self, image, **kwargs):
        image.save(self.source)
        return Image.open(io.BytesIO(compose_image(self.source, self.target, **kwargs))).convert("RGBA")

    def test_transparent_trim_and_top_center_fit(self):
        image = Image.new("RGBA", (10, 10))
        image.paste((255, 0, 0, 255), (3, 2, 7, 10))
        result = self.compose(image)
        self.assertEqual(result.size, (20, 20))
        self.assertEqual(result.getbbox(), (5, 0, 15, 20))
        self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_scale_and_percentage_offsets_crop_at_canvas(self):
        result = self.compose(Image.new("RGBA", (4, 4), "red"), scale=50, top=25, offset_x=25)
        self.assertEqual(result.getbbox(), (10, 5, 20, 15))
        result = self.compose(Image.new("RGBA", (4, 4), "red"), scale=200, top=-50)
        self.assertEqual(result.getbbox(), (0, 0, 20, 20))

    def test_green_canvas_has_pure_background_and_hard_edges(self):
        self.target["background"] = "green"
        image = Image.new("RGBA", (2, 2), (255, 0, 0, 127))
        image.putpixel((0, 0), (255, 0, 0, 200))
        result = self.compose(image)
        colors = {result.getpixel((x, y)) for x in range(20) for y in range(20)}
        self.assertEqual(colors, {(255, 0, 0, 255), (0, 255, 0, 255)})

    def test_green_removal_trims_screen_and_despills_edges(self):
        image = Image.new("RGBA", (4, 4), (0, 255, 0, 255))
        image.paste((180, 230, 100, 255), (1, 1, 3, 3))
        result = self.compose(image, remove_green=True, scale=50)
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        red, green, blue, alpha = result.getpixel((10, 2))
        self.assertGreater(alpha, 0)
        self.assertLess(alpha, 255)
        self.assertLessEqual(green, red)

    def test_exif_orientation_is_applied(self):
        image = Image.new("RGB", (8, 4), "red")
        exif = image.getexif()
        exif[274] = 6
        image.save(self.source, exif=exif)
        result = Image.open(io.BytesIO(compose_image(self.source, self.target)))
        self.assertEqual(result.getbbox(), (5, 0, 15, 20))

    def test_invalid_sizes_parameters_and_input_rejected(self):
        Image.new("RGB", (2, 2)).save(self.source)
        for change in ({"width": 0}, {"height": -1}, {"width": True}, {"width": 100000}, {"background": "blue"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                compose_image(self.source, dict(self.target, **change))
        for change in ({"scale": 0}, {"scale": float("inf")}, {"top": float("nan")}, {"offset_x": 10000}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                compose_image(self.source, self.target, **change)
        self.source.write_bytes(b"not an image")
        with self.assertRaises(ValueError):
            compose_image(self.source, self.target)

    def test_oversized_decoded_image_rejected_before_load(self):
        self.source.write_bytes(b"synthetic image header")
        image = Image.new("RGB", (2, 2))
        image._size = (50000, 50000)
        with patch("manager.media.Image.open", return_value=image), patch.object(image, "load", side_effect=AssertionError("must not decode")), self.assertRaises(ValueError):
            compose_image(self.source, self.target)

    def test_video_list_extracts_only_paths_and_deduplicates(self):
        data = b"Known videos:\nBacchus/Movie/Fam/A.mp4\n video avc1\nBacchus/Movie/Fam/A.mp4\nBacchus/Movie/Event/B.mp4\n"
        self.assertEqual(video_targets(data), ["Bacchus/Movie/Fam/A.mp4", "Bacchus/Movie/Event/B.mp4"])

    def test_video_formats_are_readable(self):
        from manager.media import video_formats
        data = (b"Bacchus/Movie/Fam/A.mp4\n    video avc1 2560x1440 1.42s 24.00fps; audio mp4a\n"
                b"Bacchus/Movie/Event/B.mp4\n    video avc1 1320x600 3.00s 30.00fps\nBacchus/Movie/Event/C.mp4\n")
        self.assertEqual(video_formats(data), {
            "Bacchus/Movie/Fam/A.mp4": "H.264 · 2560 × 1440 · 24 fps · 1.42 s · with audio",
            "Bacchus/Movie/Event/B.mp4": "H.264 · 1320 × 600 · 30 fps · 3 s · no audio"})

    def test_video_list_rejects_traversal_backslashes_and_bad_paths(self):
        for path in ("Bacchus/Movie/../A.mp4", "Bacchus/Movie/./A.mp4", "Bacchus/Movie/Fam\\A.mp4", "/Bacchus/Movie/A.mp4", "Bacchus/Movie/C:/A.mp4"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                video_targets(path.encode())


if __name__ == "__main__":
    unittest.main()
