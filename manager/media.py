"""Bounded, cross-platform preparation of personal replacement media."""

import io
import math
from pathlib import Path
import re
import warnings

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError


MAX_PIXELS = 16_000_000
MAX_DIMENSION = 8192
MAX_SOURCE_BYTES = 64 * 1024 * 1024
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP", "BMP", "GIF", "TIFF"}


def _dimensions(width, height):
    if (type(width) is not int or type(height) is not int or
            not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION or
            width * height > MAX_PIXELS):
        raise ValueError("Image dimensions must be positive, at most 8192 per side and 16 million pixels.")


def _percent(value, label, low, high):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or not low <= value <= high):
        raise ValueError("{} must be a finite number between {} and {}.".format(label, low, high))
    return float(value)


def _remove_green(image):
    red, green, blue, alpha = image.split()
    other = ImageChops.lighter(red, blue)
    excess = ImageChops.subtract(green, other)
    strength = excess.point(lambda value: 255 if value <= 40 else max(0, round(255 * (110 - value) / 70)))
    alpha = ImageChops.multiply(alpha, strength)
    green = Image.composite(other, green, excess.point(lambda value: 255 if value > 40 else 0))
    return Image.merge("RGBA", (red, green, blue, alpha))


def _harden_alpha(image):
    red, green, blue, alpha = image.split()
    edges = alpha.point(lambda value: 255 if 0 < value < 255 else 0)
    green = Image.composite(ImageChops.darker(green, ImageChops.lighter(red, blue)), green, edges)
    return Image.merge("RGBA", (red, green, blue, alpha.point(lambda value: 255 if value >= 128 else 0)))


def compose_image(source: Path, target: dict, scale: float = 100, top: float = 0,
                  offset_x: float = 0, remove_green: bool = False) -> bytes:
    """Return a PNG fitted top-center, with offsets relative to canvas dimensions.

    Transparent borders are trimmed before fitting. Green canvases use hard alpha
    edges to avoid halos in the game's chroma-key material. Nothing is written.
    """
    width, height = target.get("width"), target.get("height")
    _dimensions(width, height)
    background = target.get("background", "transparent")
    if background not in ("transparent", "green"):
        raise ValueError("Image background must be transparent or green.")
    scale = _percent(scale, "Scale", 1, 500)
    top = _percent(top, "Top offset", -200, 200)
    offset_x = _percent(offset_x, "Horizontal offset", -200, 200)
    if type(remove_green) is not bool:
        raise ValueError("Remove green must be a boolean.")
    try:
        source = Path(source)
        if source.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("Source image exceeds the 64 MiB limit.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as opened:
                _dimensions(*opened.size)
                if opened.format not in SUPPORTED_FORMATS:
                    raise ValueError("Unsupported image format. Use PNG, JPEG, WebP, BMP, GIF or TIFF.")
                image = ImageOps.exif_transpose(opened).convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValueError("Cannot read this image: {}".format(exc)) from exc
    if remove_green:
        image = _remove_green(image)
    bounds = image.getchannel("A").point(lambda value: 255 if value > 16 else 0).getbbox()
    if bounds:
        image = image.crop(bounds)
    if background == "green":
        image = _harden_alpha(image)
    fit = min(width / image.width, height / image.height) * scale / 100
    resized_width = max(1, round(image.width * fit))
    resized_height = max(1, round(image.height * fit))
    _dimensions(resized_width, resized_height)
    image = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height))
    x = round((width - resized_width) / 2 + width * offset_x / 100)
    y = round(height * top / 100)
    canvas.alpha_composite(image, (x, y))
    if background == "green":
        canvas = _harden_alpha(canvas)
        green = Image.new("RGBA", (width, height), (0, 255, 0, 255))
        canvas = Image.alpha_composite(green, canvas)
    result = io.BytesIO()
    canvas.save(result, format="PNG")
    return result.getvalue()


def video_targets(data: bytes) -> list[str]:
    """Extract safe, unique Bacchus/Movie/*.mp4 paths from VIDEOS.txt."""
    if not isinstance(data, bytes) or len(data) > 2 * 1024 * 1024:
        raise ValueError("Video list must be UTF-8 data under 2 MiB.")
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("Video list is not UTF-8.") from exc
    paths = []
    seen = set()
    for line in lines:
        path = line.strip()
        if not path or not (path.startswith(("Bacchus/", "/Bacchus/", "./Bacchus/")) or
                               path.lower().endswith(".mp4")):
            continue
        parts = path.split("/")
        if (not re.fullmatch(r"Bacchus/Movie/(?:[A-Za-z0-9_ .-]+/)*[A-Za-z0-9_ .-]+\.mp4", path) or
                any(part in (".", "..") or part.endswith((".", " ")) for part in parts)):
            raise ValueError("Unsafe or unsupported video target: {}".format(path))
        if path.casefold() not in seen:
            paths.append(path)
            seen.add(path.casefold())
    return paths
