"""Small pywin32 loading and VARIANT helpers."""

from __future__ import annotations

import re
from typing import Any, Iterable, Tuple

from .exceptions import PyGcadWinImportError

GSTARCAD_PROGIDS = (
    "GStarCAD.Application.27",
    "GStarCAD.Application.26",
    "GStarCAD.Application",
)
GSTARCAD_PROGID = GSTARCAD_PROGIDS[0]
_GSTARCAD_PROGID_RE = re.compile(r"^(?:Gcad|GStarCAD|GCAD)\.Application(?:\.(\d+))?$")


def load_pywin32() -> Tuple[Any, Any]:
    """Return ``(win32com.client, pythoncom)`` or raise a clear dependency error."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:  # pragma: no cover - depends on host platform
        raise PyGcadWinImportError(
            "pygcadwin live COM automation requires pywin32. "
            "Install it with `pip install pywin32` on Windows."
        ) from exc
    return win32com.client, pythoncom


def gstarcad_prog_id_candidates(prog_id: str = GSTARCAD_PROGID) -> tuple[str, ...]:
    """Return explicit or discovered GstarCAD COM ProgIDs to try."""
    if prog_id != GSTARCAD_PROGID:
        return (prog_id,)
    return _dedupe((*registered_gstarcad_prog_ids(), *GSTARCAD_PROGIDS))


def registered_gstarcad_prog_ids() -> tuple[str, ...]:
    """Return GstarCAD application ProgIDs registered under HKCR."""
    try:
        import winreg
    except ImportError:
        return ()

    found: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "") as root:
            key_count = winreg.QueryInfoKey(root)[0]
            for index in range(key_count):
                name = winreg.EnumKey(root, index)
                if _GSTARCAD_PROGID_RE.match(name):
                    found.append(name)
    except OSError:
        return ()
    return tuple(sorted(found, key=_prog_id_sort_key))


def _prog_id_sort_key(prog_id: str) -> tuple[int, int]:
    base_priority = {
        "GStarCAD.Application": 0,
        "Gcad.Application": 1,
        "GCAD.Application": 2,
    }
    base = prog_id.rsplit(".", 1)[0] if prog_id.rsplit(".", 1)[-1].isdigit() else prog_id
    match = _GSTARCAD_PROGID_RE.match(prog_id)
    has_version = bool(match and match.group(1))
    version = int(match.group(1)) if has_version else 0
    return (0 if has_version else 1, base_priority.get(base, 99), -version)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def variant_array(
    values: Iterable[Any],
    vt_type: int,
    *,
    com_client: Any | None = None,
    pythoncom_module: Any | None = None,
) -> Any:
    """Build a pywin32 COM VARIANT array."""
    if com_client is None or pythoncom_module is None:
        com_client, pythoncom_module = load_pywin32()
    return com_client.VARIANT(pythoncom_module.VT_ARRAY | vt_type, list(values))
