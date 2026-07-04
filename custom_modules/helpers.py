from PIL import Image
from pathlib import Path


def get_all_exts():
    """Every extension Pillow knows about (readable and/or writable)."""
    Image.init()
    ext_map = Image.registered_extensions()
    return set(ext.lstrip('.').lower() for ext in ext_map.keys())


def get_readable_exts():
    """Extensions Pillow can actually open (valid conversion *sources*).

    Not every registered extension is openable -- some formats are write-only
    (e.g. PDF), so filter by ``Image.OPEN`` rather than listing them as inputs.
    """
    Image.init()
    ext_map = Image.registered_extensions()
    return set(ext.lstrip('.').lower()
               for ext, fmt in ext_map.items() if fmt in Image.OPEN)


def get_savable_exts():
    """Extensions Pillow can write (i.e. valid conversion targets)."""
    Image.init()
    ext_map = Image.registered_extensions()
    savable = set()
    for ext, fmt in ext_map.items():
        if fmt in Image.SAVE:
            savable.add(ext.lstrip('.').lower())
    return savable


def get_suffix(path: Path):
    """Return the lower-case extension of ``path`` without a leading dot."""
    return Path(path).suffix.lower().lstrip('.')


def format_for_ext(ext: str):
    """Map a bare extension (e.g. ``"jpg"``) to its Pillow format name (``"JPEG"``).

    Returns ``None`` if the extension is not registered, in which case Pillow
    will fall back to inferring the format from the output filename.
    """
    Image.init()
    return Image.registered_extensions().get('.' + ext.lower().lstrip('.'))
