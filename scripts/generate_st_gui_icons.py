"""Generate PNG/ICO assets for the STB GUI (taskbar / title bar icons)."""

from __future__ import annotations

import io
import os
import struct
import zlib

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON_DIR = os.path.join(_ROOT, "stb_gui", "static", "icons")

_PNG_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 192, 256, 512)
_ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _load_font(size: int):
    from PIL import ImageFont

    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = (
        os.path.join(windir, "Fonts", "arialbd.ttf"),
        os.path.join(windir, "Fonts", "segoeuib.ttf"),
        "arialbd.ttf",
        "Arial Bold.ttf",
        "segoeuib.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_icon(size: int):
    from PIL import Image, ImageDraw

    # High-scale draw, then nearest-neighbor downscale for crisp taskbar glyphs.
    scale = 8 if size <= 24 else 6 if size <= 40 else 4 if size <= 64 else 2
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    font = _load_font(max(8, int(round(canvas * 0.5))))
    text = "ST"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = int(round((canvas - tw) / 2 - bbox[0]))
    y = int(round((canvas - th) / 2 - bbox[1]))
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    if scale > 1:
        from PIL import Image as PILImage

        img = img.resize((size, size), PILImage.Resampling.NEAREST)
    return img


def _write_png(path: str, size: int) -> None:
    try:
        img = _render_icon(size)
        img.save(path, format="PNG")
    except ImportError:
        _write_png_fallback(path, size)


def _write_png_fallback(path: str, size: int) -> None:
    row = b"\x00" + b"\x00\x00\x00" * size
    raw = row * size
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def _write_png_ico(path: str, sizes: tuple[int, ...]) -> None:
    """Write a multi-size ICO with embedded PNG frames (Windows Vista+)."""

    png_frames = []
    for size in sizes:
        try:
            img = _render_icon(size)
        except ImportError:
            return
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_frames.append((size, buf.getvalue()))

    if not png_frames:
        return

    count = len(png_frames)
    header = struct.pack("<HHH", 0, 1, count)
    entries = bytearray()
    data = bytearray()
    offset = 6 + 16 * count
    for size, png in png_frames:
        dim = 0 if size >= 256 else size
        entries.extend(struct.pack(
            "<BBBBHHII",
            dim,
            dim,
            0,
            0,
            1,
            32,
            len(png),
            offset,
        ))
        data.extend(png)
        offset += len(png)

    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(entries)
        fh.write(data)


def main():
    os.makedirs(_ICON_DIR, exist_ok=True)
    for size in _PNG_SIZES:
        _write_png(os.path.join(_ICON_DIR, "st-icon-{0}.png".format(size)), size)
    _write_png_ico(os.path.join(_ICON_DIR, "favicon.ico"), _ICO_SIZES)
    print("Icons written to", _ICON_DIR)


if __name__ == "__main__":
    main()
