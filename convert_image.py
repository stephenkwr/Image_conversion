"""Convert images from one format to another.

Two ways to use it:

    # Command line (scriptable)
    python convert_image.py photo.png out_dir --to jpg
    python convert_image.py ./album ./converted --to webp --recursive
    python convert_image.py --list-formats

    # Graphical (no arguments -> point-and-click dialogs)
    python convert_image.py
"""

import argparse
import os
import sys
from pathlib import Path

from custom_modules.constants import COMMON_TARGET_EXTS, SAVABLE_EXTS
from custom_modules.converter import convert_path, DEFAULT_BG


def _print_formats():
    print("Recommended targets (common image formats):")
    print("  " + ", ".join(COMMON_TARGET_EXTS))
    print("\nAll formats Pillow can write on this machine:")
    print("  " + ", ".join(sorted(SAVABLE_EXTS)))


def _parse_bg(text):
    try:
        parts = tuple(int(p) for p in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("background must be 'R,G,B' with integers 0-255")
    if len(parts) != 3 or any(not 0 <= p <= 255 for p in parts):
        raise argparse.ArgumentTypeError("background must be 'R,G,B' with each value 0-255")
    return parts


def _report(report):
    for r in report.results:
        if r.ok:
            print(f"  OK    {r.source.name} -> {r.target.name}")
        elif r.status == "not_image":
            print(f"  SKIP  {r.source.name}  (not an image: {r.message})")
        else:
            print(f"  SKIP  {r.source.name}  (can't convert: {r.message})")
    print(
        f"\nDone: {report.converted} converted, "
        f"{report.skipped_incompatible} skipped (incompatible target), "
        f"{report.skipped_not_image} skipped (not images)."
    )


def run_cli(args):
    ext = args.to.lower().lstrip(".")
    if ext not in SAVABLE_EXTS:
        print(f"Error: '{ext}' is not a format Pillow can write.", file=sys.stderr)
        print("Run with --list-formats to see valid targets.", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input path does not exist: {input_path}", file=sys.stderr)
        return 2

    # Default the output folder next to the input.
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_path.parent if input_path.is_file() else input_path

    print(f"Converting to .{ext}  (output: {output_dir})")
    report = convert_path(
        input_path,
        output_dir,
        ext,
        background=args.background,
        keep_animation=not args.no_animation,
        overwrite=args.overwrite,
        recursive=args.recursive,
    )
    _report(report)
    # Non-zero exit (for scripts) when something went wrong: a real image
    # couldn't be written to the target, or nothing at all was produced from a
    # non-empty input. An empty folder (nothing to do) is not an error.
    ok = report.skipped_incompatible == 0 and (report.converted > 0 or report.total == 0)
    return 0 if ok else 1


def run_gui():
    # Imported lazily so the CLI works on machines without a display / Tk.
    from custom_modules.GUI import launch_gui

    # Diagnostic seam: build the window and immediately close it. Used to smoke
    # test that Tk is bundled correctly in the packaged executable.
    if os.environ.get("IMAGECONVERTER_SELFTEST"):
        launch_gui(_on_ready=lambda ctx: ctx.root.quit())
        return 0

    launch_gui()
    return 0


def main(argv=None):
    # In a windowed (no-console) packaged build, stdout/stderr can be None.
    # Route them to the void so any CLI print never crashes the process.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    parser = argparse.ArgumentParser(
        description="Convert images from one format to another.",
        epilog="Run with no arguments to launch the graphical interface.",
    )
    parser.add_argument("input", nargs="?", help="input image file or folder")
    parser.add_argument("output", nargs="?", help="output folder (default: next to the input)")
    parser.add_argument("-t", "--to", help="target format, e.g. png, jpg, webp")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="recurse into sub-folders when input is a folder")
    parser.add_argument("--overwrite", action="store_true",
                        help="overwrite existing files instead of adding _1, _2 ...")
    parser.add_argument("--no-animation", action="store_true",
                        help="save only the first frame of animated images")
    parser.add_argument("--background", type=_parse_bg, default=DEFAULT_BG, metavar="R,G,B",
                        help="fill colour when flattening transparency (default 255,255,255)")
    parser.add_argument("--list-formats", action="store_true",
                        help="list supported target formats and exit")
    parser.add_argument("--gui", action="store_true", help="force the graphical interface")

    args = parser.parse_args(argv)

    if args.list_formats:
        _print_formats()
        return 0

    # Launch the GUI only when the user gave no CLI-relevant arguments (bare
    # invocation) or asked for it explicitly. If they supplied flags but forgot
    # the input path, that is a CLI error -- don't silently open a blocking GUI.
    if args.gui or (args.input is None and args.to is None):
        return run_gui()

    if args.input is None:
        parser.error("an input file or folder is required in command-line mode "
                     "(or run with no arguments for the GUI)")
    if not args.to:
        parser.error("the --to/-t argument is required in command-line mode "
                     "(or run with no arguments for the GUI)")

    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
