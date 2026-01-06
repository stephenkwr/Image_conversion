from custom_modules.helpers import *

image_exts = frozenset(get_all_exts())
print(f"{image_exts=}")

savable_exts = frozenset(get_savable_exts())
print(f"{savable_exts=}")

IMAGE_FILETYPES = [("Supported images", " ".join(f"*.{e}" for e in sorted(image_exts))),
                   ("All files", "*.*")]