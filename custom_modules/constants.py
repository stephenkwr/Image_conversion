image_exts = frozenset({"avif", "blp", "bmp", "dds", "dib", "eps", "gif", 
                         "icns", "ico", "im", "jpeg", "jpg2k", "mpo", "msp",
                         "pcx", "pfm", "png", "ppm", "qoi", "sgi", "spider", "tga",
                         "tiff", "webp", "xbm"})


IMAGE_FILETYPES = [("Supported images", " ".join(f"*.{e}" for e in sorted(image_exts))),
                   ("All files", "*.*")]