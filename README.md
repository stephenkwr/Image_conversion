# Image_conversion

Convert images from one format to another — e.g. TIFF → PNG, PNG → JPG,
animated GIF → WEBP. Works on one image, several selected images, or a whole
folder, from either a **graphical app** or the **command line**.

The hard part of "convert anything to anything" is that formats accept
different pixel data: JPEG has no transparency, GIF is palette based, ICO only
holds icon-sized images, and so on. This tool handles those differences
automatically:

- **Transparency** is preserved when the target supports it (PNG, WEBP, GIF,
  TIFF, TGA, AVIF, …) and flattened onto a background colour when it does not
  (JPEG, BMP, PPM, …), so transparent areas don't turn black.
- **Colour mode** (palette, CMYK, grayscale, 16-bit, …) is adjusted as needed
  for the chosen format, keeping the best fidelity first.
- **Animation** (GIF/WEBP/APNG/multi-page TIFF) is preserved — including
  per-frame timing — when the target can store multiple frames, and collapsed
  to the first frame otherwise.
- **Icons** are written at a valid size instead of producing an empty file.
- The source format is **auto-detected**; you only pick the format to convert *to*.

## Quick start — the app (no Python needed)

Build a standalone executable and just run it:

```bash
pip install -r requirements-dev.txt
python build_exe.py
```

This produces **`dist/ImageConverter.exe`**. Double-click it to open the
converter — no Python, IDE, or install required. You can share that single
`.exe` with anyone on Windows.

In the window you can:

1. Choose **Individual images** (select one or many) or **A folder**
   (optionally including sub-folders).
2. Pick an **output folder** (defaults to the input location).
3. Choose the **format to convert to**.
4. Click **Convert**.

When it finishes, a dialog reports:

- how many images were **converted** and **where they were saved**,
- how many files were **skipped because they can't be written to that format**,
- how many files were **skipped because they aren't images at all**.

Files/folders that aren't images are ignored automatically; nothing crashes the
batch.

## Run from source

```bash
pip install -r requirements.txt

python convert_image.py                # launches the GUI
```

## Command line

```bash
# Single file -> a chosen folder
python convert_image.py photo.png ./converted --to jpg

# Whole folder (output defaults to the input folder if omitted)
python convert_image.py ./album --to webp

# Recurse into sub-folders
python convert_image.py ./album ./out --to png --recursive

# See every supported target format
python convert_image.py --list-formats
```

| Option | Meaning |
| --- | --- |
| `-t`, `--to FORMAT` | target format (required on the command line), e.g. `png`, `jpg`, `webp` |
| `-r`, `--recursive` | recurse into sub-folders when the input is a folder |
| `--overwrite` | overwrite existing files instead of adding `_1`, `_2`, … |
| `--no-animation` | save only the first frame of animated images |
| `--background R,G,B` | fill colour used when flattening transparency (default `255,255,255`) |
| `--list-formats` | list supported target formats and exit |
| `--gui` | force the graphical interface |

Existing files are never overwritten unless you pass `--overwrite`, the source
image itself is never clobbered, and two different sources that would land on
the same name never overwrite each other.

## Supported formats

- **Input:** anything Pillow can open (~70 formats, including read-only ones
  like PSD, FITS, PCD).
- **Output (recommended):** PNG, JPG/JPEG, WEBP, GIF, BMP, TIFF, ICO, TGA, PDF,
  AVIF, PPM/PGM/PBM, ICNS, QOI, JP2, DDS, PCX, SGI, IM.
- The command line additionally accepts any other format your Pillow can write
  (`--list-formats` shows the full list).

## Limitations

- Truly any-to-any is not possible: scientific containers (GRIB, HDF5, FITS,
  BUFR) and vector/video-ish formats can't store an arbitrary raster image, and
  PDF/EPS can be written but not read back by Pillow.
- Format conversions can be lossy (JPEG compression, GIF/ICO quantisation, ICO
  size limits). The tool picks sensible defaults rather than exposing every
  encoder knob.

## Tests

```bash
python -m unittest discover -s tests
```
