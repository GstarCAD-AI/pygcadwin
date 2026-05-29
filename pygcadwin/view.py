"""Viewport snapshot support for GstarCAD COM automation."""

from __future__ import annotations

import base64
import struct
import time
import zlib
from pathlib import Path
from typing import Any, Callable

from .exceptions import PyGcadWinError, PyGcadWinImportError


class Snapshot:
    """RGBA viewport capture with stdlib PNG helpers."""

    __slots__ = ("_data", "_png_cache", "width", "height", "size", "mode")

    def __init__(self, data: bytes | bytearray | memoryview, width: int, height: int):
        self._data = bytes(data)
        self._png_cache: bytes | None = None
        self.width = int(width)
        self.height = int(height)
        self.size = (self.width, self.height)
        self.mode = "RGBA"
        expected = self.width * self.height * 4
        if self.width <= 0 or self.height <= 0:
            raise ValueError("snapshot dimensions must be positive")
        if len(self._data) != expected:
            raise ValueError(f"snapshot expected {expected} RGBA bytes, got {len(self._data)}")

    def tobytes(self) -> bytes:
        """Return raw RGBA row-major bytes."""
        return self._data

    def to_png_bytes(self) -> bytes:
        """Return PNG-encoded bytes."""
        if self._png_cache is None:
            self._png_cache = _encode_png_rgba(self.width, self.height, self._data)
        return self._png_cache

    def to_base64(self, data_url: bool = False) -> str:
        """Return base64 PNG text, optionally as a data URL."""
        encoded = base64.b64encode(self.to_png_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}" if data_url else encoded

    def data_url(self) -> str:
        """Return a PNG data URL."""
        return self.to_base64(data_url=True)

    def save(self, path: str | Path | Any, format: str | None = None) -> None:
        """Write the snapshot as PNG."""
        del format
        png = self.to_png_bytes()
        if hasattr(path, "write"):
            path.write(png)
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png)

    def __repr__(self) -> str:
        return f"Snapshot(size={self.width}x{self.height}, mode={self.mode})"


class View:
    """View operations bound to a :class:`pygcadwin.context.Context`."""

    def __init__(self, context: Any):
        self.context = context

    def snapshot(
        self,
        width: int | None = None,
        height: int | None = None,
        *,
        retries: int = 2,
        retry_delay: float = 0.5,
    ) -> Snapshot:
        """Capture the live GstarCAD viewport as a PNG-capable snapshot."""
        capture = getattr(self.context, "_snapshot_capture", None)
        if capture is not None:
            return _snapshot_from_capture(capture, width, height)

        hwnd = _find_application_hwnd(self.context)
        _prepare_hwnd_for_capture(hwnd)
        zoom_extents = getattr(self.context, "zoom_extents", None)
        if callable(zoom_extents):
            try:
                zoom_extents()
                time.sleep(0.25)
            except Exception:
                pass
        attempts = max(1, int(retries) + 1)
        last_snapshot: Snapshot | None = None
        for attempt in range(attempts):
            if attempt:
                time.sleep(max(0.0, float(retry_delay)))
            rgba, actual_width, actual_height = _capture_hwnd_rgba(hwnd)
            target_width, target_height = _resolve_size(width, height, actual_width, actual_height)
            if (target_width, target_height) != (actual_width, actual_height):
                rgba = _resize_rgba_nearest(
                    rgba,
                    actual_width,
                    actual_height,
                    target_width,
                    target_height,
                )
            last_snapshot = Snapshot(rgba, target_width, target_height)
            if not _is_uniform_rgba(rgba):
                return last_snapshot
        assert last_snapshot is not None
        raise PyGcadWinError(
            "Captured GstarCAD screenshot is blank after repaint retries; "
            "restore or maximize the GstarCAD window and retry."
        )


def _snapshot_from_capture(
    capture: Callable[[int | None, int | None], Any],
    width: int | None,
    height: int | None,
) -> Snapshot:
    value = capture(width, height)
    if isinstance(value, Snapshot):
        return value
    if isinstance(value, tuple) and len(value) == 3:
        data, actual_width, actual_height = value
        return Snapshot(data, actual_width, actual_height)
    raise TypeError("_snapshot_capture must return Snapshot or (rgba_bytes, width, height)")


def _resolve_size(
    width: int | None,
    height: int | None,
    actual_width: int,
    actual_height: int,
) -> tuple[int, int]:
    if width is None and height is None:
        return actual_width, actual_height
    if width is None:
        assert height is not None
        width = round(actual_width * (int(height) / actual_height))
    if height is None:
        height = round(actual_height * (int(width) / actual_width))
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("snapshot width and height must be positive")
    return width, height


def _find_application_hwnd(context: Any) -> int:
    owner = getattr(context.document, "_owner", None)
    app = getattr(owner, "_app", None)
    for attr in ("HWND", "Hwnd", "hWnd", "hwnd"):
        value = getattr(app, attr, None)
        if value:
            return int(value)
    raise PyGcadWinError("Could not resolve GstarCAD application window handle for screenshot")


def _prepare_hwnd_for_capture(hwnd: int) -> None:
    try:
        import win32con  # type: ignore
        import win32gui  # type: ignore
    except ImportError:
        return

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        if int(right - left) < 300 or int(bottom - top) < 300:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        win32gui.BringWindowToTop(hwnd)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        win32gui.UpdateWindow(hwnd)
        time.sleep(0.25)
    except Exception:
        pass


def _capture_hwnd_rgba(hwnd: int) -> tuple[bytes, int, int]:
    try:
        import win32con  # type: ignore
        import win32gui  # type: ignore
        import win32ui  # type: ignore
    except ImportError as exc:
        raise PyGcadWinImportError(
            "pygcadwin snapshot capture requires pywin32 modules win32gui and win32ui."
        ) from exc

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = int(right - left)
    height = int(bottom - top)
    if width <= 0 or height <= 0:
        raise PyGcadWinError("GstarCAD client area is empty; cannot capture screenshot")

    hwnd_dc = mem_dc = bitmap = None
    try:
        hwnd_dc = win32gui.GetDC(hwnd)
        src_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        mem_dc = src_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(src_dc, width, height)
        mem_dc.SelectObject(bitmap)
        mem_dc.BitBlt((0, 0), (width, height), src_dc, (0, 0), win32con.SRCCOPY)
        bgra = bitmap.GetBitmapBits(True)
        return _bgra_bottom_up_to_rgba(bytes(bgra), width, height), width, height
    finally:
        if bitmap is not None:
            win32gui.DeleteObject(bitmap.GetHandle())
        if mem_dc is not None:
            mem_dc.DeleteDC()
        if hwnd_dc is not None:
            win32gui.ReleaseDC(hwnd, hwnd_dc)


def _is_uniform_rgba(data: bytes) -> bool:
    if len(data) < 4:
        return True
    first = data[:4]
    return all(data[index : index + 4] == first for index in range(4, len(data), 4))


def _bgra_bottom_up_to_rgba(data: bytes, width: int, height: int) -> bytes:
    stride = width * 4
    out = bytearray(len(data))
    for y in range(height):
        src_row = height - 1 - y
        src_offset = src_row * stride
        dst_offset = y * stride
        row = data[src_offset : src_offset + stride]
        for x in range(width):
            b, g, r, a = row[x * 4 : x * 4 + 4]
            out[dst_offset + x * 4 : dst_offset + x * 4 + 4] = bytes((r, g, b, a))
    return bytes(out)


def _resize_rgba_nearest(data: bytes, src_w: int, src_h: int, dst_w: int, dst_h: int) -> bytes:
    out = bytearray(dst_w * dst_h * 4)
    for y in range(dst_h):
        src_y = min(src_h - 1, int(y * src_h / dst_h))
        for x in range(dst_w):
            src_x = min(src_w - 1, int(x * src_w / dst_w))
            src = (src_y * src_w + src_x) * 4
            dst = (y * dst_w + x) * 4
            out[dst : dst + 4] = data[src : src + 4]
    return bytes(out)


def _encode_png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    rows = bytearray()
    stride = width * 4
    for y in range(height):
        rows.append(0)
        rows.extend(rgba[y * stride : (y + 1) * stride])
    compressed = zlib.compress(bytes(rows), 6)

    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
