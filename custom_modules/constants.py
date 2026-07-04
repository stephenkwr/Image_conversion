from custom_modules.helpers import get_readable_exts, get_savable_exts

# Everything Pillow can actually open. Used to decide what we accept as *input*.
READABLE_EXTS = frozenset(get_readable_exts())

# Everything Pillow can write. Used to decide what is a valid *target*.
SAVABLE_EXTS = frozenset(get_savable_exts())

# Backwards-compatible aliases (older code imports these names).
image_exts = READABLE_EXTS
savable_exts = SAVABLE_EXTS

# Curated, user-facing conversion targets: common raster formats that hold
# real images well. Deliberately excludes scientific containers (GRIB, HDF5,
# FITS, BUFR), monochrome-only (XBM, MSP) and other niche formats that Pillow
# can technically write but that make no sense for ordinary photos. The CLI
# still accepts any format in SAVABLE_EXTS for power users.
# Note: EPS is intentionally excluded — Pillow can write it but needs
# Ghostscript for any round-trip, so it is a poor "common" target. It stays in
# SAVABLE_EXTS and remains reachable via the CLI.
_CURATED = (
    "png", "jpg", "jpeg", "jfif", "webp", "gif", "bmp", "dib", "tiff", "tif",
    "ico", "tga", "pdf", "avif", "ppm", "pgm", "pbm", "pnm", "icns", "qoi",
    "jp2", "im", "pcx", "sgi", "dds",
)
COMMON_TARGET_EXTS = tuple(e for e in _CURATED if e in SAVABLE_EXTS)

# File-dialog filters.
# The input picker should default to everything Pillow can *read*, so
# read-only sources (PSD, CUR, XPM, …) are visible without switching filters.
INPUT_FILETYPES = [
    ("All readable images", " ".join(f"*.{e}" for e in sorted(READABLE_EXTS))),
    ("Common images", " ".join(f"*.{e}" for e in COMMON_TARGET_EXTS)),
    ("All files", "*.*"),
]

# Kept for backwards compatibility / general use; same contents, common-first.
IMAGE_FILETYPES = [
    ("Common images", " ".join(f"*.{e}" for e in COMMON_TARGET_EXTS)),
    ("All readable images", " ".join(f"*.{e}" for e in sorted(READABLE_EXTS))),
    ("All files", "*.*"),
]

# Guard against decompression-bomb sized images while still allowing very large
# legitimate scans (~39370 x 6622 px).
MAX_PIXEL_LIMIT = 39370 * 6622
