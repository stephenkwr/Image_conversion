from custom_modules.helpers import *

image_exts = frozenset(get_all_exts())
# print(f"{image_exts=}")

savable_exts = frozenset(get_savable_exts())
# print(f"{savable_exts=}")

IMAGE_FILETYPES = [("Supported images", " ".join(f"*.{e}" for e in sorted(savable_exts))),
                   ("All Pillow file types", " ".join(f"*.{e}" for e in sorted(image_exts)))]
# print(f"{IMAGE_FILETYPES}")

MAX_PIXEL_LIMIT = 39370 * 6622