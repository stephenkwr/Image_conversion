from PIL import Image
from pathlib import Path

def get_all_exts():
    Image.init()
    ext_map = Image.registered_extensions()
    all_exts = set(ext.lstrip('.').lower() for ext in ext_map.keys())
    return all_exts

def get_savable_exts():
    Image.init()
    ext_map = Image.registered_extensions()
    savable = set()
    for ext, fmt in ext_map.items():
        if fmt in Image.SAVE:
            savable.add(ext.lstrip('.').lower())
    return savable

def get_suffix(path : Path):
    suffix = Path(path).suffix.lower().lstrip('.')
    