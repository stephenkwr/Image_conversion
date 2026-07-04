"""Image conversion engine.

The public entry points are :func:`convert_file` (one image) and
:func:`convert_path` (a single image or a whole folder).

The tricky part of "convert any image to any format" is that formats accept
different pixel modes: JPEG cannot store an alpha channel, GIF is palette based,
etc. Rather than hard-code a per-format mode table (which drifts between Pillow
versions), the engine tries to save the image as-is first (best fidelity) and,
if Pillow refuses, walks a sequence of progressively more compatible renditions
until one succeeds.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageSequence, UnidentifiedImageError

from custom_modules.constants import SAVABLE_EXTS, MAX_PIXEL_LIMIT
from custom_modules.helpers import get_suffix, format_for_ext

Image.MAX_IMAGE_PIXELS = MAX_PIXEL_LIMIT

# Default background used when flattening a transparent image onto an opaque
# format (e.g. PNG-with-alpha -> JPEG).
DEFAULT_BG = (255, 255, 255)

# Extensions whose format supports writing multiple frames via ``save_all``.
ANIMATED_TARGETS = {"gif", "webp", "apng", "tif", "tiff", "pdf", "mpo", "png"}

# Extensions whose format can store an alpha channel. For every other target,
# a transparent source is flattened onto the background first -- otherwise
# Pillow drops the alpha uncomposited and transparent pixels keep their (often
# black) hidden colour instead of the intended background. Determined
# empirically against Pillow's writers.
ALPHA_CAPABLE_TARGETS = {
    "png", "apng", "webp", "gif", "tiff", "tif", "tga",
    "avif", "qoi", "jp2", "im", "sgi", "dds", "ico",
}

# Per-extension save options for nicer output quality.
SAVE_OPTIONS = {
    "jpg": {"quality": 95},
    "jpeg": {"quality": 95},
    "jfif": {"quality": 95},
    "jpe": {"quality": 95},
    "webp": {"quality": 90},
}


class ConversionError(Exception):
    """Base class for conversion problems raised by :func:`convert_file`."""


class NotAnImageError(ConversionError):
    """The input could not be opened as a usable image."""


class IncompatibleTargetError(ConversionError):
    """A valid image could not be written to the requested target format."""


# Outcome status codes for a single file.
CONVERTED = "converted"
NOT_IMAGE = "not_image"        # skipped: not a readable image at all
INCOMPATIBLE = "incompatible"  # skipped: real image, but not writable as target


@dataclass
class FileResult:
    source: Path
    target: Path | None = None
    status: str = NOT_IMAGE
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == CONVERTED


@dataclass
class ConvertReport:
    results: list[FileResult] = field(default_factory=list)
    output_dir: Path | None = None

    def _count(self, status) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def converted(self) -> int:
        return self._count(CONVERTED)

    @property
    def skipped_not_image(self) -> int:
        return self._count(NOT_IMAGE)

    @property
    def skipped_incompatible(self) -> int:
        return self._count(INCOMPATIBLE)

    @property
    def skipped(self) -> int:
        return self.skipped_not_image + self.skipped_incompatible

    @property
    def total(self) -> int:
        return len(self.results)


def _has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (
        im.mode == "P" and "transparency" in im.info
    )


def _flatten(im: Image.Image, bg=DEFAULT_BG) -> Image.Image:
    """Composite a transparent image onto a solid background, returning RGB."""
    rgba = im.convert("RGBA")
    base = Image.new("RGBA", rgba.size, tuple(bg) + (255,))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def _renditions(im: Image.Image, bg, ext: str):
    """Ordered callables producing progressively more compatible versions.

    Each is a thunk so a conversion that raises can be skipped cleanly. When the
    source is transparent and the target cannot keep an alpha channel, the
    flattened version is tried first (correct colours); otherwise the image is
    tried as-is first (best fidelity, keeps transparency where supported).
    """
    thunks = []
    has_alpha = _has_alpha(im)
    if has_alpha and ext not in ALPHA_CAPABLE_TARGETS:
        thunks.append(lambda: _flatten(im, bg))
    else:
        thunks.append(lambda: im)
        if has_alpha:
            thunks.append(lambda: _flatten(im, bg))
    thunks.extend(
        [
            lambda: im.convert("RGB"),
            lambda: im.convert("RGBA"),
            lambda: im.convert("L"),
            lambda: im.convert("P"),
            lambda: im.convert("1"),
        ]
    )
    return thunks


def _ico_options(im: Image.Image) -> dict:
    """ICO writes fixed size "buckets" and skips any larger than the source, so
    a sub-16px image yields an empty file. Pin an explicit size (capped to the
    256px ICO maximum) so a valid, correctly-sized icon is always written."""
    w, h = im.size
    return {"sizes": [(max(1, min(w, 256)), max(1, min(h, 256)))]}


def _save_static(im: Image.Image, out_path: Path, ext: str, bg) -> None:
    fmt = format_for_ext(ext)
    base_opts = SAVE_OPTIONS.get(ext, {})
    last_error: Exception | None = None
    for make in _renditions(im, bg, ext):
        try:
            rendition = make()
        except Exception as exc:  # a mode conversion can fail; try the next
            last_error = exc
            continue
        opts = dict(base_opts)
        if ext in ("ico",):
            opts.update(_ico_options(rendition))
        try:
            rendition.save(out_path, format=fmt, **opts)
            return
        except Exception as exc:
            last_error = exc
            continue
    raise last_error if last_error else OSError("could not encode image")


def _save_animated(im: Image.Image, out_path: Path, ext: str, bg) -> None:
    """Save every frame of a multi-frame image, falling back to frame 0."""
    fmt = format_for_ext(ext)
    opts = dict(SAVE_OPTIONS.get(ext, {}))

    # Formats whose animated form can carry an alpha channel. For everything
    # else (notably PDF) transparent frames are flattened onto the background.
    alpha_ok = ext in {"webp", "apng", "png", "tiff", "tif", "gif"}
    frames: list[Image.Image] = []
    durations: list = []
    for frame in ImageSequence.Iterator(im):
        # Capture each frame's duration here, from the source frame, before the
        # iterator advances -- reading im.info afterwards would only see the
        # last frame's value and collapse variable timing to a single number.
        durations.append(frame.info.get("duration"))
        if _has_alpha(frame):
            frames.append(frame.convert("RGBA") if alpha_ok else _flatten(frame, bg))
        else:
            frames.append(frame.convert("RGB"))

    if len(frames) <= 1:
        _save_static(im, out_path, ext, bg)
        return

    # Preserve per-frame timing as a list rather than one scalar for all frames.
    if all(d is not None for d in durations):
        opts.setdefault("duration", durations)
    elif "duration" in im.info:
        opts.setdefault("duration", im.info["duration"])
    if "loop" in im.info:
        opts.setdefault("loop", im.info["loop"])

    frames[0].save(
        out_path,
        format=fmt,
        save_all=True,
        append_images=frames[1:],
        **opts,
    )


def _unique_path(path: Path, claimed=None) -> Path:
    """Avoid clobbering an existing file by appending ``_1``, ``_2`` …

    A path counts as taken if it already exists on disk *or* is in ``claimed``
    (targets already written earlier in the same batch run).
    """
    def taken(p: Path) -> bool:
        return p.exists() or (claimed is not None and p.resolve() in claimed)

    if not taken(path):
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not taken(candidate):
            return candidate
        i += 1


def convert_file(
    input_path,
    output_dir,
    target_ext: str,
    *,
    background=DEFAULT_BG,
    keep_animation: bool = True,
    overwrite: bool = False,
    claimed=None,
) -> Path:
    """Convert a single image file to ``target_ext`` inside ``output_dir``.

    Returns the path of the written file. Raises on unreadable input or an
    unwritable target extension. ``claimed`` is an optional set of already-
    written target paths (used by :func:`convert_path` to keep distinct sources
    from overwriting one another within a single batch run).
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    ext = target_ext.lower().lstrip(".")

    if ext not in SAVABLE_EXTS:
        raise ValueError(
            f"'{ext}' is not a format Pillow can write. "
            f"Choose one of: {', '.join(sorted(SAVABLE_EXTS))}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{input_path.stem}.{ext}"

    # Never overwrite the source image itself.
    if out_path.resolve() == input_path.resolve():
        out_path = output_dir / f"{input_path.stem}_converted.{ext}"
    if overwrite:
        # --overwrite may replace files that pre-existed the run, but must not
        # let two distinct in-run sources collapse onto the same output.
        if claimed is not None and out_path.resolve() in claimed:
            out_path = _unique_path(out_path, claimed)
    else:
        out_path = _unique_path(out_path, claimed)

    # Opening/decoding failures mean "not a usable image"; failures while
    # writing mean "this image can't be written as the chosen target". The two
    # are reported to the user as distinct skip reasons.
    try:
        im = Image.open(input_path)
        im.load()  # force decode now so truncated/corrupt files fail here
    except (UnidentifiedImageError, Image.DecompressionBombError,
            OSError, SyntaxError, ValueError) as exc:
        raise NotAnImageError(str(exc)) from exc

    # Write to a temp file next to the target, then rename into place, so a
    # crash or a killed process (e.g. closing the GUI mid-write) can never leave
    # a truncated file at the real destination.
    tmp_path = out_path.with_name(out_path.name + ".part")
    try:
        with im:
            animated = keep_animation and getattr(im, "is_animated", False)
            if animated and ext in ANIMATED_TARGETS:
                try:
                    _save_animated(im, tmp_path, ext, background)
                except Exception:
                    # Any animation-specific failure: fall back to a clean
                    # single-frame conversion rather than producing nothing.
                    im.seek(0)
                    _save_static(im, tmp_path, ext, background)
            else:
                if getattr(im, "is_animated", False):
                    im.seek(0)
                _save_static(im, tmp_path, ext, background)
        os.replace(tmp_path, out_path)
    except Exception as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        # The source opened fine but no rendition could be written as `ext`.
        raise IncompatibleTargetError(
            f"cannot convert to .{ext}: {exc}"
        ) from exc

    return out_path


def convert_path(
    input_path,
    output_dir,
    target_ext: str,
    *,
    background=DEFAULT_BG,
    keep_animation: bool = True,
    overwrite: bool = False,
    recursive: bool = False,
    on_event=None,
) -> ConvertReport:
    """Convert a single file, a list of files, or every image in a folder.

    ``input_path`` may be a file path, a folder path, or a list/tuple of file
    paths (e.g. several images selected in the GUI). ``on_event(kind, result)``
    is an optional callback (kind is ``"ok"``, ``"skip"``) for progress
    reporting. Returns a :class:`ConvertReport` summarising what happened.
    """
    report = ConvertReport(output_dir=Path(output_dir))

    def _emit(result: FileResult):
        report.results.append(result)
        if on_event:
            on_event("ok" if result.ok else "skip", result)

    # Resolve the set of source files.
    if isinstance(input_path, (list, tuple, set)):
        sources = [Path(p) for p in input_path]
    else:
        input_path = Path(input_path)
        if input_path.is_file():
            sources = [input_path]
        elif input_path.is_dir():
            globber = input_path.rglob("*") if recursive else input_path.iterdir()
            sources = sorted(p for p in globber if p.is_file())
        else:
            raise FileNotFoundError(f"No such file or folder: {input_path}")

    claimed: set = set()  # target paths written during this run
    for src in sources:
        if src.is_dir():
            continue  # a sub-folder in a multi-selection: nothing to convert
        try:
            target = convert_file(
                src,
                output_dir,
                target_ext,
                background=background,
                keep_animation=keep_animation,
                overwrite=overwrite,
                claimed=claimed,
            )
            claimed.add(target.resolve())
            _emit(FileResult(source=src, target=target, status=CONVERTED))
        except NotAnImageError as exc:
            _emit(FileResult(source=src, status=NOT_IMAGE, message=str(exc)))
        except (IncompatibleTargetError, ValueError) as exc:
            _emit(FileResult(source=src, status=INCOMPATIBLE, message=str(exc)))
        except Exception as exc:
            # Any other unexpected error: classify as incompatible so the batch
            # keeps going rather than crashing.
            _emit(FileResult(source=src, status=INCOMPATIBLE,
                             message=f"{type(exc).__name__}: {exc}"))

    return report
