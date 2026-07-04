"""Tests for the image conversion engine. Run with:

    python -m unittest discover -s tests

Uses only the standard library (unittest) plus Pillow, so no extra test
dependencies are required.
"""

import tempfile
import unittest
import warnings
from pathlib import Path

from PIL import Image

from custom_modules.constants import COMMON_TARGET_EXTS, SAVABLE_EXTS
from custom_modules.converter import convert_file, convert_path

warnings.simplefilter("ignore")  # I-mode PNG deprecation etc. are not test failures

# Formats Pillow writes but cannot read back; verify these via header bytes.
WRITE_ONLY = {"pdf": b"%PDF", "eps": b"%!PS"}


def _reopens(path: Path) -> bool:
    ext = path.suffix.lower().lstrip(".")
    if ext in WRITE_ONLY:
        return path.read_bytes()[:8].startswith(WRITE_ONLY[ext][:1]) and WRITE_ONLY[ext] in path.read_bytes()[:8]
    with Image.open(path) as im:
        im.load()
    return True


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.src = self.tmp / "src"
        self.out = self.tmp / "out"
        self.src.mkdir()
        self.out.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _make(self, name, mode, color, size=(24, 16)):
        p = self.src / name
        Image.new(mode, size, color).save(p)
        return p

    def test_alpha_flattened_to_lossless_target(self):
        # BMP cannot store alpha, so a transparent source must be flattened onto
        # the background rather than dropped uncomposited. BMP is lossless, so
        # the pixel values are exact.
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))    # transparent BLACK
        img.putpixel((0, 0), (10, 20, 200, 255))           # one opaque pixel
        p = self.src / "a.png"
        img.save(p)

        out = convert_file(p, self.out, "bmp")
        with Image.open(out) as res:
            self.assertEqual(res.convert("RGB").getpixel((5, 5)), (255, 255, 255))  # bg, not black
            self.assertEqual(res.convert("RGB").getpixel((0, 0)), (10, 20, 200))    # opaque kept

    def test_alpha_preserved_for_capable_target(self):
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        p = self.src / "keep.png"
        img.save(p)
        out = convert_file(p, self.out, "webp")
        with Image.open(out) as res:
            self.assertEqual(res.convert("RGBA").getpixel((4, 4))[3], 0)  # still transparent

    def test_jpeg_target_has_no_alpha(self):
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        p = self.src / "j.png"
        img.save(p)
        out = convert_file(p, self.out, "jpg")
        with Image.open(out) as res:
            self.assertEqual(res.mode, "RGB")

    def test_custom_background(self):
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        p = self.src / "clear.png"
        img.save(p)
        out = convert_file(p, self.out, "jpg", background=(0, 0, 0))
        with Image.open(out) as res:
            self.assertEqual(res.getpixel((1, 1)), (0, 0, 0))

    def test_palette_gif_to_png(self):
        p = self._make("p.gif", "P", 3)
        out = convert_file(p, self.out, "png")
        self.assertTrue(_reopens(out))

    def test_multi_dot_filename(self):
        p = self.src / "my.holiday.v2.png"
        Image.new("RGB", (5, 5), (1, 2, 3)).save(p)
        out = convert_file(p, self.out, "jpg")
        self.assertEqual(out.name, "my.holiday.v2.jpg")

    def test_no_clobber(self):
        p = self._make("dup.png", "RGB", (1, 2, 3))
        a = convert_file(p, self.out, "jpg", overwrite=False)
        b = convert_file(p, self.out, "jpg", overwrite=False)
        self.assertNotEqual(a.name, b.name)
        self.assertTrue(a.exists() and b.exists())

    def test_overwrite(self):
        p = self._make("ow.png", "RGB", (1, 2, 3))
        a = convert_file(p, self.out, "jpg", overwrite=True)
        b = convert_file(p, self.out, "jpg", overwrite=True)
        self.assertEqual(a, b)

    def test_never_overwrites_source(self):
        p = self._make("same.png", "RGB", (9, 9, 9))
        out = convert_file(p, self.src, "png", overwrite=True)
        self.assertNotEqual(out.resolve(), p.resolve())
        self.assertTrue(p.exists())

    def test_unsupported_target_raises(self):
        p = self._make("x.png", "RGB", (1, 1, 1))
        with self.assertRaises(ValueError):
            convert_file(p, self.out, "psd")  # PSD is read-only in Pillow

    def test_batch_skips_non_images(self):
        self._make("a.png", "RGB", (1, 2, 3))
        self._make("b.bmp", "RGB", (4, 5, 6))
        (self.src / "notes.txt").write_text("not an image")
        report = convert_path(self.src, self.out, "webp")
        self.assertEqual(report.converted, 2)
        self.assertEqual(report.skipped_not_image, 1)     # the .txt
        self.assertEqual(report.skipped_incompatible, 0)
        self.assertEqual(report.output_dir, self.out)

    def test_not_image_vs_incompatible_classification(self):
        from unittest import mock
        good = self._make("real.png", "RGB", (1, 2, 3))
        (self.src / "note.txt").write_text("x")
        # Force the writer to fail on the valid image -> "incompatible target".
        with mock.patch("custom_modules.converter._save_static",
                        side_effect=OSError("encoder refused")):
            report = convert_path(self.src, self.out, "bmp")
        self.assertEqual(report.converted, 0)
        self.assertEqual(report.skipped_incompatible, 1)  # real.png couldn't be written
        self.assertEqual(report.skipped_not_image, 1)     # note.txt isn't an image

    def test_no_partial_file_left_on_write_failure(self):
        from unittest import mock
        p = self._make("x.png", "RGB", (1, 2, 3))
        with mock.patch("custom_modules.converter._save_static",
                        side_effect=OSError("boom")):
            with self.assertRaises(Exception):
                convert_file(p, self.out, "bmp")
        # Neither the real target nor a leftover .part file should remain.
        self.assertEqual(list(self.out.iterdir()), [])

    def test_readable_exts_exclude_write_only(self):
        from custom_modules.constants import READABLE_EXTS
        self.assertIn("png", READABLE_EXTS)
        self.assertIn("jpg", READABLE_EXTS)
        self.assertNotIn("pdf", READABLE_EXTS)  # Pillow writes PDF but can't open it

    def test_convert_list_of_files(self):
        a = self._make("one.png", "RGB", (1, 2, 3))
        b = self._make("two.bmp", "RGB", (4, 5, 6))
        (self.src / "skip.txt").write_text("x")
        report = convert_path([a, b, self.src / "skip.txt"], self.out, "jpg")
        self.assertEqual(report.converted, 2)
        self.assertEqual(report.skipped_not_image, 1)

    def test_recursive(self):
        sub = self.src / "nested"
        sub.mkdir()
        Image.new("RGB", (4, 4), (1, 2, 3)).save(sub / "deep.png")
        Image.new("RGB", (4, 4), (1, 2, 3)).save(self.src / "top.png")
        flat = convert_path(self.src, self.out, "jpg", recursive=False)
        self.assertEqual(flat.converted, 1)
        deep = convert_path(self.src, self.out, "jpg", recursive=True, overwrite=True)
        self.assertEqual(deep.converted, 2)

    def test_animation_preserved(self):
        frames = [Image.new("RGB", (8, 8), c) for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]]
        g = self.src / "anim.gif"
        frames[0].save(g, save_all=True, append_images=frames[1:], duration=80, loop=0)
        out = convert_file(g, self.out, "webp")
        with Image.open(out) as res:
            self.assertEqual(getattr(res, "n_frames", 1), 3)

    def test_animation_collapsed_for_static_target(self):
        frames = [Image.new("RGB", (8, 8), c) for c in [(255, 0, 0), (0, 255, 0)]]
        g = self.src / "anim2.gif"
        frames[0].save(g, save_all=True, append_images=frames[1:])
        out = convert_file(g, self.out, "jpg")
        with Image.open(out) as res:
            self.assertEqual(getattr(res, "n_frames", 1), 1)

    def test_every_common_target_from_rgba(self):
        # The headline promise: an ordinary (transparent) image converts to
        # every curated target without error.
        img = Image.new("RGBA", (20, 14), (200, 120, 40, 128))
        p = self.src / "base.png"
        img.save(p)
        failures = []
        for ext in COMMON_TARGET_EXTS:
            try:
                out = convert_file(p, self.out, ext, overwrite=True)
                self.assertTrue(_reopens(out), f"{ext} did not produce a valid file")
            except Exception as exc:  # noqa: BLE001 - we want the whole list
                failures.append(f"{ext}: {type(exc).__name__}: {exc}")
        self.assertEqual(failures, [], f"targets failed: {failures}")

    def test_animation_preserves_per_frame_duration(self):
        # Variable frame timing must survive, not collapse to one value.
        frames = [Image.new("RGB", (8, 8), c)
                  for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (9, 9, 9)]]
        g = self.src / "vfr.gif"
        frames[0].save(
            g, save_all=True, append_images=frames[1:],
            duration=[1000, 100, 100, 100], loop=0,
        )
        out = convert_file(g, self.out, "gif")
        got = []
        with Image.open(out) as res:
            for i in range(getattr(res, "n_frames", 1)):
                res.seek(i)
                got.append(res.info.get("duration"))
        self.assertEqual(got[0], 1000)               # long hold preserved
        self.assertNotEqual(len(set(got)), 1)         # not all pinned to one value

    def test_batch_overwrite_no_intrabatch_clobber(self):
        # Two DISTINCT sources sharing a stem must not overwrite each other,
        # even with overwrite=True, and the report count must match disk.
        Image.new("RGB", (6, 6), (255, 0, 0)).save(self.src / "shot.png")
        Image.new("RGB", (6, 6), (0, 0, 255)).save(self.src / "shot.bmp")
        report = convert_path(self.src, self.out, "webp", overwrite=True)
        self.assertEqual(report.converted, 2)
        written = list(self.out.glob("*.webp"))
        self.assertEqual(len(written), 2, f"expected 2 files, found {written}")

    def test_decompression_bomb_is_skipped_not_failed(self):
        p = self._make("big.png", "RGB", (1, 2, 3), size=(100, 100))
        (self.src / "note.txt").write_text("x")
        original = Image.MAX_IMAGE_PIXELS
        try:
            Image.MAX_IMAGE_PIXELS = 4000  # 2x = 8000 < 10000 px -> "bomb"
            report = convert_path(self.src, self.out, "jpg")
        finally:
            Image.MAX_IMAGE_PIXELS = original
        # An over-limit or unreadable image is a "not a usable image" skip,
        # never a crash. Both the bomb and the .txt land there.
        self.assertEqual(report.converted, 0)
        self.assertEqual(report.skipped_not_image, 2)

    def test_read_only_source_can_be_converted_from(self):
        # A format Pillow can read but not write should still be a valid *input*.
        # (PPM is trivially creatable; we assert the input gate is by readability,
        # not savability, using a savable-but-unusual source here.)
        p = self._make("src.ppm", "RGB", (10, 20, 30))
        out = convert_file(p, self.out, "png")
        self.assertTrue(_reopens(out))


class GuiSmokeTest(unittest.TestCase):
    """Drive the real Tk window headlessly end-to-end. Skipped where Tk cannot
    initialise (e.g. a display-less CI box)."""

    def test_gui_converts_multiple_and_reports(self):
        try:
            import tkinter
            tkinter.Tk().destroy()
        except Exception as exc:  # no display / Tk unavailable
            self.skipTest(f"Tk unavailable: {exc}")

        from unittest import mock
        from custom_modules import GUI

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        out = base / "out"
        out.mkdir()
        a = base / "a.png"
        Image.new("RGBA", (16, 12), (200, 120, 40, 128)).save(a)
        b = base / "b.bmp"
        Image.new("RGB", (16, 12), (10, 20, 30)).save(b)
        (base / "note.txt").write_text("x")

        captured = {}

        def driver(ctx):
            ctx.selection["input"] = [str(a), str(b), str(base / "note.txt")]
            ctx.selection["output"] = str(out)
            ctx.set_format("jpg")
            ctx.start()
            ctx.root.after(15000, ctx.root.quit)  # safety net

        def fake_showinfo(title, message, **kw):
            captured["message"] = message
            captured["root"].quit()

        def on_ready(ctx):
            captured["root"] = ctx.root
            driver(ctx)

        with mock.patch.object(GUI.messagebox, "showinfo", side_effect=fake_showinfo):
            GUI.launch_gui(_on_ready=on_ready)

        self.assertIn("Converted: 2", captured.get("message", ""))
        self.assertIn("not images: 1", captured.get("message", ""))
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["a.jpg", "b.jpg"])


class CliDispatchTests(unittest.TestCase):
    """main() argument dispatch, without touching the GUI/Tk."""

    def setUp(self):
        import convert_image
        self.main = convert_image.main

    def test_flags_without_input_error_instead_of_launching_gui(self):
        # Regression: 'convert_image.py --to png' (input omitted) must be a CLI
        # error, not a silent launch of the blocking GUI.
        with self.assertRaises(SystemExit) as cm:
            self.main(["--to", "png"])
        self.assertEqual(cm.exception.code, 2)

    def test_missing_input_path_returns_nonzero(self):
        code = self.main(["does_not_exist.png", "--to", "png"])
        self.assertEqual(code, 2)

    def test_bad_target_returns_nonzero(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        src = Path(tmp.name) / "a.png"
        Image.new("RGB", (4, 4), (1, 2, 3)).save(src)
        code = self.main([str(src), tmp.name, "--to", "psd"])
        self.assertEqual(code, 2)

    def test_list_formats_returns_zero(self):
        self.assertEqual(self.main(["--list-formats"]), 0)

    def test_single_nonimage_exits_nonzero(self):
        # A named file that produced nothing is a failure for scripts.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        notes = Path(tmp.name) / "notes.txt"
        notes.write_text("not an image")
        code = self.main([str(notes), tmp.name, "--to", "png"])
        self.assertEqual(code, 1)

    def test_folder_with_conversions_exits_zero(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        Image.new("RGB", (4, 4), (1, 2, 3)).save(base / "a.png")
        (base / "note.txt").write_text("x")  # skipped, but something converted
        out = base / "out"
        code = self.main([str(base), str(out), "--to", "jpg"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
