"""Build a standalone Windows executable of the image converter.

Usage:
    python build_exe.py

Produces a single self-contained file at ``dist/ImageConverter.exe`` that end
users can run by double-clicking -- no Python or IDE required. Double-clicking
opens the graphical converter; the same exe also works from a terminal with the
command-line options (see ``convert_image.py``).

Requires PyInstaller (``pip install pyinstaller``).
"""

import subprocess
import sys

APP_NAME = "ImageConverter"

ARGS = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                       # one self-contained .exe
    "--windowed",                      # no console window (clean GUI launch)
    "--name", APP_NAME,
    "--noconfirm", "--clean",
    # Ensure the whole helper package is bundled even though GUI is imported
    # lazily inside a function.
    "--collect-submodules", "custom_modules",
    "--hidden-import", "custom_modules.GUI",
    "convert_image.py",
]


def main():
    print("Building", APP_NAME, "...")
    result = subprocess.run(ARGS)
    if result.returncode == 0:
        print(f"\nDone. Executable: dist/{APP_NAME}.exe")
    else:
        print("\nBuild failed.", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
